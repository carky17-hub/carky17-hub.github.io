"""v1.9 first-party discovery and evidence updates; no external API data stored."""
import datetime as dt, json, re, html, os, collections
from urllib.parse import urlsplit
from settings import flag, POLICY_APPROVED, POLICY_VERSION

def config():
 endpoint=os.getenv('ANALYTICS_WORKER_URL','').rstrip('/')
 if endpoint and endpoint!='https://eodigagae-api.carky17.workers.dev': raise ValueError('Use approved analytics Worker origin')
 enabled=flag('ENABLE_ANALYTICS')
 if enabled and (not endpoint or not POLICY_APPROVED or POLICY_VERSION.startswith('draft')):raise ValueError('Approve privacy and configure analytics Worker before enabling')
 return endpoint if enabled else ''

def annotate(places,src,google_ids,merged):
 today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date(); rows=json.loads((src/'information-checks.json').read_text());assert isinstance(rows,list)
 by={p['id']:p for p in places}; seen=set()
 for r in rows:
  assert set(r)=={'placeId','checkedOn','sourceUrl','fields','approved'} and r['approved'] is True
  pid=merged.get(r['placeId'],r['placeId']);assert pid in by and pid not in seen;seen.add(pid)
  d=dt.date.fromisoformat(r['checkedOn']);assert d<=today
  u=urlsplit(r['sourceUrl']);assert u.scheme=='https' and u.hostname and not u.username and not u.password and not u.fragment and not u.query and not any(c.isspace() for c in r['sourceUrl'])
  assert isinstance(r['fields'],list) and r['fields'] and len(set(r['fields']))==len(r['fields']) and set(r['fields'])<={'name','address','phone','hours','closedDays','indoor','outdoor','parking','petSize','petSizeLarge','operating','licenseNo','homepage'}
  by[pid]['informationCheck']={k:r[k] for k in ('checkedOn','sourceUrl','fields')}
 for p in places:
  p['googleMatchConfirmed']=p['id'] in google_ids and not p['id'].startswith('f')
  dates=[v.get('checkedOn') for v in p.get('operatorCorrections',{}).values()]+[p.get('lastChecked'),(p.get('informationCheck') or {}).get('checkedOn')]
  valid=[]
  for v in dates:
   try:
    d=dt.date.fromisoformat(v);assert d<=today;valid.append(d.isoformat())
   except (ValueError,TypeError,AssertionError):pass
  p['latestEvidenceDate']=max(valid,default=None)

def rank(p):return (-int(bool(p.get('ownerPhoto') or p.get('tourPhoto'))),int('동물병원' in (p.get('services') or [])),-int(bool(p.get('googleMatchConfirmed'))),-(p.get('infoCompleteness') or 0))

def compact_index(index):
 table=[]; ids={}
 def enc(x):
  if x is None:return -1
  if x not in ids:ids[x]=len(table);table.append(x)
  return ids[x]
 return {'version':2,'strings':table,'places':[[r[0],r[1],*[enc(x) for x in r[2:]]] for r in index['places']], 'regions':[[r[0],r[1],enc(r[2]),enc(r[3]),enc(r[4]),[enc(x) for x in r[5]] if isinstance(r[5],list) else enc(r[5]),r[6]] for r in index['regions']]}

PRIVACY='''\n## 선택적 이용 통계 (활성화 시)\n- 검색 실행·제안 선택, 전화·길찾기·저장·상담·사진 제보 링크 클릭의 일별 합계만 운영 개선에 이용합니다. 관광공사 외부 이미지의 로딩 성공·실패 횟수와 이미지 제공 호스트명도 일별로 집계합니다. 이미지 URL 경로와 쿼리, 검색어, 업체 ID, 연락처, 위치, 쿠키, 기기 ID, 방문 경로 또는 이용자별 기록을 통계에 포함하지 않습니다. Cloudflare로 HTTPS 요청이 전송되므로 통신 과정에서 IP 등 접속 정보가 처리될 수 있습니다. 자체 집계에 저장하지 않으며 Worker 요청 로그와 추적을 비활성화합니다. 집계 보유기간은 최대 90일(자동 삭제), 맞춤형 광고에는 사용하지 않습니다. 브라우저의 DNT/GPC 설정과 아래 통계 거부 설정을 존중합니다. 거부 여부만 브라우저에 저장하며 서버에는 보내지 않습니다. 개인정보 처리 위탁·국외 이전 조건은 활성화 전에 확정합니다.\n- 방문자 사진은 승인 후 선택한 공개 닉네임을 사진 크레딧에 표시할 수 있습니다. 닉네임 공개는 선택이며 혜택·협찬은 별도 표시합니다.\n'''
