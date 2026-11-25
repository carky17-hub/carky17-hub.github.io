import sys,pathlib,tempfile,json,csv,copy
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tourapi import basic,integrate,report,point,km
from tour24 import shopping_candidate,shopping_state,clean_name
from tour25 import share_photo,share_tags,review_csv

def row(i,name='사직동커피하우스',t='39',**kw):
    d=dict(contentid=str(i),title=name,addr1='서울특별시 종로구 사직로 49-4',contenttypeid=t,mapx=126.966,mapy=37.575,cpyrhtDivCd='Type1',firstimage='https://tong.visitkorea.or.kr/test.jpg');d.update(kw);return basic(d)
def place(i,name='사직동커피하우스',**kw):
    d=dict(id=i,name=name,address='서울특별시 종로구 사직로 49-4',lat=37.575,lng=126.966,geoPrecision='exact',sido='서울특별시',category='카페',services=['카페']);d.update(kw);return d
# Example hierarchy is synthetic; SH is the documented shopping major category.
m=row(10,'스타필드 고양','38',lclsSystm1='SH',lclsSystm2='SH01',lclsSystm3='SH010100');assert m['lclsSystm3']=='SH010100' and shopping_candidate(m)
assert shopping_state(m)=='pending-pet-evidence'
assert shopping_state(dict(m,detailDone=True,pet={'acmpyTypeCd':'일부 구역 동반 가능'}))=='eligible'
assert not shopping_candidate(dict(m,name='나이키 스타필드 고양점'))
assert not shopping_candidate(dict(m,lclsSystm3=''))
assert not shopping_candidate(dict(m,lclsSystm1='FD'))
assert shopping_candidate(dict(m,lclsSystm1='',lclsSystm2='',lclsSystm3='',cat3='A04010600'))
with tempfile.TemporaryDirectory() as d:
    src=pathlib.Path(d);rs=[row(1),row(2,'다른카페'),row(3,'새로운카페'),row(4,'삭제예정카페')];(src/'tourapi.json').write_text(json.dumps({'records':rs}),encoding='utf-8');base=[place('p1'),place('p2')]
    ps=copy.deepcopy(base);a=integrate(src,ps);assert a[0]['status']=='manual-review'
    n,k=review_csv(src/'internal'/'review.csv',rs,ps,a,point,km,clean_name);assert n==4 and k>=4
    with (src/'internal'/'review.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f));assert rows[0]['거리(m,정확좌표)']=='0.0' and rows[0]['이름 유사도(%)']=='100.0'
    o=src/'tour-match-overrides.json';o.write_text(json.dumps({'1':'p1','2':'p2','3':'new','4':'skip'}));ps=copy.deepcopy(base);a=integrate(src,ps);s=report(src,ps,a);assert s['manual_override_records']==2 and s['manual_new_records']==1 and s['manual_skipped_records']==1 and len(ps)==3
    for bad in ['{"1":"p1","2":"p1"}','{"1":"p1","1":"p2"}','{"1":"p999"}']:
        o.write_text(bad);ps=copy.deepcopy(base)
        try:integrate(src,ps)
        except ValueError:pass
        else:raise AssertionError('invalid override allowed')
base='https://eodigagae.com';p=place('p1',tourPhoto={'src':'https://tong.visitkorea.or.kr/test.jpg','license':'1'})
assert share_photo(p,base)[0].endswith('/test.jpg') and '한국관광공사' in share_tags(p,base)
assert share_photo(dict(p,tourPhoto=dict(p['tourPhoto'],license='3')),base) is None
assert share_photo(dict(p,tourPhoto=dict(p['tourPhoto'],src='https://evil.test/test.jpg')),base) is None
assert share_photo(dict(p,ownerPhoto={'src':'/approved-photos/a.jpg','label':'사장님 제공','credit':'매장'}),base)[0]==base+'/approved-photos/a.jpg'
assert share_photo(dict(p,services=['장례·추모']),base) is None
print('v2.5 classification, manual decisions, CSV, share metadata PASS')
