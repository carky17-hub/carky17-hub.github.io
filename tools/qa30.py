#!/usr/bin/env python3
"""Static QA for built eodigagae site. No network access or site mutation."""
import argparse, collections, csv, json, pathlib, posixpath, re, sys, time
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, unquote
import xml.etree.ElementTree as ET
try:
    from lxml import html as lx
except ImportError:
    lx = None

VOID=set('area base br col embed hr img input link meta param source track wbr'.split())
SKIP={'script','style','template'}
def norm(s): return ' '.join((s or '').split())
def tokens(s): return set(re.split(r'[\s,]+',(s or '').lower()))
def route(f): return '/'+(f[:-10] if f=='index.html' or f.endswith('/index.html') else f)
class Node:
    def __init__(self,tag,attrs,line): self.tag=tag;self.attrib=dict(attrs);self.sourceline=line;self.children=[];self.parent=None
    def get(self,k,default=None): return self.attrib.get(k,default)
    def __iter__(self): return (c for c in self.children if isinstance(c,Node))
class Tree(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True);self.root=Node('document',[],1);self.stack=[self.root];self.nodes=[]
    def handle_starttag(self,t,a):
        n=Node(t,a,self.getpos()[0]);self.stack[-1].children.append(n);n.parent=self.stack[-1];self.nodes.append(n)
        if t not in VOID:self.stack.append(n)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t:del self.stack[i:];break
    def handle_startendtag(self,t,a):self.handle_starttag(t,a);self.handle_endtag(t)
    def handle_data(self,d):self.stack[-1].children.append(d)
def parse(text,engine):
    if engine=='lxml':return list(lx.document_fromstring(text).iter())
    p=Tree();p.feed(text);p.close();return p.nodes

def hidden(n):return 'hidden' in n.attrib or n.get('aria-hidden')=='true' or n.tag in SKIP

def text_of(n,include_hidden=False):
    if not include_hidden and hidden(n):return ''
    if n.tag=='img':return n.get('alt') or ''
    if isinstance(n,Node):return ' '.join(c if isinstance(c,str) else text_of(c,include_hidden) for c in n.children)
    parts=[n.text or '']
    for c in n:
        if isinstance(c.tag,str):parts.append(text_of(c,include_hidden))
        parts.append(c.tail or '')
    return ' '.join(parts)

def parent(n):return n.parent if isinstance(n,Node) else n.getparent()
def in_head(n):
    while (n:=parent(n)) is not None:
        if n.tag=='head':return True
        if n.tag=='body':return False
    return False
def control_name(n,ids):
    refs=norm(n.get('aria-labelledby')).split()
    if refs:
        name=norm(' '.join(text_of(ids[x],True) for x in refs if x in ids))
        if name:return name
    if norm(n.get('aria-label')):return norm(n.get('aria-label'))
    if n.tag=='input':
        t=(n.get('type') or '').lower()
        if t in ('submit','reset'):return norm(n.get('value')) or t
        if t=='image':return norm(n.get('alt')) or norm(n.get('title'))
        return norm(n.get('value')) or norm(n.get('title'))
    # The control may be hidden initially; aria-hidden descendants do not supply its name.
    if isinstance(n,Node):v=' '.join(c if isinstance(c,str) else text_of(c) for c in n.children)
    else:v=' '.join([n.text or '']+[part for c in n for part in ((text_of(c) if isinstance(c.tag,str) else ''),c.tail or '')])
    return norm(v) or norm(n.get('title'))

