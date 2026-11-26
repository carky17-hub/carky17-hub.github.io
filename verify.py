"""Full data, static page and redirect validation; standard library only."""
import json,re,collections,pathlib,xml.etree.ElementTree as ET,urllib.parse,math,html,os
R=pathlib.Path(__file__).resolve().parent; S=R/'site'; src=R/'source'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
from source_data import load_source
from v13 import funeral_places,funeral_seo,match,extra_paths,is_funeral,neutral_key,reject_funeral_overlays
# v1.3.2 neutral funeral verification
from category32 import apply_overrides as category32_apply
from regions32 import intro as region32_intro
a=load_source(src/'places-all.json'); category32_report=category32_apply(a,src); a+=funeral_places(src,a); from tourapi import integrate as tour_integrate; tour_integrate(src,a); seo=load_source(src/'seo-pages.json'); merged=load_source(src/'merged-ids.json'); m=load(S/'data/manifest.json'); report=load(S/'data/build-report.json'); 
from settings import ENABLE_KAKAO_LINKS,ENABLE_ADFIT,RELEASE_MODE,FORMS_LIVE,FORM_ENDPOINT
from region_rules import dong_key,display_services,seo_pages,recount,indexable
seo,alias_redirects=seo_pages(seo+funeral_seo(a))
assert all(p.get('geoSource') in (None,'public-data','소상공인시장진흥공단 상가(상권)정보 2026-09') and not p.get('kakaoPlaceId') and not p.get('kakaoMapUrl') and (not p.get('roadAddress') or p.get('geoSource')=='소상공인시장진흥공단 상가(상권)정보 2026-09') for p in a)
if not ENABLE_KAKAO_LINKS:
 for p in a:p['kakaoPlaceId']=None;p['kakaoMapUrl']=None
from admin import apply,schedules,active
snapshot=load(R/'build-admin-snapshot.json'); reject_funeral_overlays(snapshot,a); assert apply(a,snapshot)==report['admin']['corrections']
from hospital import annotate,telephone
annotate(a,src)
from review_integrations import score,load_ids,config as review_config,google_enabled
for p in a:p["infoCompleteness"]=score(p)
review_ids=load_ids(src,{p["id"] for p in a}); review_cfg=review_config()
from operations import annotate as ops_annotate,rank as ops_rank,compact_index
from owner_photos import load_owner_photos
owner_photos=load_owner_photos(src,a,merged)
ops_annotate(a,src,review_ids,merged)
from cards22 import annotate as own_ratings
from v13 import content
reviews,_=content(src,S,{p['id'] for p in a},merged); own_ratings(a,reviews)
by={p['id']:p for p in a}
assert len(by)==len(a)==m['total']; assert not by.keys()&merged.keys() and set(merged.values())<=by.keys()
seen={}; actual=collections.Counter(); idx=collections.defaultdict(set)
for sh in m['shards']:
 full=load(S/sh['full']); rows=load(S/sh['index']); assert len(full)==len(rows)==sh['count']; assert set(sh['services'])=={v for p in full for v in p['services']}
 for p,arr in zip(full,rows):
  i=p['id'];assert i not in seen and p==by[i];seen[i]=p;assert arr==[p.get(f) for f in m['fields']]
  for v in display_services(p):
   actual[v]+=1
   for sig,d in {(None,None),(p['sigungu'],None),(p['sigungu'],dong_key(p['sido'],p['sigungu'],p['dongKey']))}:idx[v,p['sido'],sig,d].add(i)
assert seen==by and actual==report['serviceCounts']
assert report['categoryOverrides']==category32_report
lookup={k:v for f in (S/'data/lookup').glob('*.json') for k,v in load(f).items()}; assert set(lookup)==set(by)
for sh in m['shards']:
 assert all(lookup[p['id']]==sh['key'] for p in load(S/sh['full']))
