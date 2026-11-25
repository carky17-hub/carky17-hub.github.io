import json, pathlib, collections, re, html, os, math, urllib.parse, shutil, hashlib
from source_data import load_source
from search_routing import encode as route_encode
from images26 import carousel as photo_carousel, prioritize as prioritize_photos, sitemap_xml, image_candidates
from xml.sax.saxutils import escape as xml_escape
ROOT=pathlib.Path(__file__).resolve().parent; SITE=ROOT/'site'; SRC=ROOT/'source'; BASE=None
from settings import SITE_URL as BASE, ALLOW_INDEXING, FORMS_LIVE as ENABLE_FORMS, NAVER_VERIFICATION, GOOGLE_VERIFICATION, POLICY_VERSION, ENABLE_ADFIT, ADFIT_MID, ADFIT_BOTTOM, ENABLE_KAKAO_LINKS, CONTACT_EMAIL
PREVIEW=not ALLOW_INDEXING
assert BASE.startswith('https://') and urllib.parse.urlsplit(BASE).netloc and not urllib.parse.urlsplit(BASE).path
from tourapi import integrate as tour_integrate, report as tour_report, PET, SOURCE as TOUR_SOURCE
from tour24 import detail_html as tour_detail_html, clean_name
from tour25 import review_csv, share_photo, share_tags
from tourapi import read as tour_read, point as tour_point, km as tour_km
from art23 import SCENES, BASE as ART_BASE
from cards22 import annotate as own_ratings, card as card22, rating as rating22, curated as curated22
from v13 import funeral_places,funeral_seo,match,extra_paths,content,detail_content,publish_pages,funeral_cta,funeral_actions,fee_notice,is_funeral,neutral_key,reject_funeral_overlays,ROLE,DISCLOSURE,PRIVACY_TEXT
# v1.3.2 neutral funeral integration
A=load_source(SRC/'places-all.json');
A+=funeral_places(SRC,A)
tour_audit=tour_integrate(SRC,A)
assert all(p.get('geoSource') in (None,'public-data','소상공인시장진흥공단 상가(상권)정보 2026-09') and not p.get('kakaoPlaceId') and not p.get('kakaoMapUrl') and (not p.get('roadAddress') or p.get('geoSource')=='소상공인시장진흥공단 상가(상권)정보 2026-09') for p in A), 'Unexpected v7 coordinate/address provenance'
if not ENABLE_KAKAO_LINKS:
 for p in A:p['kakaoPlaceId']=None;p['kakaoMapUrl']=None
from admin import load_inputs,apply,schedules,premium_html,active
from hospital import annotate,hospital_badges,telephone,maps
from review_integrations import score,load_ids,config as review_config,detail as review_detail,SCORE_HTML,SEARCH_HTML,PRIVACY as REVIEW_PRIVACY,TERMS as REVIEW_TERMS
from settings import ADS_POLICY_APPROVED, RELEASE_MODE
from operations import annotate as ops_annotate,rank as ops_rank,compact_index,config as analytics_config,PRIVACY as ANALYTICS_PRIVACY
from owner_photos import load_owner_photos,cover as photo_cover,gallery as owner_gallery
from policies import identity,business_lines,business_html,adfit_notice
admin_snapshot=load_inputs(); reject_funeral_overlays(admin_snapshot,A); correction_count=apply(A,admin_snapshot); annotate(A,SRC)
for p in A:p["infoCompleteness"]=score(p)
(ROOT/'build-admin-snapshot.json').write_text(json.dumps(admin_snapshot,ensure_ascii=False),encoding='utf-8')
from region_rules import dong_key,display_services,seo_pages,recount,indexable,GROUPS
SEO,ALIAS_REDIRECTS=seo_pages(load_source(SRC/'seo-pages.json')+funeral_seo(A)); assert len(set(p['id'] for p in A))==len(A)
MERGED=load_source(SRC/'merged-ids.json'); IDS={p['id'] for p in A}
GOOGLE_IDS=load_ids(SRC,IDS); REVIEW_CONFIG=review_config(); ops_annotate(A,SRC,GOOGLE_IDS,MERGED); ANALYTICS_ENDPOINT=analytics_config()
assert not (IDS & MERGED.keys()) and set(MERGED.values()) <= IDS
assert all(re.fullmatch(r'[pf]\d+',i) for i in IDS | MERGED.keys())
# Clear generated pages and data on rebuild; preserve only hand-authored assets.
for f in SITE.iterdir():
 if f.is_dir():shutil.rmtree(f)
 elif f.name not in {'app.js','map.js','kakao-map.js','style.css','og-brand.png','brand.svg','ui.js','sw.js','manifest.webmanifest','icon-192.png','icon-512.png','icon-maskable.png','offline.html','adfit.js','hours.js','v13.css','contribute.js','nearby.js','v15.js','pwa.js','external-reviews.js','naver-search.js','search.js','search-ui.js','search-worker.js','analytics.js','compare.js','CNAME','hours.js'}:f.unlink()
KAKAO_JS_KEY=os.environ.get('KAKAO_JS_KEY','').strip()
assert not KAKAO_JS_KEY or re.fullmatch(r'[A-Za-z0-9_-]{10,128}',KAKAO_JS_KEY), 'Invalid Kakao JS key'
reviews,photos=content(SRC,SITE,IDS,MERGED)
owner_photos=load_owner_photos(SRC,A,MERGED,SITE)
own_ratings(A,reviews)
(SITE/'bundle.css').write_text('\n'.join(line.strip() for f in (SITE/'style.css',SITE/'v13.css') for line in f.read_text(encoding='utf-8').splitlines() if line.strip()),encoding='utf-8')
for name,assets in [('core.js',('hours.js','v15.js','ui.js','pwa.js','analytics.js','compare.js')),('discovery.js',('search.js','app.js','search-ui.js'))]:
 (SITE/name).write_text(('globalThis.EGAnalyticsEndpoint='+json.dumps(ANALYTICS_ENDPOINT)+';\n' + 'globalThis.EGKakaoKey='+json.dumps(KAKAO_JS_KEY)+';\n' if name=='core.js' else 'globalThis.EGArt23='+json.dumps({'base':ART_BASE,'scenes':SCENES},ensure_ascii=False)+';\n')+'\n;\n'.join((SITE/asset).read_text(encoding='utf-8') for asset in assets),encoding='utf-8')
ASSET_HASH=hashlib.sha256(b''.join(f.read_bytes() for f in sorted(SITE.glob('*.js'))+sorted(SITE.glob('*.css')))).hexdigest()[:16]
E=lambda x:html.escape(str(x if x is not None else ''),quote=True)
def fmt(x):
 if x is None or x=='':return '확인 필요'
 if isinstance(x,bool):return '가능' if x else '불가'
 if isinstance(x,list):return ', '.join(map(str,x)) or '확인 필요'
 return str(x)
def coord(p):return p.get('geoPrecision')=='exact' and all(type(p.get(k)) in (float,int) and math.isfinite(p[k]) and p[k]!=0 and abs(p[k])<=lim for k,lim in [('lat',90),('lng',180)])
def approx(p):return p.get('geoPrecision') in ('dong','sigungu')
def status(p):return '정확 좌표' if coord(p) else '대략 위치' if approx(p) else '지도 위치 미확인'
def url(path):return BASE+urllib.parse.quote(path,safe='/-._~')
def write(path,content):
 assert not '..' in pathlib.PurePosixPath(path).parts
 if path.endswith('.html'):
  content=prioritize_photos(content)
  content=re.sub(r'((?:src|href)="/(?:core|discovery|bundle)\.(?:js|css))"',lambda m:m[1]+'?v='+ASSET_HASH+'"',content)
 f=SITE/path.lstrip('/');f.parent.mkdir(parents=True,exist_ok=True);f.write_text(content,encoding='utf-8')
