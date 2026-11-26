import unittest,sys,copy,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from category32 import scan,apply_overrides,proposal,write_review
from regions32 import intro,Nearby

def p(**kw):
    v={'id':'p1','name':'마이티그루밍','category':'카페','services':['미용','카페'],'subType':'카페','registryCategories':['미용 (일반)'],'verified':True,'licenseNo':'123','source':'농림축산식품부','description':'애견카페','sido':'서울특별시','sigungu':'강남구','dongKey':'논현동','geoPrecision':'exact','lat':37.51,'lng':127.03};v.update(kw);return v

def s(gu,cat='cafe'):return {'category':cat,'level':'sigungu','sido':'서울특별시','sigungu':gu,'filter':{'dongKey':None},'mainKeyword':gu+' 카페'}
class Tests(unittest.TestCase):
    def test_mighty(self):
        x=p();o,r=scan([x]);self.assertEqual(len(o),1);self.assertEqual(r,[]);self.assertEqual(apply_overrides([x],None,o)['changed'],1);self.assertEqual(x['services'],['미용']);self.assertEqual(x['subType'],'미용 (일반)');self.assertIsNone(x['description'])
    def test_dual(self):
        for x in [p(name='그루밍카페'),p(source='식약처'),p(registryCategories=['미용 (일반)','동물전시업']),p(description='애견카페, 호텔')]:self.assertEqual(proposal(x)[0],'review')
    def test_weak(self):self.assertEqual(proposal(p(name='펫스파',registryCategories=[],verified=False,licenseNo=None))[0],'review')
    def test_reverse(self):
        x=p(name='커피 베이커리',category='미용',services=['미용'],subType='커피숍',registryCategories=[],verified=False,licenseNo=None,source='식약처 반려동물 동반출입 음식점');self.assertEqual(proposal(x)[:2],('auto','카페'))
    def test_stale(self):
        x=p();o,_=scan([x]);x['name']='다른 업체';with_error=False
        with self.assertRaises(ValueError):apply_overrides([x],None,o)
    def test_funeral(self):self.assertIsNone(proposal(p(category='장례·추모',services=['장례·추모'],name='장례 카페')))
    def test_intro(self):
        t=intro(s('강남구'),[p(indoor=True,parking=False,petSize='모두 가능'),p(indoor=None,parking=True,petSizeLarge=False,petSize='모두 가능')]);self.assertIn('2곳',t);self.assertIn('실내 동반 가능으로 등록된 곳은 1곳',t);self.assertIn('주차 가능은 1곳',t);self.assertIn('표시된 곳은 1곳',t)
    def test_nearby(self):
        a=s('강남구');b=s('서초구');c=s('송파구');x=p();y=p(id='p2',sigungu='서초구',lat=37.49,lng=127.01);z=p(id='p3',sigungu='송파구',lat=37.50,lng=127.11);n=Nearby([x,y,z],[(a,'/a/',[x],None,None),(b,'/b/',[y],None,None),(c,'/c/',[],None,None)]);self.assertEqual(n.links(a,'/a/'),[('/b/','서초구 카페',1)])
if __name__=='__main__':unittest.main()