assert load(S/'data/merged-ids.json')==merged
ld_re=re.compile(r'<script type="application/ld\+json">(.*?)</script>',re.S)
row_re=re.compile(r'<li class="seo-row"><a href="/place/([pf]\d+)/"')
expected={'/','/regions/','/owner/','/privacy/','/terms/','/sources/','/owner/pricing/','/owner/terms-ads/','/information-score/','/naver-search/','/compare/','/recommendation-policy/'}
expected.update(extra_paths(src))
expected.update(json.loads((S/'data/build-report.json').read_text(encoding='utf-8'))['themePaths'])
regionpaths={x['path'].rstrip('/')+'/' for x in seo}
meta_keys=['og:title','og:description','og:url','og:image','og:type','twitter:card','naver-site-verification','google-site-verification']
def valid_meta(h):
 assert all(re.search(r'<meta (?:name|property)="'+k+r'" content="[^"]*">',h) for k in meta_keys)
 assert re.search(r'<meta property="og:url" content="([^"]+)">',h)[1]==re.search(r'<link rel="canonical" href="([^"]+)">',h)[1]
def valid_crumb(h,ld,path):
 assert ld['@type']=='BreadcrumbList' and ld['itemListElement'][0]['name']=='홈'
 items=ld['itemListElement'];assert [i['position'] for i in items]==list(range(1,len(items)+1));assert urllib.parse.unquote(urllib.parse.urlsplit(items[-1]['item']).path)==path
 c=re.search(r'<nav class="breadcrumbs".*?</nav>',h)[0]
 assert all(html.escape(i['name'],quote=True) in c for i in items)
 assert all(urllib.parse.unquote(urllib.parse.urlsplit(i['item']).path) in regionpaths|{'/'} for i in items[:-1])
 assert [html.unescape(x) for x in re.findall(r'<a href="([^"]+)"',c)]==[urllib.parse.unquote(urllib.parse.urlsplit(i['item']).path) for i in items[:-1]]
def exact_coord(p):return p.get('geoPrecision')=='exact' and all(type(p.get(k)) in (int,float) and math.isfinite(p[k]) and 0<abs(p[k])<=lim for k,lim in [('lat',90),('lng',180)])
fields=('phone','hours','closedDays','parking','indoor','outdoor','petSize','petSizeSmall','petSizeMedium','petSizeLarge','petFee','restrictions','floorAllowed','terrace','carrierRequired','vaccinationCheck','menu','description','homepage')
def tier(p):return 0 if '식약처 인증' in (p.get('tags') or []) else 1 if '등록업체' in (p.get('tags') or []) else 2 if any(t in str(p.get('source')) for t in ('식약처','농림축산식품부','한국문화정보원','공공데이터','한국관광공사')) else 3
def known(v):return v not in (None,'',[],{}) and (not isinstance(v,str) or bool(v.strip()) and v.strip() not in ('확인 필요','미확인','정보 없음','-'))
def sortkey(p,sv):return (1,*neutral_key(p)) if is_funeral(p) else (0,*ops_rank(p),tier(p),not exact_coord(p),-sum(known(p.get(k)) for k in fields),('카페' if p['category']=='애견카페' else p['category']) not in sv,p['name'],p['id'])
related_count=0
areas={}
empty_paths=set(); noindex_paths=set()
report_by_path={r['path']:r for r in report['regionCounts']}
assert len(report_by_path)==len(seo)

