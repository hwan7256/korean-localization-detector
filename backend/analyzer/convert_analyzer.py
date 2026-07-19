"""ConvertRadar — DeepSeek API를 활용한 전환율 & UX 분석기

v2.0 개선사항:
- temperature 0.0 + response_format JSON 모드 (결정론적 출력)
- 정량적 성능 점수 Python 규칙 기반 계산 (로딩속도, SEO)
- 자가 보정 검증기 (마찰점 vs 점수 논리적 모순 후처리)
- 재시도 로직 (Rate limit, 네트워크 오류)
- LLM 점수 + 규칙 기반 점수 하이브리드 블렌딩 (7:3)
- 신뢰도(confidence) 지표 추가
"""
import os
import json
import time
import requests

API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = None

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


def calculate_programmatic_performance(crawled_data: dict) -> tuple[float, dict]:
    """Python 규칙 기반 정량적 성능 점수 계산 (LLM 의존도 제거)

    Returns:
        (total_score, detail_breakdown) — 0-100 점수 + 세부 내역
    """
    detail = {}
    seo = crawled_data.get("seo_metadata", {})

    # 1. 로딩 속도 점수 (500ms 이하 100점, 이후 50ms당 1점 감점)
    load_time = crawled_data.get("load_time_ms", 500)
    perf_score = max(0, 100 - max(0, (load_time - 500) // 50))
    detail["load_time_ms"] = load_time
    detail["load_score"] = perf_score

    # 2. SEO 메타데이터 점수
    seo_score = 100
    seo_issues = []

    h1_count = seo.get("h1_count", 0)
    if h1_count != 1:
        seo_score -= 15
        seo_issues.append(f"H1 태그 {h1_count}개 (권장 1개)")

    if not seo.get("has_canonical", False):
        seo_score -= 10
        seo_issues.append("Canonical 태그 누락")

    total_images = seo.get("total_images", 0)
    missing_alt = seo.get("missing_alt_images", 0)
    if total_images > 0:
        missing_ratio = missing_alt / total_images
        penalty = int(missing_ratio * 25)
        seo_score -= penalty
        if penalty > 0:
            seo_issues.append(f"이미지 Alt 누락 {missing_alt}/{total_images}개")

    title_len = seo.get("title_length", 0)
    if title_len > 0 and (title_len < 30 or title_len > 65):
        seo_score -= 8
        seo_issues.append(f"타이틀 길이 {title_len}자 (권장 30-65자)")

    meta_len = seo.get("meta_desc_length", 0)
    if meta_len > 0 and meta_len < 80:
        seo_score -= 5
        seo_issues.append(f"메타 설명 {meta_len}자 (권장 80자 이상)")

    detail["seo_score"] = max(0, seo_score)
    detail["seo_issues"] = seo_issues

    # 3. 종합: 로딩 60% + SEO 40%
    total = max(0, min(100, (perf_score * 0.6) + (seo_score * 0.4)))
    detail["total"] = round(total, 1)

    return total, detail


def calibrate_analysis_result(parsed_json: dict, rule_perf_score: float) -> dict:
    """LLM 응답 후처리: 논리적 모순 보정 + 신뢰도 계산

    보정 규칙:
    1. 마찰점 수/심각도와 점수 간 불일치 감지 → 하향 보정
    2. 점수 범위 0-100 클램핑
    3. 규칙 기반 점수와 LLM 점수 간 괴리가 크면 신뢰도 하락
    """
    scores = parsed_json.setdefault("scores", {})

    # 0-100 범위 클램핑
    for k in ["clarity", "cta", "hierarchy", "social_proof", "performance"]:
        scores[k] = max(0, min(100, int(scores.get(k, 50))))

    # 마찰점 기반 보정
    frictions = parsed_json.get("friction_points", [])
    high_count = sum(1 for f in frictions if f.get("severity") == "High")
    medium_count = sum(1 for f in frictions if f.get("severity") == "Medium")

    original_score = parsed_json.get("score_overall", 70)
    deduction = (high_count * 10) + (medium_count * 4)
    calibrated_score = max(20, min(98, int(original_score) - deduction))

    # 규칙 기반 점수와 LLM 점수의 괴리 계산 → 신뢰도
    llm_perf = scores.get("performance", 50)
    perf_gap = abs(llm_perf - rule_perf_score)

    # 신뢰도: gap이 클수록 낮아짐, 마찰점 불일치도 반영
    confidence = max(30, 100 - (perf_gap * 0.4) - (high_count * 8) - (medium_count * 3))

    # 점수 블렌딩 (LLM 70% + 규칙 30%)
    blended_perf = round((llm_perf * 0.7) + (rule_perf_score * 0.3), 1)
    scores["performance"] = blended_perf

    parsed_json["score_overall"] = calibrated_score
    parsed_json["confidence"] = round(confidence, 1)
    parsed_json["rule_based_performance"] = round(rule_perf_score, 1)
    parsed_json["calibration_applied"] = deduction > 0
    parsed_json["calibration_deduction"] = deduction

    return parsed_json


def _call_deepseek_with_retry(prompt: str, max_retries: int = 3) -> str:
    """DeepSeek API 호출 with 재시도 + exponential backoff"""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY가 설정되지 않았습니다.")

    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a conversion rate optimization (CRO) expert. "
                                "You MUST output exactly one valid JSON object matching "
                                "the specified schema. No markdown, no code blocks, no extra text."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 3000
                },
                timeout=90
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            last_error = f"API 타임아웃 (시도 {attempt + 1}/{max_retries})"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                last_error = f"Rate limit 초과 (시도 {attempt + 1}/{max_retries})"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt * 2)
            else:
                raise
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"DeepSeek API 호출 실패 ({max_retries}회 재시도): {last_error}")


