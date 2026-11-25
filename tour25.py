"""v2.5 helpers: classification evidence, explicit review decisions, share metadata, private CSV."""
import csv, difflib, html, json, pathlib, re, collections, urllib.parse

LCLS=('lclsSystm1','lclsSystm2','lclsSystm3')

def classification(row):
    # Keep all levels verbatim except surrounding whitespace, no invented codes.
    return {k:str(row.get(k) or '').strip()[:80] for k in LCLS}

def shopping_code(r, legacy):
    a,b,c=(str(r.get(k) or '').strip().upper() for k in LCLS)
    if any((a,b,c)):
        # SH = shopping. Require a populated, consistent hierarchy; the strict
        # mall-name rule and pet evidence are separate gates, not code inference.
        return a=='SH' and bool(re.fullmatch(r'SH[A-Z0-9]+',b)) and len(c)>len(b) and c.startswith(b) and bool(re.fullmatch(r'[A-Z0-9]+',c))
    return r.get('cat3') in legacy

def new_distribution(records):
    rows=[r for r in records if str(r.get('type'))=='38']
    return {'type38_lclsSystm':{'/'.join(k):n for k,n in sorted(collections.Counter(tuple(str(r.get(f) or '(empty)') for f in LCLS) for r in rows).items())}}

def _strict_pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate override key: '+k)
        d[k]=v
    return d

def load_overrides(src,records,places,eligible,compatible,region):
    path=src/'tour-match-overrides.json'
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=_strict_pairs)
    if not isinstance(data,dict):raise ValueError('tour-match-overrides.json must be an object')
    byid={p['id']:p for p in places}; bycid={r['contentId']:r for r in records}; claimed=set(); active={}
    for cid,target in data.items():
        if not re.fullmatch(r'\d{1,12}',cid) or not isinstance(target,str) or not (target in ('new','skip') or re.fullmatch(r'p\d+',target)):
            raise ValueError('invalid override: '+str(cid))
        if cid not in bycid:
            print('TourAPI override inactive (not in current snapshot):',cid);continue
        r=bycid[cid]
        if target!='skip' and not eligible(r):raise ValueError('override cannot bypass category/pet evidence: '+cid)
        if target not in ('new','skip'):
            p=byid.get(target)
            if not p or target.startswith('f') or set(p.get('services') or []) & {'동물병원','장례·추모'} or not compatible(r,p) or p.get('sido')!=region(r['address']):
                raise ValueError('invalid or incompatible override target: '+cid+' -> '+target)
            if target in claimed:raise ValueError('duplicate override target: '+target)
            claimed.add(target)
        active[cid]=target
    return active

def review_csv(path,records,places,audit,point,km,clean_name):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    byid={p['id']:p for p in places};bycid={r['contentId']:r for r in records}
    headers=['contentId','관광공사명','관광공사 주소','후보 placeId','후보업체명','후보업체 주소','거리(m,정확좌표)','이름 유사도(%)','관광공사 허용사진','후보 자체/관광사진','후보수','결정(placeId/new/skip)']
    def safe(x):
        if isinstance(x,str) and x.lstrip().startswith(('=','+','-','@')):return "'"+x
        return x
    count=0; cases=0
    tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(headers)
        for a in audit:
            if a['status']!='manual-review':continue
            cases+=1;r=bycid[a['contentId']];candidates=a.get('candidates') or ['']; rows=[]
            for pid in candidates:
                p=byid.get(pid,{})
                x,y=point(r.get('lng'),r.get('lat'));u,v=point(p.get('lng'),p.get('lat'))
                d=round(km(x,y,u,v)*1000,1) if x is not None and u is not None and p.get('geoPrecision')=='exact' else ''
                sim=round(100*difflib.SequenceMatcher(None,clean_name(r['name']),clean_name(p['name']),autojunk=False).ratio(),1) if p else ''
                rows.append([r['contentId'],r['name'],r['address'],pid,p.get('name',''),p.get('roadAddress') or p.get('address',''),d,sim,'Y' if r.get('images') else 'N','Y' if p.get('tourPhoto') or p.get('ownerPhoto') else 'N',len(a.get('candidates') or []),''])
            for row in sorted(rows,key=lambda z:(z[6] if isinstance(z[6],(float,int)) else float('inf'),-(z[7] or 0),z[3])):w.writerow([safe(x) for x in row]);count+=1
    tmp.replace(path);return cases,count

def share_photo(p,base):
    """Only share approved local photos or licensed Type1; Type3 can be cropped by SNS."""
    if '장례·추모' in (p.get('services') or []):return None
    owner=p.get('ownerPhoto') or {};src=str(owner.get('src') or '')
    if re.fullmatch(r'/approved-photos/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)',src):
        return base+src, f"{owner.get('label','승인 사진')} · {owner.get('credit','')}"
    for ph in [p.get('tourPhoto') or {}]+list(p.get('tourPhotos') or []):
        if str(ph.get('license'))!='1':continue
        u=urllib.parse.urlsplit(str(ph.get('src') or ''))
        if u.scheme=='https' and u.hostname and (u.hostname=='visitkorea.or.kr' or u.hostname.endswith('.visitkorea.or.kr')) and not (u.username or u.password or u.query or u.fragment or u.netloc!=u.hostname):
            return u.geturl(),'한국관광공사 · 공공누리 1유형'
    return None

def share_tags(p,base):
    ph=share_photo(p,base)
    if not ph:return ''
    E=lambda v:html.escape(str(v),quote=True)
    return '<meta property="og:image:alt" content="'+E(p['name']+' · '+ph[1])+'"><meta name="twitter:image" content="'+E(ph[0])+'"><meta name="twitter:image:alt" content="'+E(p['name']+' · '+ph[1])+'">'
