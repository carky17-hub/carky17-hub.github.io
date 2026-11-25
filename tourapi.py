"""KTO factual data + explicitly licensed image URLs; no images copied."""
import urllib.error, collections, datetime as dt, json, math, os, re, urllib.parse, urllib.request, pathlib, unicodedata
BASE='https://apis.data.go.kr/B551011/KorPetTourService2'
SOURCE='https://www.data.go.kr/data/15135102/openapi.do'
REGIONS=dict(zip(['서울','인천','대전','대구','광주','부산','울산','세종','경기','강원','충북','충남','경북','경남','전북','전남','제주'],['서울특별시','인천광역시','대전광역시','대구광역시','광주광역시','부산광역시','울산광역시','세종특별자치시','경기도','강원특별자치도','충청북도','충청남도','경상북도','경상남도','전북특별자치도','전라남도','제주특별자치도']))
CODES=['11','28','30','27','29','26','31','36','41','51','43','44','47','48','52','46','50']
REGIONS.update({'강원도':'강원특별자치도','전라북도':'전북특별자치도','제주도':'제주특별자치도'})
PET={'acmpyTypeCd':'동반 구역','acmpyPsblCpam':'동반 가능 동물','acmpyNeedMtr':'필요사항','relaAcdntRiskMtr':'유의사항','etcAcmpyInfo':'기타 동반 정보','relaPosesFclty':'구비 시설','relaFrnshPrdlst':'비치 품목','relaPurcPrdlst':'구매 품목','relaRntlPrdlst':'렌탈 품목'}
def today():return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
def norm(x):return re.sub(r'[^0-9a-z가-힣]','',unicodedata.normalize('NFKC',str(x or '')).lower())
def region(addr):
 s=str(addr or '').split(); v=s[0] if s else ''; return REGIONS.get(v, next((x for k,x in REGIONS.items() if v==x or v.startswith(k) and len(v)>2),None))
def addrkey(a):
 a=str(a or '').split('(')[0].strip(); ss=a.split(); return norm(' '.join([region(a) or (ss[0] if ss else '')]+ss[1:]))
def point(x,y):
 try:
  a,b=float(y),float(x)
  return (a,b) if 32<=a<=39 and 124<=b<=132 else (None,None)
 except (ValueError,TypeError):return None,None
def km(a,b,c,d):return 111.2*math.hypot(a-c,(b-d)*math.cos(math.radians((a+c)/2)))
def licensed(row,key):
 typ=str(row.get('cpyrhtDivCd','')).strip().lower(); url=str(row.get(key,'')).strip()
 try:u=urllib.parse.urlsplit(url); port=u.port
 except ValueError:return None
 if typ not in ('type1','type3') or u.scheme not in ('http','https') or not u.hostname or u.username or u.password or port or not (u.hostname=='visitkorea.or.kr' or u.hostname.endswith('.visitkorea.or.kr')) or u.query or u.fragment:return None
 return {'src':urllib.parse.urlunsplit(u._replace(scheme='https')),'license':typ[-1],'credit':'한국관광공사','caption':str(row.get('imgname') or '한국관광공사 제공 사진')[:150]}
def basic(r):
 cid=str(r.get('contentid','')); addr=str(r.get('addr1') or '').strip(); name=str(r.get('title') or '').strip(); ct=str(r.get('contenttypeid',''))
 if not re.fullmatch(r'\d{1,12}',cid) or not name or not addr or not region(addr) or ct not in ('12','14','15','25','28','32','38','39') or str(r.get('showflag','1'))=='0':return None
 a,b=point(r.get('mapx'),r.get('mapy')); ph=licensed(r,'firstimage')
 return {'contentId':cid,'name':name,'address':addr,'lat':a,'lng':b,'type':ct,'cat3':str(r.get('cat3') or ''),'modified':str(r.get('modifiedtime') or ''),'phone':str(r.get('tel') or '')[:100],'representative':ph,'images':[ph] if ph else [],'pet':{},'detailDone':False,'imageDone':False,'checkedOn':today()}
