"""v1.7: strictly separated provider content and local information completeness."""
import os, re, json, html
from urllib.parse import urlsplit
from settings import POLICY_APPROVED
E=lambda x:html.escape(str(x or ''),quote=True)
FIELDS=('address','phone','homepage','parking','indoor','outdoor','petSize','restrictions','geoPrecision','closedDays')
UNKNOWN={'','확인 필요','미확인','정보 없음','-','정보 미확인','null','미등록','없음'}
def known(v):
 if v is None:return False
 if isinstance(v,str):return v.strip() not in UNKNOWN
 if isinstance(v,(list,dict)):return bool(v)
 return True

def score(p):
 if '장례·추모' in p.get('services',[]):return None
 flags=[known(p.get(k)) if k!='geoPrecision' else p.get(k)=='exact' for k in FIELDS]
 official=bool(set(p.get('tags') or [])&{'식약처 인증','등록업체'}) or any(t in str(p.get('source') or '') for t in ('식약처','농림축산식품부','한국문화정보원','공공데이터','소상공인시장진흥공단'))
 hours=known(p.get('hours')) and bool(p.get('source') or p.get('operatorCorrections',{}).get('hours'))
 return 6*sum(flags)+20*int(official)+10*int(hours) # owner verification not implemented, 0/10

def load_ids(src,ids):
 d=json.loads((src/'google-place-ids.json').read_text(encoding='utf-8'))
 if not isinstance(d,dict) or any(k not in ids or not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{5,512}',v) for k,v in d.items()):raise ValueError('Invalid approved Google place IDs')
 if len(set(d.values()))!=len(d):raise ValueError('Duplicate Google place ID; manually review')
 return d

def config():
 endpoint=(os.environ.get('NAVER_WORKER_URL') or os.environ.get('NAVER_BLOG_WORKER_URL','')).strip().rstrip('/')
 mode=os.environ.get('GOOGLE_MODE','all').strip()
 if mode not in ('fallback','all','off'):raise ValueError('GOOGLE_MODE must be fallback, all or off')
 if endpoint:
  u=urlsplit(endpoint)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('','/blog'):raise ValueError('NAVER_WORKER_URL must be an HTTPS origin (legacy /blog allowed)')
  endpoint=u.scheme+'://'+u.netloc
 enabled=os.environ.get('REVIEW_APIS_APPROVED','false').lower()=='true' and POLICY_APPROVED
 nav=enabled and bool(endpoint) and os.environ.get('NAVER_SEARCH_APPROVED','false').lower()=='true'
 match=nav and os.environ.get('NAVER_MATCH_APPROVED','false').lower()=='true'
 image=nav and os.environ.get('NAVER_IMAGE_APPROVED','false').lower()=='true'
 # Card embedding is explicitly not supported by the reviewed terms. Never silently bypass.
 if os.environ.get('IMAGE_ON_CARDS','false').lower()=='true':raise ValueError('IMAGE_ON_CARDS requires separate written provider permission and a reviewed implementation; keep false')
 google_endpoint=os.environ.get('GOOGLE_WORKER_URL','').strip().rstrip('/')
 if google_endpoint:
  u=urlsplit(google_endpoint)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path:raise ValueError('GOOGLE_WORKER_URL must be an HTTPS origin')
 return {'googleKey':'', 'googleEndpoint':google_endpoint if enabled and (mode=='all' or mode=='fallback' and match) else '', 'naverEndpoint':endpoint if nav else '', 'photos':enabled and os.environ.get('GOOGLE_PHOTOS_ENABLED','false').lower()=='true', 'googleMode':mode,'naverMatch':bool(match),'naverImage':bool(image),'imageOnCards':False}

def google_enabled(p,ids,cfg):
 return bool(score(p) is not None and cfg['googleEndpoint'] and p.get('sigungu') and (p.get('roadAddress') or p.get('address')) and (cfg['googleMode']=='all' or cfg['googleMode']=='fallback' and cfg['naverMatch']))

def detail(p,ids,cfg):
 if score(p) is None:return ''
 from urllib.parse import quote,urlencode
 gid=ids.get(p['id'],'') if google_enabled(p,ids,cfg) else ''
 q=' '.join(str(x) for x in (p.get('name'),p.get('sido'),p.get('sigungu')) if x)
 nlink='https://map.naver.com/p/search/'+quote(q,safe='')
 nav=('<a class="btn" href="/naver-search/?'+E(urlencode({'q':q}))+'">네이버 블로그 검색결과 보기</a>' if cfg['naverEndpoint'] else '')
 h=f'<div class="eg-info-score">정보 충실도 <b>{score(p)}/100</b> · <a href="/information-score/">산식 보기</a><small>이용자 평점 또는 안전 인증이 아닙니다.</small></div><section class="panel external-review"><h2>외부 리뷰·사진 확인</h2><p><a class="btn" href="{E(nlink)}" target="_blank" rel="noopener noreferrer nofollow">네이버 평점·사진 보기</a> {nav}</p><p class="muted">네이버 별점 API는 제공되지 않습니다. 검색결과는 방문 후기 수와 다릅니다.</p></section>'
 if google_enabled(p,ids,cfg):
  h+=f'<section class="panel external-review" data-eg-reviews data-google-id="{E(gid)}" data-blog-query="{E(q)}" data-match-name="{E(p.get("name"))}" data-match-district="{E(p.get("sigungu"))}" data-match-sido="{E(p.get("sido"))}" data-match-address="{E(p.get("roadAddress") or p.get("address"))}"><h2>Google Maps 외부 정보</h2><button type="button" class="btn" data-google-load hidden>Google Maps 외부 정보</button><div data-google-result aria-live="polite"></div></section><script src="/reviews-config.js" defer></script><script src="/external-reviews.js" defer></script>'
 return h

SEARCH_HTML='''<h1>네이버 검색결과</h1><p>별도의 검색 화면입니다. 네이버 검색결과는 업체가 등록한 사진, 실제 방문 후기 또는 동반 조건을 증명하지 않습니다.</p><form id="naver-search-form"><label>업체명·지역 검색<input id="naver-query" maxlength="180" required></label><button type="submit" class="btn primary">지역 검색</button><button type="button" class="btn" data-kind="blog">블로그 검색</button><button type="button" class="btn" data-kind="image" hidden>이미지 검색</button></form><section id="naver-results" aria-live="polite"></section><p><a href="/">어디가개 홈</a> · <a href="/privacy/">개인정보처리방침</a></p><script src="/reviews-config.js" defer></script><script src="/naver-search.js" defer></script>'''

SCORE_HTML='''<h1>어디가개 정보 충실도 산식</h1><p>정보 충실도는 장소의 공개 정보가 얼마나 채워져 있는지 보여주는 지표입니다. 소비자 평점, 서비스 품질, 안전성, 실제 영업 및 동반 가능 여부에 대한 인증이 아닙니다. 순위·광고·장례업체 중립 목록에는 사용하지 않습니다.</p><h2>100점 기준</h2><ul><li>정보 항목 10개 × 6점 = 최대 60점: 주소, 전화, 홈페이지, 주차, 실내 동반, 실외 동반, 반려동물 크기, 제한사항, 정확 좌표, 휴무일. 미확인 값은 제외하며 명확한 불가 정보도 정보로 인정합니다.</li><li>공공데이터 출처 또는 공공 등록 표기: 20점. 현재 허가·영업을 보증하지 않습니다.</li><li>출처가 기재된 운영시간 데이터: 10점. 실시간 영업 확인은 아닙니다.</li><li>사장님 인증: 10점 예정. 인증 시스템이 없으므로 현재 모든 업체 0점, 최고 90점입니다.</li></ul><p>Google Maps 평점·평가 수, 네이버 검색결과 수, 광고 구매 여부는 산식에 포함하지 않습니다. 장례·추모에는 표시하지 않습니다.</p>'''
PRIVACY='''\n## 외부 검색 및 평점·사진\n- 외부 기능은 승인 후 작동합니다. Google Maps 정보는 업체 상세 화면 진입 시에만 조회하고 네이버 검색은 별도 화면에서 이용자가 선택한 경우에만 조회합니다. 네이버 API HUB에는 업체명·지역 검색어(별도 허락을 받은 매칭 기능은 공개 업체 주소 포함)가 Cloudflare Worker를 통해 전달됩니다. Google Maps에는 공개 업체명·주소 또는 장소 ID가 Cloudflare Worker를 통해 전달됩니다. 호출 한도 카운터만 저장하며 검색결과·사진·평점을 저장하지 않습니다. 외부 콘텐츠 제공자 및 이미지 호스트는 IP 등 접속 정보를 처리할 수 있습니다. 보호자 연락처·GPS·상담 내용은 전달하지 않습니다. 개인 정보를 검색어에 입력하지 마세요.\n- 검색결과·사진·평점은 복제하거나 장기 저장하지 않으며 공개 데이터와 자체 점수에 반영하지 않습니다. 운영자가 별도로 승인한 Google 장소 ID만 저장할 수 있으며 자동 조회 결과는 저장하지 않습니다. 공개 사용 전 처리 국가·보유기간·국외 이전 근거 및 제공자 정책을 확정합니다.\n- Google: https://policies.google.com/privacy / 네이버클라우드: https://www.ncloud.com/policy/privacy / Cloudflare: https://www.cloudflare.com/privacypolicy/\n'''
TERMS='''\n## 외부 콘텐츠\n- 네이버 검색결과는 별도 광고 없는 화면에서 제공하며 원문 링크와 출처를 유지합니다. 검색 결과 수는 방문 후기 수가 아니며 이미지 검색은 매장 사진 확인을 보증하지 않습니다. 검색결과를 업체 대표 이미지나 자체 점수로 사용하지 않습니다. Google Maps 정보는 별도 표시하며 Google 서비스 약관 https://policies.google.com/terms 및 Google Maps 추가 약관 https://www.google.com/help/terms_maps/ 이 적용됩니다.\n- 점주·방문자 사진은 저작권과 초상권을 확인하고 게시 권한을 받은 자료만 운영자 검수 후 게시합니다. 무단 복제, 허위 후기 및 이용자 오인 표시를 금지합니다.\n'''
