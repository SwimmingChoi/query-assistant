"""safety.validate_sql() 회귀 검증 스크립트.

사용:
    cd backend && python scripts/try_safety.py

unittest 등 테스트 프레임워크 의존성 없이 케이스 매트릭스를 돌려
정상 통과/차단 SQL 의 분류가 의도대로인지 확인한다.

종료 코드:
    0 — 모든 케이스 기대대로
    1 — 하나 이상 불일치
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.query_assistant.safety import SafetyViolation, validate_sql  # noqa: E402


# (description, sql, should_pass)
CASES: list[tuple[str, str, bool]] = [
    # --- 통과 기대 -----------------------------------------------------------
    (
        "Oracle few-shot 정상 쿼리",
        "SELECT COUNT(*) AS \"신규계약건수\" FROM CONTRACT "
        "WHERE REG_DATE >= TRUNC(ADD_MONTHS(SYSDATE,-1),'MM');",
        True,
    ),
    (
        "MSSQL TOP + N'...' 문자열",
        "SELECT TOP 10 [신규계약건수]=COUNT(*) FROM CONTRACT "
        "WHERE REGION=N'강원도';",
        True,
    ),
    (
        "Greenplum LIMIT",
        "SELECT REGION, COUNT(*) FROM CONTRACT GROUP BY REGION LIMIT 100;",
        True,
    ),
    (
        "WITH CTE → SELECT (정상 분석 쿼리)",
        "WITH last_month AS (SELECT * FROM CONTRACT WHERE REG_DATE >= "
        "TRUNC(ADD_MONTHS(SYSDATE,-1),'MM')) SELECT REGION, COUNT(*) "
        "FROM last_month GROUP BY REGION;",
        True,
    ),
    (
        "WITH CTE 중첩",
        "WITH a AS (WITH b AS (SELECT 1 FROM DUAL) SELECT * FROM b) "
        "SELECT * FROM a;",
        True,
    ),
    (
        "윈도우 함수 (ROW_NUMBER OVER PARTITION BY)",
        "SELECT POL_NO, ROW_NUMBER() OVER (PARTITION BY REGION ORDER BY REG_DATE) AS rn "
        "FROM CONTRACT;",
        True,
    ),
    (
        "문자열 리터럴 안에 키워드 (DROP)",
        "SELECT 'DROP TABLE x' AS MSG FROM DUAL;",
        True,
    ),
    (
        "Oracle Q-quote 안에 키워드",
        "SELECT q'[ DROP TABLE x ]' AS MEMO FROM DUAL;",
        True,
    ),
    (
        "Oracle NQ-quote + 한글",
        "SELECT nq'<강원도 INSERT 신규>' AS MEMO FROM DUAL;",
        True,
    ),
    (
        "PG dollar-quote 안에 키워드",
        "SELECT $$ DROP TABLE x $$ AS MEMO;",
        True,
    ),
    (
        "PG named dollar-quote 안에 키워드",
        "SELECT $tag$ INSERT INTO t VALUES (1) $tag$ AS MEMO;",
        True,
    ),
    (
        "Oracle 옵티마이저 힌트 안에 키워드 (블록 주석)",
        "SELECT /*+ INDEX(t IDX_DROP_FLAG) */ * FROM CONTRACT t;",
        True,
    ),
    (
        "큰따옴표 식별자 안에 키워드 (INSERT_DATE)",
        'SELECT "INSERT_DATE" FROM AUDIT_LOG WHERE ROWNUM <= 10;',
        True,
    ),
    (
        "대괄호 식별자 안에 키워드 (DELETE_FLAG, MSSQL)",
        "SELECT [DELETE_FLAG] FROM dbo.CONTRACT WHERE [DELETE_FLAG]=0;",
        True,
    ),
    (
        "라인 주석 후 정상 SELECT",
        "-- 지난달 강원도 분석\nSELECT COUNT(*) FROM CONTRACT;",
        True,
    ),
    (
        "블록 주석 후 정상 SELECT",
        "/* by query-assistant */ SELECT COUNT(*) FROM CONTRACT;",
        True,
    ),
    (
        "이중 작은따옴표 이스케이프 (It''s)",
        "SELECT MEMO FROM CONTRACT WHERE MEMO = 'It''s ok';",
        True,
    ),
    (
        "컬럼명에 키워드 단어가 포함 (INSERT_DATE, DELETE_FLAG)",
        "SELECT INSERT_DATE, DELETE_FLAG FROM CONTRACT;",
        True,
    ),
    (
        "세미콜론 없음 (생성기가 가끔 누락)",
        "SELECT 1 FROM DUAL",
        True,
    ),
    # --- 차단 기대 -----------------------------------------------------------
    ("INSERT INTO 차단",        "INSERT INTO CONTRACT VALUES (1, 2);", False),
    ("UPDATE 차단",             "UPDATE CONTRACT SET STATUS='X' WHERE POL_NO='A';", False),
    ("DELETE 차단",             "DELETE FROM CONTRACT WHERE POL_NO='A';", False),
    ("DROP TABLE 차단",         "DROP TABLE CONTRACT;", False),
    ("CREATE TABLE 차단",       "CREATE TABLE t AS SELECT * FROM CONTRACT;", False),
    ("MERGE 차단",              "MERGE INTO t USING s ON (t.id=s.id) WHEN MATCHED THEN UPDATE SET t.x=s.x;", False),
    ("TRUNCATE 차단",           "TRUNCATE TABLE CONTRACT;", False),
    ("ALTER 차단",              "ALTER TABLE CONTRACT ADD x INT;", False),
    ("GRANT 차단",              "GRANT SELECT ON CONTRACT TO PUBLIC;", False),
    ("REVOKE 차단",             "REVOKE SELECT ON CONTRACT FROM u;", False),
    ("EXEC 프로시저 차단",      "EXEC sp_dangerous;", False),
    ("CALL 프로시저 차단",      "CALL audit_purge();", False),
    ("DO 익명 블록 차단 (PG)",  "DO $$ BEGIN PERFORM 1; END $$;", False),
    ("BEGIN…END 블록 차단",     "BEGIN NULL; END;", False),
    ("DECLARE T-SQL 차단",      "DECLARE @x INT; SELECT @x;", False),
    ("COMMIT 차단",             "COMMIT;", False),
    ("ROLLBACK 차단",           "ROLLBACK;", False),
    ("SELECT … INTO 새 테이블 차단", "SELECT * INTO NEW_T FROM CONTRACT;", False),
    ("다중 문장: SELECT; DROP", "SELECT 1 FROM DUAL; DROP TABLE x;", False),
    ("다중 문장: SELECT; SELECT","SELECT 1; SELECT 2;", False),
    ("라인 주석으로 위장한 다중 문장",
     "SELECT 1; -- end\nDROP TABLE x;", False),
    ("블록 주석으로 위장한 키워드",
     "/* harmless */ DROP TABLE x;", False),
    ("WITH CTE 안에 INSERT 합성 우회",
     "WITH x AS (SELECT 1) INSERT INTO t SELECT * FROM x;", False),
    ("RETURNING 합성 우회 (PG DELETE 차단으로 잡힘)",
     "SELECT * FROM (DELETE FROM t WHERE x=1 RETURNING *) sub;", False),
    ("빈 문자열",               "", False),
    ("공백만",                  "   \n\t  ", False),
    ("세미콜론만",              ";;;", False),
    ("주석만",                  "-- only comment\n/* and block */", False),
    ("LOCK TABLE 차단",         "LOCK TABLE CONTRACT IN EXCLUSIVE MODE;", False),
    ("COPY (PG 서버측 파일 I/O)",
     "COPY CONTRACT TO '/tmp/leak.csv';", False),
    ("VACUUM (PG/Greenplum 운영)",
     "VACUUM ANALYZE CONTRACT;", False),
    ("ANALYZE (PG/Greenplum 운영)",
     "ANALYZE CONTRACT;", False),
    ("REINDEX (PG/Greenplum 운영)",
     "REINDEX TABLE CONTRACT;", False),
    ("CLUSTER (PG/Greenplum 운영)",
     "CLUSTER CONTRACT USING idx_pol;", False),
    ("REFRESH MATERIALIZED VIEW",
     "REFRESH MATERIALIZED VIEW mv_contract;", False),
    ("BACKUP DATABASE (MSSQL)",
     "BACKUP DATABASE HW TO DISK='X:\\hw.bak';", False),
    ("RESTORE DATABASE (MSSQL)",
     "RESTORE DATABASE HW FROM DISK='X:\\hw.bak';", False),
    ("SHUTDOWN (Oracle)",       "SHUTDOWN IMMEDIATE;", False),
    ("KILL session (MSSQL)",    "KILL 52;", False),
    ("SET ROLE 권한 전환",      "SET ROLE admin;", False),
    ("RESET 세션",              "RESET ALL;", False),
    ("DISCARD ALL (PG)",        "DISCARD ALL;", False),
    ("유니코드 ZWSP 우회: SELECT 1\\u200B; DROP",
     "SELECT 1 FROM DUAL;​ DROP TABLE x;", False),
    ("유니코드 NBSP 우회: SELECT;\\u00A0DROP",
     "SELECT 1 FROM DUAL; DROP TABLE x;", False),
    ("길이 초과 (50_000 바이트 + 1)",
     "SELECT 1 FROM DUAL -- " + ("x" * 50_000), False),
]


def run() -> int:
    fails: list[tuple[str, str]] = []
    print(f"{'기대':<4} | {'결과':<4} | 설명")
    print("-" * 80)

    for desc, sql, should_pass in CASES:
        try:
            validate_sql(sql)
            actual_pass, err = True, ""
        except SafetyViolation as exc:
            actual_pass, err = False, str(exc)

        ok = actual_pass == should_pass
        expected = "PASS" if should_pass else "DENY"
        actual = "PASS" if actual_pass else "DENY"
        mark = "✓" if ok else "✗"
        detail = "" if ok else f"  ← MISMATCH (msg={err!r})"
        print(f"{expected:<4} | {actual:<4} | {mark} {desc}{detail}")
        if not ok:
            fails.append((desc, err))

    print("-" * 80)
    total = len(CASES)
    if fails:
        print(f"\n[FAIL] {len(fails)}/{total} 케이스 불일치:")
        for d, msg in fails:
            print(f"  · {d}  (msg={msg!r})")
        return 1
    print(f"\n[OK] {total}/{total} 케이스 통과")
    return 0


if __name__ == "__main__":
    sys.exit(run())
