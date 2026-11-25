"""Validated build-time public content overlays. No applicant or payment data."""
import csv, io, json, os, re, urllib.request, urllib.parse, datetime, pathlib, html
ROOT=pathlib.Path(__file__).resolve().parent
COLUMNS={
 'corrections':('place_id','field','value','evidence_url','checked_on','approved'),
 'ads':('page_path','slot','place_id','start','end','product','paid'),
 'premium':('place_id','start_date','end_date','intro','menu','reservation_url','photo_urls','photo_rights_confirmed','approved')}
BOOL={'parking','indoor','outdoor','petSizeSmall','petSizeMedium','petSizeLarge','floorAllowed','terrace','carrierRequired','vaccinationCheck','operating'}
TEXT={'name','phone','hours','closedDays','petSize','petFee','restrictions','description','homepage','menu','weightLimit'}
TZ=datetime.timezone(datetime.timedelta(hours=9))
def today():return datetime.datetime.now(TZ).date().isoformat()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def url(s,google=False):
 u=urllib.parse.urlsplit(s);require(u.scheme=='https' and u.hostname and not u.username and not u.password and not u.fragment,'HTTPS URL required')
 if google:require(u.hostname=='docs.google.com' and re.fullmatch(r'/spreadsheets/d/(?:e/)?[\w-]+/pub',u.path) and urllib.parse.parse_qs(u.query).get('output')==['csv'] and 'gid' in urllib.parse.parse_qs(u.query),'Use Google Sheets published CSV URL with gid and output=csv')
 return s
