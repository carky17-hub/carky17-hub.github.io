import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from qa30_meta import place_meta
from qa30 import Audit,lx
BASE='https://eodigagae.com'
NS='http://www.sitemaps.org/schemas/sitemap/0.9'
def page(path,title='제목',desc='설명',body='',robots='',canonical=None,extra=''):
    return f'<!doctype html><html lang="ko"><head><title>{title}</title><meta name="description" content="{desc}"><link rel="canonical" href="{canonical if canonical is not None else BASE+path}"><meta name="robots" content="{robots}">{extra}</head><body>{body}</body></html>'
def make(root,rel,text):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
def sitemap(root,paths):
    make(root,'sitemap.xml',f'<urlset xmlns="{NS}" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'+''.join(f'<url><loc>{BASE+p}</loc><image:image><image:loc>https://other.example/a.jpg</image:loc></image:image></url>' for p in paths)+'</urlset>')
def report(root,regions=(),preview=False):make(root,'data/build-report.json',json.dumps({'siteUrl':BASE,'preview':preview,'regionCounts':regions}))
def engines():return ['stdlib']+(['lxml'] if lx is not None else [])
class Tests(unittest.TestCase):
    def test_valid(self):
        for engine in engines():
            with self.subTest(engine=engine),tempfile.TemporaryDirectory() as t:
                r=pathlib.Path(t);report(r,[{'path':'/empty/','actualCount':0,'indexable':False}]);sitemap(r,['/','/한글/'])
                make(r,'index.html',page('/',body='<a href="/%ED%95%9C%EA%B8%80/?a=1#x">내부</a><a href="https://www.eodigagae.com/한글/">www</a><a href="#dynamic">동적</a><img alt="" src="/brand.svg"><button aria-label="저장"><svg><title>장식</title></svg></button><button aria-labelledby="lbl"></button><span hidden id="lbl">닫기</span>'))
                make(r,'한글/index.html',page('/한글/','다른 제목','다른 설명',body='<a href="../">홈</a>'))
                make(r,'empty/index.html',page('/empty/',robots='noindex,follow'))
                make(r,'old/index.html',page('/old/',robots='noindex',canonical=BASE+'/한글/',extra='<meta http-equiv="refresh" content="0;url=/한글/">'))
                self.assertEqual(Audit(r,BASE,engine).run()['issues'],[])
    def test_faults(self):
        for engine in engines():
            with self.subTest(engine=engine),tempfile.TemporaryDirectory() as t:
                r=pathlib.Path(t);report(r,[{'path':'/zero/','actualCount':0,'indexable':False}]);sitemap(r,['/','/zero/','/missing/','/zero/'])
                make(r,'index.html',page('/',title='가'*61,desc='가'*161,body='<a href="/missing/">x</a><img src="/x.png"><button><span aria-hidden="true">×</span></button><button aria-labelledby="no-such-id"></button>'))
                make(r,'zero/index.html',page('/zero/',title='가'*61,desc='가'*161,canonical=BASE+'/missing/'))
                make(r,'orphan/index.html',page('/orphan/'))
                a=Audit(r,BASE,engine).run();codes=a['counts']
                for c in ('INTERNAL_LINK_404','IMG_ALT_MISSING','BUTTON_NAME_MISSING','EMPTY_REGION_INDEXABLE','SITEMAP_TARGET_INVALID','SITEMAP_DUPLICATE','CANONICAL_INVALID','INDEXABLE_MISSING_SITEMAP','TITLE_DUPLICATE','DESCRIPTION_DUPLICATE','TITLE_LONG','DESCRIPTION_LONG'):self.assertIn(c,codes,c)
                self.assertEqual(codes['BUTTON_NAME_MISSING'],2)
    def test_preview(self):
        with tempfile.TemporaryDirectory() as t:
            r=pathlib.Path(t);report(r,preview=True);sitemap(r,['/']);make(r,'index.html',page('/',robots='noindex'));make(r,'place/p1/index.html',page('/place/p1/',robots='noindex'))
            a=Audit(r,BASE,'stdlib').run();self.assertIn('PREVIEW_EXPECTED_SITEMAP_MISSING',a['counts']);self.assertNotIn('SITEMAP_NONINDEXABLE',a['counts'])
    def test_sitemap_index(self):
        with tempfile.TemporaryDirectory() as t:
            r=pathlib.Path(t);report(r);sitemap(r,['/']);(r/'sitemap.xml').rename(r/'sitemap-1.xml');make(r,'sitemap.xml',f'<sitemapindex xmlns="{NS}"><sitemap><loc>{BASE}/sitemap-1.xml</loc></sitemap></sitemapindex>');make(r,'index.html',page('/'));self.assertFalse(Audit(r,BASE,'stdlib').run()['issues'])
    def test_metadata(self):
        def p(i,si,addr=None,name='동물병원'):return dict(id=i,name=name,services=['동물병원'],sido=si,sigungu=None,dong=None,address=addr)
        rows=[p('p1','서울','서울 1'),p('p2','경기','경기 1'),p('p3',None),p('p4',None),p('p5','서울','서울 2'),p('p6','서울',name='고유')];m=place_meta(rows)
        self.assertEqual(m['p3'],m['p4']);self.assertIn('서울 1',m['p1'][0]);self.assertIn('서울 2',m['p5'][1]);self.assertIn('경기',m['p2'][0]);self.assertEqual(m['p6'][0],'고유 · 동물병원 | 어디가개')
if __name__=='__main__':unittest.main()
