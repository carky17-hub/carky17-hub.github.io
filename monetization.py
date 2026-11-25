import json,html,re
from pathlib import Path
from settings import ENABLE_ADFIT
E=lambda x:html.escape(str(x),quote=True)
def recommend(path,rows,bookings):
 by={p['id']:p for p in rows}
 h='<section class="sponsored"><div class="sponsor-head"><b>추천 매장</b><span class="ad-label">AD</span></div><div class="sponsor-grid">'
 for r in sorted(bookings,key=lambda x:(x['slot'],x['start_date'])):
  i=r['place_id'];h+=f'<a hidden data-period data-slot="{E(r["slot"])}" data-start="{E(r["start_date"])}" data-end="{E(r["end_date"])}" class="sponsor-card" href="/place/{E(i)}/" rel="sponsored"><small>AD · 유료 광고</small><strong>{E(by[i]["name"])}</strong><span>{E(by[i].get("address") or "주소 확인 필요")}</span></a>'
 return h+'</div><div class="sponsor-empty" data-ad-empty><div><strong>이 자리에 내 매장 올리기</strong><p>우리 동네 반려인에게 매장을 알려 보세요.</p></div><a class="btn" href="/owner/pricing/">광고 상품 보기 →</a></div></section>'
def ad_slot(kind,unit,inside=True):
 if not ENABLE_ADFIT:return ''
 assert re.fullmatch(r'DAN-[A-Za-z0-9]+',unit), 'Check approved AdFit unit ID'
 tag='li' if inside else 'section'
 return f'<{tag} class="adfit-slot" aria-label="광고"><small>AD · 광고</small><ins class="kakao_ad_area" style="display:none" data-ad-unit="{E(unit)}" data-ad-width="320" data-ad-height="100"></ins></{tag}>' + ('' if inside else '<script src="https://t1.daumcdn.net/kas/static/ba.min.js" async></script>')
pricing='''<section class="pricing-hero"><p class="eyebrow">어디가개 사장님센터</p><h1>우리 매장을 찾는<br>반려인에게 먼저 닿으세요.</h1><p>무료 입점부터 지역 광고까지, 매장에 맞는 상품을 선택하세요.</p><a class="btn primary" href="/owner/">무료 입점 신청</a> <a class="btn" href="/owner/?type=pricing">광고 상담하기</a></section><div class="pricing-grid">
<article class="price-card"><small>기본 등록</small><h2>무료 입점</h2><div class="price">0원</div><p>매장 정보를 알리는 첫걸음</p><ul><li>매장 상세 페이지</li><li>해당 시 공공 목록 배지</li><li>정보 수정 요청</li></ul><a class="btn" href="/owner/">무료 입점 신청</a></article>
<article class="price-card featured"><small>매장 소개 강화</small><h2>프리미엄 매장</h2><div class="price">29,000원<small> / 월 · VAT 별도</small></div><p>우리 매장만의 매력을 보여주세요.</p><ul><li>사진 최대 10장·소개글 (운영자 승인)</li><li>프리미엄 표시 (공식 인증과 별개)</li><li>지역 추천 광고 1자리 (재고 확인)</li></ul><a class="btn primary" href="/owner/?type=pricing&amp;plan=premium">프리미엄 문의</a></article>
<article class="price-card"><small>지역 단위 노출</small><h2>지역 상단 광고</h2><div class="price">49,000~99,000원<small> / 월 · VAT 별도</small></div><p>동·시군구 페이지 추천 영역</p><ul><li>지역당 최대 3자리</li><li>광고 표시와 일반 목록 분리</li><li>지역·기간별 상담</li></ul><a class="btn" href="/owner/?type=pricing&amp;plan=regional">지역 광고 문의</a></article></div><section class="panel"><h2>마케팅 패키지</h2><p>블로그·카페 콘텐츠 및 홍보는 별도 상담으로 진행합니다. 광고·협찬 여부를 표시하며 검색 순위나 매출은 보장하지 않습니다.</p><a class="btn" href="/owner/?type=pricing&amp;plan=marketing">마케팅 상담</a></section><section class="panel"><h2>이용 안내</h2><p>모든 유료 상품은 VAT 별도이며 선결제입니다. 실제 판매는 계약서 최종 검토 및 재고 확인 후 진행합니다. 현재는 상담 신청만 지원하며 결제·자동 정기결제·사진 업로드는 준비 중입니다. 유료 광고는 공식 등록 배지나 일반 검색 순위와 별개입니다.</p></section>'''

pricing += """<section class="panel"><h2>기간별 선결제 할인 (VAT 별도)</h2><div class="policy-table"><table><tr><th>상품</th><th>1개월 (정가)</th><th>3개월 (5% 할인)</th><th>6개월 (10% 할인)</th></tr><tr><th>프리미엄</th><td>29,000원</td><td>82,650원</td><td>156,600원</td></tr><tr><th>지역 상단 광고</th><td>49,000~99,000원</td><td>139,650~282,150원</td><td>264,600~534,600원</td></tr></table></div><p>기간 전체 선결제 금액이며 부가세 10% 별도입니다. 시작일 전일까지 입금 확인 후 노출합니다.</p></section><section class="panel"><h2>해지 및 환불 요약</h2><ul><li>광고 시작 전 취소: 전액 환불.</li><li>광고주 사정으로 시작 후 해지: 잔여 기간 일할 금액에서 위약금 10% 공제 (1개월 상품은 시작 후 환불 불가라는 정책안).</li><li>회사 귀책으로 24시간 이상 노출 장애: 해당 일수만큼 연장 또는 일할 환불.</li></ul><p>허위 광고 중단 시 노출된 기간은 환불하지 않고, 남은 기간 일할 금액에서 위약금 10%를 공제합니다. 관련 법령 우선 적용, 계약서 최종 검토 및 개별 계약 후 판매합니다.</p><a class="btn" href="/owner/terms-ads/">이용계약서 보기</a></section>"""
