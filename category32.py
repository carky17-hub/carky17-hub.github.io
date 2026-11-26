"""Conservative food/pet-service reclassification. Never edit raw source data."""
import collections, csv, gzip, hashlib, json, re, unicodedata
from pathlib import Path

FOOD={'카페','애견카페','식당'}
PET={'미용','호텔·유치원','동물병원','장례·추모'}
FOOD_TYPES={'카페':'카페','커피숍':'카페','제과점영업':'카페','식당':'식당','한식':'식당','경양식':'식당','일식':'식당','중국식':'식당','분식':'식당','회집':'식당','호프/통닭':'식당','패밀리레스토랑':'식당','식육(숯불구이)':'식당'}
STRONG={ '미용':r'그루밍|grooming|애견\s*미용|반려동물\s*미용|강아지\s*미용|펫\s*미용|펫\s*살롱|애견\s*살롱', '호텔·유치원':r'애견\s*(?:호텔|유치원)|반려견\s*(?:호텔|유치원)|강아지\s*(?:호텔|유치원)|펫\s*(?:호텔|유치원)|도그\s*(?:호텔|유치원)', '동물병원':r'동물\s*(?:병원|의료센터|메디컬센터)|수의\s*과', '장례·추모':r'반려동물\s*장례|애견\s*장례|동물\s*장례|펫\s*장례'}
BROAD={ '미용':r'그루밍|미용|살롱|스파|grooming|salon|spa', '호텔·유치원':r'호텔|유치원|hotel|daycare', '동물병원':r'동물병원|의료센터|메디컬센터|수의', '장례·추모':r'장례|화장장|추모|납골'}
FOOD_NAME=r'카페|커피|coffee|caf[eé]|베이커리|bakery|브런치|식당|레스토랑|restaurant|한식|고깃집|국밥|분식|횟집|치킨|피자|파스타|돈까스|돈카츠|김밥|빵집|디저트|제과|제빵'
REVIEW_FIELDS=['placeId','업체명','시도','시군구','주소','현재업종','현재서비스','원본업종','등록업종','출처','후보업종','사유','검수결정']

def clean(v):return unicodedata.normalize('NFKC',str(v or '')).lower()
def hits(name,patterns):return {k for k,v in patterns.items() if re.search(v,clean(name),re.I)}
def registry(p):
    regs=p.get('registryCategories') or []
    if not isinstance(regs,list):return set()
    out=set()
    for r in regs:
        if re.fullmatch(r'미용(?:\s*\([^)]*\))?',str(r)):out.add('미용')
        if r in ('위탁관리업','위탁관리'):out.add('호텔·유치원')
        if r=='동물전시업':out.add('카페') # real exhibition businesses may also operate cafes
    return out

def subtype(p):
    s=str(p.get('subType') or '').strip()
    if s in FOOD_TYPES:return FOOD_TYPES[s]
    if re.fullmatch(r'미용(?:\s*\([^)]*\))?',s):return '미용'
    if s in ('위탁관리업','위탁관리'):return '호텔·유치원'
    if s=='동물병원':return '동물병원'
    if s in ('장례','동물장묘업','장례·추모'):return '장례·추모'
    return None

