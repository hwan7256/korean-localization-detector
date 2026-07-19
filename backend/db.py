"""KLD 데이터베이스 초기화 및 연결"""
import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", "data/kld.db")


def get_db():
    """SQLite 연결 반환"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """테이블 생성"""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS page_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        target_audience TEXT,
        screenshot_path TEXT,
        score_overall INTEGER NOT NULL,
        score_clarity INTEGER NOT NULL,
        score_cta INTEGER NOT NULL,
        score_hierarchy INTEGER NOT NULL,
        score_social_proof INTEGER NOT NULL,
        score_performance INTEGER NOT NULL,
        value_proposition TEXT,
        friction_points TEXT,
        action_checklist TEXT,
        ab_test_suggestions TEXT,
        elements TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        status TEXT NOT NULL,
        error_msg TEXT,
        duration_sec REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
