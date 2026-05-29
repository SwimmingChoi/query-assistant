---
name: project
description: HWGI Query Assistant 프로젝트 핵심 요약. 프로젝트 구조와 기술 스택 파악용.
last-updated: 2026-05-28
---

# 프로젝트 개요

> 한화손해보험 사내에서 사용하는 4종 DBMS(Oracle, MSSQL, Greenplum, Tibero)를 통합 지원하는 **자연어 → SQL 생성 도우미**. SQL을 모르는 현업이 한국어 질문을 입력하면 선택한 DBMS의 방언으로 실행 가능한 SQL을 생성·복사·다운로드한다. PoC부터 사내 vLLM(`gemma-4-31B-it`, OpenAI Chat Completions 호환) 기본 사용, OpenAI 전환은 `.env` 교체만으로 가능.

---

## TL;DR

| 항목 | 내용 |
|------|------|
| **프로젝트** | HWGI Query Assistant |
| **목적** | 보험 도메인 현업의 자연어 질문 → 4 DBMS 방언 SQL 자동 생성 |
| **기술 스택** | Python 3.13 · FastAPI · Pydantic 2 · httpx · SQLite(WAL, 예정) · Vanilla HTML/JS/CSS · vLLM `gemma-4-31B-it` (OpenAI Chat 호환, 옵션 OpenAI) |
| **MVP 기능** | DBMS 선택, 스키마 직접 입력, 자연어 → SQL 생성, SELECT-only 사후 검증, 복사/다운로드. (감사 로그는 P1 대기) |
| **작업 관리** | [TODO: 도구 선정 후 링크 추가 — 자매 프로젝트는 Notion 사용] |
| **상세 기획서** | [docs/PLAN.md](../docs/PLAN.md) |
| **자매 프로젝트** | [HWGI Translator](../../HWGI_Translator/) — 동일 인프라 패턴 재사용 |

---

## 프로젝트 구조

> 2026-05-28 기준 실제 구조. backend P0/P1 + 프론트 UI 구현 완료.

```
HWGI_Query_Assistant/
├── README.md
├── docs/
│   └── PLAN.md                 # 기획서
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 진입점, lifespan(httpx client), /health, /static mount, GET /
│   │   ├── config.py           # Pydantic Settings (.env), PROJECT_ROOT
│   │   └── query_assistant/
│   │       ├── __init__.py
│   │       ├── router.py       # POST /api/query/generate (validate_sql 통합, 502 매핑)
│   │       ├── schemas.py      # GenerateRequest, GenerateResponse
│   │       ├── prompts.py      # DBMS별 시스템 프롬프트 + few-shot
│   │       ├── dialects.py     # DBMS enum + DialectSpec (방언 메타데이터)
│   │       ├── generator.py    # LLM 호출 + JSON 파싱 (httpx 외부 주입)
│   │       └── safety.py       # SELECT-only 사후 검증 (deny-list + 정제)
│   └── scripts/
│       ├── try_generate.py     # LLM 호출 단발 검증 (CLI)
│       └── try_safety.py       # safety 회귀 매트릭스 (64 케이스)
│
├── static/                     # /static 으로 mount, GET / → hw-query.html
│   ├── hw-query.html           # UI 셸 (의미적 마크업)
│   ├── hw-query.css            # 한화 디자인 토큰(3-Layer) + 컴포넌트
│   └── hw-query.js             # Vanilla JS (DBMS 선택·예시·생성·복사·다운로드)
│
└── agent-guide/                # AI 에이전트용 가이드
    ├── GUIDE.md
    ├── PROJECT.md
    └── SESSION.md
```

