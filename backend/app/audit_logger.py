"""감사 로그 — SQLite 기록 모듈.

설계 의도:
- Python 내장 sqlite3 사용 (추가 의존성 없음).
- `log_query` 는 동기 함수. FastAPI BackgroundTasks 가 def 함수를
  자동으로 스레드풀에서 실행하므로 이벤트 루프를 차단하지 않는다.
- 로그 기록 실패는 예외를 삼키고 log.exception 으로만 기록.
  감사 로그 오류가 실제 응답을 깨선 안 된다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS query_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    dbms        TEXT    NOT NULL,
    question    TEXT    NOT NULL,
    schema_text TEXT    NOT NULL,
    sql         TEXT,
    assumptions TEXT,
    warnings    TEXT,
    success     INTEGER NOT NULL DEFAULT 1,
    error_type  TEXT,
    error_msg   TEXT,
    duration_ms INTEGER
)
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(_DDL)
        conn.commit()
    log.info("audit DB 초기화: %s", db_path)


def log_query(
    db_path: Path,
    *,
    dbms: str,
    question: str,
    schema_text: str,
    sql: str | None,
    assumptions: list[str],
    warnings: list[str],
    success: bool,
    error_type: str | None = None,
    error_msg: str | None = None,
    duration_ms: int | None = None,
) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO query_logs
                    (created_at, dbms, question, schema_text, sql,
                     assumptions, warnings, success, error_type, error_msg, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    dbms,
                    question,
                    schema_text,
                    sql,
                    json.dumps(assumptions, ensure_ascii=False),
                    json.dumps(warnings, ensure_ascii=False),
                    1 if success else 0,
                    error_type,
                    error_msg,
                    duration_ms,
                ),
            )
            conn.commit()
    except Exception:
        log.exception("audit 로그 기록 실패")
