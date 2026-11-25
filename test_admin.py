import unittest,copy,admin
A=[{'id':'p1','name':'old'},{'id':'p2','name':'second'}]; areas={'/cafe/a/':{'p1','p2'}}
def snapshot():return {'as_of':'2026-11-25','rows':{'corrections':[],'ads':[],'premium':[]}}
def ad(i='p1',slot='1',s='2026-11-24',e='2026-11-26'):return dict(page_path='/cafe/a/',place_id=i,slot=slot,start=s,end=e,product='regional',paid='Y')
def premium(**kw):return dict(place_id='p1',start_date='2026-11-24',end_date='2026-11-26',intro='<script>alert(1)</script>',menu='메뉴 1000원',reservation_url='https://example.com/book',photo_urls='',photo_rights_confirmed='TRUE',approved='TRUE')|kw
class Test(unittest.TestCase):
 def schedules(self,s):return admin.schedules(s,areas,{'p1','p2'})
 def test_boundary(self):
  r=ad()|{'start_date':'2026-11-24','end_date':'2026-11-26'};self.assertTrue(admin.active(r,'2026-11-24'));self.assertTrue(admin.active(r,'2026-11-26'));self.assertFalse(admin.active(r,'2026-11-27'));self.assertFalse(admin.active(r,'2026-11-23'))
 def test_overlap_same_slot(self):
  s=snapshot();s['rows']['ads']=[ad(),ad('p2',s='2026-11-26',e='2026-11-30')];self.assertRaisesRegex(ValueError,'overlap',self.schedules,s)
 def test_next_day(self):
  s=snapshot();s['rows']['ads']=[ad(),ad('p2',s='2026-11-27',e='2026-11-30')];self.assertEqual(len(self.schedules(s)[0]['/cafe/a/']),2)
 def test_duplicate_place_different_slot(self):
  s=snapshot();s['rows']['ads']=[ad(),ad(slot='2')];self.assertRaisesRegex(ValueError,'overlap',self.schedules,s)
 def test_bad_slot(self):
  s=snapshot();s['rows']['ads']=[ad(slot='4')];self.assertRaisesRegex(ValueError,'Slot',self.schedules,s)
 def test_unknown_place(self):
  s=snapshot();s['rows']['ads']=[ad(i='p9')];self.assertRaisesRegex(ValueError,'not in region',self.schedules,s)
 def test_premium_10_images_and_escape(self):
  s=snapshot();s['rows']['premium']=[premium(photo_urls='|'.join(f'https://example.com/{i}.png' for i in range(10)))];h=admin.premium_html(self.schedules(s)[1]['p1']);self.assertEqual(h.count('data-premium-src='),10);self.assertNotIn('<script>',h);self.assertIn('외부 예약 페이지',h)
 def test_11_images(self):
  s=snapshot();s['rows']['premium']=[premium(photo_urls='|'.join(f'https://example.com/{i}.png' for i in range(11)))];self.assertRaisesRegex(ValueError,'Maximum',self.schedules,s)
 def test_photo_rights(self):
  s=snapshot();s['rows']['premium']=[premium(photo_urls='https://example.com/a.png',photo_rights_confirmed='FALSE')];self.assertRaisesRegex(ValueError,'permission',self.schedules,s)
 def test_premium_overlap(self):
  s=snapshot();s['rows']['premium']=[premium(),premium()];self.assertRaisesRegex(ValueError,'overlap',self.schedules,s)
 def test_correction(self):
  s=snapshot();s['rows']['corrections']=[dict(place_id='p1',field='parking',value='FALSE',evidence_url='https://example.com',checked_on='2026-11-25',approved='TRUE')];a=copy.deepcopy(A);self.assertEqual(admin.apply(a,s),1);self.assertIs(a[0]['parking'],False);self.assertEqual(a[0]['operatorCorrections']['parking']['checkedOn'],'2026-11-25')
 def test_protected_field(self):
  s=snapshot();s['rows']['corrections']=[dict(place_id='p1',field='geoPrecision',value='exact',evidence_url='https://example.com',checked_on='2026-11-25',approved='TRUE')];self.assertRaises(ValueError,admin.apply,copy.deepcopy(A),s)
 def test_unapproved(self):
  s=snapshot();s['rows']['ads']=[ad()|{'paid':'N'}];self.assertEqual(self.schedules(s)[0],{})
 def test_unpaid_reserves_slot(self):
  s=snapshot();s['rows']['ads']=[ad()|{'paid':'N'},ad('p2')];self.assertRaisesRegex(ValueError,'overlap',self.schedules,s)
 def test_invalid_paid(self):
  s=snapshot();s['rows']['ads']=[ad()|{'paid':'TRUE'}];self.assertRaisesRegex(ValueError,'paid',self.schedules,s)
 def test_csv_schema(self):self.assertRaises(ValueError,admin.read_csv,'email,name\na,b','ads')
if __name__=='__main__':unittest.main(verbosity=2)
