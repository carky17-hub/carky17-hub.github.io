"""Read-only live checks. No API calls, forms, phone dialing or GPS access."""
import argparse,json,re,urllib.request,urllib.error,urllib.parse,sys
p=argparse.ArgumentParser();p.add_argument('--base',default='https://eodigagae.com');p.add_argument('--require-assetlinks',action='store_true');p.add_argument('--require-screenshots',action='store_true');p.add_argument('--fingerprint');p.add_argument('--package',default='com.eodigagae.app');a=p.parse_args();base=a.base.rstrip('/');u=urllib.parse.urlsplit(base);assert u.scheme=='https' and u.netloc and not u.path
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(NoRedirect());failed=[]
def get(path):
 assert path.startswith('/') and not path.startswith('//')
 with opener.open(urllib.request.Request(base+path,headers={'User-Agent':'Eodigagae-app-check/2.8'}),timeout=15) as r:
  assert r.status==200 and r.geturl()==base+path;return r.read(),r.headers.get('Content-Type','')
def check(name,fn):
 try:fn();print('PASS',name)
 except Exception as e:failed.append(name);print('FAIL',name,str(e))
def manifest():
 raw,ct=get('/manifest.webmanifest');assert 'json' in ct or 'manifest' in ct;d=json.loads(raw);assert d['scope']==d['start_url']=='/' and d['display']=='standalone' and any('maskable' in i.get('purpose','') for i in d['icons']);
 for i in d['icons']+d.get('screenshots',[]):assert get(i['src'])[0].startswith(b'\x89PNG\r\n\x1a\n')
 for s in d['shortcuts']:get(urllib.parse.urlsplit(s['url']).path)
 if a.require_screenshots:assert d.get('screenshots')
 print('screenshots:',len(d.get('screenshots',[])))
def dal():
 raw,ct=get('/.well-known/assetlinks.json');assert 'json' in ct;d=json.loads(raw);assert isinstance(d,list)
 if a.require_assetlinks or a.fingerprint:
  rows=[x for x in d if 'delegate_permission/common.handle_all_urls' in x.get('relation',[]) and x.get('target',{}).get('package_name')==a.package and x['target'].get('namespace')=='android_app'];assert rows
  fps=[f for x in rows for f in x['target'].get('sha256_cert_fingerprints',[])];assert fps and all(re.fullmatch(r'(?:[0-9A-F]{2}:){31}[0-9A-F]{2}',f) for f in fps)
  if a.fingerprint:assert a.fingerprint.upper() in fps
 else:print('DAL entries:',len(d),'(empty allowed pre-signing)')
def offline():
 raw,_=get('/offline.html');s=raw.decode();assert '인터넷 연결' in s and 'rel="stylesheet"' not in s;assert 'eg-public-v280-core' in get('/sw.js')[0].decode()
def privacy():
 raw,ct=get('/privacy/');s=raw.decode();assert 'html' in ct and '개인정보처리방침' in s
 if '개인정보처리방침 (초안)' in s or '초안입니다' in s:raise ValueError('Privacy policy draft: finalize before release')
def home():
 s=get('/')[0].decode();assert 'manifest.webmanifest' in s and '내 주변' in s
check('home',home);check('manifest/icons/screenshots/shortcuts',manifest);check('assetlinks',dal);check('offline/service worker',offline);check('privacy',privacy)
print('Manual Android TWA, app links, location and UGC policy checks still required.');sys.exit(bool(failed))