def read(src):return json.loads((src/'tourapi.json').read_text())
class API:
 def __init__(self,key,limit):self.key=urllib.parse.unquote(key);self.limit=limit;self.calls=0
 def call(self,op,**params):
  import time
  last='unknown'
  for attempt in range(3):
   if self.calls>=self.limit:raise RuntimeError('quota')
   self.calls+=1; query=urllib.parse.urlencode({'serviceKey':self.key,'MobileOS':'ETC','MobileApp':'eodigagae','_type':'json',**params})
   try:
    time.sleep(0.15)
    with urllib.request.urlopen(BASE+'/'+op+'?'+query,timeout=30) as f: raw=f.read().decode('utf-8','replace')
    try:r=json.loads(raw)['response']
    except Exception:
     m=re.search(r'<(?:returnAuthMsg|resultMsg|errMsg)>([^<]{0,120})',raw);last='non-json '+(m.group(1) if m else raw[:80].replace(self.key,'***'));raise ValueError(last)
    code=str(r['header'].get('resultCode'))
    if code not in ('0000','00'):last='provider '+code+' '+str(r['header'].get('resultMsg',''))[:80];raise ValueError(last)
    body=r['body']; items=body.get('items') or {}; items=items.get('item',[]) if isinstance(items,dict) else [];items=[items] if isinstance(items,dict) else items
    if not isinstance(items,list):last='invalid items';raise ValueError(last)
    return items,int(body.get('totalCount',len(items)))
   except urllib.error.HTTPError as e:last='http '+str(e.code)
   except Exception as e:
    if last=='unknown':last=type(e).__name__
   print('TourAPI retry',op,attempt+1,last.replace(self.key,'***'),flush=True)
   time.sleep(3*(attempt+1))
  raise RuntimeError('TourAPI response failed: '+op+' ('+last.replace(self.key,'***')[:120]+')')
 def pages(self,op,**params):
  page=1;got=0
  while True:
   items,total=self.call(op,numOfRows=100,pageNo=page,**params);got+=len(items);yield from items
   if got>=total:return
   if not items:raise RuntimeError('incomplete pagination')
   page+=1

def sync(src,api):
 old=read(src); day=today()
 if old.get('lastAttempt')==day and old.get('status')=='complete':return old
 result={'lastAttempt':day,'records':old['records'],'lastCompleteList':old.get('lastCompleteList'),'calls':0,'status':'partial'}
 try:
  fresh={}
  failed_regions=[]
  for code in CODES:
   try:
    for r in api.pages('areaBasedList2',lDongRegnCd=code,arrange='A'):
     p=basic(r)
     if p:fresh[p['contentId']]=p
   except RuntimeError as e:
    if str(e)=='quota':raise
    failed_regions.append(code);print('TourAPI region skipped',code,e,flush=True)
  if failed_regions:
   keep={r['contentId']:r for r in old['records'] if any(r.get('address','').startswith(n) for c,n in zip(CODES,REGIONS.values()) if c in failed_regions)}
   for cid,r in keep.items():fresh.setdefault(cid,r)
  if not fresh:raise RuntimeError('empty inventory')
  prior={r['contentId']:r for r in old['records']}
  for cid,r in fresh.items():
   prev=prior.get(cid)
   if prev and prev['modified']==r['modified'] and prev['name']==r['name'] and prev['address']==r['address'] and (day<=prev.get('checkedOn','') or (dt.date.fromisoformat(day)-dt.date.fromisoformat(prev['checkedOn'])).days<30):
    for k in ('pet','detailDone','imageDone','checkedOn'):r[k]=prev[k]
    if 'representative' in prev and r['representative']==prev['representative']:r['images']=prev['images']
    else:r['imageDone']=False
  result['records']=list(fresh.values());result['lastCompleteList']=day
  errors=0;consecutive=0
  for r in sorted(result['records'],key=lambda p:(p['detailDone'] and p['imageDone'],p['checkedOn'],p['contentId'])):
   try:
    if not r['detailDone']:
     rows,_=api.call('detailPetTour2',contentId=r['contentId'],numOfRows=10,pageNo=1);r['pet']={k:str(v)[:4000] for x in rows if str(x.get('contentid'))==r['contentId'] for k,v in x.items() if k in PET and v};r['detailDone']=True;r['checkedOn']=day
    if not r['imageDone']:
     images=list(api.pages('detailImage2',contentId=r['contentId'],imageYN='Y')); allowed=[p for x in images if str(x.get('contentid'))==r['contentId'] and (p:=licensed(x,'originimgurl'))];r['images']=list({p['src']:p for p in r['images']+allowed}.values())[:5];r['imageDone']=True
    consecutive=0
   except RuntimeError as e:
    if str(e)=='quota':raise
    errors+=1;consecutive+=1
    if consecutive>=5:raise RuntimeError('provider failures; resume next day') from None
  result['status']='complete' if not errors and not failed_regions else ('partial detail failures' if errors else 'partial regions '+','.join(failed_regions))
 except RuntimeError as e:result['status']=str(e)
 result['calls']=api.calls
 return result

