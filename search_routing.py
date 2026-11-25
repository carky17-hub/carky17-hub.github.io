"""Conservative per-shard bigram Bloom filter for Korean search. No user queries persisted."""
import unicodedata as u, base64, json
BITS=32768
CHO='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
SHORT={'서울특별시':'서울','부산광역시':'부산','인천광역시':'인천','대구광역시':'대구','대전광역시':'대전','울산광역시':'울산','광주광역시':'광주','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전북특별자치도':'전북','전라북도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주'}
SERVICES={'카페':['카페','애견동반카페','반려동물동반카페','애견카페'],'식당':['식당','애견동반식당','반려동물동반식당'],'숙소':['숙소','애견동반숙소','애견동반펜션'],'여행지':['여행지','애견동반여행지','가볼만한곳','애견동반가볼만한곳'],'놀이터':['놀이터','애견놀이터'],'미용':['미용','애견미용','애견미용실'],'동물병원':['동물병원','동물의료센터'],'호텔·유치원':['호텔','유치원','애견호텔','애견유치원','호텔유치원'],'장례·추모':['장례','추모','반려동물장례','장례식장','반려동물장례식장','납골당','봉안당']}
FLAGS=['지금 영업 중','식약처 공식 인증','반려견 크기 정보 있음','실내 동반','실외 동반','주차']
def text(x):
 if x is None:return ''
 if isinstance(x,list):return ','.join(map(text,x))
 return str(x)
def norm(x):return ''.join(c for c in ''.join(CHO[ord(c)-0x1100] if 0x1100<=ord(c)<=0x1112 else c for c in u.normalize('NFC',text(x))).lower() if u.category(c)[0] in 'LN')
def initials(s):return ''.join(CHO[(ord(c)-0xac00)//588] if 0xac00<=ord(c)<0xac00+11172 else c for c in s)
def unique(items):return list(dict.fromkeys(text(x) for x in items if x))
def short(x):return x[:-1] if x and x[-1] in '시군구동읍면' else x
# Must be a superset of site/search.js terms; all dynamic flag aliases are included.
def terms(p):
 si=text(p.get('sido'));gu=text(p.get('sigungu'));dong=text(p.get('dong'));dk=text(p.get('dongKey'))
 areas=unique([si,SHORT.get(si),gu,short(gu),dong,dk,short(dk or dong)])
 svc=unique(s for v in p.get('services',[]) for s in SERVICES.get(v,[v]))
 # travel visibility can remove aliases. Enumerate service subsets for concatenated term.
 groups=[SERVICES.get(v,[v]) for v in p.get('services',[])]
 combos=[[]]
 for g in groups:combos += [x+g for x in combos[:]]
 return unique([p.get(k) for k in ('name','address','roadAddress','category','subType','petSize')]+areas+svc+FLAGS+list(p.get('tags') or [])+[a+s for a in areas for s in svc]+[' '.join(areas+unique(c)+[text(p.get('name'))]) for c in combos])
def hashes(a,b):return ((ord(a)*131+ord(b)*17)&(BITS-1),(ord(a)*8191+ord(b)*257)&(BITS-1))
def encode(rows):
 bits=bytearray(BITS//8)
 for p in rows:
  for raw in terms(p):
   n=norm(raw)
   for s in (n,initials(n)):
    for a,b in zip(s,s[1:]):
     for h in hashes(a,b):bits[h//8]|=1<<(h%8)
 return base64.b64encode(bits).decode('ascii')
