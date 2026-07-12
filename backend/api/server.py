"""KLD FastAPI Server — REST API"""
import os
import json
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.db import get_db, init_db

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
def dashboard():
    """대시보드 HTML 서빙"""
    fp = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(fp):
        return open(fp).read()
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/stats")
def get_stats():
    """대시보드 통계"""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM discovered_services").fetchone()[0]
    analyzed = db.execute("SELECT COUNT(*) FROM analysis_reports").fetchone()[0]
    avg_score = db.execute("SELECT AVG(localization_score) FROM analysis_reports").fetchone()[0] or 0
    high = db.execute("SELECT COUNT(*) FROM analysis_reports WHERE localization_score >= 70").fetchone()[0]
    db.close()
    return {
        "total_services": total,
        "total_analyzed": analyzed,
        "avg_localization_score": round(avg_score, 1),
        "high_potential_count": high
    }


@app.get("/api/services")
def list_services(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    free_only: bool = Query(False)
):
    """서비스 목록 + 분석 결과"""
    db = get_db()
    conds = ["1=1"]
    params = []

    if source:
        conds.append("s.source = ?")
        params.append(source)
    if min_score > 0:
        conds.append("a.localization_score >= ?")
        params.append(min_score)
    if free_only:
        conds.append("a.free_tier = 1")

    where = " AND ".join(conds)
    query = f"""
        SELECT s.*, a.localization_score, a.summary_ko, a.localization_reason,
               a.free_tier, a.created_at as analyzed_at
        FROM discovered_services s
        LEFT JOIN analysis_reports a ON s.id = a.service_id
        WHERE {where}
        ORDER BY a.localization_score DESC NULLS LAST, s.discovered_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = db.execute(query, params).fetchall()
    db.close()
    return {"services": [dict(r) for r in rows], "count": len(rows)}


@app.get("/api/report/{service_id}")
def get_report(service_id: int):
    """서비스 상세 분석 보고서"""
    db = get_db()
    svc = db.execute("SELECT * FROM discovered_services WHERE id=?", (service_id,)).fetchone()
    if not svc:
        db.close()
        raise HTTPException(404, "Service not found")

    report = db.execute("SELECT * FROM analysis_reports WHERE service_id=?", (service_id,)).fetchone()
    db.close()

    if not report:
        return {"service": dict(svc), "report": None, "message": "아직 분석되지 않았습니다."}

    r = dict(report)
    # JSON 필드 파싱
    for field in ["required_korean_apis", "template_code"]:
        if r.get(field) and isinstance(r[field], str):
            try:
                r[field] = json.loads(r[field])
            except json.JSONDecodeError:
                pass

    return {"service": dict(svc), "report": r}


@app.get("/api/apis")
def list_korean_apis(category: str = Query(None)):
    """국내 API 레퍼런스"""
    db = get_db()
    if category:
        rows = db.execute(
            "SELECT * FROM korean_apis WHERE category=? ORDER BY name", (category,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM korean_apis ORDER BY category, name").fetchall()
    db.close()
    return {"apis": [dict(r) for r in rows]}


@app.get("/api/sources")
def get_sources():
    """소스별 통계"""
    db = get_db()
    rows = db.execute(
        "SELECT source, COUNT(*) as count FROM discovered_services GROUP BY source ORDER BY count DESC"
    ).fetchall()
    db.close()
    return {"sources": [dict(r) for r in rows]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8733, reload=True)
