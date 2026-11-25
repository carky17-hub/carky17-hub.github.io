import html
import settings as S
def public_value(v):return v or '확정 전'
def identity(md):
 vals={'[상호]':S.BUSINESS_NAME,'[강마케팅]':S.BUSINESS_NAME,'[대표자명]':S.BUSINESS_REPRESENTATIVE,'[이메일]':S.CONTACT_EMAIL,'[대표 이메일]':S.CONTACT_EMAIL,'[전화번호]':S.BUSINESS_PHONE,'[회사 소재지]':S.BUSINESS_JURISDICTION,'[2026년 ○월 ○일]':S.POLICY_EFFECTIVE_DATE}
 for k,v in vals.items():md=md.replace(k,public_value(v))
 md=md.replace('강마케팅 대표 ___',S.BUSINESS_NAME+' 대표 '+public_value(S.BUSINESS_REPRESENTATIVE))
 if S.POLICY_APPROVED:md=md.replace('개인정보처리방침 (초안)','개인정보처리방침').replace('이용약관 (초안)','이용약관').replace('> 초안입니다. 대괄호 [ ] 안을 채우고, 정식 오픈 전 전문가 검토를 권장합니다.','')
 return md
def business_lines():
 vals=[('상호',S.BUSINESS_NAME),('대표',S.BUSINESS_REPRESENTATIVE),('사업자등록번호',S.BUSINESS_NUMBER),('주소',S.BUSINESS_ADDRESS),('전화',S.BUSINESS_PHONE),('이메일',S.CONTACT_EMAIL)]
 return ' · '.join(f'{k}: {public_value(v)}' for k,v in vals)
def business_html():return html.escape(business_lines(),quote=True)
def adfit_notice():
 status='서비스는 카카오 애드핏 광고를 게재합니다.' if S.ENABLE_ADFIT else '현재 카카오 애드핏은 비활성 상태이며, 활성화 시 다음과 같이 처리될 수 있습니다.'
 return '\n## 맞춤형 광고 안내\n'+status+'\n- 수집 주체: (주)카카오\n- 항목: 웹 방문기록, 쿠키 등 행태정보 (환경에 따라 광고식별자)\n- 목적: 맞춤형 광고 제공\n- 거부: 브라우저 쿠키 차단 또는 카카오 맞춤형 광고 설정에서 거부\n'
