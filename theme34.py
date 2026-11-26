"""v3.4 theme collections: data-backed pages such as '서울 대형견 동반 가능 장소'."""
import collections

GENERAL = {'카페', '식당', '숙소', '여행지', '놀이터'}
THEMES = [
    ('large-dog', '대형견 동반 가능 장소', '🐕', '대형견도 함께 갈 수 있다고 등록된',
     lambda p, sv: p.get('petSizeLarge') is True and bool(sv & GENERAL)),
    ('indoor', '실내 동반 가능 장소', '🏠', '실내까지 반려동물과 함께 들어갈 수 있다고 등록된',
     lambda p, sv: p.get('indoor') is True and bool(sv & GENERAL)),
    ('parking', '주차 가능한 애견동반 장소', '🚗', '주차가 가능하다고 등록된',
     lambda p, sv: p.get('parking') is True and bool(sv & GENERAL)),
    ('24h-hospital', '24시 동물병원', '🚨', '24시간 운영으로 등록된',
     lambda p, sv: p.get('hours24Data') is True and '동물병원' in sv),
    ('pet-stay', '애견동반 숙소', '🛏️', '반려동물과 함께 묵을 수 있는',
     lambda p, sv: '숙소' in sv),
    ('walk', '공원·산책 명소', '🌳', '실외 동반이 가능한 공원·여행지로 등록된',
     lambda p, sv: '여행지' in sv and p.get('outdoor') is True),
]
MIN_ROWS = 3
THUMB = {'large-dog': 'large-dog', 'indoor': 'indoor', 'parking': 'parking', '24h-hospital': 'night-vet', 'pet-stay': 'stay', 'walk': 'park'}
LIST_CAP = 300


def sido_slugs(pageinfo):
    slugs, short = {}, {}
    for s, path, rows, *_ in pageinfo:
        if s.get('level') == 'sido' and s.get('sido') and s['sido'] not in slugs:
            parts = [x for x in path.strip('/').split('/') if x]
            if len(parts) >= 2:
                slugs[s['sido']] = parts[-1]
                short[s['sido']] = (s.get('mainKeyword') or s['sido']).split()[0]
    return slugs, short


def theme_rows(places, test, is_funeral):
    out = []
    for p in places:
        if p['id'].startswith('f') or is_funeral(p) or p.get('operating') is False:
            continue
        if test(p, set(p.get('services') or [])):
            out.append(p)
    return out


def build(places, pageinfo, h):
    """h: dict of build helpers (page, row, carousel, keys, card, crumb, listld, E, rank, is_funeral)."""
    E = h['E']
    slugs, short = sido_slugs(pageinfo)
    paths, home = [], []
    for slug, title, icon, phrase, test in THEMES:
        rows = sorted(theme_rows(places, test, h['is_funeral']), key=h['rank'])
        if len(rows) < MIN_ROWS:
            continue
        by = collections.defaultdict(list)
        for p in rows:
            if p.get('sido') in slugs:
                by[p['sido']].append(p)
        sido_links = []
        for si, items in sorted(by.items(), key=lambda x: (-len(x[1]), x[0])):
            if len(items) < MIN_ROWS:
                continue
            spath = f'/theme/{slug}/{slugs[si]}/'
            name = f'{short[si]} {title}'
            crumbs, crumbld = h['crumb']([('홈', '/'), (title, f'/theme/{slug}/'), (short[si], spath)])
            body = crumbs + f'<h1>{E(name)} {len(items):,}곳</h1>'
            body += (f'<section class="panel region-summary"><h2>요약</h2><p>{E(short[si])}에서 {E(phrase)} 장소 {len(items):,}곳을 모았어요. '
                     '공공데이터와 등록 정보 기준이라 실제 이용 조건은 방문 전 업체에 확인해 주세요.</p></section>')
            body += h['carousel'](items, h['keys'], h['card'])
            shown = items[:LIST_CAP]
            body += '<section class="panel"><h2>장소 목록</h2><ul class="seo-list">' + ''.join(h['row'](p) for p in shown) + '</ul>'
            if len(items) > LIST_CAP:
                body += f'<p class="muted">상위 {LIST_CAP}곳만 표시했어요. 전체는 <a href="/#explore">장소 찾기</a>에서 지역을 좁혀 보세요.</p>'
            body += '</section>'
            others = [f'<a href="/theme/{s2}/{slugs[si]}/">{E(t2)}</a>' for s2, t2, *_ in THEMES if s2 != slug]
            body += '<section class="panel related-regions"><h2>같은 지역 다른 테마</h2><div class="seo-links">' + ''.join(others) + '</div></section>'
            h['page'](spath, f'{name} {len(items):,}곳 | 어디가개',
                      f'{short[si]}에서 {phrase} 장소 {len(items):,}곳. 동반 조건과 위치, 연락처를 어디가개에서 확인하세요.',
                      body, [h['listld'](shown), crumbld])
            paths.append(spath)
            sido_links.append((spath, f'{short[si]}', len(items)))
        path = f'/theme/{slug}/'
        crumbs, crumbld = h['crumb']([('홈', '/'), (title, path)])
        body = crumbs + f'<h1>전국 {E(title)} {len(rows):,}곳</h1>'
        body += (f'<section class="panel region-summary"><h2>요약</h2><p>전국에서 {E(phrase)} 장소 {len(rows):,}곳이에요. '
                 '지역을 골라 더 자세히 볼 수 있어요. 실제 이용 조건은 방문 전 업체에 확인해 주세요.</p></section>')
        if sido_links:
            body += '<section class="panel"><h2>지역별 보기</h2><div class="seo-links">' + ''.join(
                f'<a href="{E(p)}">{E(t)} ({n:,})</a>' for p, t, n in sido_links) + '</div></section>'
        body += h['carousel'](rows, h['keys'], h['card'], regional=False)
        top = rows[:60]
        body += '<section class="panel"><h2>추천 장소</h2><ul class="seo-list">' + ''.join(h['row'](p) for p in top) + '</ul></section>'
        others = [f'<a href="/theme/{s2}/">{E(t2)}</a>' for s2, t2, *_ in THEMES if s2 != slug]
        body += '<section class="panel related-regions"><h2>다른 테마</h2><div class="seo-links">' + ''.join(others) + '</div></section>'
        h['page'](path, f'전국 {title} {len(rows):,}곳 | 어디가개',
                  f'전국에서 {phrase} 장소 {len(rows):,}곳을 지역별로 모았어요. 동반 조건과 위치를 어디가개에서 확인하세요.',
                  body, [h['listld'](top), crumbld])
        paths.append(path)
        if slug != '24h-hospital':
            used = {x[4] for x in home}
            ph = next((q['tourPhoto']['src'] for q in rows if q.get('tourPhoto') and q['tourPhoto'].get('src') and q['tourPhoto']['src'] not in used), '')
            home.append((path, title, icon, len(rows), ph))
    return paths, home


