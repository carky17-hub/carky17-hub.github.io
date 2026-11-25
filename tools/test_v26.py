import sys,pathlib,tempfile,unittest,xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from images26 import *
from cards22 import card

def photo(n,lic='1'):return {'src':f'https://tong.visitkorea.or.kr/a/{n}.jpg','license':lic,'caption':'공식 사진'}
def place(n,ph):return {'id':f'p{n}','name':f'장소 {n}','category':'카페','sigungu':'마포구','tourPhoto':ph,'tourPhotos':[ph],'services':['카페']}
class Test(unittest.TestCase):
 def test_carousel(self):
  rows=[place(1,photo(1)),place(2,photo(2,'3')),place(3,photo(3,'2')),dict(place(4,photo(4)),operating=False),dict(place(5,photo(5)),indoor=False,outdoor=False),dict(place(6,photo(6)),id='f1')]
  h=carousel(rows,{p['id']:'key' for p in rows},card)
  self.assertIn('/place/p1/',h);self.assertIn('/place/p2/',h);self.assertNotIn('/place/p3/',h);self.assertNotIn('/place/p4/',h);self.assertNotIn('/place/p5/',h);self.assertNotIn('/place/f1/',h);self.assertNotIn('data-save',h);self.assertEqual(carousel([],{},card),'')
 def test_priority(self):
  h=prioritize(''.join(card(place(i,photo(i))) for i in range(1,5)))
  self.assertEqual(h.count('fetchpriority="high"'),2);self.assertEqual(h.count('loading="eager"'),2);self.assertEqual(h.count('loading="lazy"'),2);self.assertEqual(len(re.findall(r'<img[^>]*width="400" height="300"',h)),4);self.assertEqual(h.count('decoding="async"'),4)
 def test_sitemap(self):
  ps=[place(1,photo(1)),place(2,photo(2,'3')),place(3,photo(3,'2'))]
  with tempfile.TemporaryDirectory() as t:
   site=pathlib.Path(t);(site/'index.html').write_text(''.join(card(p) for p in ps));(site/'regions').mkdir();(site/'regions/index.html').write_text('no photo')
   xml=sitemap_xml(['/','/regions/'],lambda p:'https://eodigagae.com'+p,site,ps,{'/','/regions/'});(site/'sitemap.xml').write_text(xml);root=ET.fromstring(xml)
   self.assertEqual(len(root.findall('{*}url/{*}loc')),2);self.assertEqual([x.text for x in root.findall('.//{'+IMAGE_NS+'}loc')],[photo(1)['src']]);verify_sitemap(site,ps,{'/','/regions/'})
 def test_allowlist(self):
  for url in ('https://evil.test/a','https://visitkorea.or.kr.evil.test/a','https://user@visitkorea.or.kr/a','https://visitkorea.or.kr/a?q=secret','https://visitkorea.or.kr:444/a'):
   self.assertIsNone(tour_photo({'src':url,'license':'1'}))
if __name__=='__main__':unittest.main()
