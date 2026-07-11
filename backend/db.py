"""KLD 데이터베이스 초기화 및 연결"""
import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", "data/kld.db")


def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS discovered_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        description TEXT,
        source TEXT NOT NULL,
        source_url TEXT,
        revenue_estimate TEXT,
        monthly_traffic TEXT,
        category TEXT DEFAULT 'unknown',
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(name, url)
    );
    CREATE TABLE IF NOT EXISTS analysis_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER NOT NULL,
        localization_score INTEGER CHECK(localization_score BETWEEN 0 AND 100),
        summary_ko TEXT,
        localization_reason TEXT,
        required_korean_apis TEXT,
        regulatory_risks TEXT,
        competitor_analysis TEXT,
        estimated_dev_time TEXT,
        monetization_ko TEXT,
        template_code TEXT,
        free_tier INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(service_id) REFERENCES discovered_services(id)
    );
    CREATE TABLE IF NOT EXISTS korean_apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT,
        description TEXT,
        docs_url TEXT,
        pricing_info TEXT
    );
    CREATE TABLE IF NOT EXISTS crawl_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        items_found INTEGER DEFAULT 0,
        new_items INTEGER DEFAULT 0,
        status TEXT,
        error_msg TEXT,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()
