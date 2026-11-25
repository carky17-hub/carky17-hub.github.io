"""Read-only release preflight, not PWABuilder's actual score. No external API calls."""
import argparse,json,re,struct,pathlib,urllib.request,urllib.parse,urllib.error,ssl,mimetypes
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]; BASE='https://eodigagae.com'; PACKAGE='com.eodigagae.app'
FP=re.compile(r'(?:[0-9A-F]{2}:){31}[0-9A-F]{2}')
def fingerprints(data,expected=(),release=False):
 if not isinstance(data,list):raise ValueError('assetlinks must be JSON array')
 fps=set()
 for r in data:
  t=r.get('target',{})
  if t.get('package_name')==PACKAGE and t.get('namespace')=='android_app' and 'delegate_permission/common.handle_all_urls' in r.get('relation',[]):
   for f in t.get('sha256_cert_fingerprints',[]):
    if not isinstance(f,str) or not FP.fullmatch(f):raise ValueError('Invalid SHA-256 format')
    fps.add(f)
 wanted={f.strip().upper() for f in expected}
 if any(not FP.fullmatch(f) for f in wanted):raise ValueError('Invalid expected fingerprint')
 if release and not wanted:raise ValueError('Release check needs actual Play app-signing SHA-256 (--fingerprint)')
 if wanted-fps:raise ValueError('Expected fingerprint missing')
 return fps
class Home(HTMLParser):
 def __init__(self,text):super().__init__();self.manifests=[];self.mixed=[];self.scripts=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='link' and 'manifest' in (a.get('rel') or '').split():self.manifests.append(a.get('href'))
  if tag=='script' and a.get('src'):self.scripts.append(a['src'])
  # Only fetched resources, not ordinary outbound href links or JSON-LD schema URLs.
  for k in (['src','poster'] if tag in ('img','script','iframe','video','audio','source','embed') else ['href'] if tag=='link' else ['action'] if tag=='form' else []):
   if (a.get(k) or '').lower().startswith('http://'):self.mixed.append(tag+':'+k)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None

def run(get,expected=(),release=False):
 fail=[];warn=[]
 def check(label,fn):
  try:fn();print('PASS',label)
  except Exception as e:fail.append(label);print('FAIL',label,str(e))
 def info(label,msg):warn.append(label);print('WARN',label,msg)
 def doc(path):return get(path)[0].decode('utf-8')
 def home():
  h=Home(doc('/'));assert h.manifests==['/manifest.webmanifest'],'manifest link missing/duplicate';assert not h.mixed,'insecure resource attributes: '+str(h.mixed)
  # Verify SW registration in the emitted first-party bundle, not just source.
  scripts=[x for x in h.scripts if x.startswith('/core.js')];assert scripts,'core script missing'
  assert "serviceWorker.register('/sw.js'" in doc(scripts[0]),'SW registration missing'
 def manifest():
  raw,ct,_=get('/manifest.webmanifest');assert 'json' in ct or 'manifest' in ct,'manifest MIME';m=json.loads(raw)
  assert m['id']==m['start_url']==m['scope']=='/' and m['display']=='standalone';assert m['name'] and m['short_name'] and m['description'] and m['lang']=='ko'
  assert all(re.fullmatch(r'#[0-9A-Fa-f]{6}',m[k]) for k in ('theme_color','background_color'))
  icons=set()
  for x in m['icons']+m.get('screenshots',[])+[i for s in m['shortcuts'] for i in s.get('icons',[])]:
   raw,ct,_=get(x['src']);assert 'image/png' in ct and raw[:8]==b'\x89PNG\r\n\x1a\n' and raw[12:16]==b'IHDR','PNG MIME or header';w,h=struct.unpack('>II',raw[16:24]);assert f'{w}x{h}' in x['sizes'].split();icons.add((w,h,x.get('purpose','any')))
  assert (192,192,'any') in icons and (512,512,'any') in icons and (512,512,'maskable') in icons
  for s in m['shortcuts']:get(urllib.parse.urlsplit(s['url']).path)
  if not m.get('screenshots'):info('screenshots','Optional manifest field empty; use actual approved captures, do not fabricate.')
 def sw():
  raw,ct,_=get('/sw.js');s=raw.decode();assert 'javascript' in ct or 'ecmascript' in ct,'SW MIME';assert all(x in s for x in ('skipWaiting()','clients.claim()','/offline.html','eg-public-v290-core',"cache:'reload'"))
  off=doc('/offline.html');assert '인터넷 연결' in off and not Home(off).scripts and 'rel="stylesheet"' not in off
 def dal():
  raw,ct,_=get('/.well-known/assetlinks.json');assert 'application/json' in ct,'DAL MIME';fps=fingerprints(json.loads(raw),expected,release)
  if not fps:info('assetlinks','No signing fingerprints yet; not ready for signed Android app.')
  print('  registered certificate count:',len(fps))
 def privacy():
  s=doc('/privacy/');assert '개인정보처리방침' in s
  if '개인정보처리방침 (초안)' in s or '초안입니다' in s or '운영자 정보 준비 중' in s:
   if release:raise ValueError('Finalize actual privacy policy before release')
   info('privacy','Draft/placeholder detected; finalize before release.')
 for label,fn in [('home / secure resource attributes / SW registration',home),('manifest / icons / shortcuts',manifest),('service worker / offline',sw),('digital asset links',dal),('privacy policy',privacy)]:check(label,fn)
 print(f'{5-len(fail)}/5 checks passed; {len(warn)} warning(s). Actual PWABuilder report and Android install still required.')
 return not fail

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true');p.add_argument('--site',type=pathlib.Path,default=ROOT/'site');p.add_argument('--fingerprint',action='append',default=[]);p.add_argument('--release',action='store_true');a=p.parse_args()
 opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 def get(path):
  u=urllib.parse.urlsplit(path);assert path.startswith('/') and not path.startswith('//') and not u.netloc and not u.scheme and '..' not in u.path.split('/'),'unsafe path'
  if a.live:
   with opener.open(urllib.request.Request(BASE+path,headers={'User-Agent':'Eodigagae-PWA-Preflight/2.9'}),timeout=12) as r:
    assert r.status==200 and r.geturl()==BASE+path;return r.read(12*1024*1024+1),r.headers.get('Content-Type',''),r.headers
  f=a.site/u.path.lstrip('/');f=f/'index.html' if f.is_dir() else f
  return f.read_bytes(), 'application/manifest+json' if f.suffix=='.webmanifest' else (mimetypes.guess_type(str(f))[0] or ''),{}
 return 0 if run(get,a.fingerprint,a.release) else 1
if __name__=='__main__':raise SystemExit(main())