for item in seo:
 f=item['filter'];sv=f['service'] if isinstance(f['service'],list) else [f['service']];ids=set().union(*(idx[v,f['sido'],f['sigungu'],dong_key(f['sido'],f['sigungu'],f['dongKey'])] for v in sv));ids={i for i in ids if match(by[i],f)};path=item['path'].rstrip('/')+'/';expected.add(path);areas[path]=ids
 h=(S/path.lstrip('/')/'index.html').read_text(encoding='utf-8');links=row_re.findall(h);ld=json.loads(ld_re.search(h)[1]); assert len(links)==len(ids) and set(links)==ids and ld['numberOfItems']==len(ids) and [x['url'].split('/')[-2] for x in ld['itemListElement']]==links;assert links==[p['id'] for p in sorted((by[i] for i in ids),key=lambda p:sortkey(p,sv))];assert '<link rel="canonical"' in h and '<meta name="description"' in h
 assert report_by_path[path]['actualCount']==len(ids) and report_by_path[path]['sourceCount']==item['count']
 if not ids:empty_paths.add(path)
 if not indexable(item,len(ids)):
  noindex_paths.add(path);assert 'name="robots" content="noindex,follow"' in h
 assert report_by_path[path]['indexable']==indexable(item,len(ids))
 title,desc,h1=recount(item,len(ids));assert '<title>'+html.escape(title,quote=True)+'</title>' in h and '<h1>'+html.escape(h1,quote=True)+'</h1>' in h and 'content="'+html.escape(desc,quote=True)+'"' in h
 valid_meta(h);lds=[json.loads(x) for x in ld_re.findall(h)];assert len(lds)==3;valid_crumb(h,lds[1],path);faq=lds[2];assert faq['@type']=='FAQPage' and 2<=len(faq['mainEntity'])<=3
 for q in faq['mainEntity']:
  assert html.escape(q['name'],quote=True) in h and html.escape(q['acceptedAnswer']['text'],quote=True) in h
 related=re.search(r'<section class="panel related-regions".*?</section>',h)[0];targets=[html.unescape(x) for x in re.findall(r'<a href="([^"]+)"',related)];assert set(targets)<=regionpaths and len(targets)==len(set(targets)) and path not in targets;related_count+=len(targets)
 assert 'region-summary' in h
 if item['category'] not in ('funeral','ossuary'):assert html.escape(region32_intro(item,[by[i] for i in ids]),quote=True) in h
ads,premium=schedules(snapshot,areas,set(by))
for path,rs in ads.items():
 h=(S/path.lstrip('/')/'index.html').read_text();assert h.count('data-slot=')==len(rs)
 for r in rs:assert f'data-slot="{r["slot"]}" data-start="{r["start_date"]}" data-end="{r["end_date"]}"' in h
geo=collections.Counter();kakao_count=0;road_count=0
for p in a:
 i=p['id'];path='/place/'+i+'/';expected.add(path);h=(S/path.lstrip('/')/'index.html').read_text(encoding='utf-8');ld=json.loads(ld_re.search(h)[1]);exact=p['geoPrecision']=='exact' and all(type(p[k]) in (int,float) and math.isfinite(p[k]) and 0<abs(p[k])<=lim for k,lim in [('lat',90),('lng',180)])
 if score(p) is not None:
  assert f'정보 충실도 <b>{score(p)}/100</b>' in h
  assert ('data-google-load' in h)==google_enabled(p,review_ids,review_cfg)
  assert ('/naver-search/?' in h)==bool(review_cfg['naverEndpoint'])
  assert ('class="cover owner-photo-cover"' in h)==bool(p.get('ownerPhoto'))
 else:assert 'data-eg-reviews' not in h and '정보 충실도 <b>' not in h
 if '동물병원' in p['services']:
  assert ('24시간 운영 (운영시간 데이터상)' in h)==bool(p.get('hours24Data'))
  assert ('야간 응급진료 확인 · 공식 출처' in h)==bool(p.get('nightEmergencySource'))
  if telephone(p.get('phone')):assert 'href="tel:'+telephone(p['phone'])+'"' in h
 assert h.count('class="panel premium-detail"')==len(premium.get(i,[]))
 assert ('영업 여부 확인 필요' in h)==('동물병원' in p['services'] and not p.get('openStatusSource'));assert '위치 정보 출처' in h
 kid=p.get('kakaoPlaceId');road=p.get('roadAddress');assert '<b>도로명주소</b>' in h
 if road:assert html.escape(road,quote=True) in h and ld['address']['streetAddress']==road;road_count+=1
 if kid:assert re.fullmatch(r'[0-9]+',kid) and f'href="https://place.map.kakao.com/{kid}"' in h;kakao_count+=1
 else:assert '카카오맵에서 보기' not in h
 tags=p.get('tags') or [];label='식약처 공식 인증' if '식약처 인증' in tags else '등록업체' if '등록업체' in tags else '공공데이터' if any(t in str(p.get('source')) for t in ('식약처','농림축산식품부','한국문화정보원','공공데이터','한국관광공사')) else '제보'
 assert ('geo' in ld)==exact and f'>{label}</span>' in h and 'source-badge' in h;assert ld['@type']=={'동물병원':'VeterinaryCare','식당':'Restaurant','카페':'CafeOrCoffeeShop','애견카페':'CafeOrCoffeeShop','숙소':'LodgingBusiness','여행지':'TouristAttraction'}.get(p['category'],'LocalBusiness') and ld['name']==p['name'];assert ({x['itemOffered']['name'] for x in ld['makesOffer']} if ld['@type']!='TouristAttraction' else {x['value'] for x in ld['additionalProperty']})==set(p['services']);valid_meta(h);valid_crumb(h,json.loads(ld_re.findall(h)[1]),path); assert 'type=correction' in h and 'type=closure' in h and 'type=owner' in h; assert [h.index('<h2>'+v+'</h2>') for v in ['동반 조건','운영시간·휴무','주차','연락처','출처·확인일']]==sorted(h.index('<h2>'+v+'</h2>') for v in ['동반 조건','운영시간·휴무','주차','연락처','출처·확인일']);geo['exact' if exact else 'approx' if p['geoPrecision'] in ('dong','sigungu') else 'none']+=1

