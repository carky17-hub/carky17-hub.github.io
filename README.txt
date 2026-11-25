어디가개 WEB v2.0 | GitHub Pages 소스
internal/V20-RELEASE.md 참고. internal/은 공개 저장소에 업로드 금지.
GitHub Actions Variable KAKAO_JS_KEY: 공개용 JavaScript 키만 등록. 키 없으면 홈 지도는 기본 지도 사용.
Worker 변경 후보는 단일 파일 worker/eodigagae-api.bundle.js. 지도 배포에는 Worker 재배포 불필요. 기존 운영 Worker 설정 보존. KV 호출 제한은 엄격한 총량 제한이 아님.
Google 서버 키와 통계 조회 토큰은 Cloudflare Worker secret에만 입력. 기본 외부 리뷰 API/이용 통계 OFF.
Python 표준 라이브러리로 build.py 및 verify.py 실행.
