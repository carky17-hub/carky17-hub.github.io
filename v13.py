"""Additive funeral directory and moderated contributions; stdlib only."""
import collections, datetime, html, json, os, pathlib, re, shutil, urllib.parse
from region_rules import dong_key
E=lambda v:html.escape(str(v),quote=True)
SERVICE='장례·추모'
FUNERAL=('장례식장','화장장'); OSSUARY=('납골시설','봉안당','납골당')
SLUGS=dict(zip('서울특별시 부산광역시 대구광역시 인천광역시 광주광역시 대전광역시 울산광역시 세종특별자치시 경기도 강원특별자치도 충청북도 충청남도 전북특별자치도 전라남도 경상북도 경상남도 제주특별자치도'.split(),'seoul busan daegu incheon gwangju daejeon ulsan sejong gyeonggi gangwon chungbuk chungnam jeonbuk jeonnam gyeongbuk gyeongnam jeju'.split()))
SLUGS.update({'강원도':'gangwon','전라북도':'jeonbuk','전남광주통합특별시':'jeonnam-gwangju'})
EXTRA_PAGES={'/funeral/','/funeral/guide/','/memorial/rituals/','/contribute/','/review-policy/'}
def read(src,name):return json.loads((src/name).read_text(encoding='utf-8'))
def https(s):
 if not isinstance(s,str):return False
 u=urllib.parse.urlsplit(s);return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and not any(c.isspace() for c in s)
