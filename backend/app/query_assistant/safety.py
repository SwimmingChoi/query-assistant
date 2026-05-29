"""LLM 출력 SQL의 사후 안전 검증.

설계 의도:
- LLM 출력은 신뢰 경계 밖. 시스템 프롬프트(`prompts.py` 절대 규칙 1)가
  SELECT 외 구문 금지를 가르치지만 100% 신뢰할 수 없으므로 응답 직전
  사후 검증을 한 지점(`router.generate`)에서 수행한다.
- 외부 의존성(`sqlparse` 등) 없이 정규식 기반 deny-list 방식.
  보수적으로 차단 — false negative 보다 false positive 를 선호.
  현업이 차단당하면 즉시 우리에게 보고할 수 있지만, DROP 이 통과되면 사고.

차단 항목:
1. SQL 길이 초과 (입력 폭주 방어, 정규식 절대 시간 가드).
2. 다중 문장 (`SELECT 1; DROP TABLE x`) — 주석·문자열·인용 식별자 안에 숨겨도 차단.
3. SELECT/WITH 외 시작 (INSERT, UPDATE, DELETE, MERGE, CREATE, DROP, ALTER, DO 등).
4. 본문 안 DML/DDL/권한/실행/운영 키워드 (`WITH x AS (...) INSERT INTO ...` 같은 합성 우회).
5. SELECT INTO (MSSQL — SELECT 결과로 새 테이블 생성).
6. 운영 명령 (VACUUM, ANALYZE, COPY, BACKUP/RESTORE, SHUTDOWN, KILL 등).

정제 단계 (검사용 사본만):
- 유니코드 NFKC 정규화 + 비ASCII 공백류(NBSP/ZWSP 등) → ASCII space.
- 블록 주석 `/* */`, 라인 주석 `--`.
- 작은따옴표 문자열 (이중 작은따옴표 이스케이프 포함).
- Oracle Q-quote `q'[...]'` `q'(...)'` `q'{...}'` `q'<...>'` `q'X...X'`.
- PostgreSQL/Greenplum dollar-quoted `$$...$$`, `$tag$...$tag$`.
- 큰따옴표 식별자, 대괄호 식별자.

**중요**: 예외 메시지에는 SQL 본문을 절대 포함하지 않는다 (키워드명/문장 수/카테고리만).
HTTP 응답 detail 과 감사 로그에 PII/스키마가 노출되는 것을 막기 위해서.

검증 통과 시 None, 위반 시 `SafetyViolation` 예외.
"""
from __future__ import annotations

import re
import unicodedata


class SafetyViolation(ValueError):
    """LLM 출력 SQL 이 사후 안전 검증을 통과하지 못함."""


# LLM 출력 길이 상한. 정규식은 ReDoS 안전(polynomial)이지만 절대 시간 가드.
# 4 DBMS 의 가장 긴 정상 케이스가 수 KB 수준이므로 50KB 는 충분히 여유.
_MAX_SQL_LEN = 50_000

# 비ASCII 공백류 (NBSP, ZWSP, 한글 IDEOGRAPHIC SPACE, BOM 등).
# `\b` 단어 경계는 ASCII 만 인식하므로, deny-list 매칭 전에 미리 ASCII space 로 치환.
_UNICODE_SPACES = re.compile(
    "[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]"
)

# --- 정제: 검사용 사본에서 노이즈 제거 ---

_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE = re.compile(r"--[^\n]*")
# 작은따옴표 문자열. 이중 작은따옴표('')는 SQL 이스케이프 → 안에 포함.
_STRING_LITERAL = re.compile(r"[Nn]?'(?:[^']|'')*'")
# Oracle/Tibero Q-quote.
# 짝 구분자: [], (), {}, <>. 임의 단일 문자 구분자: \s/괄호류 제외.
_Q_QUOTE = re.compile(
    r"[Nn]?[Qq]'(?:\[.*?\]|\(.*?\)|\{.*?\}|<.*?>|([^\s\[\]\(\)\{\}<>])[\s\S]*?\1)'",
    re.DOTALL,
)
# PostgreSQL/Greenplum dollar-quoted 문자열.
# 빈 태그(`$$..$$`)와 명명 태그(`$x$..$x$`)를 alternation 으로 분리 — Python re 는
# optional 그룹이 빈 매칭일 때 \1 이 None 이 되어 backreference 가 실패하므로 분리 필수.
_DOLLAR_QUOTE = re.compile(
    r"\$\$[\s\S]*?\$\$|\$([A-Za-z_][A-Za-z0-9_]*)\$[\s\S]*?\$\1\$",
    re.DOTALL,
)
# 큰따옴표 식별자 (Oracle/Greenplum/Tibero), 대괄호 식별자 (MSSQL).
# 한국어 별칭(`AS "신규계약건수"`) 같은 케이스도 여기서 사라져 키워드 오탐 회피.
_DQ_IDENTIFIER = re.compile(r'"(?:[^"]|"")*"')
_BR_IDENTIFIER = re.compile(r"\[[^\]]*\]")

