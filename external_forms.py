import html,re
from urllib.parse import quote
import settings as S
E=lambda v:html.escape(v,quote=True)
def contact_markup():
 parts=[]
 if S.KAKAO_CHANNEL_URL:parts.append(f'<a class="btn" href="{E(S.KAKAO_CHANNEL_URL)}" rel="noopener noreferrer" target="_blank">카카오톡 채널 문의</a>')
 if S.CONTACT_EMAIL:parts.append(f'<a class="btn" href="mailto:{E(quote(S.CONTACT_EMAIL,safe="@.+-_"))}">이메일 문의</a>')
 return ' '.join(parts) or '<p>공식 문의처 준비 중입니다.</p>'
def fallback():return '<h1>입점·정보 수정·폐업 신고 및 출시 알림 문의</h1><p class="notice">온라인 신청은 아직 운영하지 않습니다. 문의처를 이용해 주세요.</p>'+contact_markup()
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
