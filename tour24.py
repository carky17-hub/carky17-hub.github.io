"""Conservative TourAPI matching and presentation. No network access here."""
import collections, difflib, html, math, re, unicodedata
from tour25 import shopping_code,new_distribution

BASE_TYPES={'12','14','28','32','39'}
# A04010600 includes individual shops too; never accept the code alone.
MALL_CODE={'A04010300','A04010600'}
MALL_NAME=re.compile(r'^(?:스타필드(?:시티)?(?:\s*[가-힣0-9]{1,8})?|(?:롯데|현대|신세계|갤러리아|AK|NC)\s*(?:프리미엄\s*)?(?:백화점|아울렛|아웃렛|쇼핑몰|몰)(?:\s*[가-힣0-9]{1,8})?|(?:더현대|타임스퀘어|코엑스몰|아이파크몰|IFC몰|커넥트현대|메세나폴리스|마리오아울렛)(?:\s*[가-힣0-9]{1,8})?|신세계사이먼\s*(?:[가-힣]{1,6}\s*)?프리미엄아울렛(?:\s*[가-힣0-9]{1,8})?)$',re.I)
TENANT=re.compile(r'\d+\s*(?:층|호)|매장|지하|식당|카페|약국|마트|편의점|면세점|올리브영|나이키|아디다스|유니클로|다이소|팝업|주차장|푸드코트|영화관',re.I)
NEG=re.compile(r'동반\s*(?:불가|금지|불가능)|입장\s*(?:불가|금지|불가능)|반려동물\s*금지|미동반|동반\s*가능\s*(?:여부|하지\s*않)|입장\s*가능\s*여부')
POS=re.compile(r'(?:동반|입장)\s*(?:이\s*)?가능|동반\s*허용|반려동물\s*동반\s*가능|일부\s*구역\s*가능')

def shopping_candidate(r):
    if str(r.get('type'))!='38' or not shopping_code(r,MALL_CODE):return False
    name=unicodedata.normalize('NFKC',str(r.get('name') or '')).strip()
    return bool(MALL_NAME.fullmatch(name) and not TENANT.search(name) and not TENANT.search(str(r.get('address') or '')))

def shopping_state(r):
    if not shopping_candidate(r):return 'excluded'
    pet=r.get('pet') or {}
    text=' '.join(str(pet.get(k) or '') for k in ('acmpyTypeCd','acmpyPsblCpam','acmpyNeedMtr','relaAcdntRiskMtr','etcAcmpyInfo'))
    if NEG.search(text):return 'restricted-review'
    if r.get('detailDone') and POS.search(text):return 'eligible'
    return 'pending-pet-evidence'

def collect_detail(r):return str(r.get('type')) in BASE_TYPES or shopping_candidate(r)
def eligible(r):return str(r.get('type')) in BASE_TYPES or shopping_state(r)=='eligible'

def shopping_report(records):
    rows=[r for r in records if str(r.get('type'))=='38']; buckets={}
    for r in rows:
        k=str(r.get('cat3') or '(empty)');b=buckets.setdefault(k,{'records':0,'eligible':0,'pending-pet-evidence':0,'restricted-review':0,'excluded':0,'snapshot_image_records':0});b['records']+=1;b[shopping_state(r)]+=1;b['snapshot_image_records']+=bool(r.get('images'))
    return {**new_distribution(records),'type38_records':len(rows),'type38_cat3':dict(sorted(buckets.items())),'type38_candidate_records':sum(shopping_candidate(r) for r in rows),'type38_eligible_records':sum(shopping_state(r)=='eligible' for r in rows)}

def clean_name(s):
    s=unicodedata.normalize('NFKC',str(s or '')).lower().strip()
    s=re.sub(r'^(?:\(주\)|주식회사|㈜)\s*|\s*(?:\(주\)|주식회사|㈜)$','',s)
    return re.sub(r'[^0-9a-z가-힣]','',s)

def road_building(addr):
    # Require the same road and full main/sub building number; don't strip branch names.
    s=unicodedata.normalize('NFKC',str(addr or ''))
    m=re.search(r'([가-힣0-9·.]+(?:대로|로|길))\s*(\d+(?:-\d+)?)(?![\d-])',s)
    return (m.group(1),m.group(2)) if m else None

def unit(addr):
    s=str(addr or '');return set(re.findall(r'(?:지하\s*\d+\s*층|\d+\s*(?:층|호))',s))

def compatible(r,p):
    services=set(p.get('services') or [p.get('category')]);t=str(r['type'])
    if t=='39':return bool(services & {'식당','카페','애견카페'})
    if t=='32':return '숙소' in services
    return bool(services & {'여행지','놀이터'})

