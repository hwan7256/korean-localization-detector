"""KLD FastAPI Server — REST API"""
import os
import json
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from backend.db import get_db, init_db
from backend.crawlers.web_scraper import scrape_with_coordinates
from backend.analyzer.convert_analyzer import analyze_conversion_potential

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "static")

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
    url: str
    target_audience: str = ""

@app.post("/api/analyze")
def run_audit(request: AuditRequest):
    """실시간 웹사이트 크롤링 및 전환율 분석 수행"""
    url = request.url
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        # 1. 크롤링 및 좌표 수집
        crawled_data = scrape_with_coordinates(url)
        
        # 2. DeepSeek AI 분석
        analysis = analyze_conversion_potential(crawled_data, request.target_audience)
        
        # 3. DB 저장
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO page_audits (
                url, target_audience, screenshot_path,
                score_overall, score_clarity, score_cta, score_hierarchy, score_social_proof, score_performance,
                value_proposition, friction_points, action_checklist, ab_test_suggestions, elements
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(crawled_data["elements"], ensure_ascii=False)
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
            "elements": crawled_data["elements"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")

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
    for field in ["friction_points", "action_checklist", "ab_test_suggestions", "elements"]:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="127.0.0.1", port=8733, reload=True)
