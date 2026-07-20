import os
import json
import time
import ipaddress
from urllib.parse import urlparse
from fastapi import FastAPI, Query, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from backend.db import get_db, init_db
from backend.crawlers.web_scraper import scrape_with_coordinates
from backend.analyzer.convert_analyzer import analyze_conversion_potential

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "static")

# Rate limiter: IP별 분당 최대 5회
_rate_limit_store: dict[str, list[float]] = {}

def _check_rate_limit(ip: str, max_req: int = 5, window: int = 60) -> None:
    now = time.time()
    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = []
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < window]
    if len(_rate_limit_store[ip]) >= max_req:
        raise HTTPException(status_code=429, detail="너무 많은 요청입니다. 잠시 후 다시 시도해주세요.")
    _rate_limit_store[ip].append(now)

# SSRF 차단: 내부/예약 IP 블록리스트
SSRF_BLOCKED_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
]

def _validate_url(raw_url: str) -> str:
    """SSRF 방어: URL 검증 및 정규화"""
    parsed = urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    
    # 프로토콜 제한
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="http/https URL만 허용됩니다")
    
    # 파일/내부 스킴 차단
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="유효하지 않은 URL입니다")
    
    # IP 주소 체크
    try:
        ip = ipaddress.ip_address(hostname)
        for net in SSRF_BLOCKED_NETS:
            if ip in net:
                raise HTTPException(status_code=400, detail="내부 네트워크 주소는 허용되지 않습니다")
    except ValueError:
        pass  # hostname이 IP가 아니면 DNS resolve 전이므로 통과
    
    # localhost 문자열 차단
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"):
        raise HTTPException(status_code=400, detail="내부 네트워크 주소는 허용되지 않습니다")
    
    return parsed.geturl() if "://" in raw_url else f"https://{raw_url}"

