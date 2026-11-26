"""Curated SEO display groups, not modifications to legal addresses or source records."""
import re
GROUPS=[('서울특별시','성동구','성수동',['성수1가동','성수2가동','성수동1가','성수동2가','성수1가1동','성수1가2동','성수2가1동','성수2가3동']),('서울특별시','성동구','금호동',['금호4가동','금호2.3가동','금호1가동']),('서울특별시','용산구','용산동',['용산2가동']),('대구광역시','수성구','수성동',['수성1가동','수성2.3가동','수성4가동']),('서울특별시','용산구','한강로',['한강로동']),('서울특별시','용산구','원효로',['원효로동'])]
ALIASES={(si,gu,d):base for si,gu,base,aliases in GROUPS for d in aliases}
def dong_key(si,gu,d):return ALIASES.get((si,gu,d),d)
def display_services(p):
 return [s for s in p['services'] if not (s in ('여행지','놀이터') and p.get('indoor') is False and p.get('outdoor') is False)]
def seo_pages(source):
 """Drop an alias page only if its equivalent broader page already exists."""
 paths={(s['category'],s['sido'],s['sigungu'],s['filter']['dongKey']):s['path'].rstrip('/')+'/' for s in source}
 pages=[]; redirects={}
 for s in source:
  f=s['filter'];d=f['dongKey'];base=dong_key(f['sido'],f['sigungu'],d);old=s['path'].rstrip('/')+'/'
  target=paths.get((s['category'],f['sido'],f['sigungu'],base))
  if d!=base and target and target!=old:redirects[old]=target
  else:pages.append(s)
 return pages,redirects

def indexable(s,n):
 return n>0 and (s['level']!='dong' or n>=3)

def recount(s,n):
 if s['level']=='dong':
  label={'cafe':'애견동반카페','restaurant':'애견동반식당','grooming':'애견미용','hospital':'동물병원','hotel':'애견호텔','stay':'애견동반숙소','travel':'애견동반 가볼만한곳','playground':'애견놀이터','funeral':'반려동물 장례식장','ossuary':'반려동물 납골당'}.get(s['category'])
  if label:
   kw=f"{s['filter']['dongKey']} {label}"
   scope=" ".join(dict.fromkeys(x for x in (s.get("sido"),s.get("sigungu")) if x))
   suffix=f" ({scope})" if scope else ""
   return f'{kw} {n}곳{suffix} | 어디가개',f'{scope} {kw} 목록 {n}곳. 주소, 연락처 및 확인된 이용 조건을 비교하고 방문 전 업체에 확인하세요.'.strip(),f'{kw} {n}곳'
 return tuple(re.sub(r'(?<!\d)'+re.escape(str(s['count']))+r'곳',f'{n}곳',s[k]) for k in ('title','metaDescription','h1'))
