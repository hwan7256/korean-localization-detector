# 🚀 ConvertRadar — 1분 랜딩페이지 전환율 & UX/SEO 진단기

> URL만 입력하면 Playwright로 랜딩페이지를 실시간 분석(CRO, SEO, GEO)하고 피드백을 주는 AI 분석 툴

## 주요 기능

- **실시간 웹 스크래핑**: Playwright를 이용해 입력된 URL의 HTML 구조, SEO 태그, 로딩 속도 및 주요 UI 요소의 절대 좌표와 텍스트를 자동 수집하고 스크린샷 캡처
- **전환율 최적화(CRO) 및 UX 진단**: DeepSeek API를 활용해 Clarity(명확성), CTA(행동유도), Hierarchy(정보구조), Social Proof(신뢰도), Performance(성능/SEO/GEO) 등 5대 영역 진단
- **시각적 진단 오버레이**: 스크린샷 위에 요소별 이탈 장벽(Friction Point)을 핀으로 시각화하고 호버 툴팁(Tippy.js)으로 개선 가이드 제공
- **A/B 테스트 제안**: 원래 H1 헤드라인 대비 전환 유도 목적의 최적 대안 카피(A/B안) 및 처방 배경 제시
- **우선순위별 체크리스트**: 즉각 조치할 수 있는 세부 태스크와 우선순위(Critical, Recommended, Optional) 제공

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python 3.11, FastAPI |
| Database | SQLite |
| AI/ML | DeepSeek API |
| 데이터 수집 | Playwright (Headless Chromium) |
| Frontend | Vanilla HTML/CSS/JS (Dark Neon Theme, Chart.js, Tippy.js) |
| 배포 | Uvicorn |

## 빠른 시작

```bash
# 1. 클론 및 이동
git clone https://github.com/hwan7256/korean-localization-detector.git
cd korean-localization-detector

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 DeepSeek API 키 입력:
# DEEPSEEK_API_KEY=your_deepseek_api_key

# 3. 가상환경 및 패키지 설치
source .venv/bin/activate
# Playwright 브라우저 설치 필요 시:
playwright install chromium

# 4. 데이터베이스 초기화 및 서버 실행
python backend/db.py
python backend/api/server.py
# → http://localhost:8733 에서 대시보드 사용 가능
```

## 프로젝트 구조

```
korean-localization-detector/
├── backend/
│   ├── api/
│   │   └── server.py          # FastAPI 서버 (진단 API 및 static 파일 서빙)
│   ├── db.py                  # SQLite 스키마 (page_audits, audit_logs)
│   ├── analyzer/
│   │   └── convert_analyzer.py # DeepSeek AI 기반 CRO/SEO 분석 엔진
│   ├── crawlers/
│   │   └── web_scraper.py     # Playwright 기반 좌표 수집 & 스크린샷 캡처
│   └── static/
│       ├── landing.html       # ConvertRadar 메인 진단 대시보드
│       ├── index.html         # landing.html로 리다이렉트
│       └── screenshots/       # 생성된 웹사이트 스크린샷 저장소
├── data/                      # SQLite 데이터베이스 파일 저장소
├── prompts/                   # 프롬프트 백서 및 참고자료
├── .env.example               # 환경변수 템플릿
├── .gitignore
└── README.md
```

## 라이선스

MIT
