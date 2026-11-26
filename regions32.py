"""Fact-only introductions and nearby same-category links, using existing page URLs."""
import collections, math, statistics
from region_rules import dong_key,indexable

def intro(s,rows):
    n=len(rows); indoor=sum(p.get('indoor') is True for p in rows); parking=sum(p.get('parking') is True for p in rows)
    # explicit large-dog field only; original petSize wording is counted separately, with exact whitelist.
    large=sum(p.get('petSizeLarge') is True or (p.get('petSizeLarge') is None and p.get('petSize') in ('모두 가능','대형','소형/대형','중형/대형','소형/중형/대형') and not p.get('weightLimit')) for p in rows)
    return (f"{s['mainKeyword']} 목록에는 현재 수록 데이터 기준 중복을 제외한 {n:,}곳이 있습니다. "
            f"실내 동반 가능으로 등록된 곳은 {indoor:,}곳, 주차 가능은 {parking:,}곳, 대형견 가능 또는 원자료에 모든 크기 가능으로 표시된 곳은 {large:,}곳입니다. "
            "미확인 정보는 가능 수에 포함하지 않았으며 방문 전 실제 이용 조건을 확인해 주세요.")

def coords(p):
    a,b=p.get('lat'),p.get('lng')
    return (a,b) if p.get('geoPrecision')=='exact' and all(type(v) in (int,float) and math.isfinite(v) for v in (a,b)) and 32<=a<=39 and 124<=b<=132 else None

def area(s):return (s['sido'],s['sigungu'],s['filter']['dongKey'])
def km(a,b):
    x,y=map(math.radians,a);u,v=map(math.radians,b);h=math.sin((x-u)/2)**2+math.cos(x)*math.cos(u)*math.sin((y-v)/2)**2
    return 12742*math.asin(min(1,math.sqrt(h)))

class Nearby:
    def __init__(self,places,pageinfo):
        points=collections.defaultdict(list)
        for p in places:
            xy=coords(p);si=p.get('sido');gu=p.get('sigungu');d=dong_key(si,gu,p.get('dongKey'))
            if xy and si:
                for key in {(si,None,None),(si,gu,None),(si,gu,d)}:points[key].append(xy)
        self.centers={k:(statistics.median(a for a,b in v),statistics.median(b for a,b in v)) for k,v in points.items()}
        self.groups=collections.defaultdict(list);self.valid=set()
        for s,path,rows,*_ in pageinfo:
            if not indexable(s,len(rows)):continue
            self.valid.add(path);self.groups[s['category'],s['level']].append((s,path,len(rows)))
    def links(self,s,path):
        cat=s['category']; level=s['level']; a=area(s); center=self.centers.get(a)
        if not center:return []
        matches=[]
        limit={'sido':180,'sigungu':55,'dong':15}.get(level,0)
        for t,target,n in self.groups[cat,level]:
            b=area(t)
            if target==path or a==b or b not in self.centers:continue
            # Same parent preferred; neighboring districts across city borders also valid by distance.
            if level=='dong' and a[:2]!=b[:2]:continue
            d=km(center,self.centers[b]);
            if d<=limit:matches.append((d,target,t['mainKeyword'],n))
        return [(p,t,n) for _,p,t,n in sorted(matches)[:6]]
