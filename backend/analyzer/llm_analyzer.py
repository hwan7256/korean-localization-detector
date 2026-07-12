"""LLM 분석 엔진 — DeepSeek API로 해외 SaaS 한국 로컬라이징 분석"""
import os
import json
import requests
from backend.db import get_db

API_KEY = None
API_URL = "https://api.deepseek.com/v1/chat/completions"


def _get_api_key():
    global API_KEY
    if API_KEY is None:
        tk = os.getenv("DEEPSEEK_API_KEY")
        if not tk:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("DEEPSEEK_API_KEY="):
                            tk = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        API_KEY = tk
    return API_KEY

ANALYSIS_PROMPT = """당신은 한국 시장 진출 전략 분석가입니다. 다음 해외 마이크로 SaaS 서비스를 분석해주세요.

서비스명: {name}
URL: {url}
설명: {description}
출처: {source}

다음 JSON 형식으로만 응답하세요:
{{
  "summary_ko": "서비스 2-3문장 요약 (한국어)",
  "localization_score": 0-100 사이 정수,
  "localization_reason": "점수 산정 근거 1-2문장",
  "required_korean_apis": [
    {{"name": "API명", "necessity": "필수/권장/불필요", "reason": "이유"}}
  ],
  "regulatory_risks": "한국 규제 리스크 분석 (개인정보보호법, 전자상거래법 등)",
  "competitor_analysis": "국내 유사 서비스 및 경쟁 구도",
  "estimated_dev_time": "1인 개발 기준 예상 개발 기간",
  "monetization_ko": "한국 시장 맞춤 수익화 전략 제안",
  "template_code_summary": "국내 연동 핵심 코드 구조 설명 (유료 전용)"
}}

점수 기준:
- 80-100: 즉시 로컬라이징 가능, 규제 없음, 큰 시장
- 60-79: 약간의 수정 필요, 경쟁 있으나 진입 가능
- 40-59: 상당한 현지화 필요, 규제 확인 필수
- 0-39: 한국 시장 부적합 또는 과도한 규제

국내 API 참고: 카카오 로그인/알림톡/페이, 토스페이먼츠, 포트원, 네이버 로그인/클라우드, PASS 인증, 모두싸인, 알리고, NHN Cloud Notification, 카카오맵"""


def analyze_service(service: dict) -> dict:
    """단일 서비스 분석"""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set. export DEEPSEEK_API_KEY=sk-...")

    prompt = ANALYSIS_PROMPT.format(
        name=service["name"],
        url=service.get("url", ""),
        description=service.get("description", "")[:500],
        source=service.get("source", "unknown")
    )

    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2500
        },
        timeout=90
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    # 코드블록 제거
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    return json.loads(content.strip())


def save_analysis(service_id: int, analysis: dict, free_tier: bool = True):
    """분석 결과 DB 저장"""
    db = get_db()
    db.execute("""
        INSERT INTO analysis_reports
        (service_id, localization_score, summary_ko, localization_reason,
         required_korean_apis, regulatory_risks, competitor_analysis,
         estimated_dev_time, monetization_ko, template_code, free_tier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        service_id,
        analysis.get("localization_score", 0),
        analysis.get("summary_ko", ""),
        analysis.get("localization_reason", ""),
        json.dumps(analysis.get("required_korean_apis", []), ensure_ascii=False),
        analysis.get("regulatory_risks", ""),
        analysis.get("competitor_analysis", ""),
        analysis.get("estimated_dev_time", ""),
        analysis.get("monetization_ko", ""),
        json.dumps(analysis, ensure_ascii=False),
        1 if free_tier else 0
    ))
    db.commit()
    db.close()


def analyze_unanalyzed_services(limit: int = 5) -> int:
    """미분석 서비스 분석 (무료 2개, 나머지는 유료로 마킹)"""
    db = get_db()
    services = db.execute("""
        SELECT s.* FROM discovered_services s
        LEFT JOIN analysis_reports a ON s.id = a.service_id
        WHERE a.id IS NULL
        ORDER BY s.discovered_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    db.close()

    if not services:
        print("분석할 신규 서비스 없음")
        return 0

    analyzed = 0
    for svc in services:
        try:
            analysis = analyze_service(dict(svc))
            free = analyzed < 2  # 처음 2개만 무료
            save_analysis(svc["id"], analysis, free_tier=free)
            analyzed += 1
            score = analysis.get("localization_score", "?")
            print(f"  [{svc['name'][:50]}...] score={score} {'FREE' if free else 'PRO'}")
        except Exception as e:
            print(f"  분석 실패 [{svc['name'][:50]}]: {e}")

    return analyzed


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    n = analyze_unanalyzed_services(limit=5)
    print(f"분석 완료: {n}개")
