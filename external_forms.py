import html,re
from urllib.parse import quote
import settings as S
E=lambda v:html.escape(v,quote=True)
def contact_markup():
 parts=[]
 if S.KAKAO_CHANNEL_URL:parts.append(f'<a class="btn" href="{E(S.KAKAO_CHANNEL_URL)}" rel="noopener noreferrer" target="_blank">카카오톡 채널 문의</a>')
 if S.CONTACT_EMAIL:parts.append(f'<a class="btn" href="mailto:{E(quote(S.CONTACT_EMAIL,safe="@.+-_"))}">이메일 문의</a>')
 return ' '.join(parts) or '<p>공식 문의처 준비 중입니다.</p>'
OWNER_FORM_URL='https://docs.google.com/forms/d/e/1FAIpQLScH6bDJnRBfdClbPCQOhkPJ_pKdgMMRh3g5oJclEpI5IEK3lw/viewform'
OWNER_DM_URL='https://ig.me/m/eodigagae.official'
def fallback():
 perks=[('무료 등록','등록비·수수료 없이 매장을 소개해 드려요.'),('사진 있는 매장 먼저','기본 목록에서 사진이 있는 매장이 위쪽에 보여요.'),('정확한 동반 조건','실내·크기·요금 조건을 사장님 말씀대로 표시해요.'),('어디가개 SNS 소개','원하시면 인스타·스레드에서도 매장을 소개해요.')]
 steps=[('신청서 작성','매장 이름과 사진만 있으면 1분이면 끝나요.'),('확인','1~3일 안에 정보를 확인해요.'),('반영','어디가개 목록과 매장 페이지에 올라가요.')]
 h='<section class="owner-hero"><p class="owner-eyebrow">사장님 무료 등록</p><h1>사장님, 매장 사진만 보내주세요</h1><p class="owner-sub">등록부터 소개까지 어디가개가 무료로 해드려요.</p>'
 h+=f'<div class="owner-cta"><a class="btn primary owner-main" href="{E(OWNER_FORM_URL)}" target="_blank" rel="noopener">무료 등록 신청하기</a><a class="btn" href="{E(OWNER_DM_URL)}" target="_blank" rel="noopener">인스타 DM으로 보내기</a></div></section>'
 h+='<section class="owner-perks">'+''.join(f'<div><b>{E(t)}</b><span>{E(d)}</span></div>' for t,d in perks)+'</section>'
 h+='<section class="panel owner-steps"><h2>이렇게 진행돼요</h2><ol class="g-steps">'+''.join(f'<li><i>{i}</i><b>{E(t)}</b><span>{E(d)}</span></li>' for i,(t,d) in enumerate(steps,1))+'</ol></section>'
 h+='<section class="panel"><h2>정보 수정·폐업 신고도 여기서</h2><p>이미 등록된 매장의 정보가 다르거나 폐업했다면 같은 신청서에 적어 주세요. 확인 후 고치거나 목록에서 내려요.</p><p class="muted">신청서는 구글 설문으로 접수되며, 사진 첨부에는 구글 로그인이 필요해요. 특정 노출 순위는 보장하지 않아요.</p></section>'
 return h
def notice():
 if not S.FORMS_LIVE:return '온라인 신청 기능은 현재 비활성 상태입니다.'
 mode='국외 이전' if S.FORM_INTERNATIONAL_TRANSFER else '개인정보 처리 위탁'
 return f'{mode}: {S.FORM_PROVIDER} ({S.FORM_PROVIDER_COUNTRY}), 연락처 {S.FORM_PROVIDER_CONTACT}. 제출 시 신청 항목과 접속 IP 등이 네트워크로 전송되어 신청 접수·저장·관리에 사용됩니다. 수탁자 보유·삭제 기준: {S.FORM_PROVIDER_RETENTION}. 동의를 거부할 수 있으며 거부 시 온라인 신청이 제한됩니다.'
def consent_text():return '개인정보 수집·이용'
def convert(markup):
 markup=markup.replace('data-netlify="true"','').replace('netlify-honeypot="bot-field"','')
 markup=markup.replace('method="POST"',f'method="POST" action="{E(S.FORM_ENDPOINT)}"')
 markup=re.sub(r'<input type="hidden" name="form-name" value="([^"]+)">',r'<input type="hidden" name="formKind" value="\1">',markup)
 markup=markup.replace('개인정보 수집·이용 및 국외 이전',consent_text()).replace('국외 이전에 동의하지 않으면','동의하지 않으면')
 if S.FORM_INTERNATIONAL_TRANSFER:
  markup=markup.replace('<button type="submit"', '<label><input type="checkbox" name="transferConsent" value="yes" required> (필수) 국외 이전에 동의합니다. <a href="/privacy/">이전받는 자·국가·보유기간 안내</a></label><button type="submit"',1)
 return markup