def date(s):return isinstance(s,str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',s)) and datetime.date.fromisoformat(s)<=datetime.date.today()+datetime.timedelta(days=1)
SOURCE_URL='https://www.animal.go.kr/front/awtis/shop/undertaker1List.do'
DISCLOSURE='어디가개는 상담 후 연결한 장례업체로부터 소개 수수료를 받습니다. 수수료는 보호자님께 추가로 청구되지 않으며, 장례 비용은 계약 전 업체에서 최종 확인하세요.'
ROLE='어디가개는 상담·업체 연결만 제공합니다. 사체 운송·수습·대금 대리수령은 하지 않습니다. 장례 계약 및 결제는 보호자와 업체가 직접 진행합니다.'
PRIVACY_TEXT='연락처, 희망 지역, 희망 방식, 희망 연락 시간 및 동의 기록을 상담·회신 목적으로 처리합니다. 접수 자료는 상담 종료 후 3개월 이내 파기합니다. 상담 연결 전에 제공받는 업체명, 목적, 항목, 보유기간 및 동의 거부권을 안내하고 별도 동의를 받은 경우에만 필요한 연락처 등을 제공합니다. 제공에 동의하지 않아도 업체 직접 문의가 가능합니다. 공개 저장소에 접수 원본을 저장하지 않습니다. 외부 폼 위탁·국외 이전은 온라인 신청 안내를 따릅니다.'
def is_funeral(p):return SERVICE in (p.get('services') or [])
def neutral_key(p):return (p.get('sido') or '',p.get('sigungu') or '',p.get('name') or '',p['id'])
def subtypes(p):
 v=p.get('subType');types=set(v if isinstance(v,list) else re.split(r'[,/·;|]+',v or ''))
 # The supplied facility type and listed services are distinct: 봉안 is listed as a service, not proof of a separate licensed site.
 if '봉안' in (p.get('funeralServices') or []):types.add('봉안시설');types.add('봉안당')
 return types
def match(p,f):return not f.get('subTypes') or bool({x.strip() for x in subtypes(p)} & set(f['subTypes']))
def funeral_places(src,existing):
 data=read(src,'funeral-places.json'); assert isinstance(data,list) and len(data)==89, 'v1.3.2 requires supplied 89 rows; review future updates before changing count'
 ids={p['id'] for p in existing}; output=[]
 assert not any(is_funeral(p) for p in existing), 'Funeral records must originate only from funeral-places.json'
 for raw in data:
  assert set(('id','name','sido','sigungu','address','category','services','subType','funeralServices','geoPrecision','verified','source','sourceUrl','lastChecked','tags'))<=raw.keys(), 'Missing funeral fields'
  p=dict(raw)
  assert re.fullmatch(r'f[0-9]{4}',p['id']) and p['id'] not in ids and p['category']==SERVICE and p['services']==[SERVICE] and p['sido'] in SLUGS and p['name'] and p['address']
  assert p['sourceUrl']==SOURCE_URL and p['source']=='농림축산식품부 국가동물보호정보시스템 동물장묘업 등록현황' and date(p['lastChecked']) and '등록업체' in p['tags'] and subtypes(p)&set(FUNERAL+OSSUARY)
  assert not p.get('kakaoPlaceId') and not p.get('kakaoMapUrl') and p['geoPrecision'] in ('sido','sigungu') and p.get('lat') is None and p.get('lng') is None
  assert not any(p.get(k) for k in ('petFee','menu','price','priceRange','description')), 'No public price or unreviewed promotional copy'
  # Preserve source fields verbatim; only add compatibility defaults in memory.
  for k in ('dong','dongKey','licenseNo','updatedAt','geoSource','hours','closedDays','parking','indoor','outdoor','petSize','roadAddress'):p.setdefault(k,None)
  ids.add(p['id']);output.append(p)
 return sorted(output,key=neutral_key)
def reject_funeral_overlays(snapshot,places):
 ids={p['id'] for p in places if is_funeral(p)}
 for kind in ('ads','premium'):
  for r in snapshot['rows'][kind]:
   if r.get('place_id') in ids or (r.get('page_path') or '').startswith(('/funeral/','/ossuary/','/memorial/')):raise ValueError('Funeral paid placements not supported: '+str(r.get('place_id')))
 for r in snapshot['rows']['corrections']:
  if r.get('place_id') in ids and r.get('approved')=='TRUE':raise ValueError('Update funeral public-source file after verification, not CSV overlays: '+r['place_id'])
def funeral_seo(places):
 groups=collections.defaultdict(set)
 for p in places:
  if SERVICE not in p['services']:continue
  si=p['sido'];gu=p['sigungu'];d=dong_key(si,gu,p['dongKey'])
  for cat,types in [('funeral',FUNERAL),('ossuary',OSSUARY)]:
   if not match(p,{'subTypes':types}):continue
   for g,dn in [(None,None),(gu,None),(gu,d)]:
    if dn and not g:continue
    groups[cat,si,g,dn].add(p['id'])
 out=[]
 for (cat,si,gu,d),ids in sorted(groups.items(),key=lambda x:tuple(v or '' for v in x[0])):
  if si not in SLUGS:raise ValueError(si)
  kw=f'{d or gu or si} 반려동물 '+('장례식장' if cat=='funeral' else '납골당'); n=len(ids)
  path='/'+cat+'/'+SLUGS[si]+('/'+gu if gu else '')+('/'+d if d else '')
  for token in (gu,d):
   if token:assert '/' not in token and token not in ('.','..')
  out.append(dict(path=path,category=cat,sido=si,sigungu=gu,dong=d,level='dong' if d else 'sigungu' if gu else 'sido',mainKeyword=kw,subKeywords=[],count=n,title=f'{kw} {n}곳 | 어디가개',metaDescription=f'{kw} {n}곳의 공공 목록 정보를 확인하세요. 방문 전 허가 및 운영 여부를 문의하세요.',h1=f'{kw} {n}곳',intro='',filter=dict(service=SERVICE,sido=si,sigungu=gu,dongKey=d,subTypes=list(FUNERAL if cat=='funeral' else OSSUARY))))
 return out

def ritual_data(src):
 rows=read(src,'memorial-rituals.json'); seen=set()
 for r in rows:
  assert re.fullmatch(r'[a-z0-9-]+',r['slug']) and r['slug'] not in seen and all(r.get(k) for k in ('name','region','address','format','status','sourceUrl','checkedOn')) and https(r['sourceUrl']) and date(r['checkedOn']);seen.add(r['slug'])
 return rows

def extra_paths(src):return EXTRA_PAGES|{'/memorial/rituals/'+r['slug']+'/' for r in ritual_data(src)}

def content(src,site,ids,merged):
 """Public source files contain approved material ONLY. Never commit pending records or evidence."""
 out=[collections.defaultdict(list),collections.defaultdict(list)]; seen=set()
 for i,(fn,fields) in enumerate([('reviews.json',{'id','placeId','approved','publishedOn','visitOn','nickname','text','relationship','benefit','disclosure','rightsConfirmed'}),('photos.json',{'id','placeId','approved','publishedOn','filename','caption','credit','rightsConfirmed','ownerConfirmed','advertising'})]):
  for r in read(src,fn):
   assert set(r)==fields and r['approved'] is True and r['rightsConfirmed'] is True and date(r['publishedOn']) and re.fullmatch(r'[a-zA-Z0-9_-]+',r['id']) and (i,r['id']) not in seen, 'Only approved public content permitted'
   seen.add((i,r['id'])); pid=merged.get(r['placeId'],r['placeId']);assert pid in ids
   if pid.startswith('f'):
    assert i==0 and r['relationship']=='customer' and r['benefit']=='none' or i==1 and r['advertising'] is False, 'Paid funeral content prohibited' 
   if i==0:
    assert date(r['visitOn']) and r['visitOn']<=r['publishedOn'] and 20<=len(r['text'])<=2000 and 1<=len(r['nickname'])<=30 and r['relationship'] in ('customer','owner_or_staff') and r['benefit'] in ('none','provided','discount','payment','other') and (r['benefit']=='none' and r['relationship']=='customer' or bool(r['disclosure'].strip()))
    assert len(r['disclosure'])<=300
   else:
    assert r['ownerConfirmed'] is True and type(r['advertising']) is bool and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)',r['filename']) and 0<len(r['caption'])<=150 and 0<len(r['credit'])<=100
    f=src/'public-photos'/r['filename']; assert f.is_file() and 0<f.stat().st_size<=5_000_000
    head=f.read_bytes()[:12]; assert (f.suffix in ('.jpg','.jpeg') and head.startswith(b'\xff\xd8\xff')) or (f.suffix=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n')) or (f.suffix=='.webp' and head[:4]==b'RIFF' and head[8:12]==b'WEBP')
    dest=site/'approved-photos'/f.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(f,dest)
   out[i][pid].append(r)
 return out

def detail_content(pid,reviews,photos):
 h='<section class="panel" id="photos"><h2>사장님 제공 사진</h2>'
 for r in photos.get(pid,[]):
  h+=f'<figure class="approved-photo"><img loading="lazy" src="/approved-photos/{E(r["filename"])}" alt="{E(r["caption"])}"><figcaption>{"AD · " if r["advertising"] else ""}점주 제공 · {E(r["caption"])} · {E(r["credit"])} · 게시물 {E(r["id"])}</figcaption></figure>'
 if not photos.get(pid):h+='<p>게시 승인된 사진이 없습니다.</p>'
 h+=f'<a class="btn" href="/contribute/?place={E(pid)}#owner-photo">사장님 사진 제출</a></section><section class="panel" id="reviews"><h2>이용자 방문 후기</h2>'
 for r in sorted(reviews.get(pid,[]),key=lambda r:r['publishedOn'],reverse=True):
  ad=r['relationship']!='customer' or r['benefit']!='none';h+=f'<article class="approved-review"><b>{E(r["nickname"])}</b> · 방문일 {E(r["visitOn"])} · 게시물 {E(r["id"])}<p>{"AD · 이해관계 있음 · " + E(r["disclosure"]) if ad else "혜택 없음 (작성자 신고)"}</p><p>{E(r["text"])}</p></article>'
 if not reviews.get(pid):h+='<p>검수 후 공개된 방문 후기가 없습니다.</p>'
 return h+f'<p>검수 통과는 실제 방문이나 후기 내용 전체를 보증하지 않습니다.</p><a class="btn" href="/contribute/?place={E(pid)}#visit-review">방문 후기 제출</a> <a href="/review-policy/">후기·사진 운영 원칙 및 신고</a></section>'

def contributions():
 import settings as S
 from external_forms import contact_markup,notice
 if not S.FORMS_LIVE:return '<h1>후기·사진 제출</h1><p>온라인 제출은 아직 운영하지 않습니다.</p>'+contact_markup()+' <a href="/review-policy/">운영 원칙</a>'
 upload=S.flag('FORM_FILE_UPLOADS')
 def form(kind,fields,multipart=False):
  return f'<form class="panel intake" method="POST" action="{E(S.FORM_ENDPOINT)}"'+(' enctype="multipart/form-data"' if multipart else '')+'><input type="hidden" name="formKind" value="'+kind+'"><input type="hidden" name="policyVersion" value="'+E(S.POLICY_VERSION)+'"><label>업체 ID<input name="placeId" pattern="[pf][0-9]+" maxlength="20" '+('required' if kind=='visit-review' else '')+'></label><label>업체명<input name="placeName" required maxlength="120"></label>'+fields+'<label>회신 이메일<input name="email" type="email" required maxlength="254"></label><p>목적: 검수·회신 및 동의한 자료 게시. 비공개 신청 자료는 처리 후 3개월 이내 파기. 게시 자료는 삭제 요청 또는 게시 종료까지 보관합니다.</p><p>'+E(notice())+'</p><label><input type="checkbox" name="privacyConsent" value="yes" required> 개인정보 수집·이용 동의 (<a href="/privacy/">방침</a>)</label>'+('<label><input type="checkbox" name="transferConsent" value="yes" required> 국외 이전 동의</label>' if S.FORM_INTERNATIONAL_TRANSFER else '')+'<label><input type="checkbox" name="publicationRights" value="yes" required> 직접 작성·촬영했거나 게시 권한이 있으며 어디가개 공개 게시에 동의합니다.</label><button type="submit" class="btn primary">검수 요청 보내기</button></form>'
 review='<label>공개 닉네임<input name="nickname" required maxlength="30"></label><label>방문일<input type="date" name="visitOn" required></label><label>직접 이용한 경험<textarea name="text" minlength="20" maxlength="2000" required></textarea></label><label>관계<select name="relationship" required><option value="">선택</option><option value="customer">이용자</option><option value="owner_or_staff">점주·직원·관계자</option></select></label><label>혜택<select name="benefit" required><option value="">선택</option><option value="none">없음</option><option value="provided">무료 제공</option><option value="discount">할인·초대</option><option value="payment">원고료</option><option value="other">기타</option></select></label><label>이해관계 상세 (해당 시 필수)<textarea name="disclosure" maxlength="300"></textarea></label><label><input type="checkbox" name="actualVisit" required value="yes"> 실제 이용 경험이며 허위 후기나 타인의 후기가 아닙니다.</label>'
 photo='<label>점주·담당자 이름<input name="ownerName" required maxlength="80"></label><label>매장 공식 연락처<input name="phone" type="tel" required maxlength="40"></label><label>사진 설명<textarea name="caption" required maxlength="150"></textarea></label>'
 photo+=('<label>사진 파일 (JPG/PNG/WebP, 최대 10장·각 5MB)<input name="photos" type="file" accept="image/jpeg,image/png,image/webp" multiple required></label>' if upload else '<label>검수용 사진 공유 링크 (본인 소유 자료, 운영자 열람 가능)<input name="photoLink" type="url" required></label><p>현재 파일 첨부는 비활성 상태입니다. 사진 링크로 제출해 주세요.</p>')
 return '<h1>후기·사진 제출</h1><p>제출 즉시 공개되지 않습니다. 얼굴·번호판·영수증·개인정보가 보이는 자료는 제출하지 마세요.</p><a href="/review-policy/">운영 원칙</a><h2 id="visit-review">방문 후기</h2>'+form('visit-review',review)+'<h2 id="owner-photo">사장님 사진</h2>'+form('owner-photo',photo,upload)+'<script src="/contribute.js" defer></script>'

def funeral_cta(place_id='',region=''):
 query=urllib.parse.urlencode({'region':region}) if region else ''
 return '<a class="btn primary" href="/funeral/guide/'+('?' + E(query) if query else '')+'#inquiry">어디가개 상담 신청</a>'
def fee_notice():return '<p class="funeral-disclosure"><strong>'+E(DISCLOSURE)+'</strong></p>'
def funeral_actions(p,area=''):
 phone=re.sub(r'[^0-9+]','',p.get('phone') or '')
 direct=f'<a class="btn" href="tel:{E(phone)}">업체에 직접 문의 (전화)</a>' if re.fullmatch(r'\+?[0-9]{7,15}',phone) else f'<a class="btn" href="{SOURCE_URL}" rel="noopener noreferrer">업체 직접 문의처 확인 (전화번호 미제공)</a>'
 return '<section class="panel funeral-contact"><h2>장례 상담 및 직접 문의</h2><div class="funeral-actions">'+direct+funeral_cta(region=area)+'</div>'+fee_notice()+'<p>'+E(ROLE)+'</p><p><b>공공 목록에 기재된 서비스:</b> '+E(' · '.join(p.get('funeralServices') or []) or '확인 필요')+'</p><p>공공 목록에 기재된 주소·서비스입니다. 실제 시설 주소, 허가번호, 운영 여부와 계약 조건은 방문·문의 전 확인하세요. <a href="'+SOURCE_URL+'">공식 목록 확인</a></p></section>'
def funeral_inquiry():
 import settings as S
 from external_forms import contact_markup,notice
 h='<section class="panel" id="inquiry"><h2>어디가개 장례 상담 신청</h2>'+fee_notice()+'<p>'+E(ROLE)+'</p><p>신청 접수 후 운영자가 직접 전화 또는 카카오톡으로 연락하고, 보호자 동의를 얻어 제휴업체를 연결합니다. 신청만으로 예약·계약이 확정되지 않습니다. 즉시 응답을 보장하지 않습니다. 긴급한 경우 업체에 직접 문의할 수 있습니다.</p><p><a href="/funeral/">업체 목록에서 직접 문의</a></p>'
 # Kakao URL already validated by settings; never publish a guessed channel.
 h+=('<p>급한 문의: <a class="btn" href="'+E(S.KAKAO_CHANNEL_URL)+'" rel="noopener noreferrer">카카오톡 채널 문의</a></p>' if S.KAKAO_CHANNEL_URL else '')
 if not S.FORMS_LIVE:return h+'<p>온라인 상담 접수는 준비 중입니다.</p>'+contact_markup()+'</section>'
 return h+f'<form class="funeral-form" method="POST" action="{E(S.FORM_ENDPOINT)}"><input type="hidden" name="formKind" value="funeral-inquiry"><input type="hidden" name="policyVersion" value="{E(S.POLICY_VERSION)}"><label>연락처 (전화번호)<input name="contact" type="tel" autocomplete="tel" required maxlength="40"></label><label>희망 지역<input id="funeral-region" name="region" required maxlength="100"></label><label>희망 방식<select name="method" required><option value="">선택</option><option>장례·화장</option><option>봉안</option><option>추모 의식</option><option>아직 결정하지 못함</option></select></label><label>희망 연락 시간<select name="contactTime" required><option value="">선택</option><option>가능한 빠르게</option><option>오전 (09~12시)</option><option>오후 (12~18시)</option><option>저녁 (18~21시)</option><option>시간 무관</option></select></label><p>{E(PRIVACY_TEXT)}</p><p>{E(notice())}</p><label><input type="checkbox" name="privacyConsent" value="yes" required> 개인정보 수집·이용 동의 (<a href="/privacy/">방침</a>)</label>'+('<label><input type="checkbox" name="transferConsent" value="yes" required> 국외 이전 동의</label>' if S.FORM_INTERNATIONAL_TRANSFER else '')+fee_notice()+'<button class="btn primary" type="submit">상담 신청 보내기</button></form><script>document.getElementById("funeral-region").value=(new URLSearchParams(location.search).get("region")||"").slice(0,100);</script></section>'

def publish_pages(src,page,region_roots,places=()):
 rows=ritual_data(src)
 links=''.join(f'<li><a href="/memorial/rituals/{E(r["slug"])}/">{E(r["name"])}</a> · {E(r["region"])} · {E(r["status"])}</li>' for r in rows)
 page('/memorial/rituals/','반려동물 천도재·위령재 | 어디가개','공식 운영 안내 또는 언론 보도로 확인한 반려동물 추모 의식 목록.','<h1>반려동물 천도재·위령재</h1><p>종교적 추모 프로그램이며 동물장묘업 허가를 뜻하지 않습니다. 현재 접수 가능 여부를 확인하세요.</p><ul>'+links+'</ul><a href="/funeral/guide/">장례 가이드</a>')
 for r in rows:
  h=f'<h1>{E(r["name"])}</h1><p>{E(r["region"])} · {E(r["address"])}</p><section class="panel"><h2>운영 형태</h2><p>{E(r["format"])}</p><p>{E(r["status"])}</p><p>출처 확인일 기준, 방문·문의 전 확인 ({E(r["checkedOn"])})</p><a href="{E(r["sourceUrl"])}" rel="noopener noreferrer">출처 확인 (공식 안내 또는 보도)</a></section><p>사찰 추모 의식은 장례·화장·봉안시설 허가와 별개입니다.</p><a href="/memorial/rituals/">추모 목록</a>'
  if https(r.get('addressSourceUrl')):h+=f'<p><a href="{E(r["addressSourceUrl"])}" rel="noopener noreferrer">주소 확인 출처</a></p>'
  page('/memorial/rituals/'+r['slug']+'/',r['name']+' 반려동물 추모 | 어디가개',r['region']+' 반려동물 추모 의식 출처 및 확인일.',h)
 regionlinks=''.join(f'<li><a href="{E(p)}">{E(t)} ({n}곳)</a></li>' for p,t,n in sorted(region_roots,key=lambda r:r[1]) if p.startswith(('/funeral/','/ossuary/')) and n)
 directory=sorted((p for p in places if is_funeral(p)),key=neutral_key)
 listing='<h2>전체 공공 목록 ('+str(len(directory))+'곳)</h2><p>지역(시도·시군구), 업체명 순입니다. 제휴 여부와 무관하며 현재 허가 유효·영업 상태는 별도 확인이 필요합니다.</p><ul class="seo-list funeral-directory">'+''.join(f'<li class="seo-row"><a href="/place/{E(p["id"])}/"><strong>{E(p["name"])}</strong></a><div>{E(p["sido"])} · {E(p["sigungu"])} · {E(p["subType"])}</div></li>' for p in directory)+'</ul>'
 page('/funeral/','반려동물 장례·추모 | 어디가개','반려동물 장례식장, 화장장, 봉안시설 및 추모 의식 안내.','<h1>반려동물 장례·추모</h1><p>떠나보내는 시간을 준비하는 분을 위한 안내입니다.</p>'+funeral_cta()+fee_notice()+' <a class="btn" href="/funeral/guide/">장례 절차와 비용·법령</a> <a class="btn" href="/memorial/rituals/">천도재·위령재</a><h2>지역별 공공 목록 장묘업체</h2>'+('<ul>'+regionlinks+'</ul>' if regionlinks else '<p>허가 업체 데이터 준비 중입니다. <a href="https://www.animal.go.kr/">국가동물보호정보시스템에서 확인</a></p>')+listing)
 page('/funeral/guide/','반려동물 장례 가이드 | 어디가개','반려동물 장례 절차, 비용 확인 및 허가 업체와 사체 처리 법령 안내.',(src/'funeral-guide.html').read_text(encoding='utf-8')+funeral_inquiry())
 page('/contribute/','후기·사진 제출 | 어디가개','검수형 방문 후기와 사장님 사진 제출 안내.',contributions(),noindex=True)
 page('/review-policy/','후기·사진 운영 원칙 | 어디가개','허위 후기 금지, 이해관계 표시, 사진 게시 권한 및 삭제 요청 안내.',(src/'review-policy.html').read_text(encoding='utf-8'))