def dump(path,x):write(path,json.dumps(x,ensure_ascii=False,separators=(',',':')))
def jsld(x):return '<script type="application/ld+json">'+json.dumps(x,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+'</script>'
def social(title,desc,path,photo=None):
 vals={'og:title':title,'og:description':desc,'og:url':url(path),'og:image':photo[0] if photo else url('/og-brand.png'),'og:type':'website'}
 return ''.join(f'<meta property="{k}" content="{E(v)}">' for k,v in vals.items())+'<meta name="twitter:card" content="summary_large_image">'+f'<meta name="naver-site-verification" content="{E(NAVER_VERIFICATION)}"><meta name="google-site-verification" content="{E(GOOGLE_VERIFICATION)}">'
def head(title,desc,path,ld=None,noindex=False,place=None):return f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(url(path))}">'+social(title,desc+(" · "+share_photo(place,BASE)[1] if place and share_photo(place,BASE) else ""),path,share_photo(place,BASE) if place else None)+(share_tags(place,BASE) if place else "")+('<meta name="robots" content="noindex,follow">' if noindex or PREVIEW else '')+'<link rel="stylesheet" href="/bundle.css"><link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#F26B1D"><link rel="apple-touch-icon" href="/icon-192.png"><meta name="apple-mobile-web-app-capable" content="yes"><script src="/core.js" defer></script>'+(''.join(jsld(x) for x in ld) if isinstance(ld,list) else jsld(ld) if ld else '')

TIP='공공 목록에 등재됐다는 뜻이며 모든 조건을 보증하지 않음'
BADGES=[('식약처 공식 인증','mint'),('등록업체','registry'),('공공데이터','public'),('제보','report')]
def tier(p):
 tags=p.get('tags') or []
 if '식약처 인증' in tags:return 0
 if '등록업체' in tags:return 1
 if any(x in str(p.get('source') or '') for x in ('식약처','농림축산식품부','한국문화정보원','공공데이터','한국관광공사')):return 2
 return 3
def badge(p):
 t=tier(p);label,cls=BADGES[t];tip=TIP if t<3 else '이용자 제보 또는 공공 목록 미확인 정보이며 모든 조건을 보증하지 않음'
 return f'<span class="tag {cls} source-badge" tabindex="0" title="{E(tip)}" aria-label="{E(label+": "+tip)}">{E(label)}</span>' 
def placepath(p):return '/place/'+p['id']+'/'
def regionpath(s):return s['path'].rstrip('/')+'/'
def services(p):return ' · '.join(p['services'])
def row(p):return f'<li class="seo-row"><a href="{E(placepath(p))}"><strong>{E(p["name"])}</strong></a> {badge(p)} <span class="tag">{E(services(p))}</span><div class="muted">{E(p.get("address") or " ".join(filter(None,[p.get("sido"),p.get("sigungu"),p.get("dong")])) or "주소 미확인")} · {status(p)}</div>'+('<div class="hospital-badges">'+hospital_badges(p)+'</div>' if p.get("hours24Data") or p.get("nightEmergencySource") else "")+(f'<a class="btn hospital-call" href="tel:{E(telephone(p.get("phone")))}">📞 병원에 전화</a>' if "동물병원" in p["services"] and telephone(p.get("phone")) else "")+(f'<small>정보 충실도 {p["infoCompleteness"]}/100 · 리뷰는 상세에서 확인</small>' if p['infoCompleteness'] is not None else '')+'</li>'
def listld(rows):return {'@context':'https://schema.org','@type':'ItemList','numberOfItems':len(rows),'itemListElement':[{'@type':'ListItem','position':i,'name':p['name'],'url':url(placepath(p))} for i,p in enumerate(rows,1)]}
NAV='<header><div class="wrap nav"><a class="logo" href="/"><span class="mark"><img src="/brand.svg" width="36" height="36" alt=""></span>어디가개</a><nav class="links"><a href="/#explore">장소 찾기</a><a href="/regions/">지역별 장소</a><a href="/owner/pricing/">사장님 상품</a></nav><a class="btn primary nav-cta" href="/owner/">무료 입점</a></div></header>'
FOOT='<footer><div class="wrap"><b>어디가개</b> · 공공 목록 등재는 모든 동반 조건을 보증하지 않습니다. 방문 전 업체에 확인해 주세요.<br><a href="/privacy/">개인정보처리방침</a> · <a href="/terms/">이용약관</a> · <a href="/sources/">데이터 출처</a> · <a href="/?launch=1#launch">출시 알림</a> · <a href="/owner/pricing/">광고 상품</a> · <button class="text-button" data-install>앱 설치 안내</button></div></footer>'

if not ENABLE_FORMS:FOOT=FOOT.replace(' · <a href="/?launch=1#launch">출시 알림</a>','')
FOOT=FOOT.replace('<br>','<br>'+business_html()+'<br>',1).replace('<a href="/sources/">데이터 출처</a>','<a href="/sources/">데이터 출처</a> · <a href="/privacy/#adfit">맞춤형 광고 안내</a> · <a href="/owner/terms-ads/">광고 이용계약서</a>')

FOOT=FOOT.replace('<a href="/sources/">데이터 출처</a>','<a href="/sources/">데이터 출처</a> · <a href="/funeral/">장례·추모</a> · <a href="/review-policy/">후기·사진 운영 원칙</a>')
def page(path,title,desc,body,ld=None,noindex=False,place=None):write(path+'index.html','<!doctype html><html lang="ko"><head>'+head(title,desc,path,ld,noindex,place)+'</head><body>'+NAV+'<main class="wrap detail">'+body+'</main>'+FOOT+'</body></html>')
# shard generation; preserve source fields and categories
search_routes={}
regions=sorted(set(p.get('sido') or '지역 미확인' for p in A),key=lambda r:(r!='서울특별시',r=='지역 미확인',r)); cats=['식당','카페','숙소','여행지','놀이터','동물병원','미용','호텔·유치원','장례·추모']; groups=collections.defaultdict(list)
for p in A:groups[p.get('sido') or '지역 미확인',('카페' if p['category']=='애견카페' else p['category'])].append(p)
fields=['id','name','address','sigungu','dong','subType','lat','lng','verified','indoor','outdoor','parking','petSize','updatedAt','tags','geoPrecision','services','dongKey','category','petSizeLarge','lastChecked','petSizeSmall','petSizeMedium','source','roadAddress','geoSource','kakaoPlaceId','hours','closedDays','phone','hours24Data','nightEmergencySource','nightEmergencyCheckedOn','openStatusSource','infoCompleteness','ownerPhoto','googleMatchConfirmed','latestEvidenceDate','tourism','tourPhoto','ownRating','ownReviewCount','restrictions']; shards=[]; lookup=collections.defaultdict(dict)
for (r,c),rows in sorted(groups.items()):
 key=f'r{regions.index(r):02d}-c{cats.index(c):02d}'; full=f'data/full/{key}.json'; ix=f'data/index/{key}.json';dump(full,rows);dump(ix,[[p.get(f) for f in fields] for p in rows]);shards.append(dict(key=key,sido=r,category=c,services=sorted({v for p in rows for v in p['services']}),count=len(rows),mapped=sum(map(coord,rows)),verified=sum(p['verified'] is True for p in rows),full=full,index=ix));
 search_routes[key]=route_encode([{**p,"sido":r} for p in rows])
 exact=[p for p in rows if coord(p) and display_services(p)]
 shards[-1]['bounds']=[min(p['lat'] for p in exact),min(p['lng'] for p in exact),max(p['lat'] for p in exact),max(p['lng'] for p in exact)] if exact else None
 for p in rows:lookup[p['id'][:3]][p['id']]=key
