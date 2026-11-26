"""Disambiguate duplicate metadata using existing factual location fields only."""
from collections import defaultdict
import re

def clean(x):
    s=' '.join(str(x or '').split())
    return '' if s in ('미확인','지역 미확인','주소 미확인','확인 필요','정보 없음','-','None') else s

def area(p):return ' '.join(dict.fromkeys(x for k in ('sido','sigungu','dong') if (x:=clean(p.get(k)))))
def address(p):return clean(p.get('roadAddress')) or clean(p.get('address'))
def key(s):return ' '.join(s.split()).casefold()
def groups(rows,i):
    out=defaultdict(list)
    for pid,meta in rows.items():out[key(meta[i])].append(pid)
    return [g for g in out.values() if len(g)>1]

def place_meta(places):
    """Keep unique titles/descriptions unchanged. Leave unresolved data for human QA."""
    by={p['id']:p for p in places};rows={}
    for pid,p in by.items():
        svc=' · '.join(p['services']);a=' '.join(filter(None,[p['sido'],p['sigungu'],p['dong']]))
        rows[pid]=[f'{p["name"]} · {svc} | 어디가개',f'{p["name"]}의 {a or "지역 미확인"} {svc} 정보. 주소, 영업시간, 확인된 반려동물 이용 조건을 살펴보세요.']
    def title(pid,qualifier):
        p=by[pid];return f'{p["name"]} · {" · ".join(p["services"])} ({qualifier}) | 어디가개'
    def change(pid,i,v,maxlen):
        # Avoid unnecessarily long snippets. Never truncate names or addresses.
        if len(v)<=maxlen:rows[pid][i]=v
    for group in groups(rows,0):
        for pid in group:
            if a:=area(by[pid]):change(pid,0,title(pid,a),60)
    for group in groups(rows,0):
        for pid in group:
            if a:=address(by[pid]):change(pid,0,title(pid,a),60)
    for group in groups(rows,1):
        for pid in group:
            if a:=address(by[pid]):
                p=by[pid];change(pid,1,f'{p["name"]} · {" · ".join(p["services"])}. 주소: {a}. 영업시간과 확인된 반려동물 이용 조건을 살펴보세요.',160)
    return {pid:tuple(meta) for pid,meta in rows.items()}
