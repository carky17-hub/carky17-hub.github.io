import csv,pathlib,tempfile,unittest,sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from csv_to_overrides import HEAD,parse_csv,merge
class Tests(unittest.TestCase):
 def csv(self,rows):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'test.csv'
   with p.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(HEAD)
    for cid,pid,decision in rows:w.writerow([cid,'','',''+pid,'','','','','','','',decision])
   return parse_csv(p)
 def test_duplicates_blank(self):
  self.assertEqual(self.csv([('1','p1','p1'),('1','p2',''),('2','','new'),('3','','skip')]),({'1':'p1','2':'new','3':'skip'},1))
 def test_conflicting(self):
  with self.assertRaises(ValueError):self.csv([('1','p1','p1'),('1','p2','new')])
 def test_not_candidate(self):
  with self.assertRaises(ValueError):self.csv([('1','p1','p3')])
 def test_invalid(self):
  with self.assertRaises(ValueError):self.csv([('1','p1','=1+2')])
 def test_merge(self):
  self.assertEqual(merge({'1':'p1'},{'2':'new'}),{'1':'p1','2':'new'})
  with self.assertRaises(ValueError):merge({'1':'p1'},{'1':'skip'})
  with self.assertRaises(ValueError):merge({'1':'p1'},{'2':'p1'})
  self.assertEqual(merge({'1':'p1'},{'1':'skip'},True),{'1':'skip'})
if __name__=='__main__':unittest.main()
