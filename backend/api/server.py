"""KLD FastAPI Server"""
import os, json
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.db import get_db, init_db

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "static")

app = FastAPI(title="KLD", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    fp = os.path.join(STATIC_DIR, "landing.html")
    return open(fp).read() if os.path.exists(fp) else HTMLResponse("<h1>KLD</h1>")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    fp = os.path.join(STATIC_DIR, "index.html")
    return open(fp).read() if os.path.exists(fp) else HTMLResponse("<h1>Not found</h1>", 404)

@app.get("/api/stats")
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM discovered_services").fetchone()[0]
    analyzed = db.execute("SELECT COUNT(*) FROM analysis_reports WHERE is_saas IS NULL OR is_saas = 1").fetchone()[0]
    high = db.execute("SELECT COUNT(*) FROM analysis_reports WHERE localization_score >= 70 AND (is_saas IS NULL OR is_saas = 1)").fetchone()[0]
    db.close()
    return {"total_services": total, "total_analyzed": analyzed, "high_potential_count": high}

@app.get("/api/services")
def list_services(limit: int = Query(50, ge=1, le=200), offset: int = Query(0), source: str = Query(None), min_score: int = Query(0)):
    db = get_db()
    conds, params = ["(a.is_saas IS NULL OR a.is_saas = 1)"], []
    if source: conds.append("s.source = ?"); params.append(source)
    if min_score > 0: conds.append("a.localization_score >= ?"); params.append(min_score)
    where = " AND ".join(conds)
    q = f"SELECT s.*, a.localization_score, a.confidence, a.upside, a.boldness, a.summary_ko, a.localization_reason, a.free_tier, a.created_at as analyzed_at FROM discovered_services s LEFT JOIN analysis_reports a ON s.id = a.service_id WHERE {where} ORDER BY a.localization_score DESC NULLS LAST LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = db.execute(q, params).fetchall()
    db.close()
    return {"services": [dict(r) for r in rows], "count": len(rows)}

@app.get("/api/report/{service_id}")
def get_report(service_id: int):
    db = get_db()
    svc = db.execute("SELECT * FROM discovered_services WHERE id=?", (service_id,)).fetchone()
    if not svc: db.close(); raise HTTPException(404)
    report = db.execute("SELECT * FROM analysis_reports WHERE service_id=?", (service_id,)).fetchone()
    db.close()
    if not report: return {"service": dict(svc), "report": None}
    return {"service": dict(svc), "report": dict(report)}

@app.get("/api/sources")
def get_sources():
    db = get_db()
    rows = db.execute("SELECT source, COUNT(*) as count FROM discovered_services GROUP BY source ORDER BY count DESC").fetchall()
    db.close()
    return {"sources": [dict(r) for r in rows]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8733, reload=True)