class Audit:
    def __init__(self,site,base,engine,title_max=60,desc_max=160):
        self.site=site;self.base=base.rstrip('/');self.host=urlsplit(base).netloc.lower();self.hosts={self.host};self.hosts.add(self.host[4:] if self.host.startswith('www.') else 'www.'+self.host);self.engine=engine;self.title_max=title_max;self.desc_max=desc_max
        self.files={p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()};self.htmls=sorted(f for f in self.files if f.lower().endswith('.html'))
        self.issues=[];self.pages={};self.sitemap=set();self.regions={};self.preview=False;self.report_found=False;self.groups={'TITLE':collections.defaultdict(list),'DESCRIPTION':collections.defaultdict(list)};self.links=0;self.internal=0;self.images=0;self.buttons=0
    def add(self,level,code,page,detail='',line=None):self.issues.append(dict(level=level,code=code,page=page,detail=detail,line=line))
    def resolve(self,raw,current):
        try:
            u=urlsplit(urljoin(current,raw));host=u.netloc.lower()
            if u.scheme not in ('http','https') or host not in self.hosts:return None,u
            p=unquote(u.path or '/',errors='strict')
            if '\x00' in p or '\\' in p:return None,u
            p=posixpath.normpath('/'+p.lstrip('/'))
            if p=='/':c=['index.html']
            elif u.path.endswith('/'):c=[p.lstrip('/')+'/index.html']
            else:c=[p.lstrip('/'),p.lstrip('/')+'/index.html']
            return next((x for x in c if x in self.files),None),u
        except (ValueError,UnicodeError):return None,None
    def load_report(self):
        try:
            r=json.loads((self.site/'data/build-report.json').read_text(encoding='utf-8'));self.preview=bool(r.get('preview'));self.regions={x['path']:x for x in r['regionCounts']};self.report_found=True
        except (OSError,ValueError,KeyError,TypeError):self.add('warning','BUILD_REPORT_UNAVAILABLE','/data/build-report.json','Zero-place counts and preview mode not authoritative')
    def read_sitemap(self):
        seen=set();active=set();ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
        def walk(rel):
            if rel in active:self.add('error','SITEMAP_CYCLE',rel);return
            if rel in seen:return
            seen.add(rel);active.add(rel)
            try:
                f=self.site/rel
                if f.stat().st_size>52428800:self.add('error','SITEMAP_SIZE',rel)
                root=ET.parse(f).getroot()
                if root.tag==ns+'sitemapindex':
                    entries=root.findall(ns+'sitemap');child=True
                elif root.tag==ns+'urlset':entries=root.findall(ns+'url');child=False
                else:self.add('error','SITEMAP_XML_ROOT',rel,root.tag);return
                if len(entries)>50000:self.add('error','SITEMAP_URL_LIMIT',rel,str(len(entries)))
                for e in entries:
                    loc=e.findtext(ns+'loc') or '';target,u=self.resolve(loc,self.base+'/')
                    if not target or not u or not loc.startswith(self.base+'/') or u.query or u.fragment or (not child and not target.lower().endswith('.html')):
                        self.add('error','SITEMAP_CHILD_INVALID' if child else 'SITEMAP_TARGET_INVALID',rel,loc);continue
                    if child:walk(target);continue
                    if target in self.sitemap:self.add('error','SITEMAP_DUPLICATE',rel,loc)
                    self.sitemap.add(target)
                    if unquote(u.path)!=route(target):self.add('warning','SITEMAP_NONCANONICAL_PATH',rel,loc)
            except (OSError,ET.ParseError,ValueError) as e:self.add('error','SITEMAP_READ',rel,str(e))
            finally:active.remove(rel)
        walk('sitemap.xml')
    def check_page(self,rel):
        path=route(rel);current=self.base+path
        try:nodes=parse((self.site/rel).read_text(encoding='utf-8'),self.engine)
        except (OSError,UnicodeError,ValueError,ET.ParseError) as e:self.add('error','HTML_READ',path,str(e));return
        titles=[];descs=[];canon=[];robots=set();refresh=[];links=[];imgs=[];controls=[];ids={};bases=[];lang=''
        for n in nodes:
            tag=n.tag
            if not isinstance(tag,str):continue
            if tag=='html':lang=n.get('lang') or ''
            if n.get('id'):ids[n.get('id')]=n
            if tag=='title' and in_head(n):titles.append(norm(text_of(n,True)))
            if tag=='meta' and in_head(n):
                name=(n.get('name') or '').lower();v=n.get('content') or ''
                if name=='description':descs.append(norm(v))
                if name in ('robots','googlebot','bingbot','yeti'):robots|=tokens(v)
                if (n.get('http-equiv') or '').lower()=='refresh':
                    m=re.match(r'^\s*\d+(?:\.\d+)?\s*;\s*url\s*=\s*(.*?)\s*$',v,re.I);refresh.append(m[1].strip('\"\'') if m else '')
            if tag=='link' and 'canonical' in tokens(n.get('rel')):
                if in_head(n):canon.append(n.get('href') or '')
                else:self.add('error','CANONICAL_OUTSIDE_HEAD',path,n.get('href') or '',n.sourceline)
            if tag=='base' and n.get('href'):bases.append(n.get('href'))
            if tag=='a' and 'href' in n.attrib:links.append(n)
            if tag=='img':imgs.append(n)
            if tag=='button' or (n.get('role') or '').lower()=='button' or (tag=='input' and (n.get('type') or '').lower() in ('button','submit','reset','image')):controls.append(n)
        redirect=bool(refresh);noindex=bool({'noindex','none'} & robots);offline=rel in ('offline.html','404.html');self.pages[rel]=(noindex,redirect,canon[0] if len(canon)==1 else None)
        if self.preview and not offline and not noindex:self.add('error','PREVIEW_INDEXABLE',path)
        if rel in self.sitemap and (redirect or offline or (noindex and not self.preview)):self.add('error','SITEMAP_NONINDEXABLE',path)
        if not offline and not redirect and not noindex and rel not in self.sitemap:self.add('error','INDEXABLE_MISSING_SITEMAP',path)
        if self.preview and not offline and not redirect and rel not in self.sitemap and (re.fullmatch(r'place/[^/]+/index\.html',rel) or path=='/'):
            self.add('error','PREVIEW_EXPECTED_SITEMAP_MISSING',path,'Place/home expected in production sitemap even in preview')
        if redirect:
            target,u=self.resolve(refresh[0],current)
            if not target or target==rel:self.add('error','REDIRECT_INVALID',path,refresh[0])
            if not noindex:self.add('error','REDIRECT_INDEXABLE',path)
        else:target=rel
        if not offline:
            if len(canon)!=1:self.add('error','CANONICAL_COUNT',path,str(len(canon)))
            else:
                c=canon[0];ct,u=self.resolve(c,current)
                if not c.startswith(self.base+'/') or not u or u.query or u.fragment or not ct or ct!=target or unquote(u.path)!=route(ct):self.add('error','CANONICAL_INVALID',path,c)
        seo=not offline and not redirect and (not noindex or rel in self.sitemap)
        for key,values,maxlen in [('TITLE',titles,self.title_max),('DESCRIPTION',descs,self.desc_max)]:
            if not offline and (len(values)!=1 or not values[0]):self.add('error',key+'_MISSING_OR_MULTIPLE',path,str(len(values)))
            if seo and len(values)==1 and values[0]:
                v=values[0];self.groups[key][v.casefold()].append(path)
                if len(v)>maxlen:self.add('warning',key+'_LONG',path,f'{len(v)} > {maxlen}: {v}')
        if path in self.regions:
            r=self.regions[path]
            if r.get('actualCount')==0 and (not noindex or rel in self.sitemap):self.add('error','EMPTY_REGION_INDEXABLE',path)
            if r.get('indexable') is False and (not noindex or rel in self.sitemap):self.add('error','REGION_NOINDEX_MISMATCH',path)
            if r.get('indexable') is True and rel not in self.sitemap:self.add('error','REGION_MISSING_SITEMAP',path)
        self.links+=len(links);self.images+=len(imgs);self.buttons+=len(controls)
        seen=set()
        for n in links:
            raw=n.get('href') or '';line=n.sourceline
            if raw in seen:continue
            seen.add(raw)
            if not raw.strip():self.add('warning','EMPTY_HREF',path,'',line);continue
            if raw.startswith('#'):continue
            dest,u=self.resolve(raw,urljoin(current,bases[0]) if bases else current)
            if u is None or (u.scheme in ('http','https') and u.netloc.lower() in self.hosts):
                self.internal+=1
                if not dest:self.add('error','INTERNAL_LINK_404',path,raw,line)
        for n in imgs:
            if 'alt' not in n.attrib or n.get('alt') is None:self.add('error','IMG_ALT_MISSING',path,n.get('src') or n.get('data-src') or '',n.sourceline)
        for n in controls:
            if not control_name(n,ids):self.add('error','BUTTON_NAME_MISSING',path,repr({k:v for k,v in n.attrib.items() if k in ('id','class','role','type','aria-label','aria-labelledby')}),n.sourceline)
        if not lang:self.add('warning','HTML_LANG_MISSING',path)
    def run(self):
        self.load_report();self.read_sitemap()
        for i,rel in enumerate(self.htmls):
            self.check_page(rel)
            if (i+1)%5000==0:print(f'QA scanned {i+1}/{len(self.htmls)}',file=sys.stderr,flush=True)
        for r in self.regions:
            f,_=self.resolve(r,self.base+'/')
            if not f:self.add('error','REGION_FILE_MISSING',r)
        for key,groups in self.groups.items():
            for val,paths in groups.items():
                if len(paths)>1:
                    for p in paths:self.add('warning',key+'_DUPLICATE',p,f'{len(paths)} pages; {val}')
        for rel,(noindex,redirect,canonical) in self.pages.items():
            if redirect and canonical:
                dest,_=self.resolve(canonical,self.base+route(rel))
                if dest in self.pages and self.pages[dest][1]:self.add('error','REDIRECT_CHAIN',route(rel),canonical)
        self.issues.sort(key=lambda x:(x['level'],x['code'],x['page'],x['detail'],x['line'] or 0))
        return dict(site=str(self.site),base=self.base,engine=self.engine,preview=self.preview,build_report_available=self.report_found,html_pages=len(self.htmls),sitemap_pages=len(self.sitemap),redirect_pages=sum(x[1] for x in self.pages.values()),region_pages=len(self.regions),zero_region_pages=sum(r.get('actualCount')==0 for r in self.regions.values()),anchor_occurrences=self.links,unique_internal_links_per_page=self.internal,images=self.images,buttons=self.buttons,counts=dict(collections.Counter(x['code'] for x in self.issues)),severity=dict(collections.Counter(x['level'] for x in self.issues)),issues=self.issues)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=pathlib.Path,default=pathlib.Path('site'));p.add_argument('--base');p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('internal/qa30'));p.add_argument('--title-max',type=int,default=60);p.add_argument('--description-max',type=int,default=160);p.add_argument('--engine',choices=['auto','stdlib','lxml'],default='auto');p.add_argument('--strict',action='store_true',help='warnings also cause exit 1');a=p.parse_args();site=a.site.resolve();out=a.output.resolve()
    if not site.is_dir() or not (site/'index.html').is_file():p.error('built site/index.html required')
    if out==site or site in out.parents:p.error('report directory must be outside public site/')
    base=a.base
    if not base:
        try:base=json.loads((site/'data/build-report.json').read_text())['siteUrl']
        except (OSError,ValueError,KeyError):base='https://eodigagae.com'
    if not re.fullmatch(r'https?://[^/\s?#]+/?',base):p.error('base must be an HTTP(S) origin')
    engine=('lxml' if lx is not None else 'stdlib') if a.engine=='auto' else a.engine
    if engine=='lxml' and lx is None:p.error('lxml unavailable; use --engine stdlib')
    t=time.monotonic();report=Audit(site,base,engine,a.title_max,a.description_max).run();report['elapsed_seconds']=round(time.monotonic()-t,2);out.mkdir(parents=True,exist_ok=True)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'issues.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['level','code','page','detail','line']);w.writeheader();w.writerows({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in x.items()} for x in report['issues'])
    summary=json.dumps({k:v for k,v in report.items() if k!='issues'},ensure_ascii=False,indent=2);(out/'summary.json').write_text(summary+'\n',encoding='utf-8');print(summary)
    return int(bool(report['severity'].get('error') or a.strict and report['severity'].get('warning')))
if __name__=='__main__':sys.exit(main())
