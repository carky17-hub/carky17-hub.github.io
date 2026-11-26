import pathlib,re,unittest
R=pathlib.Path(__file__).resolve().parents[1]
class Test(unittest.TestCase):
 def test_assets(self):
  s=(R/'build.py').read_text();self.assertRegex(s,r"\('core\.js',\([^\n]+?'tabbar\.js'\)");self.assertIn("SITE/'tabbar.css'",s);self.assertRegex(s,r"elif f\.name not in \{[^\n]+?'tabbar\.js','tabbar\.css'")
 def test_navigation(self):
  s=(R/'site/tabbar.js').read_text();self.assertIn("['saved','저장','/#saved']",s);self.assertIn("['find','장소 찾기','/#explore']",s);self.assertIn("b.click()",s);self.assertIn('eg33-has-actions',s);self.assertNotIn('navigator.geolocation',s)
 def test_empty(self):
  s=(R/'site/search-ui.js').read_text();self.assertIn('전국으로 넓혀 보기',s);self.assertIn("region.dispatchEvent(new Event('change'",s);self.assertIn('MutationObserver(scanEmpty)',s);self.assertIn("location.hash==='#saved'",s)
 def test_css(self):
  s=(R/'site/tabbar.css').read_text();self.assertIn('max-width:767px',s);self.assertIn('safe-area-inset-bottom',s);self.assertIn('.mobile-nav{display:none!important}',s);self.assertIn('body.eg-map-full',s)
if __name__=='__main__':unittest.main()
