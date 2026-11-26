"""First-party scores and original card/curation rendering."""
import html,json,collections,os,datetime
def rotation_seed():return os.environ.get('EG_ROTATION_SEED') or (datetime.datetime.utcnow()+datetime.timedelta(hours=9)).strftime('%Y-%m-%d')
def rot(i,seed=None):
 h=0x811c9dc5
 for ch in str(i)+'|'+(seed if seed is not None else rotation_seed()):h=((h^ord(ch))*0x01000193)&0xffffffff
 return h
from art23 import art as art23
E=lambda x:html.escape(str(x if x is not None else ''),quote=True)
ICONS={'식당':'M12 4v9m-4-9v5a4 4 0 0 0 8 0V4m-4 9v15M23 4c-5 4-5 11 0 13h2V4m0 13v11','카페':'M5 10h21v9a8 8 0 0 1-8 8h-5a8 8 0 0 1-8-8zM26 12h2a4 4 0 0 1 0 8h-2M11 3v3m7-3v3','숙소':'M3 15 16 4l13 11M6 13v15h20V13M13 28V18h6v10','여행지':'M3 26 13 10l7 10 4-6 6 12zM24 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6','놀이터':'M16 5a11 11 0 1 0 0 22 11 11 0 0 0 0-22M6 10c8 2 12 12 10 17M26 10c-8 2-12 12-10 17','동물병원':'M12 4h8v8h8v8h-8v8h-8v-8H4v-8h8z','미용':'M8 18a5 5 0 1 0 0 10 5 5 0 0 0 0-10M24 18a5 5 0 1 0 0 10 5 5 0 0 0 0-10M11 19 26 4M21 19 6 4','호텔·유치원':'M3 15 16 4l13 11M6 13v15h20V13M12 20h8v8h-8z','장례·추모':'M16 4c5 6 8 11 8 15a8 8 0 0 1-16 0c0-4 3-9 8-15zM16 15v10'}
def icon(kind):return '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="'+ICONS.get(kind,ICONS['카페'])+'" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
def annotate(places,reviews):
 for p in places:
  ratings=[r['rating'] for r in reviews.get(p['id'],[]) if r.get('relationship')=='customer' and r.get('benefit')=='none' and r.get('visitVerified') is True and type(r.get('rating')) is int and 1<=r['rating']<=5] if not p['id'].startswith('f') else []
  p['ownReviewCount']=len(ratings);p['ownRating']=round(sum(ratings)/len(ratings),1) if ratings else None

def rating(p):return f'<div class="eg-own-rating">어디가개 <b>★ {p["ownRating"]:.1f}</b> · 후기 {p["ownReviewCount"]}건</div>' if p.get('ownReviewCount') else ''
def pet_chips(p):
 import re as _re
 pet=(p.get('tourism') or {}).get('pet') or {}
 out=[];cond=False
 if p.get('indoor') is False and p.get('outdoor') is True:out.append('실외만');cond=True
 elif p.get('indoor') is True and p.get('outdoor') is False:out.append('실내만');cond=True
 z=str(pet.get('acmpyTypeCd') or '')
 if '일부' in z:out.append('일부 구역만');cond=True
 elif '전구역' in z:out.append('전 구역 동반')
 if p.get('petSizeLarge') is False:out.append('대형견 불가');cond=True
 m={'목줄 착용':'목줄','입마개 착용':'입마개','이동장(켄넬)사용':'이동장','반려동물 유모차 탑승':'유모차','매너벨트 착용':'매너벨트'}
 need=[m.get(x.strip(),'') for x in str(pet.get('acmpyNeedMtr') or '').split(',')]
 need=[x for x in need if x]
 r=str(p.get('restrictions') or '').strip()
 if r and r!='제한사항 없음' and not need:
  t=_re.split(r'[,./\n(]',r)[0].strip()
  if t and t not in out:need=[t[:12]]
 if need:out.append('·'.join(need[:2]));cond=True
 if not out and r=='제한사항 없음':out.append('제한 없음')
 return out[:3],cond