def home_section(items, E):
    if not items:
        return ''
    def one(p, t, n, ph):
        img = (f'<img class="theme-thumb" src="{E(ph)}" alt="" width="600" height="400" loading="lazy" decoding="async" referrerpolicy="no-referrer">'
               if ph else '<span class="theme-thumb"></span>')
        cr = '<i class="theme-credit">사진 한국관광공사</i>' if ph else ''
        return f'<a class="theme-card" href="{E(p)}">{img}{cr}<b>{E(t)}</b><small>전국 {n:,}곳</small></a>'
    cards = ''.join(one(p, t, n, ph) for p, t, icon, n, ph in items)
    return ('<section class="section theme-section"><div class="head"><h2>테마별 모아보기</h2>'
            '<span class="muted">조건으로 바로 찾기</span></div><div class="theme-grid">' + cards + '</div></section>')


def home_guide(copy, E):
    """Static info block for the home page (usage, condition guide, checklist, FAQ)."""
    if not copy:
        return '', None
    u, g, c, f = copy.get('usage', {}), copy.get('condition_guide', {}), copy.get('checklist', {}), copy.get('faq', {})
    h = '<section class="section home-guide"><div class="guide-grid">'
    h += '<div class="guide-box"><h2>' + E(u.get('title', '사용법')) + '</h2><ol class="guide-steps">' + ''.join(
        f'<li><b>{E(s["title"])}</b><span>{E(s["text"])}</span></li>' for s in u.get('steps', [])) + '</ol></div>'
    h += '<div class="guide-box"><h2>' + E(g.get('title', '동반 조건 보는 법')) + '</h2><dl class="guide-terms">' + ''.join(
        f'<div><dt>{E(i["label"])}</dt><dd>{E(i["text"])}</dd></div>' for i in g.get('items', [])) + '</dl></div>'
    h += '<div class="guide-box"><h2>' + E(c.get('title', '체크리스트')) + '</h2><ul class="guide-check">' + ''.join(
        f'<li>{E(x)}</li>' for x in c.get('items', [])) + '</ul></div>'
    h += '</div><div class="guide-faq"><h2>' + E(f.get('title', '자주 묻는 질문')) + '</h2>' + ''.join(
        f'<details><summary>{E(i["q"])}</summary><p>{E(i["a"])}</p></details>' for i in f.get('items', [])) + '</div></section>'
    ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': i['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': i['a']}} for i in f.get('items', [])]}
    return h, ld
