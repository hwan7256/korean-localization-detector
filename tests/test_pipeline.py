"""KLD 통합 테스트"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from backend.api.server import app
from backend.db import init_db, get_db

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200


def test_dashboard():
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_stats():
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_services" in data
    assert "total_analyzed" in data
    assert "avg_localization_score" in data
    assert "high_potential_count" in data


def test_sources():
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    assert "sources" in resp.json()


def test_services_list():
    resp = client.get("/api/services?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert "count" in data


def test_korean_apis():
    resp = client.get("/api/apis")
    assert resp.status_code == 200
    apis = resp.json()["apis"]
    assert len(apis) >= 10


def test_report_404():
    resp = client.get("/api/report/99999")
    assert resp.status_code == 404


def test_db_tables():
    init_db()
    db = get_db()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "discovered_services" in table_names
    assert "analysis_reports" in table_names
    assert "korean_apis" in table_names
    assert "crawl_log" in table_names
    db.close()