for o,n in merged.items():
 h=(S/'place'/o/'index.html').read_text(encoding='utf-8');assert f'content="0;url=/place/{n}/"' in h and f'href="{report["siteUrl"]}/place/{n}/"' in h
assert (S/'sitemap.xml').stat().st_size<=52428800
locs=[urllib.parse.unquote(urllib.parse.urlsplit(e.text).path) for e in ET.parse(S/'sitemap.xml').findall('{*}url/{*}loc')];assert len(locs)<=50000 and len(locs)==len(set(locs)) and set(locs)==expected-noindex_paths-{'/contribute/','/naver-search/','/compare/'}
from images26 import verify_sitemap
verify_sitemap(S,a,{'/','/regions/'} | {x['path'].rstrip('/')+'/' for x in seo} | {'/place/'+p['id']+'/' for p in a if p.get('tourPhoto') or p.get('tourPhotos')})
redirects=load(R/'deploy/redirects.json');assert len(redirects)==len(merged)+6+len(alias_redirects)
for old,new in redirects.items():
 assert new in expected and old not in expected and (S/old.strip('/')/'index.html').is_file();h=(S/old.strip('/')/'index.html').read_text();assert f'content="0;url={new}"' in h and 'href="'+report['siteUrl']+urllib.parse.quote(new,safe='/-._~')+'"' in h
assert geo['exact']==report['mapped']; assert len([f for f in S.rglob('*.html') if f.name!='offline.html'])==len(expected)+len(redirects)
form=(S/'owner/index.html').read_text()
if FORMS_LIVE:assert all(f'name="{n}"' in form for n in ['privacyConsent','petSizeLarge','indoor','parking','operating']);assert 'type="checkbox" required name="privacyConsent"' in form
for path in ['/privacy/','/terms/','/sources/','/owner/terms-ads/']:assert (S/path.strip('/')/'index.html').is_file()
for f in S.rglob('*.html'):
 if f.name!='offline.html':valid_meta(f.read_text(encoding='utf-8'))