CONVERT_AUDIT_PROMPT = """당신은 세계 최고 수준의 전환율 최적화(CRO) 및 검색엔진 최적화(SEO), 그리고 AI 검색 최적화(GEO) 전문가이자 카피라이터입니다.
제시된 랜딩페이지의 데이터를 분석하여 잠재 고객을 구매자로 전환시키는 힘이 얼마나 강한지 평가하고, 기술적 SEO 및 AI 검색 로봇(Perplexity, ChatGPT 등)에 얼마나 잘 노출될 수 있는지(AI Search Readiness) 진단하여 개선 방향을 처방해주세요.

---
### 1. 타겟 고객 (Target Audience)
{target_audience}

### 2. 크롤링된 랜딩페이지 정보
- 페이지 타이틀: {title}
- 메타 설명: {meta_desc}
- 주요 H1 헤드라인: {h1_headers}
- 주요 H2 헤드라인: {h2_headers}
- 수집된 CTA(콜투액션) 버튼: {cta_buttons}
- 페이지 내 수집된 주요 UI 엘리먼트 (ID 및 텍스트):
{scraped_elements}
- 페이지 내 주요 본문 텍스트:
{text_content}
- 페이지 최초 로딩 속도: {load_time_ms}ms
- 온페이지/테크니컬 SEO 진단 데이터:
  * 타이틀 자수: {seo_title_length}자 (권장: 50~60자)
  * 메타 설명 자수: {seo_meta_desc_length}자 (권장: 100자 이상)
  * H1 태그 개수: {seo_h1_count}개 (권장: 1개)
  * 전체 이미지 개수: {seo_total_images}개
  * Alt 태그가 유실된 이미지 수: {seo_missing_alt_images}개 (권장: 0개)
  * Canonical 태그 존재 여부: {seo_has_canonical}
---

[주의 사항]
1. 발견된 CRO/SEO 마찰 요인이 위의 수집된 UI 엘리먼트(ID 및 텍스트) 중 하나와 명확히 매치된다면, "friction_points" 배열 내의 "matched_element_id" 필드에 해당 정수 ID를 반드시 기입해 주세요. 만약 특정 엘리먼트에 직접 해당되지 않거나 매칭이 애매하다면 null로 채우십시오. (예: 메타 설명 누락이나 로딩 속도는 특정 엘리먼트 좌표가 없으므로 null)
2. 온페이지/테크니컬 SEO 문제나 이미지 Alt 태그 유실, 그리고 AI 로봇이 정보를 긁어가기 어려운 구조적 문제(예: H1 다중 사용 또는 부재, 지나치게 짧은 설명)도 반드시 진단하고 "SEO" 카테고리로 friction_points에 포함하십시오.
3. [브랜드 규모 및 비즈니스 유형에 따른 평가 유연성]
   - 분석할 대상 페이지가 이미 인지도가 매우 높은 대형 프랜차이즈, 대기업 브랜드(예: 스타벅스, 맥도날드, 애플, 나이키 등) 혹은 대형 포털/플랫폼인지 우선 확인하십시오.
   - 이러한 기성 유명 브랜드는 복잡한 고객 후기(Social Proof)나 직접적/공격적인 전환 유도용 CTA 카피가 없더라도 브랜드 신뢰도 자체가 강력하게 형성되어 있습니다. 따라서 일반 마이크로 스타트업의 잣대와 같이 "리뷰 배지가 누락되어 신뢰도가 낮다", "CTA 버튼에 긴급성이 없다"와 같은 비합리적인 이유로 기계적 감점을 해서는 안 되며, F등급을 난발하면 보고서의 신뢰성이 크게 떨어집니다.
   - 유명 브랜드의 랜딩페이지는 브랜드 가치와 아이덴티티 전달력, 미니멀리즘 디자인 레이아웃, 직관적인 탐색 경로를 중심으로 심사하여 정당한 수준의 고점(75~95점)을 적극 부여하고, 억지로 단점을 지어내지 마십시오.
4. 반드시 다음 JSON 포맷으로만 응답해야 합니다. 어떠한 사족이나 마크다운 코드블록 기호(```)도 덧붙이지 마십시오.

{{
  "score_overall": 0-100 사이의 종합 점수,
  "scores": {{
    "clarity": 0-100 점수 (첫 3초 내 서비스 가치 이해도),
    "cta": 0-100 점수 (가입/구매 버튼의 시인성과 매력도),
    "hierarchy": 0-100 점수 (내용 전개의 논리성 및 정보 계층 구조),
    "social_proof": 0-100 점수 (리뷰, 신뢰 지표, 통계 자료의 품질),
    "performance": 0-100 점수 (로딩 속도, 테크니컬 SEO 및 AI 검색 최적화 지표 통합 점수)
  }},
  "value_proposition_analysis": "현재 히어로 섹션 카피의 명확성 및 검색 노출 관점의 강점/약점 요약 (2~3문장)",
  "friction_points": [
    {{
      "matched_element_id": 위의 엘리먼트 ID 정수 혹은 null,
      "category": "Clarity|CTA|Hierarchy|Trust|Performance|SEO 중 택1",
      "issue": "발견된 구체적 마찰/이탈/SEO 요인 1가지",
      "severity": "High|Medium|Low 중 택1",
      "solution": "해결을 위한 구체적인 액션 가이드 제시"
    }}
  ],
  "action_checklist": [
    {{
      "task": "즉각 취할 수 있는 구체적인 수정 조치 문구",
      "priority": "Critical|Recommended|Optional 중 택1"
    }}
  ],
  "ab_test_suggestions": {{
    "original_h1": "원래 있었던 H1 문구",
    "alternative_h1_A": "대안 카피 A안 (전환율 향상 목적)",
    "alternative_h1_B": "대안 카피 B안 (심리적 손실 회피 및 검색 키워드 유입 목적)",
    "reasoning": "대안 카피 제시 근거 요약"
  }}
}}
"""


