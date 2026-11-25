"""Full data, static page and redirect validation; standard library only."""
import json,re,collections,pathlib,xml.etree.ElementTree as ET,urllib.parse,math,html,os
R=pathlib.Path(__file__).resolve().parent; S=R/'site'; src=R/'source'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
from source_data import load_source
from v13 import funeral_places,funeral_seo,match,extra_paths,is_funeral,neutral_key,reject_funeral_overlays
# v1.3.2 neutral funeral verification
a=load_source(src/'places-all.json'); a+=funeral_places(src,a); seo=load_source(src/'seo-pages.json'); merged=load_source(src/'merged-ids.json'); m=load(S/'data/manifest.json'); report=load(S/'data/build-report.json'); 
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
lookup={k:v for f in (S/'data/lookup').glob('*.json') for k,v in load(f).items()}; assert set(lookup)==set(by)
for sh in m['shards']:
 assert all(lookup[p['id']]==sh['key'] for p in load(S/sh['full']))
assert load(S/'data/merged-ids.json')==merged
ld_re=re.compile(r'<script type="application/ld\+json">(.*?)</script>',re.S)
row_re=re.compile(r'<li class="seo-row"><a href="/place/([pf]\d+)/"')
expected={'/','/regions/','/owner/','/privacy/','/terms/','/sources/','/owner/pricing/','/owner/terms-ads/'}
expected.update(extra_paths(src))
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
def tier(p):return 0 if '식약처 인증' in (p.get('tags') or []) else 1 if '등록업체' in (p.get('tags') or []) else 2 if any(t in str(p.get('source')) for t in ('식약처','농림축산식품부','한국문화정보원','공공데이터')) else 3
def known(v):return v not in (None,'',[],{}) and (not isinstance(v,str) or bool(v.strip()) and v.strip() not in ('확인 필요','미확인','정보 없음','-'))
def sortkey(p,sv):return (1,*neutral_key(p)) if is_funeral(p) else (0,tier(p),not exact_coord(p),-sum(known(p.get(k)) for k in fields),('카페' if p['category']=='애견카페' else p['category']) not in sv,p['name'],p['id'])
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
ads,premium=schedules(snapshot,areas,set(by))
for path,rs in ads.items():
 h=(S/path.lstrip('/')/'index.html').read_text();assert h.count('data-slot=')==len(rs)
 for r in rs:assert f'data-slot="{r["slot"]}" data-start="{r["start_date"]}" data-end="{r["end_date"]}"' in h
geo=collections.Counter();kakao_count=0;road_count=0
for p in a:
 i=p['id'];path='/place/'+i+'/';expected.add(path);h=(S/path.lstrip('/')/'index.html').read_text(encoding='utf-8');ld=json.loads(ld_re.search(h)[1]);exact=p['geoPrecision']=='exact' and all(type(p[k]) in (int,float) and math.isfinite(p[k]) and 0<abs(p[k])<=lim for k,lim in [('lat',90),('lng',180)])
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
 tags=p.get('tags') or [];label='식약처 공식 인증' if '식약처 인증' in tags else '등록업체' if '등록업체' in tags else '공공데이터' if any(t in str(p.get('source')) for t in ('식약처','농림축산식품부','한국문화정보원','공공데이터')) else '제보'
 assert ('geo' in ld)==exact and f'>{label}</span>' in h and 'source-badge' in h;assert ld['@type']=={'동물병원':'VeterinaryCare','식당':'Restaurant','카페':'CafeOrCoffeeShop','애견카페':'CafeOrCoffeeShop','숙소':'LodgingBusiness','여행지':'TouristAttraction'}.get(p['category'],'LocalBusiness') and ld['name']==p['name'];assert ({x['itemOffered']['name'] for x in ld['makesOffer']} if ld['@type']!='TouristAttraction' else {x['value'] for x in ld['additionalProperty']})==set(p['services']);valid_meta(h);valid_crumb(h,json.loads(ld_re.findall(h)[1]),path); assert 'type=correction' in h and 'type=closure' in h and 'type=owner' in h; assert [h.index('<h2>'+v+'</h2>') for v in ['동반 조건','운영시간·휴무','주차','연락처','출처·확인일']]==sorted(h.index('<h2>'+v+'</h2>') for v in ['동반 조건','운영시간·휴무','주차','연락처','출처·확인일']);geo['exact' if exact else 'approx' if p['geoPrecision'] in ('dong','sigungu') else 'none']+=1

for o,n in merged.items():
 h=(S/'place'/o/'index.html').read_text(encoding='utf-8');assert f'content="0;url=/place/{n}/"' in h and f'href="{report["siteUrl"]}/place/{n}/"' in h
assert (S/'sitemap.xml').stat().st_size<=52428800
locs=[urllib.parse.unquote(urllib.parse.urlsplit(e.text).path) for e in ET.parse(S/'sitemap.xml').findall('.//{*}loc')];assert len(locs)<=50000 and len(locs)==len(set(locs)) and set(locs)==expected-noindex_paths-{'/contribute/'}
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
seoul=sorted([p for p in a if p.get('sido')=='서울특별시' and display_services(p)],key=lambda p:(1,*neutral_key(p)) if is_funeral(p) else (0,tier(p),not exact_coord(p),p['id']))
assert boot['total']==len(seoul) and boot['mapped']==sum(map(exact_coord,seoul))
assert [p['id'] for p in boot['rows']]==[p['id'] for p in seoul[:12]]
assert all(x['key']==lookup[x['id']] and all(x[f]==by[x['id']].get(f) for f in m['fields']) for x in boot['rows'])
assert 'id="pwaInstall"' in home and home.count('data-cat=')==10
assert indexable({'level':'dong'},3) and not indexable({'level':'dong'},2) and indexable({'level':'sigungu'},1)
assert '오프라인에 저장하지 않습니다' in (S/'offline.html').read_text()
print('v1.6 snapshot, region indexing and app association checks PASS')