def identity(p):
    return hashlib.sha256(json.dumps([p.get(k) for k in ('id','name','sido','sigungu','address','category','services','subType','registryCategories','source','licenseNo','description','verified','tags')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def proposal(p):
    cat=p.get('category'); sv=set(p.get('services') or []); reg=registry(p); st=subtype(p); name=p.get('name',''); strong=hits(name,STRONG); broad=hits(name,BROAD)
    foodname=bool(re.search(FOOD_NAME,clean(name),re.I)); foodproof=('식약처' in str(p.get('source')) or '식약처 인증' in (p.get('tags') or [])); desc=clean(p.get('description')); fooddesc=bool(re.search(r'카페|커피|식당|음식점|브런치|베이커리',desc));
    # '애견카페' alone is often the misclassified original label; other explicit descriptions remain a conflict.
    conflicting_desc=fooddesc and desc.strip() not in ('애견카페','카페','식당')
    registered=bool(p.get('verified') is True and p.get('licenseNo'))
    if not (cat in FOOD|PET or sv & (FOOD|PET)):return None
    # Never create or alter funeral registry membership (separate regulated directory).
    if '장례·추모' in sv or cat=='장례·추모':return None
    if (cat in FOOD or sv & FOOD) and (broad or reg & PET or st in PET):
        candidates=(strong|broad|(reg&PET)|({st} if st in PET else set()))
        supported=strong & ((reg if registered else set())|({st} if st in PET else set()))
        # require matching name + registry or explicit source subtype; preserve actual multi-service signals.
        if len(supported)==1 and not (candidates- supported) and not (sv & (PET-supported)) and not foodproof and not foodname and not conflicting_desc and '카페' not in reg and '장례·추모' not in supported:
            target=next(iter(supported))
            if target!='동물병원' or st=='동물병원':
                return ('auto',target,'상호와 등록/원본 업종 일치; 음식점·겸업 근거 없음')
        return ('review',' / '.join(sorted(candidates)), '펫 업종 키워드/원본 근거와 음식 서비스 충돌 또는 겸업 가능')
    if (cat in PET or sv&PET) and (foodname or foodproof or st in FOOD) and not sv&FOOD:
        # Only explicit licensed food subtype + food name and no pet-business evidence.
        if st in FOOD and foodproof and foodname and not broad and not reg and not registered and cat!='동물병원' and '동물병원' not in sv:
            return ('auto',st,'식약처 출처 및 음식 원본업종·상호 일치; 펫 업종 근거 없음')
        return ('review',st if st in FOOD else '카페 / 식당','음식 업종 단서와 펫 업종 충돌 또는 겸업 가능')
    if cat in PET and sv&FOOD and (foodname or foodproof or st in FOOD):
        return ('review',st if st in FOOD else '카페 / 식당','복수 서비스 실제 겸업 여부 확인')
    return None

def scan(rows):
    overrides={}; review=[]
    for p in rows:
        result=proposal(p)
        if not result:continue
        status,target,reason=result
        if status=='auto':
            # replace erroneous food services, but keep unrelated services; reverse likewise.
            remove=FOOD if target in PET else PET
            services=list(dict.fromkeys([v for v in p.get('services',[]) if v not in remove]+[target]))
            if p.get('category')==target and services==p.get('services'):continue
            new_sub=next((r for r in (p.get('registryCategories') or []) if (target=='미용' and str(r).startswith('미용')) or (target=='호텔·유치원' and r=='위탁관리업')),target)
            new_desc=None if (target in PET and clean(p.get('description')).strip() in ('애견카페','카페','식당')) else p.get('description')
            overrides[p['id']]={'fromSubType':p.get('subType'),'fromDescription':p.get('description'),'subType':new_sub,'description':new_desc,'fingerprint':identity(p),'name':p['name'],'fromCategory':p['category'],'fromServices':p['services'],'category':target,'services':services,'reason':reason}
        else:
            review.append(dict(zip(REVIEW_FIELDS,[p['id'],p['name'],p.get('sido'),p.get('sigungu'),p.get('address'),p.get('category'),' / '.join(p.get('services') or []),p.get('subType'),' / '.join(p.get('registryCategories') or []),p.get('source'),target,reason,''])))
    return overrides,review

def read_raw(src):
    with gzip.open(Path(src)/'places-all.json.gz','rt',encoding='utf-8') as f:return json.load(f)

def apply_overrides(rows,src,overrides=None):
    if overrides is None:overrides=json.loads((Path(src)/'category-overrides.json').read_text(encoding='utf-8'))
    if not isinstance(overrides,dict):raise ValueError('category-overrides must be object')
    by={p['id']:p for p in rows}; changes=[]
    for pid,o in sorted(overrides.items()):
        p=by.get(pid)
        if not p or not isinstance(o,dict) or identity(p)!=o.get('fingerprint'):raise ValueError('stale category override: '+pid+'; regenerate on current main')
        target=o.get('category'); sv=o.get('services'); decision=proposal(p)
        # Strictly re-evaluate automatic decisions against current raw data, not arbitrary JSON input.
        if not decision or decision[:2]!=('auto',target) or target not in FOOD|PET or target=='장례·추모':raise ValueError('unsafe category override '+pid)
        expected=scan([p])[0].get(pid)
        if expected!=o:raise ValueError('invalid category override payload '+pid)
        changes.append({'id':pid,'name':p['name'],'fromCategory':p['category'],'toCategory':target,'fromServices':p['services'],'toServices':sv,'reason':o['reason']})
    for c in changes:
        p=by[c['id']];p['category']=c['toCategory'];p['services']=c['toServices']; o=overrides[c['id']];p['subType']=o['subType'];p['description']=o['description']
        # Original subtype/description remain in override audit; registry/source preserved.
    return {'changed':len(changes),'byTransition':dict(collections.Counter(c['fromCategory']+' → '+c['toCategory'] for c in changes)),'samples':changes[:20]}

def write_review(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    def safe(v):
        s=str(v or '');return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=REVIEW_FIELDS);w.writeheader();w.writerows({k:safe(v) for k,v in row.items()} for row in rows)