def status(p):
 if p.get('category') not in ('식당','카페','애견카페','숙소','여행지','놀이터'):return ''
 if p.get('indoor') is False and p.get('outdoor') is False:return '<span class="eg-pet-state unknown">동반 불가 정보 있음</span>'
 if p.get('indoor') is True or p.get('outdoor') is True or p.get('tourism') or '식약처 인증' in (p.get('tags') or []) or p.get('restrictions'):
  chips,cond=pet_chips(p)
  return '<span class="eg-pet-state'+(' conditional' if cond else '')+'">'+(E(' · '.join(chips)) if chips else '반려동물 동반 가능')+'</span>'
 return '<span class="eg-pet-state unknown">동반 조건 확인 필요</span>'
def cover(p):
 kind=p['category'];kind='카페' if kind=='애견카페' else kind
 photo=p.get('ownerPhoto') or p.get('tourPhoto');art=art23(p,kind)
 if photo:
  art=art.replace('<div class="eg-art','<div hidden class="eg-art',1)
  lic=photo.get('license');credit='한국관광공사 · 공공누리 '+lic+'유형' if lic else photo.get('label','제공 사진')+' · '+photo.get('credit','')
  return f'<div class="eg-card-media"><div class="eg-photo-slot {"contain" if lic else ""}">{art}<img src="{E(photo["src"])}" alt="{E(photo.get("caption"))}" width="400" height="300" loading="lazy" decoding="async" fetchpriority="auto" data-card-photo></div><small class="eg-card-credit">{E(credit)}</small></div>'
 return '<div class="eg-card-media">'+art+'</div>'
def card(p,key='',recommended=False):
 b='관광공사 등록' if p.get('tourism') else '승인 사진' if p.get('ownerPhoto') else '';b=b or ('사진 추천' if recommended else '')
 attrs=' · '.join(t for k,t in [('indoor','실내 동반'),('petSizeLarge','대형견'),('parking','주차')] if p.get(k) is True)
 return f'<article class="card eg-place-card"><a href="/place/{E(p["id"])}/">{cover(p)}'+(f'<span class="eg-photo-badge">{E(b)}</span>' if b else '')+f'<div class="cardbody"><div class="name">{E(p["name"])}</div><div class="muted">{E(p.get("sigungu") or p.get("sido") or "지역 미확인")} · {E(p["category"])}</div>{status(p)}'+(f'<div class="eg-card-attrs">{E(attrs)}</div>' if attrs else '')+rating(p)+'</div></a><button type="button" class="save" data-save="'+E(p['id'])+'" data-key="'+E(key)+'" aria-label="장소 저장" aria-pressed="false">♡</button></article>'
def curated(places,keys):
 rows=[p for p in places if not p['id'].startswith('f') and p.get('operating') is not False and not (p.get('indoor') is False and p.get('outdoor') is False) and (p.get('tourPhoto') or p.get('ownerPhoto')) and not str((p.get('ownerPhoto') or {}).get('label','')).startswith('AD')]
 rows.sort(key=lambda p:(-bool(p.get('ownerPhoto')),-bool(p.get('tourPhoto')),-(p.get('infoCompleteness') or 0),p['id']))
 buckets=collections.defaultdict(list)
 for p in rows:
  cat='카페' if p['category']=='애견카페' else p['category']
  if cat not in ('카페','식당','숙소','여행지'):continue
  for k in [('전국','전체'),('전국',cat),(p['sido'],'전체'),(p['sido'],cat)]:
   if len(buckets[k])<24:buckets[k].append(p)
 if not buckets:return ''
 seed=rotation_seed();buckets={k:sorted(v,key=lambda p:(-bool(p.get('ownerPhoto')),rot(p['id'],seed)))[:8] for k,v in buckets.items()}
 data={si+'|'+cat:''.join(card(p,keys[p['id']],True) for p in ps) for (si,cat),ps in buckets.items()}
 return '<section class="section eg-curated"><div class="head"><h2>오늘의 추천 장소</h2><a href="/recommendation-policy/">추천 기준</a></div><div class="eg-curated-controls"><label>지역 <select id="curatedRegion"><option>전국</option>'+''.join('<option>'+E(x)+'</option>' for x in sorted({s for s,c in buckets if s!='전국'}))+'</select></label><div id="curatedTabs" role="group" aria-label="추천 업종">'+''.join(f'<button type="button" class="btn" data-curated="{x}" aria-pressed="{str(x=="전체").lower()}">{x}</button>' for x in ('전체','카페','식당','숙소','여행지'))+'</div></div><div id="curatedCards" class="eg-curated-cards">'+data.get('전국|전체','')+'</div><script type="application/json" id="curatedData">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script></section>'