def analyze_conversion_potential(crawled_data: dict, target_audience: str) -> dict:
    """DeepSeek API를 호출하여 랜딩페이지 전환율 분석 수행 (v2.0)

    개선사항:
    - temperature 0.0 + JSON 모드
    - Python 규칙 기반 정량 성능 점수 블렌딩
    - 자가 보정 검증기
    - 재시도 로직
    - 신뢰도(confidence) 지표
    """
    # 1. 규칙 기반 정량 성능 점수 선계산
    rule_perf_score, perf_detail = calculate_programmatic_performance(crawled_data)

    # 2. LLM 컨텍스트용 엘리먼트 직렬화
    scraped_elements_str = ""
    for el in crawled_data["elements"]:
        scraped_elements_str += f"- ID: {el['id']}, 태그: {el['tag']}, 텍스트: \"{el['text']}\"\n"
    if not scraped_elements_str:
        scraped_elements_str = "(감지된 주요 헤더나 버튼이 없음)"

    seo = crawled_data.get("seo_metadata", {})
    prompt = CONVERT_AUDIT_PROMPT.format(
        target_audience=target_audience or "General Public (일반 대중)",
        title=crawled_data["title"],
        meta_desc=crawled_data["meta_desc"],
        h1_headers=", ".join(crawled_data["headers"]["h1"]),
        h2_headers=", ".join(crawled_data["headers"]["h2"]),
        cta_buttons=json.dumps(crawled_data["cta_buttons"], ensure_ascii=False),
        scraped_elements=scraped_elements_str,
        text_content=crawled_data["text_content"][:3000],
        load_time_ms=crawled_data["load_time_ms"],
        seo_title_length=seo.get("title_length", 0),
        seo_meta_desc_length=seo.get("meta_desc_length", 0),
        seo_h1_count=seo.get("h1_count", 0),
        seo_total_images=seo.get("total_images", 0),
        seo_missing_alt_images=seo.get("missing_alt_images", 0),
        seo_has_canonical="있음" if seo.get("has_canonical", False) else "없음"
    )

    # 3. DeepSeek API 호출 (with retry, temperature=0, JSON mode)
    raw_content = _call_deepseek_with_retry(prompt)

    # 4. 마크다운 코드 블록 제거 (JSON mode로 거의 불필요하지만 안전장치)
    if "```" in raw_content:
        parts = raw_content.split("```")
        raw_content = parts[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]

    # 5. JSON 파싱
    try:
        parsed_json = json.loads(raw_content.strip())
    except json.JSONDecodeError as je:
        print(f"JSON Parsing Error: {je}")
        print(f"Raw Output was: {raw_content[:500]}")
        raise RuntimeError("DeepSeek 응답이 올바른 JSON 형식이 아닙니다.")

    # 6. 자가 보정 + 규칙 기반 점수 블렌딩 + 신뢰도 계산
    parsed_json = calibrate_analysis_result(parsed_json, rule_perf_score)

    # 7. 성능 상세 정보 추가 (프론트엔드 표시용)
    parsed_json["performance_detail"] = perf_detail

    return parsed_json


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    mock_data = {
        "url": "https://example.com",
        "title": "Fast CRM for Solopreneurs",
        "meta_desc": "Manage your clients in one dashboard. Start for free.",
        "headers": {
            "h1": ["Fast CRM for Solopreneurs"],
            "h2": ["Why choose us?", "Pricing plans"],
            "h3": []
        },
        "cta_buttons": [{"text": "Start for free", "href": "/signup"}],
        "text_content": "Super easy client management CRM. No credit card required. Trusted by 5,000+ indie hackers.",
        "load_time_ms": 350,
        "elements": [
            {"id": 1, "tag": "h1", "text": "Fast CRM for Solopreneurs", "x": 100, "y": 150, "w": 600, "h": 50},
            {"id": 2, "tag": "button", "text": "Start for free", "x": 100, "y": 300, "w": 180, "h": 45}
        ]
    }

    try:
        res = analyze_conversion_potential(mock_data, "Indie Hackers starting SaaS projects")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error during test: {e}")
