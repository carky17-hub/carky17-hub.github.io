import pathlib,sys,unittest,os
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from app_release import asset_links
from pwa29_check import fingerprints,Home,PACKAGE
A=':'.join(['AB']*32); B=':'.join(['CD']*32)
class Tests(unittest.TestCase):
 def test_both(self):
  with patch.dict(os.environ,{'ANDROID_PACKAGE_ID':PACKAGE,'ANDROID_SHA256_CERT_FINGERPRINTS':A.lower()+', '+B+','+A}):
   d=asset_links();self.assertEqual(d[0]['target']['sha256_cert_fingerprints'],[A,B]);self.assertEqual(fingerprints(d,[A,B],True),{A,B})
 def test_missing(self):
  with patch.dict(os.environ,{'ANDROID_PACKAGE_ID':PACKAGE,'ANDROID_SHA256_CERT_FINGERPRINTS':A}):
   self.assertRaises(ValueError,fingerprints,asset_links(),[A,B],True)
  self.assertRaises(ValueError,fingerprints,[],[],True)
 def test_invalid(self):
  with patch.dict(os.environ,{'ANDROID_PACKAGE_ID':PACKAGE,'ANDROID_SHA256_CERT_FINGERPRINTS':'wrong'}):self.assertRaises(ValueError,asset_links)
 def test_wrong_package(self):
  with patch.dict(os.environ,{'ANDROID_PACKAGE_ID':'com.other.app','ANDROID_SHA256_CERT_FINGERPRINTS':A}):self.assertRaises(ValueError,fingerprints,asset_links(),[A],True)
 def test_mixed(self):
  self.assertEqual(Home('<a href="http://example.org">x</a><script src="http://example.org/a"></script>').mixed,['script:src'])
if __name__=='__main__':unittest.main()
