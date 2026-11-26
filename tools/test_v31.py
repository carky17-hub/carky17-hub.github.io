"""Offline tests for owner approval, intake and card rendering. No external submissions."""
import sys, unittest, tempfile, json, datetime, base64, subprocess
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from owner_photos import load_owner_photos, cover, gallery
from cards22 import card
from v13 import detail_content
import forms
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2ZkAAAAASUVORK5CYII=')
class OwnerFlow(unittest.TestCase):
 def test_intake(self):
  for field in ('ownerHoursFields','name="hours"','name="closedDays"','ownerPhotoRights','ownerPortraitRights'):
   self.assertIn(field,forms.form)
  for fragment in ('hoursFields.hidden=hoursFields.disabled','data-owner-photo-link','p.set(\'place\',id)','new FormData(f)','ownerPhotoRights.checked','ownerPortraitRights.checked'):
   self.assertIn(fragment,forms.intake_js)
  self.assertIn('maxlength="300"',forms.form)
 def fixture(self,root):
  src=root/'source';site=root/'site';src.mkdir();site.mkdir();(src/'public-photos').mkdir();(src/'public-photos'/'test-owner.png').write_bytes(PNG)
  row={'id':'test-owner-01','placeId':'p1','filename':'test-owner.png','caption':'테스트 매장 사진','credit':'매장 제공','approved':True,'ownerConfirmed':True,'rightsConfirmed':True,'portraitConfirmed':True,'publishedOn':datetime.date.today().isoformat()}
  (src/'owner-photos.json').write_text(json.dumps([row]));(src/'visitor-photos.json').write_text('[]')
  p={'id':'p1','name':'검수 테스트','category':'카페','services':['카페'],'sigungu':'테스트','indoor':True,'tourPhoto':{'src':'https://example.com/other.jpg','license':'1','caption':'다른 사진'}}
  return src,site,row,p
 def test_approval_to_card_and_detail(self):
  with tempfile.TemporaryDirectory() as t:
   src,site,row,p=self.fixture(Path(t));out=load_owner_photos(src,[p],{},site)
   self.assertEqual((site/'approved-photos'/row['filename']).read_bytes(),PNG)
   self.assertEqual(p['ownerPhoto']['src'],'/approved-photos/test-owner.png')
   for text in (cover(p,'카페'),gallery(out['p1']),card(p)):
    self.assertIn('/approved-photos/test-owner.png',text);self.assertNotIn('https://example.com/other.jpg',text)
   self.assertNotIn('게시 승인된 사진이 없습니다.',detail_content('p1',{}, {},out['p1']))
   self.assertIn('게시 승인된 사진이 없습니다.',detail_content('p1',{},{}))
 def test_three_photos_and_duplicate(self):
  with tempfile.TemporaryDirectory() as t:
   src,site,row,p=self.fixture(Path(t));rows=[row]
   for i in (2,3):
    name=f'test-owner-{i}.png';(src/'public-photos'/name).write_bytes(PNG);rows.append(dict(row,id=f'test-owner-{i}',filename=name))
   (src/'owner-photos.json').write_text(json.dumps(rows));out=load_owner_photos(src,[p],{},site)
   self.assertEqual(len(out['p1']),3);self.assertTrue(all((site/'approved-photos'/r['filename']).is_file() for r in rows));self.assertEqual(p['ownerPhoto']['src'],'/approved-photos/test-owner.png')
   self.assertEqual(gallery(out['p1']).count('<figure>'),3)
   rows.append(dict(row,id='test-duplicate'));(src/'owner-photos.json').write_text(json.dumps(rows))
   with self.assertRaises(AssertionError):load_owner_photos(src,[p],{},site)
 def test_missing_approval_and_file(self):
  with tempfile.TemporaryDirectory() as t:
   src,site,row,p=self.fixture(Path(t));row['portraitConfirmed']=False;(src/'owner-photos.json').write_text(json.dumps([row]))
   with self.assertRaises(AssertionError):load_owner_photos(src,[p],{},site)
   row['portraitConfirmed']=True;(src/'owner-photos.json').write_text(json.dumps([row]));(src/'public-photos'/row['filename']).unlink()
   with self.assertRaises(AssertionError):load_owner_photos(src,[p],{},site)
 def test_merged_id(self):
  with tempfile.TemporaryDirectory() as t:
   src,site,row,p=self.fixture(Path(t));row['placeId']='p99';(src/'owner-photos.json').write_text(json.dumps([row]));out=load_owner_photos(src,[p],{'p99':'p1'},site);self.assertIn('p1',out)
if __name__=='__main__':unittest.main(verbosity=2)
