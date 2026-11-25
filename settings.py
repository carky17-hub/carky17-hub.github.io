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
if ALLOW_INDEXING and not PUBLIC_DATA_APPROVED:raise RuntimeError('Confirm public data rights before deployment.')
if ENABLE_FORMS and os.environ.get("FORM_ENDPOINT", "").strip() and not POLICY_APPROVED:raise RuntimeError('Finalize privacy policy before accepting personal data.')

POLICY_VERSION=os.environ.get('POLICY_VERSION','draft-2026-11-25')
if ENABLE_FORMS and os.environ.get("FORM_ENDPOINT", "").strip() and POLICY_VERSION.startswith('draft'):raise RuntimeError('Set approved POLICY_VERSION before accepting personal data.')

ENABLE_ADFIT=flag('ENABLE_ADFIT')
ADFIT_MID=os.environ.get('ADFIT_MID','')
ADFIT_BOTTOM=os.environ.get('ADFIT_BOTTOM','')
ENABLE_KAKAO_LINKS=flag('ENABLE_KAKAO_LINKS')
CONTACT_EMAIL=os.environ.get('CONTACT_EMAIL','')
# Local review may opt into provisional link IDs; public build requires separate approval.
if ENABLE_KAKAO_LINKS and ALLOW_INDEXING and not flag('KAKAO_LINKS_APPROVED'):raise RuntimeError('Confirm Kakao link ID reuse before publication.')
if ENABLE_FORMS and os.environ.get("FORM_ENDPOINT", "").strip() and not CONTACT_EMAIL:raise RuntimeError('Set contact email for offline alternative.')
if ENABLE_ADFIT and (not POLICY_APPROVED or not ADFIT_MID or not ADFIT_BOTTOM):raise RuntimeError('Approve advertising privacy notice and set both AdFit IDs.')

BUSINESS_NAME=os.environ.get('BUSINESS_NAME','강마케팅').strip()
BUSINESS_REPRESENTATIVE=os.environ.get('BUSINESS_REPRESENTATIVE','').strip()
BUSINESS_NUMBER=os.environ.get('BUSINESS_NUMBER','').strip()
BUSINESS_ADDRESS=os.environ.get('BUSINESS_ADDRESS','').strip()
BUSINESS_PHONE=os.environ.get('BUSINESS_PHONE','').strip()
BUSINESS_JURISDICTION=os.environ.get('BUSINESS_JURISDICTION','').strip()
POLICY_EFFECTIVE_DATE=os.environ.get('POLICY_EFFECTIVE_DATE','').strip()
ADS_POLICY_APPROVED=flag('ADS_POLICY_APPROVED')
RELEASE_MODE=flag('RELEASE_MODE') or ALLOW_INDEXING
if RELEASE_MODE:
 if not PUBLIC_DATA_APPROVED or not POLICY_APPROVED:raise RuntimeError('Confirm public data rights and privacy/terms before publishing.')
 if not all((BUSINESS_NAME,BUSINESS_REPRESENTATIVE,BUSINESS_NUMBER,BUSINESS_ADDRESS,BUSINESS_PHONE,BUSINESS_JURISDICTION,CONTACT_EMAIL,POLICY_EFFECTIVE_DATE)):raise RuntimeError('Complete public business identity and policy effective date first.')
 if POLICY_VERSION.startswith('draft'):raise RuntimeError('Set approved POLICY_VERSION.')
if ENABLE_KAKAO_LINKS:raise RuntimeError('v1.2 excludes all Kakao API-derived IDs.')
if ENABLE_ADFIT and not ADS_POLICY_APPROVED:raise RuntimeError('Approve advertising policy first.')

# GitHub Pages / external form transport. Endpoint must be a public HTTPS POST URL, not a credential.
from urllib.parse import urlsplit
FORM_ENDPOINT=os.environ.get('FORM_ENDPOINT','').strip()
KAKAO_CHANNEL_URL=os.environ.get('KAKAO_CHANNEL_URL','').strip()
FORM_PROVIDER=os.environ.get('FORM_PROVIDER','').strip()
FORM_PROVIDER_COUNTRY=os.environ.get('FORM_PROVIDER_COUNTRY','').strip()
FORM_PROVIDER_CONTACT=os.environ.get('FORM_PROVIDER_CONTACT','').strip()
FORM_PROVIDER_RETENTION=os.environ.get('FORM_PROVIDER_RETENTION','').strip()
_transfer_raw=os.environ.get('FORM_INTERNATIONAL_TRANSFER','').strip().lower()
if _transfer_raw not in ('','true','false'):raise ValueError('FORM_INTERNATIONAL_TRANSFER must be true or false')
FORM_INTERNATIONAL_TRANSFER=_transfer_raw=='true'
def https_url(v):
 u=urlsplit(v);return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and not u.fragment and not any(c.isspace() for c in v)
if FORM_ENDPOINT and not https_url(FORM_ENDPOINT):raise ValueError('FORM_ENDPOINT must be a public HTTPS URL')
if KAKAO_CHANNEL_URL and (not https_url(KAKAO_CHANNEL_URL) or urlsplit(KAKAO_CHANNEL_URL).hostname!='pf.kakao.com'):raise ValueError('Use a public https://pf.kakao.com/ channel URL')
FORMS_LIVE=ENABLE_FORMS and bool(FORM_ENDPOINT)
if FORMS_LIVE and _transfer_raw not in ('true','false'):raise RuntimeError('Explicitly confirm whether form data is transferred abroad.')
if FORMS_LIVE and not all((FORM_PROVIDER,FORM_PROVIDER_COUNTRY,FORM_PROVIDER_CONTACT,FORM_PROVIDER_RETENTION)):raise RuntimeError('Configure form processor, country, contact and retention before enabling online forms.')

# Formspree current endpoint format; generic compatible HTTPS POST remains supported.
if FORM_ENDPOINT and urlsplit(FORM_ENDPOINT).hostname=="formspree.io" and not __import__("re").fullmatch(r"/f/[A-Za-z0-9]+",urlsplit(FORM_ENDPOINT).path):raise ValueError("Use https://formspree.io/f/<form-id>")
FORM_FILE_UPLOADS=flag("FORM_FILE_UPLOADS")