> 정적 자산은 `static/` 단일 디렉토리만 `/static` 으로 mount. `backend/`·`docs/`·`agent-guide/` 등은 노출되지 않는다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.13 |
| 웹 프레임워크 | FastAPI + uvicorn |
| 검증 | Pydantic 2 + pydantic-settings |
| HTTP 클라이언트 | httpx |
| 데이터베이스 | SQLite(WAL 모드, 예정) — 감사 로그·즐겨찾기. 운영은 PostgreSQL 예정 |
| 프론트엔드 | 분리 정적 자산 (`static/hw-query.{html,js,css}`) · Vanilla JS · 한화 디자인 토큰 3-Layer · 빌드 도구 없음 |
| LLM (메인) | 사내 vLLM `gemma-4-31B-it` (OpenAI Chat Completions 호환, 인증 불필요) — 상세: [`docs/VLLM_API_GUIDE.md`](../docs/VLLM_API_GUIDE.md) |
| LLM (옵션) | OpenAI Chat Completions (`gpt-4o-mini` 등) — `.env` 의 `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY` 만 교체 |
| 대상 DBMS | Oracle, MSSQL, Greenplum, Tibero |
| 인프라 (목표) | 사내망 배포 — 자매 프로젝트의 AWS Private VPC 청사진 재사용 가능 |

---

## 핵심 파일

요청 흐름(`POST /api/query/generate`) 기준 정독 순서:

| 파일 | 역할 |
|------|------|
| `backend/app/main.py` | FastAPI 진입점. `lifespan` 으로 `httpx.AsyncClient` 단일 인스턴스를 `app.state.http` 로 공유. `/static` mount, `GET /` → `static/hw-query.html`. |
| `backend/app/query_assistant/router.py` | `POST /api/query/generate` 라우트. `generate_sql()` 호출 직후 `validate_sql()` 로 사후 검증. `GeneratorError`·`SafetyViolation` 모두 502 로 매핑. |
| `backend/app/query_assistant/schemas.py` | `GenerateRequest` (`dbms`/`schema_text`/`question`), `GenerateResponse` (`sql`/`assumptions`/`warnings`). |
| `backend/app/query_assistant/prompts.py` | DBMS 4종 방언 시스템 프롬프트. `dialects.py` 의 `DialectSpec` 을 단일 소스로 조립. few-shot 예시 1건/DBMS 포함. |
| `backend/app/query_assistant/dialects.py` | `DBMS` enum + `DialectSpec` (current_timestamp/paging/string_concat/null_coalesce/identifier_quote/date_diff_month 등). prompts·safety 가 공유. |
| `backend/app/query_assistant/generator.py` | OpenAI Chat Completions 호환 호출. JSON 모드 + 코드블록 fallback 파싱. `BASE_URL`/`MODEL` 환경변수로 OpenAI ↔ vLLM 전환. |
| `backend/app/query_assistant/safety.py` | LLM 출력 사후 검증. 정제(주석·문자열·Q-quote·dollar-quote·인용 식별자·유니코드 공백) → 다중 문장 차단 → SELECT/WITH 화이트리스트 → 운영 키워드 deny-list. 50KB 길이 가드. |
| `backend/app/config.py` | `Settings` (pydantic-settings). `PROJECT_ROOT` 도 여기서 정의. `get_settings()` 는 `lru_cache`. |
| `static/hw-query.js` | 프론트 로직. DBMS 4종 예시 스키마, `/health`/`/api/query/generate` 호출, 422/502/network 분기, clipboard·다운로드. |

---

## 빠른 시작

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # LLM_API_KEY 등 채우기 (사내 vLLM은 키 생략 가능)
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

접속:
- **UI**: http://localhost:8090/
- **헬스**: http://localhost:8090/health
- **API 문서**: http://localhost:8090/docs

회귀·검증 스크립트:
```bash
python scripts/try_safety.py        # safety 64 케이스 매트릭스
python scripts/try_generate.py      # LLM 호출 단발 검증 (LLM_API_KEY 필요)
python scripts/try_generate.py --dbms oracle --question "지난달 강원도 신규 계약"
```

---

## 상세 참조

| 문서 | 내용 |
|------|------|
| [SESSION.md](SESSION.md) | 현재 상태, 세션 로그, 다음 작업 |
| [GUIDE.md](GUIDE.md) | 작업 원칙, 용어, 체크리스트 |
| [docs/PLAN.md](../docs/PLAN.md) | 기획서 (배경, MVP 범위, DBMS 방언, 로드맵, 리스크) |
| [HWGI_Translator](../../HWGI_Translator/) | 자매 프로젝트 (인프라 패턴·vLLM 전환 사례) |
