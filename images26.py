"""Static photo discovery and image sitemap helpers. No network requests."""
import html,re,urllib.parse,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from xml.sax.saxutils import escape
NS='http://www.sitemaps.org/schemas/sitemap/0.9'
IMAGE_NS='http://www.google.com/schemas/sitemap-image/1.1'

def tour_photo(photo,licenses=('1','3')):
    if not isinstance(photo,dict) or str(photo.get('license')) not in licenses:return None
    src=photo.get('src')
    if not isinstance(src,str):return None
    try:
        u=urllib.parse.urlsplit(src);h=u.hostname or ''
        if u.scheme=='https' and not (u.username or u.password or u.port or u.query or u.fragment) and (h=='visitkorea.or.kr' or h.endswith('.visitkorea.or.kr')) and u.path:return src
    except ValueError:pass
    return None

def owner_photo(photo):
    return isinstance(photo,dict) and re.fullmatch(r'/approved-photos/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)',str(photo.get('src',''))) and not str(photo.get('label','')).startswith('AD')

def eligible(p):
    return not p['id'].startswith('f') and p.get('operating') is not False and not(p.get('indoor') is False and p.get('outdoor') is False) and bool(owner_photo(p.get('ownerPhoto')) or tour_photo(p.get('tourPhoto')))

def carousel(rows,keys,card,regional=True):
    selected=[p for p in rows if eligible(p)][:8]
    if not selected:return ''
    # Region pages do not load the home-only save handler. Do not add inert controls.
    cards=[]
    for p in selected:
        markup=card(p,keys[p['id']])
        markup,n=re.subn(r'<button\b[^>]*\bdata-save="[^"]+"[^>]*>.*?</button>','',markup,count=1,flags=re.S)
        if n!=1:raise ValueError('regional card save anchor changed')
        cards.append(markup)
    return '<section class="panel eg-region-photos" aria-label="사진 있는 장소"><div class="head"><h2>사진 있는 장소</h2><span>좌우로 둘러보기</span></div><p>등록된 사진이 있는 '+('이 지역 장소' if regional else '전국 장소')+'입니다. 동반 조건은 방문 전 확인하세요.</p><div class="eg-curated-cards" tabindex="0" aria-label="사진 있는 장소 목록">'+''.join(cards)+'</div></section>'

def prioritize(markup):
    # Exactly first two rendered card photos (not placeholder SVG or JSON strings).
    n=0
    def tag(m):
        nonlocal n
        s=m.group(0);n+=1
        s=re.sub(r'\s(?:loading|fetchpriority)="[^"]*"','',s)
        return s[:-1]+(' loading="eager" fetchpriority="high"' if n<=2 else ' loading="lazy" fetchpriority="auto"')+'>'
    return re.sub(r'<img\b[^>]*\bdata-card-photo\b[^>]*>',tag,markup)

class Photos(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.src=set()
    def handle_starttag(self,tag,attrs):
        if tag=='img':
            a=dict(attrs)
            if 'src' in a and 'hidden' not in a:self.src.add(a['src'])

def actual_images(path,allowed):
    markup=path.read_text(encoding='utf-8')
    if 'visitkorea.or.kr' not in markup:return []
    parser=Photos();parser.feed(markup);return sorted(parser.src & allowed)[:1000]

def allowed_images(places):
    # Type 3 stays on our pages unmodified; external search thumbnail cropping is not controlled.
    return {u for p in places if not p['id'].startswith('f') and p.get('operating') is not False for ph in [p.get('tourPhoto'),*(p.get('tourPhotos') or [])] if (u:=tour_photo(ph,('1',)))}

def image_candidates(places,pageinfo):
    return {'/','/regions/'} | {path for _,path,rows,_,_ in pageinfo if any(eligible(p) and tour_photo(p.get('tourPhoto'),('1',)) and not p.get('ownerPhoto') for p in rows)} | {'/place/'+p['id']+'/' for p in places if p.get('tourPhoto') or p.get('tourPhotos')}

def sitemap_xml(paths,url,site,places,candidates):
    allowed=allowed_images(places);chunks=[];count=0;with_images=0
    for path in paths:
        photos=actual_images(site/path.strip('/')/'index.html',allowed) if allowed and path in candidates else []
        count+=len(photos);with_images+=bool(photos)
        chunks.append('<url><loc>'+escape(url(path))+'</loc>'+''.join('<image:image><image:loc>'+escape(x)+'</image:loc></image:image>' for x in photos)+'</url>\n')
    print(f'v2.6 image sitemap: {count} image entries across {with_images} pages')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="'+NS+'" xmlns:image="'+IMAGE_NS+'">\n'+''.join(chunks)+'</urlset>'

def verify_sitemap(site,places,paths):
    allowed=allowed_images(places);root=ET.parse(site/'sitemap.xml').getroot();count=0
    for e in root.findall('{'+NS+'}url'):
        path=urllib.parse.unquote(urllib.parse.urlsplit(e.findtext('{'+NS+'}loc')).path)
        found=[i.findtext('{'+IMAGE_NS+'}loc') for i in e.findall('{'+IMAGE_NS+'}image')]
        assert len(found)==len(set(found))<=1000 and set(found)<=allowed
        expected=actual_images(site/path.strip('/')/'index.html',allowed) if allowed and path in paths else []
        assert found==expected,(path,'image sitemap differs from visible HTML')
        count+=len(found)
    print('v2.6 image sitemap verified:',count)
