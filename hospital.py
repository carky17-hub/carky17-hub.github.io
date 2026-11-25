"""Conservative hours classification and manually checked official provider evidence."""
import datetime,json,re,html,urllib.parse
E=lambda x:html.escape(str(x or ''),quote=True)
def telephone(value):
 if not isinstance(value,str) or not re.fullmatch(r'[+\d\s().-]+',value):return ''
 n=re.sub(r'[^\d+]','',value)
 return n if re.fullmatch(r'(?:0\d{8,10}|1\d{7}|\+82\d{8,10})',n) else ''
def all_day(p):
 # Only explicit daily all-day schedule, never name/tags, no known exceptions.
 h=re.sub(r'\s+','',str(p.get('hours') or ''))
 c=re.sub(r'\s+','',str(p.get('closedDays') or ''))
 return bool(re.fullmatch(r'(?:매일|월~일|연중)(?:00:00~(?:24:00|00:00)|24시간)',h) and c in ('','연중무휴','없음','휴무없음'))
def annotate(places,src):
 by={p['id']:p for p in places}; seen=set()
 for p in places:
  if '동물병원' in p['services']:
   p['hours24Data']=all_day(p)
 for r in json.loads((src/'hospital-emergency.json').read_text(encoding='utf-8')):
  i=r['id'];p=by.get(i);u=urllib.parse.urlsplit(r['sourceUrl']);d=datetime.date.fromisoformat(r['checkedOn'])
  if i in seen or not p or '동물병원' not in p['services'] or p['name']!=r['name'] or p.get('address')!=r['address'] or u.scheme!='https' or not u.hostname or u.username or u.password or not r['evidence'].strip():raise ValueError('Invalid or mismatched official hospital evidence: '+i)
  seen.add(i)
  p['nightEmergencySource']=r['sourceUrl'];p['nightEmergencyCheckedOn']=d.isoformat();p['nightEmergencyEvidence']=r['evidence']
def hospital_badges(p):
 if '동물병원' not in p['services']:return ''
 b='<span class="tag hospital-24">24시간 운영 (운영시간 데이터상)</span> ' if p.get('hours24Data') else ''
 if p.get('nightEmergencySource'):b+=f'<a class="tag hospital-night" href="{E(p["nightEmergencySource"])}" target="_blank" rel="noopener noreferrer">야간 응급진료 확인 · 공식 출처</a> <span class="muted">{E(p["nightEmergencyCheckedOn"])} 확인</span>'
 return b
def maps(p):
 q=urllib.parse.quote(' '.join(filter(None,[p.get('name'),p.get('roadAddress') or p.get('address') or p.get('sigungu')])),safe='')
 return f'<div class="map-links"><a class="btn" href="https://map.naver.com/p/search/{q}" target="_blank" rel="noopener noreferrer">네이버지도 검색·길찾기</a> <a class="btn" href="https://map.kakao.com/link/search/{q}" target="_blank" rel="noopener noreferrer">카카오맵 검색·길찾기</a><small>지도에서 목적지를 확인하고 길찾기를 선택하세요.</small></div>'