for k,v in lookup.items():dump('data/lookup/'+k+'.json',v)
dump('data/merged-ids.json',MERGED)
dump('data/search-routes.json',{'version':1,'bits':32768,'shards':search_routes})
# v1.4: static nationwide exact-coordinate index; no visitor information.
near_groups=collections.defaultdict(list)
for p in A:
 if coord(p) and p.get('sido') and display_services(p):near_groups[p['sido']].append([p['lat'],p['lng']])
dump('data/nearby-index.json',{'version':1,'groups':sorted(near_groups.items())})
HOME_FIELDS=tuple(fields)
HOME_KEYS={pid:key for g in lookup.values() for pid,key in g.items()}
dump('data/manifest.json',dict(version=230,dongGroups=GROUPS,total=len(A),mapped=sum(map(coord,A)),verified=sum(p['verified'] is True for p in A),regions=regions,categories=cats,fields=fields,shards=shards))
# static region filters; only clear administrative token prefixes, no fuzzy matching
category={'grooming':'미용','hotel':'호텔·유치원','hospital':'동물병원','cafe':'카페','restaurant':'식당','travel':'여행지','stay':'숙소','playground':'놀이터','ossuary':'장례·추모','funeral':'장례·추모'}
idx=collections.defaultdict(list)
for p in A:
 for c in display_services(p):
  for sig,dong in {(None,None),(p['sigungu'],None),(p['sigungu'],dong_key(p['sido'],p['sigungu'],p['dongKey']))}:idx[c,p['sido'],sig,dong].append(p)
INFO_FIELDS=('phone','hours','closedDays','parking','indoor','outdoor','petSize','petSizeSmall','petSizeMedium','petSizeLarge','petFee','restrictions','floorAllowed','terrace','carrierRequired','vaccinationCheck','menu','description','homepage')
def known(v):return v not in (None,'',[],{}) and (not isinstance(v,str) or bool(v.strip()) and v.strip() not in ('확인 필요','미확인','정보 없음','-'))
def info_score(p):return sum(known(p.get(k)) for k in INFO_FIELDS)
def rank(p,svc):return (1,*neutral_key(p)) if is_funeral(p) else (0,*ops_rank(p),tier(p),not coord(p),-info_score(p),('카페' if p['category']=='애견카페' else p['category']) not in svc,p['name'],p['id'])
sitemap=['/','/regions/','/owner/','/privacy/','/terms/','/sources/','/owner/pricing/','/owner/terms-ads/','/information-score/','/recommendation-policy/']; report=[]; pageinfo=[]; child=collections.defaultdict(list)
for s in SEO:
 f=s['filter']; svc=f['service'] if isinstance(f['service'],list) else [f['service']]; rows=sorted({p['id']:p for c in svc for p in idx[c,f['sido'],f['sigungu'],dong_key(f['sido'],f['sigungu'],f['dongKey'])] if match(p,f)}.values(),key=lambda p:rank(p,svc));path=regionpath(s);n=len(rows);kw=s['mainKeyword'];title,desc,h1=recount(s,n);s=dict(s,h1=h1);info=(s,path,rows,title,desc);pageinfo.append(info)
 if indexable(s,n):sitemap.append(path)
 report.append({'path':path,'sourceCount':s['count'],'actualCount':n,'indexable':indexable(s,n), 'adjusted':n!=s['count']})
 if s['level']!='sido':child[(s['category'],s['sido'],None if s['level']=='sigungu' else s['sigungu'])].append((path,kw,n))
# v1.8 lazy first-party search suggestions. Excludes hidden travel rows.
search_places=[[p['id'],p['name'],p['sido'],p.get('sigungu'),dong_key(p['sido'],p.get('sigungu'),p.get('dongKey')) or p.get('dong'), ' · '.join(display_services(p))] for p in A if display_services(p)]
search_regions=[[s['h1'],path,s['sido'],s['sigungu'],s['filter']['dongKey'],s['filter']['service'],len(rows)] for s,path,rows,_,_ in pageinfo if rows]
search_index={'version':1,'places':search_places,'regions':search_regions}
dump('data/search-index.json',search_index)
dump('data/search-compact.json',compact_index(search_index))
byregion={(s['category'],s['sido'],s['sigungu'],s['filter']['dongKey']):(path,s['mainKeyword'],len(rows)) for s,path,rows,_,_ in pageinfo}
byarea=collections.defaultdict(list)
for (cat,si,gu,dong),item in byregion.items():byarea[si,gu,dong].append((cat,item))
def crumb(items):
 h='<nav class="breadcrumbs" aria-label="현재 위치"><ol>'+''.join(f'<li><a href="{E(path)}">{E(name)}</a></li>' if i<len(items)-1 and path else f'<li>{E(name)}</li>' if i<len(items)-1 else f'<li aria-current="page">{E(name)}</li>' for i,(name,path) in enumerate(items))+'</ol></nav>'
 ld={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i,'name':name,'item':url(path)} for i,(name,path) in enumerate([(name,path) for name,path in items if path],1)]}
 return h,ld
def region_crumb(cat,si,gu,dong,show_missing=False):
 items=[('홈','/')]
 for name,key in [(si,(cat,si,None,None)),(gu,(cat,si,gu,None)),(dong,(cat,si,gu,dong))]:
  if name and key in byregion:items.append((name,byregion[key][0]))
  elif name and show_missing:items.append((name,None))
 return items
def summary_faq(s,rows):
 n=len(rows); reg=sum(tier(p)==1 for p in rows); official=sum(tier(p)==0 for p in rows); exact=sum(map(coord,rows)); f=s['filter']; kw=s['mainKeyword']
 field='sigungu' if s['level']=='sido' else 'dongKey'; counts=collections.Counter((dong_key(p['sido'],p['sigungu'],p.get(field)) if field=='dongKey' else p.get(field)) for p in rows if p.get(field)) if s['level']!='dong' else collections.Counter(); top=sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:1]
 summary=f'{kw} 목록에는 중복을 제외한 {n:,}곳이 있습니다. 식약처 공식 인증 {official:,}곳, 등록업체 {reg:,}곳이며 정확 좌표가 있는 곳은 {exact:,}곳입니다.'
 if top:summary+=f' {"시군구" if field=="sigungu" else "동·읍·면"} 기준으로는 {top[0][0]}에 {top[0][1]:,}곳으로 수록 업체가 가장 많습니다.'
 else:
  phones=sum(known(p.get('phone')) for p in rows); hours=sum(known(p.get('hours')) for p in rows); summary+=f' 전화번호 정보가 있는 곳은 {phones:,}곳, 운영시간 정보가 있는 곳은 {hours:,}곳입니다.'
 faq=[(f'{kw} 목록에는 몇 곳이 있나요?',f'현재 데이터에서 해당 지역과 서비스에 일치하는 고유 업체는 {n:,}곳입니다.'),(f'{kw}에서 지도에 표시할 수 있는 곳은 몇 곳인가요?',f'정확 좌표가 있는 {exact:,}곳입니다. 나머지 {n-exact:,}곳은 목록에만 표시됩니다.')]
 if top:faq.append((f'{kw} 수록 업체가 가장 많은 지역은 어디인가요?',f'{top[0][0]}에 {top[0][1]:,}곳이 있습니다. 현재 수록된 데이터 기준입니다.'))
 else:faq.append((f'{kw} 중 등록업체는 몇 곳인가요?',f'식약처 공식 인증 배지 {official:,}곳, 등록업체 배지 {reg:,}곳입니다. 공공 목록 등재는 모든 동반 조건을 보증하지 않습니다.'))
 h='<section class="panel region-summary"><h2>지역 데이터 요약</h2><p>'+E(summary)+'</p></section>'
 faqhtml='<section class="panel region-faq"><h2>자주 묻는 질문</h2>'+''.join(f'<h3>{E(q)}</h3><p>{E(a)}</p>' for q,a in faq)+'</section>'
 ld={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in faq]}
 return h,faqhtml,ld