# --- 차단 키워드 ---
# 단어 경계(\b) 기준이라 컬럼명 `INSERT_DATE` 같은 식별자는 매칭되지 않음
# (언더스코어가 단어 문자라 \b 가 성립하지 않음).
_FORBIDDEN_KEYWORDS = (
    # DML
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "REPLACE",
    # DDL
    "CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME",
    # 권한
    "GRANT", "REVOKE",
    # 실행/블록
    "EXEC", "EXECUTE", "CALL", "DO",
    "BEGIN", "DECLARE",
    # 트랜잭션
    "COMMIT", "ROLLBACK", "SAVEPOINT",
    # 새 테이블 생성 (MSSQL SELECT INTO)
    "INTO",
    # 운영 명령 (Greenplum/PG/Oracle/MSSQL)
    "LOCK", "VACUUM", "ANALYZE", "REINDEX", "CLUSTER", "REFRESH",
    "COPY",                       # PG/Greenplum 서버측 파일 I/O — 보안 위험
    "BACKUP", "RESTORE",          # MSSQL
    "SHUTDOWN", "KILL",           # 인스턴스/세션 종료
    "SET", "RESET", "DISCARD",    # 세션 상태 전환
)
_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

_LEADING_TOKEN_RE = re.compile(r"^\s*([A-Za-z]+)")


def validate_sql(sql: str) -> None:
    """LLM 이 생성한 SQL 의 사후 안전성 검증.

    위반 시 `SafetyViolation`. 안전하면 None 반환.
    예외 메시지에는 SQL 본문을 포함하지 않는다.
    """
    if not sql or not sql.strip():
        raise SafetyViolation("빈 SQL")

    if len(sql) > _MAX_SQL_LEN:
        raise SafetyViolation(
            f"SQL 길이 초과 ({len(sql)} > {_MAX_SQL_LEN} 바이트)"
        )

    # 0. 유니코드 정규화 + 비ASCII 공백 치환 (ZWSP/NBSP 우회 차단)
    normalized = unicodedata.normalize("NFKC", sql)
    normalized = _UNICODE_SPACES.sub(" ", normalized)

    # 1. 정제: 주석 → 리터럴(Q-quote/dollar-quote/일반) → 인용 식별자
    #    Q-quote 와 dollar-quote 를 일반 작은따옴표 정제보다 먼저 적용해야
    #    내부에 작은따옴표가 있어도 안전하게 통째로 제거됨.
    sanitized = _COMMENT_BLOCK.sub(" ", normalized)
    sanitized = _COMMENT_LINE.sub(" ", sanitized)
    sanitized = _Q_QUOTE.sub(" ", sanitized)
    sanitized = _DOLLAR_QUOTE.sub(" ", sanitized)
    sanitized = _STRING_LITERAL.sub(" ", sanitized)
    sanitized = _DQ_IDENTIFIER.sub(" ", sanitized)
    sanitized = _BR_IDENTIFIER.sub(" ", sanitized)
    sanitized = sanitized.strip()

    # 2. 다중 문장 검사: 의미 있는 세미콜론 분할 결과가 2개 이상이면 거부
    statements = [s for s in sanitized.split(";") if s.strip()]
    if len(statements) > 1:
        raise SafetyViolation(
            f"다중 문장 금지 (감지된 문장 수: {len(statements)})"
        )
    if not statements:
        raise SafetyViolation("실행 가능한 문장이 없음 (주석/공백뿐)")

    body = statements[0]

    # 3. 첫 토큰: SELECT 또는 WITH 만 허용 (EXPLAIN/SHOW/DESCRIBE 도 거부)
    m = _LEADING_TOKEN_RE.match(body)
    if not m:
        raise SafetyViolation("SQL 시작 토큰을 찾을 수 없음")
    leading = m.group(1).upper()
    if leading not in {"SELECT", "WITH"}:
        raise SafetyViolation(
            f"SELECT 외 구문 금지 (시작 토큰: {leading})"
        )

    # 4. 본문 안 위험 키워드 (WITH 절 안에 숨긴 INSERT 등 합성 우회 차단)
    forbidden = _FORBIDDEN_RE.search(body)
    if forbidden:
        raise SafetyViolation(
            f"금지 키워드 감지: {forbidden.group(1).upper()}"
        )
