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
    """테이블 생성 + 마이그레이션"""
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
        score_performance REAL NOT NULL,
        value_proposition TEXT,
        friction_points TEXT,
        action_checklist TEXT,
        ab_test_suggestions TEXT,
        elements TEXT,
        confidence REAL DEFAULT 0,
        rule_based_performance REAL DEFAULT 0,
        calibration_applied INTEGER DEFAULT 0,
        performance_detail TEXT,
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

    # 마이그레이션: 기존 DB에 신규 컬럼 추가
    _migrate_schema(conn)

    conn.commit()
    conn.close()


def _migrate_schema(conn):
    """기존 DB에 누락된 컬럼 추가 (멱등적)"""
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(page_audits)").fetchall()}

    migrations = {
        "confidence": "ALTER TABLE page_audits ADD COLUMN confidence REAL DEFAULT 0",
        "rule_based_performance": "ALTER TABLE page_audits ADD COLUMN rule_based_performance REAL DEFAULT 0",
        "calibration_applied": "ALTER TABLE page_audits ADD COLUMN calibration_applied INTEGER DEFAULT 0",
        "performance_detail": "ALTER TABLE page_audits ADD COLUMN performance_detail TEXT",
    }

    for col, sql in migrations.items():
        if col not in existing_cols:
            try:
                conn.execute(sql)
                print(f"[마이그레이션] {col} 컬럼 추가 완료")
            except Exception as e:
                print(f"[마이그레이션] {col} 추가 실패: {e}")


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