app = FastAPI(title="KLD - Korean Localization Detector", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kld.lat", "https://kld.etfsimulator.blog", "http://kld.etfsimulator.blog"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# 정적 파일 — static 디렉토리가 있어야 마운트
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    fp = os.path.join(STATIC_DIR, "landing.html")
    if os.path.exists(fp):
        return open(fp).read()
    return HTMLResponse("<h1>KLD</h1>", status_code=200)


@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/dashboard.html", response_class=HTMLResponse)
def dashboard():
    """대시보드 HTML 서빙"""
    fp = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(fp):
        return open(fp).read()
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


class AuditRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    target_audience: str = Field(default="", max_length=500)

@app.post("/api/analyze")
def run_audit(request: AuditRequest, req: Request):
    """실시간 웹사이트 크롤링 및 전환율 분석 수행"""
    _check_rate_limit(req.client.host if req.client else "unknown")
    url = _validate_url(request.url)

    try:
        # 1. 크롤링 및 좌표 수집
        crawled_data = scrape_with_coordinates(url)
        
        # 2. DeepSeek AI 분석
        analysis = analyze_conversion_potential(crawled_data, request.target_audience)
        
        # 3. DB 저장
        db = get_db()
        cursor = db.cursor()
        # 신뢰도 및 상세 정보 추출
        confidence = analysis.get("confidence", 0)
        rule_perf = analysis.get("rule_based_performance", 0)
        calib_applied = 1 if analysis.get("calibration_applied") else 0
        perf_detail = json.dumps(analysis.get("performance_detail", {}), ensure_ascii=False)

        cursor.execute("""
            INSERT INTO page_audits (
                url, target_audience, screenshot_path,
                score_overall, score_clarity, score_cta, score_hierarchy, score_social_proof, score_performance,
                value_proposition, friction_points, action_checklist, ab_test_suggestions, elements,
                confidence, rule_based_performance, calibration_applied, performance_detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            url,
            request.target_audience,
            crawled_data["screenshot_url"],
            analysis["score_overall"],
            analysis["scores"]["clarity"],
            analysis["scores"]["cta"],
            analysis["scores"]["hierarchy"],
            analysis["scores"]["social_proof"],
            analysis["scores"]["performance"],
            analysis["value_proposition_analysis"],
            json.dumps(analysis["friction_points"], ensure_ascii=False),
            json.dumps(analysis["action_checklist"], ensure_ascii=False),
            json.dumps(analysis["ab_test_suggestions"], ensure_ascii=False),
            json.dumps(crawled_data["elements"], ensure_ascii=False),
            confidence,
            rule_perf,
            calib_applied,
            perf_detail
        ))
        db.commit()
        audit_id = cursor.lastrowid
        db.close()
        
        # 4. 결과 반환
        return {
            "id": audit_id,
            "success": True,
            "url": url,
            "target_audience": request.target_audience,
            "overall_score": analysis["score_overall"],
            "scores": analysis["scores"],
            "value_proposition": analysis["value_proposition_analysis"],
            "friction_points": analysis["friction_points"],
            "action_checklist": analysis["action_checklist"],
            "ab_test_suggestions": analysis["ab_test_suggestions"],
            "screenshot_url": crawled_data["screenshot_url"],
            "elements": crawled_data["elements"],
            "confidence": analysis.get("confidence", 0),
            "rule_based_performance": analysis.get("rule_based_performance", 0),
            "calibration_applied": analysis.get("calibration_applied", False),
            "calibration_deduction": analysis.get("calibration_deduction", 0),
            "performance_detail": analysis.get("performance_detail", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

@app.get("/api/history")
def get_history(limit: int = Query(20, ge=1, le=100)):
    """과거 분석 이력 조회"""
    db = get_db()
    rows = db.execute("""
        SELECT id, url, target_audience, score_overall, created_at
        FROM page_audits
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    db.close()
    return {"history": [dict(r) for r in rows]}

@app.get("/api/audit/{audit_id}")
def get_audit(audit_id: int):
    """특정 분석 상세 리포트 조회"""
    db = get_db()
    row = db.execute("SELECT * FROM page_audits WHERE id=?", (audit_id,)).fetchone()
    db.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="해당 분석 리포트를 찾을 수 없습니다.")
        
    r = dict(row)
    # JSON 문자열 필드를 객체로 복원
    for field in ["friction_points", "action_checklist", "ab_test_suggestions", "elements", "performance_detail"]:
        if r.get(field) and isinstance(r[field], str):
            try:
                r[field] = json.loads(r[field])
            except Exception:
                pass
                
    return r


@app.get("/robots.txt")
def robots():
    fp = os.path.join(STATIC_DIR, "robots.txt")
    if os.path.exists(fp):
        return Response(open(fp).read(), media_type="text/plain")
    raise HTTPException(404)


@app.get("/sitemap.xml")
def sitemap():
    """Google Search Console 사이트맵"""
    fp = os.path.join(STATIC_DIR, "sitemap.xml")
    if os.path.exists(fp):
        return Response(open(fp).read(), media_type="application/xml")
    raise HTTPException(404)


@app.get("/privacy", response_class=HTMLResponse)
@app.get("/privacy.html", response_class=HTMLResponse)
def privacy_page():
    fp = os.path.join(STATIC_DIR, "privacy.html")
    if not os.path.exists(fp): raise HTTPException(404)
    return HTMLResponse(open(fp).read())

@app.get("/terms", response_class=HTMLResponse)
@app.get("/terms.html", response_class=HTMLResponse)
def terms_page():
    fp = os.path.join(STATIC_DIR, "terms.html")
    if not os.path.exists(fp): raise HTTPException(404)
    return HTMLResponse(open(fp).read())

@app.exception_handler(404)
async def spa_fallback(request, exc):
    """SPA 폴백 — 알 수 없는 경로는 landing.html 제공 (클라이언트 라우팅)"""
    fp = os.path.join(STATIC_DIR, "landing.html")
    if os.path.exists(fp):
        return HTMLResponse(open(fp).read(), status_code=200)
    return HTMLResponse("""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>404 — ConvertRadar</title><style>:root{--bg:#07070b;--text-muted:#888;--primary:#00ffb2}*{margin:0;padding:0;box-sizing:border-box}body{background:var(--bg);color:#fff;font-family:'Noto Sans KR',sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;flex-direction:column}h1{font-size:4rem;color:var(--primary);margin-bottom:12px}p{color:var(--text-muted);font-size:1rem;margin-bottom:24px}a{color:var(--primary);text-decoration:none;font-size:0.95rem}a:hover{text-decoration:underline}</style></head><body><h1>404</h1><p>페이지를 찾을 수 없습니다</p><a href="/">ConvertRadar 홈으로</a></body></html>""", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="127.0.0.1", port=8733, reload=True)