assert (S/'og-brand.png').is_file()
ns=(S/'naver-search/index.html').read_text();assert 'name="robots" content="noindex,follow"' in ns and 'adfit.js' not in ns and '/owner/pricing/' not in ns and '/core.js' not in ns
assert road_count==report['roadAddressCount'] and kakao_count==report['kakaoIdCount']
assert not (S/'_redirects').exists() and not (S/'_headers').exists() and (S/'.nojekyll').is_file()
home=(S/'index.html').read_text();privacy=(S/'privacy/index.html').read_text()
assert report['formsEnabled']==FORMS_LIVE
for text in (home,form):
 assert 'data-netlify=' not in text and 'netlify-honeypot' not in text
 if FORMS_LIVE:
  assert 'action="'+html.escape(FORM_ENDPOINT,quote=True)+'"' in text and 'data-live="true"' in text
  assert all('name="'+k+'"' in text for k in ('acquisitionChannel','utm_source','utm_medium','utm_campaign','utm_content','utm_term'))
  assert all('value="'+k+'"' in text for k in ('blog','cafe','instagram','threads','store_qr','other'))
 else:assert 'name="eodigagae-launch"' not in text and 'id="intake"' not in text
assert 'Netlify' not in privacy
assert all(redirects.get(k)==v for k,v in alias_redirects.items())
assert ('Disallow: /\n' in (S/'robots.txt').read_text())==report['preview']
print(json.dumps({'relatedLinks':related_count,'regionFaqPages':len(seo),'breadcrumbPages':len(a)+len(seo),'socialMetaPages':len(expected)+len(redirects),'uniquePlaces' :len(a),'regionPages':len(seo),'regionMismatch':0,'redirects':len(redirects),'sitemapUrls':len(locs),'htmlFiles':len(expected)+len(redirects),'coordinateCounts':geo,'serviceCounts':actual,'kakaoLinks':kakao_count,'roadAddresses':road_count,'aliasRedirects':len(alias_redirects),'emptyRegionPages':len(empty_paths),'adjustedRegionCounts':report['adjustedRegionCounts'],'travelExcluded':report['travelExcluded'],'formsEnabled':report['formsEnabled'],'indexingAllowed':not report['preview'],'admin':report['admin'],'status':'PASS'},ensure_ascii=False,indent=2))

from v13 import DISCLOSURE, ROLE, ritual_data
def verify_funeral_output(root):
 root=pathlib.Path(root);src=root/'source';site=root/'site';rows=funeral_places(src,[]);ids=[p['id'] for p in rows];assert len(ids)==89
 def read(path):return (site/path.strip('/')/'index.html').read_text(encoding='utf-8')
 def row_ids(h):return re.findall(r'<li class="seo-row"><a href="/place/(f\d+)/"',h)
 def no_paid(h):
  assert 'class="panel premium-detail"' not in h and 'data-slot=' not in h and '추천 매장' not in h and '이 자리에 내 매장 올리기' not in h and 'kakao_adfit' not in h and 'kakao_ad_area' not in h and 'data-ad-unit=' not in h and '인기 매장' not in h and 'BEST' not in h
 h=read('/funeral/');assert row_ids(h)==ids and DISCLOSURE in h;no_paid(h)
 for s in funeral_seo(rows):
  h=read(s['path']);f=s['filter'];from v13 import match
  want=[p['id'] for p in rows if p['sido']==f['sido'] and (not f['sigungu'] or p['sigungu']==f['sigungu']) and (not f['dongKey'] or p['dongKey']==f['dongKey']) and match(p,f)]
  assert row_ids(h)==want and len(want)==s['count'],s['path'];no_paid(h);assert DISCLOSURE in h
 for p in rows:
  h=read('/place/'+p['id']+'/');assert DISCLOSURE in h and ROLE in h and '어디가개 상담 신청' in h and 'funeral-actions' in h;no_paid(h)
  if p.get('phone'):assert 'href="tel:'+re.sub(r'[^0-9+]','',p['phone'])+'"' in h
  else:assert '업체 직접 문의처 확인 (전화번호 미제공)' in h
  assert '공공 목록에 기재된 서비스' in h
  assert not re.search(r'\d[\d,]*\s*만원|\d[\d,]*\s*원\s*(?:부터|~)',h),p['id']
 g=read('/funeral/guide/');assert DISCLOSURE in g and ROLE in g and '21그램' not in g and '35만원' not in g;no_paid(g)
 t=read('/terms/');assert ROLE in t and DISCLOSURE in t
 p=read('/privacy/');assert '희망 연락 시간' in p and '반려동물 종류 및 체중(선택)' not in p
 for r in ritual_data(src):assert '출처 확인일 기준, 방문·문의 전 확인' in read('/memorial/rituals/'+r['slug']+'/')
 print('v1.3.2 funeral verification PASS:',len(rows),'places;',len(funeral_seo(rows)),'region pages')


