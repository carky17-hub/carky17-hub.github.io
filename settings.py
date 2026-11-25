import os
SITE_URL=os.environ.get('SITE_URL','https://eodigagae.com').rstrip('/')
def flag(name):
 value=os.environ.get(name,'false').lower()
 if value not in ('true','false'):raise ValueError(name+' must be true or false')
 return value=='true'
ALLOW_INDEXING=flag('ALLOW_INDEXING')
ENABLE_FORMS=flag('ENABLE_FORMS')
PUBLIC_DATA_APPROVED=flag('PUBLIC_DATA_APPROVED')
POLICY_APPROVED=flag('POLICY_APPROVED')
NAVER_VERIFICATION=os.environ.get('NAVER_SITE_VERIFICATION','')
GOOGLE_VERIFICATION=os.environ.get('GOOGLE_SITE_VERIFICATION','')
if (ALLOW_INDEXING or os.environ.get('NETLIFY')=='true') and not PUBLIC_DATA_APPROVED:raise RuntimeError('Confirm public data rights before deployment.')
if ENABLE_FORMS and not POLICY_APPROVED:raise RuntimeError('Finalize privacy policy before accepting personal data.')

POLICY_VERSION=os.environ.get('POLICY_VERSION','draft-2026-11-25')
if ENABLE_FORMS and POLICY_VERSION.startswith('draft'):raise RuntimeError('Set approved POLICY_VERSION before accepting personal data.')

ENABLE_ADFIT=flag('ENABLE_ADFIT')
ADFIT_MID=os.environ.get('ADFIT_MID','')
ADFIT_BOTTOM=os.environ.get('ADFIT_BOTTOM','')
ENABLE_KAKAO_LINKS=flag('ENABLE_KAKAO_LINKS')
CONTACT_EMAIL=os.environ.get('CONTACT_EMAIL','')
# Local review may opt into provisional link IDs; public build requires separate approval.
if ENABLE_KAKAO_LINKS and (ALLOW_INDEXING or os.environ.get('NETLIFY')=='true') and not flag('KAKAO_LINKS_APPROVED'):raise RuntimeError('Confirm Kakao link ID reuse before publication.')
if ENABLE_FORMS and not CONTACT_EMAIL:raise RuntimeError('Set contact email for offline alternative.')
if ENABLE_ADFIT and (not POLICY_APPROVED or not ADFIT_MID or not ADFIT_BOTTOM):raise RuntimeError('Approve advertising privacy notice and set both AdFit IDs.')

BUSINESS_NAME=os.environ.get('BUSINESS_NAME','강마케팅').strip()
BUSINESS_REPRESENTATIVE=os.environ.get('BUSINESS_REPRESENTATIVE','').strip()
BUSINESS_NUMBER=os.environ.get('BUSINESS_NUMBER','').strip()
BUSINESS_ADDRESS=os.environ.get('BUSINESS_ADDRESS','').strip()
BUSINESS_PHONE=os.environ.get('BUSINESS_PHONE','').strip()
BUSINESS_JURISDICTION=os.environ.get('BUSINESS_JURISDICTION','').strip()
POLICY_EFFECTIVE_DATE=os.environ.get('POLICY_EFFECTIVE_DATE','').strip()
ADS_POLICY_APPROVED=flag('ADS_POLICY_APPROVED')
RELEASE_MODE=flag('RELEASE_MODE') or os.environ.get('NETLIFY')=='true' or ALLOW_INDEXING
if RELEASE_MODE:
 if not PUBLIC_DATA_APPROVED or not POLICY_APPROVED:raise RuntimeError('Confirm public data rights and privacy/terms before publishing.')
 if not all((BUSINESS_NAME,BUSINESS_REPRESENTATIVE,BUSINESS_NUMBER,BUSINESS_ADDRESS,BUSINESS_PHONE,BUSINESS_JURISDICTION,CONTACT_EMAIL,POLICY_EFFECTIVE_DATE)):raise RuntimeError('Complete public business identity and policy effective date first.')
 if POLICY_VERSION.startswith('draft'):raise RuntimeError('Set approved POLICY_VERSION.')
if ENABLE_KAKAO_LINKS:raise RuntimeError('v1.1 excludes all Kakao API-derived IDs.')
if ENABLE_ADFIT and not ADS_POLICY_APPROVED:raise RuntimeError('Approve advertising policy first.')