class Matcher:
    def __init__(self,places,region,addrkey,point,km,norm):
        self.region,self.addrkey,self.point,self.km,self.norm=region,addrkey,point,km,norm
        self.names=collections.defaultdict(list);self.addresses=collections.defaultdict(list);self.cells=collections.defaultdict(list)
        for p in places:self.add(p)
    def cell(self,a,b):return math.floor(a/.002),math.floor(b/.002)
    def add(self,p):
        if str(p['id']).startswith('f'):return
        si=p.get('sido');ad=p.get('roadAddress') or p.get('address')
        self.names[si,self.norm(p['name'])].append(p);self.addresses[si,self.addrkey(ad)].append(p)
        a,b=self.point(p.get('lng'),p.get('lat'))
        if a is not None and p.get('geoPrecision')=='exact':self.cells[self.cell(a,b)].append(p)
    def match(self,r,strict=False):
        si=self.region(r['address']);ak=self.addrkey(r['address']);n=self.norm(r['name']);a,b=self.point(r.get('lng'),r.get('lat'))
        exactname=self.names[si,n];sameaddr=self.addresses[si,ak];pool={p['id']:p for p in exactname+sameaddr};near=[]
        if a is not None:
            x,y=self.cell(a,b)
            for dx in range(-2,3):
                for dy in range(-2,3):
                    for p in self.cells[x+dx,y+dy]:
                        if p.get('sido')==si and self.km(a,b,p['lat'],p['lng'])<=.15:near.append(p)
        exact=[];fuzzy=[]
        for p in near:
            ad=p.get('roadAddress') or p.get('address');same=self.addrkey(ad)==ak
            pn=self.norm(p['name']);d=self.km(a,b,p['lat'],p['lng'])
            if pn==n and same and unit(r['address'])==unit(ad):
                # Preserve the prior exact match, except medical/funeral conflicts and claimed rows.
                if not set(p.get('services') or []) & {'동물병원','장례·추모'} and (str(r['type'])!='38' or compatible(r,p)):
                    exact.append((p,1.,d))
                continue
            if strict:continue
            x,y=clean_name(r['name']),clean_name(p['name']);sim=difflib.SequenceMatcher(None,x,y,autojunk=False).ratio()
            ra,pa=road_building(r['address']),road_building(ad);ua,ub=unit(r['address']),unit(ad)
            # Candidate is not proof. Keep similar nearby rows in review even if address differs.
            if sim>=.78 and min(len(x),len(y))>=4:pool[p['id']]=p
            if not compatible(r,p) or not (same or ra and ra==pa) or ua!=ub or not min(len(x),len(y))>=5:continue
            if re.findall(r'\d+',x)!=re.findall(r'\d+',y):continue
            if x!=y and (x.endswith('점') or y.endswith('점')):continue
            # For nonidentical names require high similarity; no prefix-only/substring acceptance.
            if sim>=.92 or x==y:fuzzy.append((p,sim,d))
        def result(rows,method):
            if len(rows)!=1:return None
            p,s,d=rows[0]
            if p.get('tourism'):return None
            return p,{'matchMethod':method,'nameSimilarity':round(s,4),'distanceM':round(d*1000,1)}
        if exact:
            found=result(exact,'exact')
            if found:return found[0],found[1],[]
            return None,{},[p['id'] for p,_,_ in exact]
        if fuzzy and not strict:
            # More than one qualifying candidate -> manual. Also block a different near-identical name at same address.
            found=result(fuzzy,'name-address-distance')
            if found and not any(p['id']!=found[0]['id'] for p in exactname):return found[0],found[1],[]
        return None,{},sorted(pool)

def detail_html(p,labels,source):
    E=lambda x:html.escape(str(x or ''),quote=True)
    t=p.get('tourism') or {};pet=t.get('pet') or {}
    if not t:return ''
    keys=['acmpyTypeCd','acmpyPsblCpam','acmpyNeedMtr','relaAcdntRiskMtr','etcAcmpyInfo']+[k for k in labels if k not in ('acmpyTypeCd','acmpyPsblCpam','acmpyNeedMtr','relaAcdntRiskMtr','etcAcmpyInfo')]
    known=[k for k in keys if str(pet.get(k) or '').strip() not in ('','-','미확인','정보 없음')]
    photos=list(p.get('tourPhotos') or [])[:5]
    h='<section class="panel tour-info" id="tour-pet-info"><h2>한국관광공사 동반 여행 정보</h2><p class="muted">한국관광공사 등록 · 자료 조회일 '+E(t.get('checkedOn'))+' · <a href="'+E(source)+'">원자료</a> · 방문 전 확인해 주세요.</p>'
    if known:h+='<dl class="tour-pet-facts">'+''.join('<dt>'+E(labels[k])+'</dt><dd>'+E(pet[k])+'</dd>' for k in known if k in labels)+'</dl>'
    else:h+='<p>상세 동반 조건은 아직 수집되지 않았습니다. 방문 전 동반 가능 구역, 이동장·목줄 조건을 직접 확인해 주세요.</p>'
    if str(p.get('subType'))=='쇼핑·복합몰':h+='<p class="notice">복합몰 공용부와 개별 매장의 반려동물 동반 정책은 다를 수 있습니다.</p>'
    h+='</section>'
    if photos:
        h+='<section class="panel tour-gallery" id="tour-gallery"><h2>한국관광공사 제공 사진 <small>'+str(len(photos))+'장</small></h2><p class="muted">좌우로 넘겨 보세요.</p><div class="tour-gallery-track" tabindex="0" role="region" aria-label="관광공사 사진 갤러리">'
        for ph in photos:
            h+='<figure><a href="'+E(ph['src'])+'" target="_blank" rel="noopener noreferrer"><img loading="lazy" decoding="async" src="'+E(ph['src'])+'" alt="'+E(ph.get('caption') or '한국관광공사 제공 사진')+'"></a><figcaption>한국관광공사 · <a href="'+E(source)+'">출처</a> · <a href="https://www.kogl.or.kr/info/license.do">공공누리 '+E(ph['license'])+'유형</a><br>'+E(ph.get('caption'))+'</figcaption></figure>'
        h+='</div></section>'
    return h
