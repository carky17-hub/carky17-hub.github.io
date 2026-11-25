"""Build optional verified PWA screenshots; never embed mock or third-party API images."""
import json, pathlib, struct, re, shutil

def png_size(path):
 with path.open('rb') as f: h=f.read(24)
 if len(h)!=24 or h[:8]!=b'\x89PNG\r\n\x1a\n' or h[12:16]!=b'IHDR': raise ValueError(f'PNG required: {path.name}')
 w,h=struct.unpack('>II',h[16:24]);return w,h

def prepare_manifest(root,site):
 path=site/'manifest.webmanifest';m=json.loads(path.read_text(encoding='utf-8'))
 for icon in m['icons']:
  w,h=png_size(site/icon['src'].lstrip('/'));assert f'{w}x{h}' in icon['sizes'].split()
 assert any('maskable' in i.get('purpose','').split() for i in m['icons'])
 # Explicit, operator-approved screenshots only; no mock/stale public images.
 src=root/'source'/'app-screenshots'; shots=[]
 meta=src/'approved.json'
 if meta.is_file():
  rows=json.loads(meta.read_text(encoding='utf-8'))
  if not isinstance(rows,list) or len(rows)>8:raise ValueError('approved.json: 0–8 screenshots')
  seen=set()
  for row in rows:
   name=row['file'];label=row['label'];form=row.get('form_factor','narrow')
   if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}\.png',name) or name in seen or not isinstance(label,str) or not label.strip() or len(label)>100 or form not in ('narrow','wide'):raise ValueError('Invalid screenshot metadata')
   seen.add(name);f=src/name
   if f.is_symlink() or f.stat().st_size>8*1024*1024:raise ValueError('Invalid screenshot file')
   w,h=png_size(f)
   if not 320<=min(w,h)<=max(w,h)<=3840 or max(w,h)>2.3*min(w,h) or (form=='narrow' and w>=h) or (form=='wide' and w<h):raise ValueError('Invalid screenshot dimensions')
   dest=site/'app-screenshots'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(f,dest)
   shots.append({'src':'/app-screenshots/'+name,'sizes':f'{w}x{h}','type':'image/png','form_factor':form,'label':label})
 m['screenshots']=shots
 path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return m

def verify_manifest(site):
 m=json.loads((site/'manifest.webmanifest').read_text(encoding='utf-8'))
 assert m['start_url']=='/' and m['scope']=='/' and m['display']=='standalone'
 assert any('maskable' in i.get('purpose','').split() for i in m['icons'])
 for i in m['icons']+m['screenshots']:
  w,h=png_size(site/i['src'].lstrip('/'));assert f'{w}x{h}' in i['sizes'].split()
 for s in m['shortcuts']:
  from urllib.parse import urlsplit
  u=urlsplit(s['url']);assert not u.scheme and not u.netloc and u.path.startswith('/')
  assert (site/u.path.lstrip('/')/'index.html').is_file()
 for x in m['screenshots']:assert x['form_factor'] in ('narrow','wide')
 assert '<link rel="stylesheet"' not in (site/'offline.html').read_text(encoding='utf-8')
 print('v2.8 manifest, offline shell and screenshot assets PASS:',len(m['screenshots']),'approved screenshots')