verify_funeral_output(R)

# v1.6 first-screen data and app association checks
from app_release import asset_links
assert load(S/'.well-known/assetlinks.json')==asset_links()
home=(S/'index.html').read_text(encoding='utf-8')
boot=json.loads(re.search(r'<script type="application/json" id="homeBoot">(.*?)</script>',home,re.S)[1])
seoul=sorted([p for p in a if p.get('sido')=='서울특별시' and display_services(p)],key=lambda p:(1,*neutral_key(p)) if is_funeral(p) else (0,not (p.get('ownerPhoto') or p.get('tourPhoto') or p.get('googlePlaceId')),'동물병원' in (p.get('services') or []),__import__('cards22').rot(p['id'],re.search(r'<meta name="eg-rotation" content="([^"]*)">',(S/'index.html').read_text())[1])/(7 if (p.get('ownerPhoto') or p.get('tourPhoto')) else 1) if (p.get('ownerPhoto') or p.get('tourPhoto') or p.get('googlePlaceId')) else 0,*ops_rank(p),tier(p),not exact_coord(p),p['id']))
assert boot['total']==len(seoul) and boot['mapped']==sum(map(exact_coord,seoul))
assert [p['id'] for p in boot['rows']]==[p['id'] for p in seoul[:20]]
assert all(x['key']==lookup[x['id']] and all(x[f]==by[x['id']].get(f) for f in m['fields']) for x in boot['rows'])
assert 'id="pwaInstall"' in home and home.count('data-cat=')==10
assert indexable({'level':'dong'},3) and not indexable({'level':'dong'},2) and indexable({'level':'sigungu'},1)
assert '오프라인에 저장하지 않습니다' in (S/'offline.html').read_text()
print('v1.6 snapshot, region indexing and app association checks PASS')

# v1.8 nationwide first-party search index must exactly reflect visible public listings and nonempty SEO pages.
search=load(S/'data/search-index.json')
assert search['version']==1
assert search['places']==[[p['id'],p['name'],p['sido'],p.get('sigungu'),dong_key(p['sido'],p.get('sigungu'),p.get('dongKey')) or p.get('dong'),' · '.join(display_services(p))] for p in a if display_services(p)]
# Build report keys differ across older releases; use the actual verified SEO membership index.
expected_regions=[]
for s in seo:
 f=s['filter']; sv=f['service'] if isinstance(f['service'],list) else [f['service']]
 ids=set().union(*(idx[c,f['sido'],f['sigungu'],dong_key(f['sido'],f['sigungu'],f['dongKey'])] for c in sv))
 n=sum(match(by[i],f) for i in ids)
 if n:expected_regions.append([recount(s,n)[2],s['path'].rstrip('/')+'/',s['sido'],s['sigungu'],f['dongKey'],f['service'],n])
assert search['regions']==expected_regions
assert all((S/r[1].lstrip('/')/'index.html').is_file() for r in search['regions'])
assert all((S/'place'/r[0]/'index.html').is_file() for r in search['places'])
assert 'role="combobox"' in home and 'id="searchSuggestions"' in home and '/data/search-index.json' not in home
print('v1.8 search index verification PASS:',len(search['places']),'places;',len(search['regions']),'region suggestions')

assert load(S/'data/search-compact.json')==compact_index(search)
print('v1.9 compact index verified')

