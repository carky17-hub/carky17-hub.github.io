"""Digital Asset Links: only public, explicitly supplied app-signing certificate fingerprints."""
import os,re

def asset_links():
 package=os.environ.get('ANDROID_PACKAGE_ID','com.eodigagae.app').strip()
 if not re.fullmatch(r'[a-zA-Z][\w]*(?:\.[a-zA-Z][\w]*)+',package,flags=re.ASCII):raise ValueError('Invalid Android package ID')
 raw=os.environ.get('ANDROID_SHA256_CERT_FINGERPRINTS','').strip()
 if not raw:return []
 fps=[v.strip().upper() for v in raw.split(',') if v.strip()]
 if not fps or any(not re.fullmatch(r'(?:[0-9A-F]{2}:){31}[0-9A-F]{2}',v) for v in fps):raise ValueError('Invalid SHA-256 certificate fingerprint')
 return [{'relation':['delegate_permission/common.handle_all_urls'],'target':{'namespace':'android_app','package_name':package,'sha256_cert_fingerprints':list(dict.fromkeys(fps))}}]
