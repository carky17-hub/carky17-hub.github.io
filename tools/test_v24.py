import pathlib,sys,tempfile,json,copy
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tourapi import Matcher,region,addrkey,point,km,norm,integrate,report,PET,SOURCE,basic
from tour24 import shopping_candidate,shopping_state,detail_html
from cards22 import cover

def row(cid,name,addr='서울특별시 종로구 사직로 49-4',t='39',cat='A05020900',lat=37.575,lng=126.966):
    return basic(dict(contentid=str(cid),title=name,addr1=addr,contenttypeid=t,cat3=cat,mapx=lng,mapy=lat,cpyrhtDivCd='Type1',firstimage='https://tong.visitkorea.or.kr/test.jpg'))
def p(id,name,addr='서울특별시 종로구 사직로 49-4',lat=37.575,lng=126.966,service='카페'):
    return dict(id=id,name=name,address=addr,lat=lat,lng=lng,geoPrecision='exact',sido='서울특별시',services=[service],category=service)
def match(r,ps):return Matcher(ps,region,addrkey,point,km,norm).match(r)
r=row(1,'주식회사 사직동커피하우스'); a=p('p1','사직동커피하우스');assert match(r,[a])[0] is a
assert match(r,[dict(a,lat=37.58)])[0] is None
assert match(r,[dict(a,geoPrecision='approx')])[0] is None
assert match(r,[a,dict(a,id='p2')])[0] is None
assert match(row(2,'사직동커피하우스'),[dict(a,address='서울특별시 종로구 사직로 49-5')])[0] is None
assert match(row(3,'사직동커피하우스 강남점'),[dict(a,name='사직동커피하우스 강북점')])[0] is None
assert match(row(4,'사직동커피하우스'),[dict(a,address='서울특별시 종로구 사직로 49-4 2층')])[0] is None
assert match(r,[dict(a,services=['동물병원'])])[0] is None
mall=row(5,'스타필드 고양',addr='경기도 고양시 덕양구 고양대로 1955',t='38',cat='A04010600',lat=37.64,lng=126.89);assert shopping_candidate(mall) and shopping_state(mall)=='pending-pet-evidence'
mall.update(detailDone=True,pet={'acmpyTypeCd':'일부 구역 동반 가능','acmpyNeedMtr':'이동장 필요','relaAcdntRiskMtr':'매장별 조건 확인'})
assert shopping_state(mall)=='eligible'
for n,c in [('나이키 스타필드 고양점','A04010600'),('스타필드 고양','A04011000'),('일반 상점','A04010600')]:assert not shopping_candidate(row(6,n,t='38',cat=c))
assert shopping_state(dict(mall,pet={'acmpyTypeCd':'동반 불가'}))=='restricted-review'
assert shopping_state(dict(mall,pet={'acmpyTypeCd':'동반 가능 여부 문의'}))=='restricted-review'
with tempfile.TemporaryDirectory() as d:
    src=pathlib.Path(d);(src/'tourapi.json').write_text(json.dumps({'records':[r,mall,row(6,'올리브영',t='38',cat='A04011000')]}),encoding='utf-8')
    places=[copy.deepcopy(a)];audit=integrate(src,places);s=report(src,places,audit);assert s['matched_records']==1 and s['fuzzy_matched_records']==1 and s['new_records']==1 and s['type38_records']==2 and s['type38_eligible_records']==1
    q=places[1];assert q['category']=='여행지' and q['subType']=='쇼핑·복합몰';h=detail_html(q,PET,SOURCE);assert all(x in h for x in ['동반 구역','필요사항','유의사항','공공누리 1유형','tour-gallery-track']);assert '<div hidden class="eg-art' in cover(places[0]);assert '<div hidden class="eg-art' not in cover(a)
    assert '아직 수집되지 않았습니다' in detail_html(dict(q,tourism={'pet':{},'checkedOn':'2026-11-26'}),PET,SOURCE)
    assert '<script>' not in detail_html(dict(q,tourism={'pet':{'acmpyNeedMtr':'<script>'}}),PET,SOURCE)
print('v2.4 match, mall selection, detail, placeholder and report PASS')