# v2.0: every visible exact point is covered by its shard's geographic bounds.
geo=collections.defaultdict(list)
for p in a:
 if exact_coord(p) and display_services(p):geo[lookup[p['id']]].append((p['lat'],p['lng']))
assert m['version']==230
for sh in m['shards']:
 pts=geo[sh['key']];expected_bounds=[min(x[0] for x in pts),min(x[1] for x in pts),max(x[0] for x in pts),max(x[1] for x in pts)] if pts else None
 assert sh['bounds']==expected_bounds,sh['key']
assert 'id="mapLocate"' in home and 'id="mapSearchArea"' in home and '<option value="distance">' in home
assert 'dapi.kakao.com' not in home and 'dapi.kakao.com' not in (S/'core.js').read_text()
assert 'autoload=false&libraries=clusterer' in (S/'kakao-map.js').read_text()
assert 'globalThis.EGKakaoKey='+json.dumps(os.environ.get('KAKAO_JS_KEY','').strip()) in (S/'core.js').read_text()
assert '카카오 지도 사용 시' in privacy
print('v2.0 shard bounds, lazy SDK, key injection and privacy verification PASS:',len(m['shards']),'shards;',sum(map(len,geo.values())),'exact visible places')

# v2.1: routing schema and comparison/privacy regression guards.
import base64
route_ix=load(S/'data/search-routes.json')
assert route_ix['version']==1 and route_ix['bits']==32768 and set(route_ix['shards'])=={sh['key'] for sh in m['shards']}
assert all(len(base64.b64decode(v,validate=True))==4096 for v in route_ix['shards'].values())
compare_page=(S/'compare/index.html').read_text();assert 'id="compareList"' in compare_page and 'noindex,follow' in compare_page and '동반 조건 비교함' in privacy
for p in a:
 h=(S/'place'/p['id']/'index.html').read_text();assert h.count('class="panel unknown-summary"')<=1
 assert ('data-compare=' in h)==(score(p) is not None)
 assert ('data-hero-rating' in h)==(score(p) is not None)
assert 'eg-public-v290-core' in (S/'sw.js').read_text()
print('v2.1 routing schema, comparison, attribution slot and cache version PASS')
# v2.2: own ratings, image license and curation integrity.
from tourapi import licensed
from cards22 import curated as curated22
from tourapi import report as tour_report
assert 'eg-place-card' in home and 'eg-art23' in home
expected_curation=curated22(a,lookup)
assert ('id="curatedData"' in home)==bool(expected_curation)
assert load(S/'data/tourapi-summary.json')==tour_report(src,a,load(S/'data/tourapi-audit.json'))
assert re.search(r'/core\.js\?v=[0-9a-f]{16}',home) and re.search(r'/bundle\.css\?v=[0-9a-f]{16}',home) and re.search(r'/discovery\.js\?v=[0-9a-f]{16}',home)
assert load(S/'release.json')['version']==re.search(r'/core\.js\?v=([0-9a-f]{16})',home)[1]
assert 'skipWaiting()' in (S/'sw.js').read_text() and 'clients.claim()' in (S/'sw.js').read_text()
for p in a:
 assert (p['ownRating'] is None)==(p['ownReviewCount']==0)
 for ph in p.get('tourPhotos',[]):assert licensed({'cpyrhtDivCd':'Type'+ph['license'],'url':ph['src']},'url')
 if p.get('tourism'):
  h=(S/'place'/p['id']/'index.html').read_text();assert '한국관광공사 동반 여행 정보' in h
  if p.get('tourPhoto') and not p.get('ownerPhoto'):assert 'tour-photo-cover' in h
 if p['ownReviewCount']:
  h=(S/'place'/p['id']/'index.html').read_text();assert f'★ {p["ownRating"]:.1f}' in h
print('v2.2 card layout, versioned assets, licensed images and first-party ratings PASS')

from app28 import verify_manifest
verify_manifest(S)