def integrate(src,places):
 """Conservative exact name + address + coordinate match; ambiguous candidates withheld."""
 snap=read(src); byname=collections.defaultdict(list); byaddr=collections.defaultdict(list); existing={p['id'] for p in places}
 for p in places:
  if p['id'].startswith('f'):continue
  byname[(p.get('sido'),norm(p['name']))].append(p);byaddr[(p.get('sido'),addrkey(p.get('roadAddress') or p.get('address')))].append(p)
 audit=[]
 seen=set()
 for r in snap['records']:
  assert re.fullmatch(r'\d{1,12}',r['contentId']) and r['contentId'] not in seen;seen.add(r['contentId'])
  if r['type'] not in ('12','14','28','32','39'):
   audit.append({'contentId':r['contentId'],'status':'unsupported-category'});continue
  si=region(r['address']); name=norm(r['name']); ak=addrkey(r['address']);a,b=point(r['lng'],r['lat']); candidates=byname[(si,name)];same=[p for p in candidates if ak==addrkey(p.get('roadAddress') or p.get('address')) and a is not None and p.get('geoPrecision')=='exact' and point(p.get('lng'),p.get('lat'))[0] is not None and km(a,b,p['lat'],p['lng'])<=.15]
  if len(same)==1:p=same[0];status='matched'
  elif candidates or byaddr[(si,ak)]:audit.append({'contentId':r['contentId'],'status':'manual-review','candidates':[p['id'] for p in candidates or byaddr[(si,ak)]]});continue
  else:
   pid='p8'+r['contentId'].zfill(12);assert pid not in existing;existing.add(pid)
   ss=r['address'].split();gu=ss[1] if len(ss)>1 and ss[1].endswith(('시','군','구')) else None
   if gu and len(ss)>2 and ss[2].endswith('구'):gu+=' '+ss[2]
   cat={'32':'숙소','39':'카페' if r['cat3']=='A05020900' else '식당'}.get(r['type'],'여행지');p={k:None for k in ('dong','dongKey','roadAddress','hours','closedDays','parking','indoor','outdoor','petSize','restrictions','petFee','description','homepage','licenseNo','lastChecked','petSizeSmall','petSizeMedium','petSizeLarge','floorAllowed','terrace','carrierRequired','vaccinationCheck','menu','imageRights','kakaoPlaceId','kakaoMapUrl')};p.update(id=pid,sido=si,sigungu=gu,address=r['address'],lat=a,lng=b,phone=r['phone'] or None,name=r['name'],category=cat,services=[cat],subType='관광공사 등록',verified=False,tags=['관광공사 등록'],registryCategories=[],source='한국관광공사 반려동물 동반여행 공공데이터',sourceUrl=SOURCE,geoSource='public-data' if a is not None else None,geoPrecision='exact' if a is not None else None,updatedAt=r['checkedOn']);places.append(p);byname[(si,name)].append(p);byaddr[(si,ak)].append(p);status='new'
  # Do not override contradictory existing operator/public data. Preserve source wording separately.
  if not p.get('restrictions') and r['pet'].get('acmpyNeedMtr'):p['restrictions']=r['pet']['acmpyNeedMtr']
  p['tourism']={'contentId':r['contentId'],'checkedOn':r['checkedOn'],'pet':r['pet'],'sourceUrl':SOURCE};p['tourPhoto']=next((ph for ph in r['images'] if licensed({'cpyrhtDivCd':'Type'+ph['license'],'url':ph['src']},'url')),None);p['tourPhotos']=[ph for ph in r['images'] if licensed({'cpyrhtDivCd':'Type'+ph['license'],'url':ph['src']},'url')];audit.append({'contentId':r['contentId'],'status':status,'placeId':p['id']})
 return audit
if __name__=='__main__':
 src=pathlib.Path(__file__).parent/'source';key=os.getenv('TOURAPI_SERVICE_KEY','').strip()
 if not key:print('TourAPI disabled: no key')
 else:
  snap=sync(src,API(key,min(900,max(1,int(os.getenv('TOURAPI_DAILY_LIMIT','900'))))));path=src/'tourapi.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(snap,ensure_ascii=False,separators=(',',':')));tmp.replace(path);print('TourAPI',snap['status'],snap['calls'],'calls',len(snap['records']),'records')
