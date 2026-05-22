"""
DBMS 방언(Dialect) 메타데이터.

prompts.py가 참조하는 단일 소스. 각 DBMS의 핵심 문법 차이를 구조화해두고
시스템 프롬프트는 여기서 텍스트를 끌어다 조립한다.

방언 정보를 코드에 한 번만 정의하는 이유:
- 프롬프트와 후처리 검증(safety.py)이 동일 정보를 공유
- 새 DBMS 추가 시 한 곳만 수정
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DBMS(str, Enum):
    """지원하는 DBMS 4종."""

    ORACLE = "oracle"
    MSSQL = "mssql"
    GREENPLUM = "greenplum"
    TIBERO = "tibero"


@dataclass(frozen=True)
class DialectSpec:
    """DBMS 방언 핵심 차이 명세.

    LLM 시스템 프롬프트에 주입할 항목만 추림. 실행/드라이버 관련 정보는 포함하지 않음.
    """

    display_name: str
    current_timestamp: str
    paging: str
    string_concat: str
    null_coalesce: str
    identifier_quote: str
    date_diff_month: str
    date_add_month: str
    truncate_date: str
    notes: tuple[str, ...]


DIALECTS: dict[DBMS, DialectSpec] = {
    DBMS.ORACLE: DialectSpec(
        display_name="Oracle",
        current_timestamp="SYSDATE 또는 CURRENT_TIMESTAMP",
        paging="ROWNUM 또는 12c+ FETCH FIRST n ROWS ONLY",
        string_concat="|| 연산자 (예: 'A' || 'B')",
        null_coalesce="NVL(expr, default) / COALESCE(expr1, expr2, ...)",
        identifier_quote='큰따옴표("...") — 단, 대소문자 구분이 시작됨. 보통은 따옴표 없이 사용',
        date_diff_month="MONTHS_BETWEEN(date1, date2)",
        date_add_month="ADD_MONTHS(date, n)",
        truncate_date="TRUNC(date, 'MM') / TRUNC(date, 'DD')",
        notes=(
            "DATE 타입은 시·분·초 포함. 날짜만 비교하려면 TRUNC 필수.",
            "문자열 리터럴은 작은따옴표('...'). 작은따옴표 이스케이프는 '' (두 개).",
            "DUAL 가상 테이블 사용 가능 (예: SELECT SYSDATE FROM DUAL).",
        ),
    ),
    DBMS.MSSQL: DialectSpec(
        display_name="Microsoft SQL Server (MSSQL)",
        current_timestamp="GETDATE() 또는 SYSDATETIME() / CURRENT_TIMESTAMP",
        paging="TOP n (간단) 또는 ORDER BY ... OFFSET n ROWS FETCH NEXT m ROWS ONLY",
        string_concat="+ 연산자 또는 CONCAT(a, b, ...) — NULL 안전한 CONCAT 권장",
        null_coalesce="ISNULL(expr, default) / COALESCE(expr1, expr2, ...)",
        identifier_quote='대괄호([...]) 또는 큰따옴표("...") — 대괄호가 관용적',
        date_diff_month="DATEDIFF(month, start, end)",
        date_add_month="DATEADD(month, n, date)",
        truncate_date="DATEFROMPARTS / CAST(... AS DATE) / FORMAT(date,'yyyy-MM-01')",
        notes=(
            "DATE/DATETIME/DATETIME2 구분. 비교 시 타입 일치 권장.",
            "문자열 리터럴 N'...' 은 NVARCHAR. 한글 안전성을 위해 N 접두사 사용 권장.",
            "DUAL 같은 가상 테이블 없음. SELECT GETDATE() 만으로 가능.",
        ),
    ),
    DBMS.GREENPLUM: DialectSpec(
        display_name="Greenplum (PostgreSQL 기반 MPP)",
        current_timestamp="NOW() 또는 CURRENT_TIMESTAMP",
        paging="LIMIT n OFFSET m",
        string_concat="|| 연산자 또는 CONCAT(a, b, ...) — || 는 NULL 전파 주의",
        null_coalesce="COALESCE(expr1, expr2, ...) — NVL 미지원",
        identifier_quote='큰따옴표("...") — 미사용 시 자동 소문자화 주의',
        date_diff_month="EXTRACT(YEAR FROM age(end, start))*12 + EXTRACT(MONTH FROM age(end, start))",
        date_add_month="date + INTERVAL 'n month'",
        truncate_date="DATE_TRUNC('month', date) / DATE_TRUNC('day', date)",
        notes=(
            "분산 테이블이 많아 DISTRIBUTED BY 키와 무관한 조인은 비용 큼 (생성 시 주의 권고).",
            "대용량 집계용 DB. SELECT * 보다 필요한 컬럼 명시 + 적절한 WHERE 필수.",
            "GROUP BY 시 비집계 컬럼 모두 명시 필요.",
        ),
    ),
    DBMS.TIBERO: DialectSpec(
        display_name="Tibero (Oracle 호환 국산 DBMS)",
        current_timestamp="SYSDATE 또는 CURRENT_TIMESTAMP (Oracle 호환)",
        paging="ROWNUM (Oracle 호환). 일부 버전은 FETCH FIRST n ROWS ONLY 지원",
        string_concat="|| 연산자 (Oracle 호환)",
        null_coalesce="NVL(expr, default) / COALESCE(expr1, expr2, ...) (Oracle 호환)",
        identifier_quote='큰따옴표("...") (Oracle 호환)',
        date_diff_month="MONTHS_BETWEEN(date1, date2) (Oracle 호환)",
        date_add_month="ADD_MONTHS(date, n) (Oracle 호환)",
        truncate_date="TRUNC(date, 'MM') / TRUNC(date, 'DD') (Oracle 호환)",
        notes=(
            "기본적으로 Oracle 문법과 호환. Oracle 쿼리를 거의 그대로 사용 가능.",
            "버전에 따라 미지원 함수가 있을 수 있어 12c 미만 Oracle 호환 범위 권장.",
            "DUAL 가상 테이블 사용 가능 (Oracle 호환).",
        ),
    ),
}


def get_spec(dbms: DBMS) -> DialectSpec:
    return DIALECTS[dbms]
