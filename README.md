#  Korean Localization Detector (KLD)

> 해외에서 검증된 마이크로 SaaS를 발굴하고, 한국 시장 로컬라이징 적합도를 분석해주는 대시보드

## 주요 기능

- **자동 데이터 수집**: Product Hunt, Hacker News 등에서 최근 인기 마이크로 SaaS 자동 크롤링
- **로컬라이징 분석**: 각 서비스의 한국 시장 적합도를 Score / Confidence / Upside / Boldness 기준으로 평가
- **Triage Table 대시보드**: 정렬·필터 가능한 마스터-디테일 뷰로 기회 빠르게 탐색
- **상세 분석 리포트**: 선택한 서비스의 Summary, Risk Factors, Next Actions 확인
- **DeepSeek AI 기반**: 서비스 설명을 분석해 현지화 난이도·잠재력을 자동 평가

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python 3.11, FastAPI |
| Database | SQLite |
| AI/ML | DeepSeek API |
| 데이터 수집 | Reddit API, Product Hunt RSS, Hacker News |
| Frontend | Vanilla HTML/CSS/JS (다크 테마) |
| 배포 | Uvicorn |

## 빠른 시작

```bash
# 1. 클론
git clone https://github.com/hwan7256/korean-localization-detector.git
cd korean-localization-detector

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력:
#   REDDIT_CLIENT_ID=your_id
#   REDDIT_CLIENT_SECRET=***   DEEPSEEK_API_KEY=*** 3. 실행
pip install -r requirements.txt
cd backend/api
python server.py
# → http://localhost:8733
```

## 프로젝트 구조

```
korean-localization-detector/
├── backend/
│   ├── api/
│   │   └── server.py          # FastAPI 서버
│   ├── db.py                  # SQLite 스키마
│   └── static/
│       ├── index.html         # Triage Table 대시보드
│       ├── css/style.css      # 스타일
│       └── js/app.js          # 프론트엔드 로직
├── data/                      # 크롤링/분석 데이터
├── .env.example               # 환경변수 템플릿
├── .gitignore
└── README.md
```

## 라이선스

MIT