def date(s):
 require(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',s)),f'Invalid date: {s}');return datetime.date.fromisoformat(s)
def flag(s):require(s in ('TRUE','FALSE'),'approved/rights must be TRUE or FALSE');return s=='TRUE'
def read_csv(text,kind):
 r=csv.DictReader(io.StringIO(text));require(tuple(r.fieldnames or [])==COLUMNS[kind],f'{kind}: invalid header')
 rows=[]
 for line,d in enumerate(r,2):
  require(None not in d and all(v is not None for v in d.values()),f'{kind} row {line}: incorrect column count')
  d={k:v.strip() for k,v in d.items()};
  if not any(d.values()):continue
  require(all(len(v)<=15000 for v in d.values()),f'{kind} row {line}: too long');rows.append(d)
 return rows
def load_inputs():
 local=os.getenv('ADMIN_CSV_DIR',''); urls={k:os.getenv('SHEET_'+k.upper()+'_CSV_URL','') for k in COLUMNS}
 require(not local or not any(urls.values()),'Do not mix local and remote sheet inputs')
 require(not local or not (os.getenv('NETLIFY')=='true' or os.getenv('RELEASE_MODE')=='true' or os.getenv('ALLOW_INDEXING')=='true'),'Local sample CSV not allowed in release build')
 require(not any(urls.values()) or all(urls.values()),'Set all three sheet URLs or none')
 if os.getenv('REQUIRE_ADMIN_SHEETS','false')=='true':require(all(urls.values()),'All three production sheet URLs required')
 rows={}
 for k,header in COLUMNS.items():
  if local: text=(pathlib.Path(local)/(k+'.csv')).read_text(encoding='utf-8-sig')
  elif urls[k]:
   url(urls[k],True)
   with urllib.request.urlopen(urllib.request.Request(urls[k],headers={'User-Agent':'Eodigagae-build/1.0'}),timeout=30) as r:
    require(urllib.parse.urlsplit(r.geturl()).hostname in ('docs.google.com','docs.googleusercontent.com') or (urllib.parse.urlsplit(r.geturl()).hostname or '').endswith('.googleusercontent.com'),'Unexpected sheet redirect')
    b=r.read(5_000_001);require(len(b)<=5_000_000,'Sheet exceeds 5 MB');text=b.decode('utf-8-sig')
  else:text=','.join(header)+'\n'
  rows[k]=read_csv(text,k)
 return {'as_of':today(),'mode':'local' if local else 'sheets' if any(urls.values()) else 'empty','rows':rows}
def apply(a,snapshot):
 by={p['id']:p for p in a};seen=set();n=0
 for r in snapshot['rows']['corrections']:
  if not flag(r['approved']):continue
  i,k,v=r['place_id'],r['field'],r['value'];require(i in by and k in BOOL|TEXT,f'correction invalid ID/field: {i}/{k}');require((i,k) not in seen,f'duplicate correction: {i}/{k}');seen.add((i,k));url(r['evidence_url']);require(date(r['checked_on'])<=date(snapshot['as_of']),'Future evidence date');require(bool(v),'Blank correction; use NULL to clear')
  if v=='NULL':value=None
  elif k in BOOL:require(v in ('TRUE','FALSE'),f'{i}/{k}: TRUE/FALSE/NULL required');value=v=='TRUE'
  else:
   require(len(v)<=3000,'Correction too long');value=url(v) if k=='homepage' else v
  p=by[i];p[k]=value;p.setdefault('operatorCorrections',{})[k]={'source':r['evidence_url'],'checkedOn':r['checked_on']};n+=1
 return n
def schedules(snapshot,areas,ids):
 ads={};reserved={};premium={};asof=snapshot['as_of']
 def interval(r):
  start,end=date(r['start_date']),date(r['end_date']);require(start<=end,'Start after end');return (start,end)
 def overlaps(a,b):return a[0]<=b[1] and b[0]<=a[1]
 for r in snapshot['rows']['ads']:
  require(r['paid'] in ('Y','N'),'paid must be Y or N');require(r['product'] in ('premium','regional'),'product must be premium or regional')
  r={**r,'start_date':r['start'],'end_date':r['end']}
  path=r['page_path'].rstrip('/')+'/';i=r['place_id'];require(path in areas and i in areas[path],f'Ad place not in region: {path} {i}');require(r['slot'] in ('1','2','3'),'Slot must be 1, 2 or 3');r={**r,'region_path':path};iv=interval(r)
  for old in reserved.get(path,[]):
   require(not (overlaps(iv,interval(old)) and (r['slot']==old['slot'] or i==old['place_id'])),f'Ad inventory overlap: {path} slot {r["slot"]} {i}')
  reserved.setdefault(path,[]).append(r)
  if r['paid']=='Y':ads.setdefault(path,[]).append(r)
 for r in snapshot['rows']['premium']:
  if not flag(r['approved']):continue
  i=r['place_id'];require(i in ids,f'Invalid premium ID: {i}');iv=interval(r);photos=[x.strip() for x in r['photo_urls'].split('|') if x.strip()];require(len(photos)<=10 and len(set(photos))==len(photos),'Maximum 10 distinct photos');rights=flag(r['photo_rights_confirmed']);require(not photos or rights,'Photo permission required');[url(x) for x in photos];require(not r['reservation_url'] or url(r['reservation_url']),'Invalid reservation URL');require(len(r['intro'])<=3000 and len(r['menu'])<=3000,'Premium text too long')
  for old in premium.get(i,[]):require(not overlaps(iv,interval(old)),f'Premium period overlap: {i}')
  premium.setdefault(i,[]).append({**r,'photos':photos})
 return ads,premium
def active(r,d):return r['start_date']<=d<=r['end_date']
E=lambda x:html.escape(str(x),quote=True)
def premium_html(rows):
 out=''
 for r in rows:
  attrs=f'data-start="{E(r["start_date"])}" data-end="{E(r["end_date"])}"'
  images=''.join(f'<figure><img loading="lazy" decoding="async" referrerpolicy="no-referrer" data-premium-src="{E(u)}" alt="매장 제공 사진 {i}"></figure>' for i,u in enumerate(r['photos'],1))
  out+=f'<section class="panel premium-detail" data-period {attrs} hidden><span class="tag premium-tag">AD · 프리미엄 매장</span><h2>사장님이 소개하는 매장</h2><p class="muted">매장 제공 정보입니다. 공공 등록 배지와 별개입니다.</p>'+(f'<p class="premium-text">{E(r["intro"])}</p>' if r['intro'] else '')+(f'<div class="premium-gallery">{images}</div>' if images else '')+(f'<h3>메뉴·가격</h3><p class="premium-text">{E(r["menu"])}</p>' if r['menu'] else '')+(f'<a class="btn primary" href="{E(r["reservation_url"])}" target="_blank" rel="noopener noreferrer sponsored">외부 예약 페이지</a>' if r['reservation_url'] else '')+'</section>'
 return out
