"""390px Chromium fixture route; never contacts/dials external services. pip install playwright; Chromium installed separately."""
import pathlib,mimetypes,urllib.parse,os
from playwright.sync_api import sync_playwright
site=pathlib.Path(__file__).resolve().parents[1]/'site'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='block');page=c.new_page();errors=[];requested=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def route(r):
  u=urllib.parse.urlsplit(r.request.url);requested.append(r.request.url)
  if u.hostname!='eodigagae.com':return r.abort()
  f=site/u.path.lstrip('/');f=f/'index.html' if f.is_dir() else f
  if f.is_file():return r.fulfill(status=200,content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream',body=f.read_bytes())
  r.fulfill(status=404,body='')
 c.route('**/*',route)
 page.set_content((site/'offline.html').read_text(encoding='utf-8'),wait_until='load');assert page.get_by_role('heading',name='인터넷 연결을 확인해 주세요.').count()==1;assert page.locator('a.btn').get_attribute('href')=='/';assert page.evaluate('document.documentElement.scrollWidth')==390;assert all(urllib.parse.urlsplit(u).path in ('/offline.html','/favicon.ico') for u in requested)
 f=next(x for x in (site/'place').glob('p*/index.html') if all(k in x.read_text(encoding='utf-8') for k in ['href="tel:','https://map.kakao.com/link/to/','https://map.naver.com/']) and '검수 전용' not in x.read_text(encoding='utf-8'))
 # Offline inlined HTML/CSS only; do not execute application JS or request providers.
 import re
 text=f.read_text(encoding='utf-8');text=re.sub(r'<script\b[^>]*>.*?</script>','',text,flags=re.S|re.I);text=re.sub(r'<link\b[^>]*rel="stylesheet"[^>]*>','',text,flags=re.I);text=text.replace('</head>','<style>'+ (site/'bundle.css').read_text(encoding='utf-8')+'</style></head>');page.set_content(text,wait_until='domcontentloaded')
 phone=page.locator('a[href^="tel:"]').first;assert phone.get_attribute('href').startswith('tel:');assert phone.count()
 for host,prefix in [('map.kakao.com','https://map.kakao.com/link/to/'),('map.naver.com','https://map.naver.com/')]:
  a=page.locator('a[href^="'+prefix+'"]').first
  assert a.count() and a.get_attribute('target')=='_blank' and 'noopener' in (a.get_attribute('rel') or '')
  # Browser navigation target only; do not open/call actual service.
  print(host,a.get_attribute('href'))
 print('390px offline shell + rendered detail telephone/external HTTPS link attributes PASS; real Android intent not tested',f.parent.name, 'page errors:',errors)
 assert not errors;b.close()