def searchlink(s):
 f=s['filter'];return '/?'+urllib.parse.urlencode({k:v for k,v in f.items() if v is not None},doseq=True)+'#explore'
def links(items):return '<div class="seo-links">'+''.join(f'<a href="{E(p)}">{E(t)} ({n:,})</a>' for p,t,n in items if n)+'</div>'
from monetization import pricing, recommend, ad_slot
admin_ads,admin_premium=schedules(admin_snapshot,{path:{p['id'] for p in rows} for _,path,rows,_,_ in pageinfo},IDS)
if (admin_ads or admin_premium) and not ADS_POLICY_APPROVED:raise RuntimeError('Approve ad contract and policy before paid content.')
closed={p['id'] for p in A if p.get('operating') is False}
assert not (closed & (set(admin_premium)|{r['place_id'] for rs in admin_ads.values() for r in rs})), 'Closed place cannot advertise'
assert not json.loads((SRC/'ads.json').read_text()), "Migrate legacy ads.json to the ads CSV; do not use both"
for s,path,rows,title,desc in pageinfo:
 n=len(rows);kw=s['mainKeyword'];cat=s['category'];si=s['sido'];gu=s['sigungu'];dong=s['filter']['dongKey'];children=child.get((cat,si,gu),[]) if s['level']!='dong' else []
 crumbs,crumbld=crumb(region_crumb(cat,si,gu,dong)); summary,faqhtml,faqld=summary_faq(s,rows)
 h=crumbs+f'<p><a href="{E(searchlink(s))}">{"장례·추모 전체 검색·지도 보기" if s["filter"].get("subTypes") else "이 지역 검색·지도 보기"}</a></p><h1>{E(s["h1"])}</h1>'+summary
 if s['level']=='dong' and not indexable(s,n):
  parent=byregion.get((cat,si,gu,None)) or byregion.get((cat,si,None,None))
  if parent:h+=f'<p class="notice">수록 업체가 3곳 미만인 지역입니다. <a href="{E(parent[0])}">상위 지역 전체 목록 보기</a></p>'
 if cat in ("funeral","ossuary"):h+=funeral_cta(region=" ".join(filter(None,[si,gu,dong])))+fee_notice()+'<p>지역·업체명 순 · 제휴 여부와 무관한 공공 목록입니다.</p>'
 else:h+=photo_carousel(rows,HOME_KEYS,card22)+recommend(path,rows,admin_ads.get(path,[]))
 h+= '<section class="panel"><h2>장소 목록</h2>'+('<ul class="seo-list">'+''.join(row(p)+(ad_slot('mid',ADFIT_MID) if cat not in ('funeral','ossuary') and i==max(1,len(rows)//2)-1 else '') for i,p in enumerate(rows))+'</ul>' if rows else '<p>현재 필터에 일치하는 업체가 없습니다. 지역 정보 검증 중입니다.</p>')+'</section>'
 if cat not in ('funeral','ossuary'):h+=ad_slot('bottom',ADFIT_BOTTOM,False)
 if children:h+='<section class="panel"><h2>세부 지역</h2>'+links(children)+'</section>'
 h+=faqhtml
 parents=[byregion[k] for k in [(cat,si,None,None),(cat,si,gu,None)] if k in byregion and byregion[k][0]!=path];parents=list(dict.fromkeys(parents))
 siblings=[v for v in child.get((cat,si,gu),[]) if v[0]!=path] if dong else []
 others=[v for c,v in byarea[si,gu,dong] if c!=cat]
 h+='<section class="panel related-regions" aria-label="관련 지역 및 서비스">'
 for label,items in [('상위 지역',parents),('같은 시군구의 다른 동',siblings),('같은 지역의 다른 서비스',others)]:
  if items:h+='<h2>'+label+'</h2>'+links(sorted(items,key=lambda v:(v[1],v[0])))
 h+='</section>';page(path,title,desc,h,[listld(rows),crumbld,faqld],not indexable(s,n))

page('/compare/','동반 조건 비교 | 어디가개','최대 3개 장소의 공개 동반 조건을 비교합니다.','<h1>동반 조건 비교</h1><p>최대 3곳을 비교할 수 있어요. 미확인은 허용 또는 금지로 판단하지 않습니다. 방문 전에 업체에 직접 확인하세요.</p><div id="compareList" aria-live="polite"></div><p><a class="btn primary" href="/#explore">장소 더 찾기</a> <button type="button" class="btn" id="compareClear">비교함 비우기</button></p>',noindex=True)
roots=[(path,s['mainKeyword'],len(rows)) for s,path,rows,_,_ in pageinfo if s['level']=='sido'];page('/regions/','지역별 반려동물 장소 | 어디가개','전국 지역별 식당, 카페, 숙소 및 반려생활 장소 목록.','<h1>지역별 장소 찾기</h1><p>지역과 카테고리를 선택해 장소를 찾아보세요.</p>'+photo_carousel(sorted((p for p in A if display_services(p)),key=ops_rank),HOME_KEYS,card22,regional=False)+links(roots),{'@context':'https://schema.org','@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i,'name':t,'url':url(p)} for i,(p,t,n) in enumerate([r for r in roots if r[2]],1)]})
publish_pages(SRC,page,roots,A)
sitemap.extend(sorted(extra_paths(SRC)-{'/contribute/'}))
# detail and feedback form
facts=[('반려동물 크기·무게 (원본 정보)','petSize'),('소형견','petSizeSmall'),('중형견','petSizeMedium'),('대형견','petSizeLarge'),('실내 동반','indoor'),('실외 동반','outdoor'),('추가 요금','petFee'),('바닥에 내려놓기','floorAllowed'),('테라스','terrace'),('이동장 필요','carrierRequired'),('접종 확인 필요','vaccinationCheck'),('동반 제한','restrictions'),('무게 제한','weightLimit'),('메뉴 및 가격','menu'),('이미지 사용 권한','imageRights')]
def _fv(p,v):
 x=p.get(v)
 if v=="operating" and isinstance(x,bool):return E("영업 중" if x else "폐업 신고 확인")
 if v=="phone" and isinstance(x,str) and re.search(r"\d{2,4}-\d{3,4}-\d{4}",x):return f'<a href="tel:{E(re.sub(r"[^0-9]","",x))}">{E(x)}</a>'
 if v in("homepage","sourceUrl") and isinstance(x,str) and x.startswith(("https://","http://")):return f'<a href="{E(x)}" rel="nofollow noopener" target="_blank">{E(x)}</a>'
 return E(fmt(x))
def block(title,p,fields):
 kn=[(k,v) for k,v in fields if known(p.get(v)) or (v=="operating" and isinstance(p.get(v),bool))]
 return ('<section class="panel known-facts"'+(' hidden' if not kn else '')+'><h2>'+E(title)+'</h2>'+('<dl class="kv">'+''.join(f'<div><dt>{E(k)}</dt><dd>{_fv(p,v)}</dd></div>' for k,v in kn)+'</dl>' if kn else '')+'</section>')
def unknown_summary(p,fields):
 labels=[k for k,v in fields if not known(p.get(v))];labels=list(dict.fromkeys(labels))
 return ('<details class="panel unknown-summary"><summary>미확인 정보 '+str(len(labels))+'개 · 방문 전 확인</summary><p>'+E(' · '.join(labels))+'</p><p>미확인은 가능 또는 불가를 의미하지 않습니다.</p></details>') if labels else ''
reglookup={(s['category'],s['sido'],s['sigungu'],s['filter']['dongKey']):path for s,path,rows,_,_ in pageinfo if rows};inv={v:k for k,v in category.items()}
for p in A:
 path=placepath(p);sitemap.append(path);name=p['name'];address=p.get('roadAddress') or p.get('address');area=' '.join(filter(None,[p['sido'],p['sigungu'],p['dong']]));title=f'{name} · {services(p)} | 어디가개';desc=f'{name}의 {area or "지역 미확인"} {services(p)} 정보. 주소, 영업시간, 확인된 반려동물 이용 조건을 살펴보세요.';schema={'@context':'https://schema.org','@type':{'동물병원':'VeterinaryCare','식당':'Restaurant','카페':'CafeOrCoffeeShop','애견카페':'CafeOrCoffeeShop','숙소':'LodgingBusiness','여행지':'TouristAttraction'}.get(p['category'],'LocalBusiness'),'name':name,'url':url(path),'description':desc,'makesOffer':[{'@type':'Offer','itemOffered':{'@type':'Service','name':v}} for v in p['services']]}
 if schema['@type']=='TouristAttraction':schema.pop('makesOffer');schema['additionalProperty']=[{'@type':'PropertyValue','name':'서비스','value':v} for v in p['services']]
 if address:schema['address']={'@type':'PostalAddress','streetAddress':address,'addressCountry':'KR'}
 if p.get('phone'):schema['telephone']=p['phone']
 if coord(p):schema['geo']={'@type':'GeoCoordinates','latitude':p['lat'],'longitude':p['lng']}
 if p.get('homepage') and isinstance(p['homepage'],str) and p['homepage'].startswith(('https://','http://')):schema['sameAs']=[p['homepage']]
 c=inv['카페' if p['category']=='애견카페' else p['category']];parent=next((reglookup[k] for k in [(c,p['sido'],p['sigungu'],dong_key(p['sido'],p['sigungu'],p['dongKey'])),(c,p['sido'],p['sigungu'],None),(c,p['sido'],None,None)] if k in reglookup),'/regions/')
 items=region_crumb(c,p['sido'],p['sigungu'],dong_key(p['sido'],p['sigungu'],p['dongKey']),True);crumbs,crumbld=crumb(items+[(name,path)])
 hero_rating=rating22(p)+'<div class="eg-hero-rating" data-hero-rating hidden></div>' if not is_funeral(p) else ''
 h=crumbs+f'<div class="detailhero">{photo_cover(p,services(p))}<div class="detailintro">{badge(p)}<h1>{E(name)}</h1>{hero_rating}<p>{E(address or area or "주소 미확인")}</p><p>{E(services(p))} · {status(p)}</p>'+(f'<p><span class="open-pill" data-hours="{E(p.get("hours") or "")}" data-closed="{E(p.get("closedDays") or "")}"></span> <span class="muted">등록된 운영시간 기준 · 방문 전 전화 확인</span></p>' if p.get('hours') or p.get('closedDays') else '')+f'<p class="ext-links"><a class="btn" rel="nofollow noopener" target="_blank" href="https://map.naver.com/p/search/{urllib.parse.quote((p.get("sigungu") or "")+" "+p["name"])}">네이버 평점·사진 보기</a></p>'
 if '동물병원' in p['services']:
  h+='<div class="hospital-badges">'+hospital_badges(p)+'</div><p class="muted">진료 가능 여부와 접수 마감은 방문 전 전화로 확인하세요. 운영시간 표기는 실시간 진료 확인이 아닙니다.</p>'
  if telephone(p.get('phone')):h+=f'<a class="btn primary hospital-call" href="tel:{E(telephone(p.get("phone")))}">📞 병원에 전화</a>'
 if '동물병원' in p['services'] and not p.get('openStatusSource'):h+='<p class="notice">영업 여부 확인 필요</p>'
 h+='<div class="quickfacts">'+''.join(f'<div><small>{E(k)}</small><strong>{E(fmt(p.get(v)))}</strong></div>' for k,v in [('대형견','petSizeLarge'),('실내 동반','indoor'),('주차','parking')] if known(p.get(v)))+'</div>'
 h+='<details class="address-block address-details"><summary>주소 상세</summary><div class="detailgrid"><div class="fact"><b>도로명주소</b><span>'+E(fmt(p.get('roadAddress')))+'</span></div><div class="fact"><b>원본 주소</b><span>'+E(fmt(p.get('address')))+'</span></div></div></details>'
 if not is_funeral(p):
  compare_data={'id':p['id'],'name':name,'area':area,**{k:p.get(k) for k in ('indoor','outdoor','petSizeSmall','petSizeMedium','petSizeLarge','parking','petFee','restrictions','weightLimit','carrierRequired','latestEvidenceDate')}}
  h+=f'<button type="button" class="btn compare-add" data-compare="{E(json.dumps(compare_data,ensure_ascii=False))}" aria-pressed="false">＋ 동반 조건 비교</button> <a class="btn" href="/compare/">비교함 보기</a>'
 kid=p.get('kakaoPlaceId')
 if isinstance(kid,str) and re.fullmatch(r'[0-9]+',kid):h+=f'<a class="btn primary" href="https://place.map.kakao.com/{kid}" rel="noopener noreferrer" target="_blank">카카오맵에서 보기</a> '
 if coord(p):h+=f'<a class="btn" href="https://map.naver.com/p/search/{urllib.parse.quote(name+" "+(address or area),safe="")}" rel="noopener" target="_blank">지도 검색</a>'
 h+=f' <button class="btn detail-save" data-place-save="{E(p["id"])}" data-shard="{E(lookup[p["id"][:3]][p["id"]])}" aria-pressed="false">♡ 저장</button> <a class="btn" href="/owner/?type=correction&amp;place={E(p["id"])}&amp;name={E(urllib.parse.quote(name))}">정보 수정 제안</a> <a class="btn" href="/owner/?type=closure&amp;place={E(p["id"])}&amp;name={E(urllib.parse.quote(name))}">폐업 신고</a> <a class="btn primary" href="/owner/?type=owner&amp;place={E(p["id"])}&amp;name={E(urllib.parse.quote(name))}">사장님 무료 입점 신청</a></div></div>'
 h+=tour_detail_html(p,PET,TOUR_SOURCE)
 h+=block('동반 조건',p,[f for f in facts if f[1] not in ('petFee','menu')] if is_funeral(p) else facts)
 h+=block('운영시간·휴무',p,[('영업시간','hours'),('휴무일','closedDays'),('영업 여부','operating')])+block('주차',p,[('주차','parking')])+block('연락처',p,[('전화','phone'),('홈페이지','homepage')])+block('출처·확인일',p,[('정보 출처','source'),('위치 정보 출처','geoSource'),('영업 확인 출처','openStatusSource'),('출처 URL','sourceUrl'),('최근 기록상 확인일','latestEvidenceDate'),('원본 정보 확인일','lastChecked'),('데이터 갱신일','updatedAt'),('인허가 번호','licenseNo')])+block('기타 정보',p,[('업종 상세','subType'),('소개','description'),('등록 업종','registryCategories')])
 h+=unknown_summary(p,facts+[('영업시간','hours'),('휴무일','closedDays'),('영업 여부','operating'),('주차','parking'),('전화','phone'),('홈페이지','homepage'),('정보 출처','source'),('위치 정보 출처','geoSource'),('영업 확인 출처','openStatusSource'),('출처 URL','sourceUrl'),('최근 기록상 확인일','latestEvidenceDate'),('원본 정보 확인일','lastChecked'),('데이터 갱신일','updatedAt'),('인허가 번호','licenseNo'),('업종 상세','subType'),('소개','description'),('등록 업종','registryCategories')])
 h+=review_detail(p,GOOGLE_IDS,REVIEW_CONFIG)
 h+=maps(p)
 if coord(p):h+=f'<section class="panel detail-kakao"><h2>위치</h2><button class="btn" type="button" data-detail-map data-lat="{E(p["lat"])}" data-lng="{E(p["lng"])}">카카오 지도 보기</button> <a class="btn" href="https://map.kakao.com/link/to/{urllib.parse.quote(name,safe="")},{p["lat"]},{p["lng"]}" target="_blank" rel="noopener noreferrer">카카오맵 길찾기</a><div class="detail-map-canvas" hidden></div><p class="muted">공공데이터 좌표 기준 · 방문 전 확인</p></section><script src="/kakao-map.js" defer></script>' 
 h+=f'<div hidden data-recent-place="{E(p["id"])}" data-recent-name="{E(name)}" data-recent-region="{E(area)}"></div>'
 if is_funeral(p):h+=funeral_actions(p,area)
 else:h+=premium_html(admin_premium.get(p['id'],[]))
 if '장례·추모' in p['services']:h+='<p class="notice">공공 목록 등재는 현재 허가 유효·영업 상태를 보증하지 않습니다. 방문·문의 전 허가번호와 시설 주소를 확인하세요. <a href="/funeral/guide/">장례 가이드</a></p>'
 if ENABLE_FORMS:h+='<aside class="panel"><h2>댕댕이와 갈 곳, 더 쉽게 찾아보세요</h2><a class="btn primary" href="/?launch=1#launch">출시 알림 받기</a></aside>'
 if p.get('informationCheck'):
  check=p['informationCheck'];h+=f'<section class="panel"><h2>최근 정보 확인</h2><p>{E(check["checkedOn"])} · {E(", ".join(check["fields"]))} · <a href="{E(check["sourceUrl"])}" rel="noopener noreferrer" target="_blank">확인 근거</a></p><p>표시된 항목만 확인했으며 전체 정보나 영업 상태를 보증하지 않습니다.</p></section>'
 if p.get('operatorCorrections'):
  h+='<section class="panel"><h2>운영자 확인 정보</h2><ul>'+''.join(f'<li>{E(k)} · {E(v["checkedOn"])} · <a href="{E(v["source"])}" rel="noopener noreferrer" target="_blank">확인 근거</a></li>' for k,v in p['operatorCorrections'].items())+'</ul></section>'
 ph=p.get('phone') if isinstance(p.get('phone'),str) and re.search(r"\d{2,4}-\d{3,4}-\d{4}",p.get('phone') or '') else None
 h+='<div class="m-actions">'+(f'<a class="btn" href="tel:{E(re.sub(r"[^0-9]","",ph))}">📞 전화</a>' if ph else '')+f'<a class="btn" rel="nofollow noopener" target="_blank" href="https://map.naver.com/p/search/{urllib.parse.quote((p.get("sigungu") or "")+" "+p["name"])}">🗺️ 지도·리뷰</a><button class="btn primary detail-save" data-place-save="{E(p["id"])}" data-shard="{E(lookup[p["id"][:3]][p["id"]])}" aria-pressed="false">♡ 저장</button></div>'
 h+=owner_gallery(owner_photos.get(p['id'],[]))
 if not is_funeral(p):h+=f'<section class="panel" id="photo-contribute"><h2>이 장소 사진 올리기</h2><p>직접 촬영한 사진을 보내 주세요. 검수 후 대표 사진으로 채택될 수 있으며, 희망하면 공개 닉네임을 사진 크레딧에 표시합니다. 금전 보상·노출 우대는 없습니다.</p><a class="btn primary" data-eg-event="photo" href="/contribute/?place={E(p["id"])}&amp;name={E(urllib.parse.quote(name))}#visitor-photo">이 장소 사진 올리기</a></section>'
 h+=detail_content(p['id'],reviews,photos).replace('?place='+p['id']+'#','?place='+p['id']+'&amp;name='+E(urllib.parse.quote(name))+'#')
 page(path,title,desc,h,[schema,crumbld],place=p)
# centralized form and policy pages; local download only
from forms import form, intake_js, md_html
from launch import launch_markup
from external_forms import convert, fallback, notice, contact_markup
import settings as config
if ENABLE_FORMS:
 form=convert(form.replace('[대표 이메일 확정 후 안내]',E(CONTACT_EMAIL)).replace('data-live="false"',f'data-live="true" data-processor-notice="{E(notice())}"').replace('value="draft-2026-11-25"',f'value="{E(POLICY_VERSION)}"').replace('검수용: 실제 개인정보를 입력하지 마세요. 서버 접수 없이 입력한 내용을 JSON으로 저장하는 시연입니다. 정책은 초안입니다.','신청 내용은 접수 후 검토합니다. 제보가 즉시 업체 정보에 반영되지는 않습니다.').replace('검수용 JSON 저장 (접수 아님)','신청 접수하기').replace('개인정보처리방침(초안)','개인정보처리방침'))
else:form=fallback()
if ENABLE_FORMS and config.KAKAO_CHANNEL_URL:form+='<p>'+contact_markup()+'</p>'
form+='<p><a class="btn" href="/contribute/#owner-photo">사장님 사진 제출 (입점과 별도 검수)</a></p>'
page('/owner/pricing/','사장님 광고 상품 | 어디가개','무료 입점, 프리미엄 매장 월 29,000원, 지역 상단 광고 월 49,000~99,000원 안내.',pricing)
adpolicy=(SRC/'ad-policy.md').read_text(); contract=adpolicy.split('## C.',1)[1].split('## D.',1)[0].split('\n',1)[1]; contract='# 광고·프리미엄 이용계약서 (초안)\n> 계약서 초안입니다. 개별 계약 조건 및 최종 법률 검토 후 사용하세요. 허위 광고 중단 시 노출된 기간은 환불하지 않고, 남은 기간 일할 금액에서 위약금 10%를 공제합니다.\n'+contract
page('/owner/terms-ads/','광고 이용계약서 | 어디가개','광고 및 프리미엄 상품 이용계약서 초안',md_html(identity(contract).replace('**','')+'\n'+business_lines()))
page('/owner/','무료 입점 및 정보 수정 | 어디가개','반려동물 동반 장소 등록 및 수정 신청서.',form)
write('intake.js',intake_js)
privacy=(SRC/'privacy.md').read_text().split('> v0.7 운영 검토:')[0]; privacy=privacy.replace('[호스팅 업체명]','GitHub, Inc. (GitHub Pages; 정적 웹 호스팅)').replace('[6개월]','6개월').replace('[3개월]','3개월'); privacy=privacy.replace('| GitHub, Inc. (GitHub Pages; 정적 웹 호스팅) | 서버 운영 및 데이터 보관 |', '| GitHub, Inc. (GitHub Pages; 정적 웹 호스팅) | 정적 페이지 제공 |'+('\n| '+config.FORM_PROVIDER.replace('|','／')+' | 신청 접수·저장·관리 |' if ENABLE_FORMS else '')); privacy=privacy.replace('| 서비스 이용 시 자동 수집', '| 유료상품 문의 | 상호, 담당자명, 연락처, 희망 상품·지역, 문의 내용, 이메일(선택) | 광고 상담 |\n| 서비스 이용 시 자동 수집'); privacy=privacy.replace('- 접속 기록:', '- 유료상품 문의: 미계약 상담 종료 후 3개월, 계약 고객은 계약 종료 후 5년 (관련 법령 및 최종 계약 기준)\n- 접속 기록:'); privacy+='\n## 온라인 신청 및 개인정보 처리 위탁·국외 이전\n- '+notice()+'\n- 문의: '+(CONTACT_EMAIL or '공식 문의처 준비 중')+'\n- 입점 해지·반려 후 6개월, 정보 수정 및 폐업 신고 처리 후 3개월, 출시 안내 발송 또는 철회 시 파기.\n'; privacy+=adfit_notice()+'\n## 추가 안내\n- 장소 저장은 브라우저 로컬 저장소를 사용합니다. 오프라인 캐시는 공개 화면만 보관합니다.'; terms=(SRC/'terms.md').read_text(); terms, sources=terms.split('---',1)
sources=sources.split('- 위치·도로명주소 보완: 카카오',1)[0]+'\n- 소상공인시장진흥공단 상가(상권)정보 2026-09 (공공데이터포털 15083033): 위치·주소 보완. 공공 목록 등재는 현재 영업 여부를 보증하지 않습니다.\n'
privacy=privacy.replace('이메일 또는 휴대전화번호 | 출시 소식 안내','이메일, 유입 경로(선택), UTM 캠페인 값(존재 시) | 출시 소식 안내 및 채널별 신청 집계').replace('이메일 또는 휴대전화 | - | 발송 후 즉시','이메일 | 유입 경로 및 UTM 캠페인 값 | 발송 후 즉시')
privacy+='\n## 출시 알림 유입 경로 안내\n- 선택한 유입 경로와 utm_source, utm_medium, utm_campaign, utm_content, utm_term을 신청과 함께 저장해 캠페인 성과를 집계합니다. UTM은 현재 탭의 세션 저장소에서 유지되며, 신청 데이터는 출시 안내 발송 후 또는 철회 시 파기합니다. 개인정보를 UTM에 넣지 마세요.\n'
privacy+='\n## 방문 후기·매장 사진\n- 후기: 업체 ID·업체명, 회신 이메일, 닉네임, 방문일, 후기, 관계 및 혜택 표시, 동의 기록. 사진: 업체 ID(있는 경우)·상호, 담당자, 매장 공식 연락처, 회신 이메일, 사진 또는 링크, 설명 및 권리 동의. 검수·회신 및 게시 목적이며 비공개 접수 자료는 처리 후 3개월 이내 파기, 공개 자료는 삭제 요청 또는 게시 종료까지 유지합니다. 공개되는 항목은 닉네임·방문일·후기·관계/혜택 표시 또는 승인된 사진·설명·제공자 표시입니다. 원본·연락처·회신 이메일·권리 증빙은 공개 저장소에 넣지 않습니다. 처리 위탁 및 국외 이전은 위 온라인 신청 안내와 같습니다.\n'
privacy+='\n## 장례 상담 문의\n- '+PRIVACY_TEXT+'\n'
terms+='\n## 장례 상담 및 업체 연결\n- '+ROLE+'\n- '+DISCLOSURE+'\n- 업체 목록은 제휴 여부와 무관하게 지역·이름순으로 표시합니다. 장례 계약은 업체와 직접 체결하며 상담 신청은 계약·예약을 의미하지 않습니다. 개인정보는 업체 제공 전에 별도 동의를 받습니다.\n'
privacy+='\n## 내 주변 찾기\n- 위치 접근에 동의한 경우 현재 위치는 브라우저 메모리에서만 거리 계산에 사용하며 서버, 신청서, URL 또는 저장소에 전송·저장하지 않습니다. 전국 공개 장소의 샤드 범위와 비교하여 필요한 파일만 요청합니다. 카카오 지도 사용 시 카카오 SDK가 표시 영역(현재 위치 중심으로 이동하는 경우 해당 영역), IP 등 접속 정보를 처리할 수 있습니다. 위치 좌표 자체를 당사 서버나 통계에 보내지 않습니다. 외부 길찾기 링크에는 업체명과 공개 목적지 좌표를 전달합니다. 카카오 지도 서비스의 개인정보 처리에 대해서는 카카오 개인정보처리방침(https://www.kakao.com/policy/privacy)을 확인하세요. 키 미설정 또는 로딩 실패 시 OpenStreetMap 지도 타일을 요청할 수 있습니다. 위치 권한은 브라우저 설정에서 철회할 수 있습니다.\n'
privacy+='\n## 최근 본 장소 및 저장 폴더\n- 최근 본 장소(최대 20곳), 저장한 장소와 폴더명은 이용자의 브라우저 localStorage에만 저장합니다. 동반 조건 비교함(최대 3곳의 공개 업체 정보)도 해당 기기에 저장합니다. 서버에 전송하지 않으며 이용자가 삭제하거나 브라우저 저장소를 지우면 제거됩니다. 외부 지도 검색 링크에는 장소명과 주소만 전달합니다.\n'
privacy+=REVIEW_PRIVACY+ANALYTICS_PRIVACY;terms+=REVIEW_TERMS
page('/information-score/','어디가개 정보 충실도 산식','업체 정보 충실도 산정 기준 및 한계',SCORE_HTML)
# No ads, no commercial navigation, no core/ad scripts on the independent provider search page.
search_head=head('네이버 검색결과 | 어디가개','네이버 지역·블로그·이미지 검색결과','/naver-search/',noindex=True).replace('<script src="/core.js" defer></script>','')
write('/naver-search/index.html','<!doctype html><html lang="ko"><head>'+search_head+'</head><body><main class="wrap detail">'+SEARCH_HTML+'</main></body></html>')
write('reviews-config.js','window.EGReviewConfig='+json.dumps(REVIEW_CONFIG,ensure_ascii=False).replace('<','\\u003c')+';')
privacy=privacy.replace('[이메일·문자 발송 업체명]','발송 수단 확정 후 고지').replace('비밀번호 등 중요 정보 암호화 저장','접근 권한이 있는 운영자만 신청 내역 열람')
for path,title,doc in [('/privacy/','개인정보처리방침',privacy),('/terms/','이용약관',terms),('/sources/','데이터 출처',sources+'\n## 한국관광공사\n- 반려동물 동반여행 서비스 (https://www.data.go.kr/data/15135102/openapi.do), 지역 목록·동반 조건 및 이용허락이 확인된 사진. 조회일은 방문 확인일이 아닙니다. 사진 출처 한국관광공사, 공공누리 제1·3유형만 사용하며 제3유형은 원본 비율을 유지합니다.\n')]:page(path,title+' | 어디가개',title+' 안내',md_html(identity(doc)+'\n'+business_lines()).replace('<h2>맞춤형 광고 안내</h2>','<h2 id="adfit">맞춤형 광고 안내</h2>')+('<p><button class="btn" data-stats-toggle hidden>익명 이용 통계 설정</button></p>' if path=='/privacy/' else ''))
# Legacy detail routes: static fallback plus deployment redirect table.
for old,new in MERGED.items():
 path='/place/'+new+'/'; dest='/place/'+old+'/'
 write(dest+'index.html','<!doctype html><html lang="ko"><head>'+head('이전된 장소 | 어디가개','중복 업체 정보가 통합되었습니다.',path,noindex=True)+'<meta http-equiv="refresh" content="0;url='+E(path)+'"></head><body><main><p>업체 정보가 통합되었습니다. <a href="'+E(path)+'">새 업체 페이지로 이동</a></p></main></body></html>')
(ROOT/'deploy').mkdir(exist_ok=True)
redirects={}
for old,new in MERGED.items():redirects['/place/'+old+'/']='/place/'+new+'/'
valid={path for _,path,_,_,_ in pageinfo}
for old in json.loads((ROOT/'OLD-REGION-PATHS.json').read_text()):
 dest=old.rsplit('/',1)[0]+'/'
 while dest not in valid and dest.count('/')>2:dest=dest.rstrip('/').rsplit('/',1)[0]+'/'
 assert dest in valid,(old,dest)
 path=old.rstrip('/')+'/';redirects[path]=dest
 write(path+'index.html','<!doctype html><html lang="ko"><head>'+head('이전된 지역 | 어디가개','상위 지역으로 이동합니다.',dest,noindex=True)+'<meta http-equiv="refresh" content="0;url='+E(dest)+'"></head><body><a href="'+E(dest)+'">상위 지역으로 이동</a></body></html>')
for path,dest in ALIAS_REDIRECTS.items():
 assert path not in valid and dest in valid
 redirects[path]=dest
 write(path+'index.html','<!doctype html><html lang="ko"><head>'+head('통합 지역 | 어디가개','통합 지역 목록으로 이동합니다.',dest,noindex=True)+'<meta http-equiv="refresh" content="0;url='+E(dest)+'"></head><body><a href="'+E(dest)+'">통합 지역으로 이동</a></body></html>')
write('.nojekyll','')
dump('release.json',{'version':ASSET_HASH})
(ROOT/'deploy'/'redirects.json').write_text(json.dumps(redirects,ensure_ascii=False,indent=2))

# v1.6 first-screen snapshot; actual full search loads only on interaction.
home_rows=sorted((p for p in A if p['sido']=='서울특별시' and display_services(p)),key=lambda p:(1,*neutral_key(p)) if is_funeral(p) else (0,*ops_rank(p),tier(p),not coord(p),p['id']))
home_boot={'rows':[dict({f:p.get(f) for f in HOME_FIELDS},sido=p['sido'],key=HOME_KEYS[p['id']]) for p in home_rows[:12]],'total':len(home_rows),'mapped':sum(map(coord,home_rows))}
def home_card(p):return card22(p,HOME_KEYS[p['id']])
home=(SRC/'home-template.html').read_text().replace('<!--PLACE_COUNT-->',f'{len(A):,}');home=home.replace('<!--SEO_HEAD-->',f'<link rel="canonical" href="{E(url("/"))}">'+social('어디가개 | 반려동물 동반 장소 찾기','반려동물과 함께 갈 수 있는 식당, 카페, 숙소를 찾아보세요.','/')+jsld(listld(home_rows[:12])));home=home.replace('<!--CURATION-->',curated22(A,HOME_KEYS));home=home.replace('<!--STATIC_HOME-->',''.join(home_card(p) for p in home_rows[:12])).replace('<!--REGION_LINKS-->',''.join(f'<a href="{E(p)}">{E(t)} ({n:,})</a>' for p,t,n in roots if n));home=re.sub(r'<footer>.*?</footer>',lambda _:FOOT,home,flags=re.S);home=home.replace('</head>',('<meta name="robots" content="noindex,follow">' if PREVIEW else '')+'<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#F26B1D"><link rel="apple-touch-icon" href="/icon-192.png"><meta name="apple-mobile-web-app-capable" content="yes"><script src="/core.js" defer></script></head>');home=home.replace('/style.css','/bundle.css').replace('<script src="/hours.js" defer></script>','').replace('<script src="nearby.js" defer></script><script src="app.js" defer></script>','<script src="/discovery.js" defer></script>');home=home.replace('<footer>','<section class="wrap section"><h2>장례·추모 안내</h2><a class="btn" href="/funeral/">장례·추모</a> <a class="btn" href="/funeral/guide/">장례 가이드</a> <a class="btn" href="/memorial/rituals/">천도재·위령재</a></section><footer>',1);home=home.replace('<footer>',(launch_markup(True,POLICY_VERSION) if ENABLE_FORMS else '<aside id="launch" class="launch-banner wrap"><p>출시 알림 문의</p>'+contact_markup()+'</aside>')+'<footer>',1);home=home.replace('<!--HOME_BOOT-->', '<script type="application/json" id="homeBoot">'+json.dumps(home_boot,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+'</script>');write('index.html',home)
page('/recommendation-policy/','사진 추천 기준 | 어디가개','사진과 정보 출처 기준을 공개합니다.','<h1>사진 추천 기준</h1><p>한국관광공사 이용 허락 사진 또는 운영 승인된 자체 사진이 있는 장소를 소개합니다. 사진이 있어도 품질·영업·동반 가능성을 보증하지 않습니다. 광고 구매, Google 평점은 추천 산식에 반영하지 않습니다. 장례업체는 제외합니다.</p><p>승인 사진 여부 → 관광공사 사진 여부 → 정보 충실도 → 고유 ID 순으로 선정합니다. 지역·업종별 최대 8곳을 보여주며 추천 사진이 없으면 영역을 숨깁니다.</p><a href="/review-policy/">후기 운영 원칙</a>')
dump('data/tourapi-audit.json',tour_audit)
tour_summary=tour_report(SRC,A,tour_audit)
review_cases,review_rows=review_csv(ROOT/'internal'/'tour-match-review.csv',tour_read(SRC)['records'],A,tour_audit,tour_point,tour_km,clean_name)
print(f'TourAPI private review CSV: {review_cases} cases, {review_rows} candidate rows')
dump('data/tourapi-summary.json',tour_summary)
print('TourAPI match report:',json.dumps(tour_summary,ensure_ascii=False))
if os.getenv('GITHUB_STEP_SUMMARY'):
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write('\n### TourAPI 매칭 리포트\n'+''.join(f'- {k}: {v}\n' for k,v in tour_summary.items()))
from app_release import asset_links
write('.well-known/assetlinks.json',json.dumps(asset_links(),ensure_ascii=False,indent=2))
write('.nojekyll','')
dump('release.json',{'version':ASSET_HASH})
assert len(sitemap)<=50000, 'Sitemap URL limit exceeded; split sitemap before deploying.'
write('sitemap.xml',sitemap_xml(sitemap,url,SITE,A,image_candidates(A,pageinfo)));assert (SITE/'sitemap.xml').stat().st_size<=52428800;write('robots.txt',('User-agent: *\nDisallow: /\n' if PREVIEW else 'User-agent: *\nAllow: /\nDisallow: /data/\n')+'Sitemap: '+url('/sitemap.xml')+'\n');dump('data/build-report.json',{'total':len(A),'redirects':len(redirects),'badgeCounts':dict(collections.Counter(BADGES[tier(p)][0] for p in A)),'serviceCounts':dict(collections.Counter(v for p in A for v in display_services(p))), 'travelExcluded':sum('여행지' in p['services'] and '여행지' not in display_services(p) for p in A), 'aliasRedirects':ALIAS_REDIRECTS,'mapped':sum(map(coord,A)),'approx':sum(map(approx,A)),'verified':sum(p['verified'] is True for p in A),'seoPages':len(SEO),'empty':sum(r['actualCount']==0 for r in report),'noindexRegionCount':sum(not r['indexable'] for r in report),'mismatch':0,'adjustedRegionCounts':sum(r['adjusted'] for r in report),'sitemapUrls':len(sitemap),'shards':len(shards),'regionCounts':report,'siteUrl':BASE,'preview':PREVIEW,'formsEnabled':ENABLE_FORMS,'admin':{'mode':admin_snapshot['mode'],'asOf':admin_snapshot['as_of'],'corrections':correction_count,'adBookings':sum(map(len,admin_ads.values())),'activeAds':sum(active(r,admin_snapshot['as_of']) for rows in admin_ads.values() for r in rows),'premiumBookings':sum(map(len,admin_premium.values())),'activePremium':sum(active(r,admin_snapshot['as_of']) for rows in admin_premium.values() for r in rows)},'roadAddressCount':sum(bool(p.get('roadAddress')) for p in A),'kakaoIdCount':sum(bool(p.get('kakaoPlaceId')) for p in A)});print('build complete',len(A),len(SEO),len(sitemap),'empty regions',sum(not r['indexable'] for r in report),'recounted regions',sum(r['sourceCount']!=r['actualCount'] for r in report))
