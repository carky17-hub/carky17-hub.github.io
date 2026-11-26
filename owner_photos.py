"""Only operator-approved, rights-cleared owner photos. Public metadata only."""
import json,re,html,collections,shutil,datetime
E=lambda x:html.escape(str(x or ''),quote=True)
FIELDS={'id','placeId','filename','caption','credit','approved','ownerConfirmed','rightsConfirmed','portraitConfirmed','publishedOn'}
def load_owner_photos(src,places,merged,site=None):
 rows=json.loads((src/'owner-photos.json').read_text(encoding='utf-8'));assert isinstance(rows,list)
 visitor=json.loads((src/'visitor-photos.json').read_text(encoding='utf-8'));assert isinstance(visitor,list)
 rows=[(r,False) for r in rows]+[(r,True) for r in visitor]
 by={p['id']:p for p in places};out=collections.defaultdict(list);seen=set()
 for r,is_visitor in rows:
  required=(FIELDS-{'ownerConfirmed'})|{'visitConfirmed','advertising'} if is_visitor else FIELDS
  assert set(r)==required and all(r[k] is True for k in ('approved','visitConfirmed' if is_visitor else 'ownerConfirmed','rightsConfirmed','portraitConfirmed')) and (not is_visitor or type(r['advertising']) is bool), 'Owner photos require explicit approval, copyright and portrait rights'
  assert re.fullmatch(r'[A-Za-z0-9_-]{1,80}',r['id']) and r['id'] not in seen;seen.add(r['id'])
  pid=merged.get(r['placeId'],r['placeId']);assert pid in by and not pid.startswith('f'),'Owner photos for neutral funeral excluded'
  assert re.fullmatch(r'[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)',r['filename']) and 0<len(r['caption'])<=150 and 0<len(r['credit'])<=100
  assert datetime.date.fromisoformat(r['publishedOn'])<=datetime.date.today()
  f=src/'public-photos'/r['filename'];assert f.is_file() and 0<f.stat().st_size<=5_000_000
  h=f.read_bytes()[:12];assert f.suffix in ('.jpg','.jpeg') and h.startswith(b'\xff\xd8\xff') or f.suffix=='.png' and h.startswith(b'\x89PNG\r\n\x1a\n') or f.suffix=='.webp' and h[:4]==b'RIFF' and h[8:12]==b'WEBP'
  assert len(out[pid])<10 and ('/approved-photos/'+r['filename']) not in {x['src'] for x in out[pid]}
  out[pid].append({'src':'/approved-photos/'+f.name,'caption':r['caption'],'credit':r['credit'],'label':('AD · ' if r.get('advertising') else '')+('방문자 제공' if is_visitor else '사장님 제공')})
  if site is not None:
   d=site/'approved-photos'/f.name;d.parent.mkdir(exist_ok=True);shutil.copyfile(f,d)
 for p in places:p['ownerPhoto']=out[p['id']][0] if out[p['id']] else None
 return out

def cover(p,service):
 r=p.get('ownerPhoto')
 if r:return f'<div class="cover owner-photo-cover"><img src="{E(r["src"])}" alt="{E(r["caption"])}" width="480" height="300" loading="lazy" decoding="async"><span class="photo-credit">{E(r["label"])} · {E(r["credit"])}</span></div>'
 if p.get('tourPhoto'):
  t=p['tourPhoto'];return f'<div class="cover tour-photo-cover"><img src="{E(t["src"])}" alt="{E(t["caption"])}" loading="lazy" decoding="async"><span class="photo-credit">한국관광공사 · 공공누리 {E(t["license"])}유형 · <a href="https://www.data.go.kr/data/15135102/openapi.do">출처</a></span></div>'
 return f'<div class="cover place-art" data-kind="{E(p["category"])}"><span class="art-label">{E(service)} · 사진 준비 중</span></div>'

def gallery(rows):
 if not rows:return ''
 return '<section class="panel owner-photo-gallery"><h2>승인된 매장·방문자 사진</h2><div class="premium-gallery">'+''.join(f'<figure><img src="{E(r["src"])}" alt="{E(r["caption"])}" width="480" height="300" loading="lazy" decoding="async"><figcaption>{E(r["label"])} · {E(r["caption"])} · {E(r["credit"])}</figcaption></figure>' for r in rows)+'</div></section>'
