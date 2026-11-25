import pathlib,sys,tempfile,json,shutil,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app28 import prepare_manifest,verify_manifest
from app_release import asset_links
from unittest.mock import patch
class App(unittest.TestCase):
 def test_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   r=pathlib.Path(d);s=r/'site';s.mkdir()
   for f in ['manifest.webmanifest','icon-192.png','icon-512.png','icon-maskable.png','offline.html']:shutil.copyfile(ROOT/'site'/f,s/f)
   (s/'index.html').touch();(s/'funeral').mkdir();(s/'funeral/index.html').touch()
   self.assertEqual(prepare_manifest(r,s)['screenshots'],[]);verify_manifest(s)
   from struct import pack
   a=r/'source/app-screenshots';a.mkdir(parents=True)
   # Header only, synthetic dimensions for unit test, never shipped/published.
   (a/'test.png').write_bytes(b'\x89PNG\r\n\x1a\n'+pack('>I',13)+b'IHDR'+pack('>II',1080,1920))
   (a/'approved.json').write_text(json.dumps([{'file':'test.png','label':'test'}]));self.assertEqual(prepare_manifest(r,s)['screenshots'][0]['sizes'],'1080x1920');verify_manifest(s)
   (a/'approved.json').write_text(json.dumps([{'file':'../test.png','label':'bad'}]));self.assertRaises(ValueError,prepare_manifest,r,s)
 def test_assetlinks(self):
  with patch.dict('os.environ',{'ANDROID_PACKAGE_ID':'com.eodigagae.app','ANDROID_SHA256_CERT_FINGERPRINTS':''}):self.assertEqual(asset_links(),[])
  with patch.dict('os.environ',{'ANDROID_PACKAGE_ID':'com.eodigagae.app','ANDROID_SHA256_CERT_FINGERPRINTS':':'.join(['AB']*32)}):self.assertEqual(asset_links()[0]['target']['package_name'],'com.eodigagae.app')
 def test_offline(self):
  text=(ROOT/'site/offline.html').read_text();self.assertNotIn('src="/',text);self.assertNotIn('rel="stylesheet"',text);self.assertIn('href="/"',text)
if __name__=='__main__':unittest.main()
