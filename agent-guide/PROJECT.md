---
name: project
description: HWGI Query Assistant 프로젝트 핵심 요약. 프로젝트 구조와 기술 스택 파악용.
last-updated: 2026-05-22
---

# 프로젝트 개요

> 한화손해보험 사내에서 사용하는 4종 DBMS(Oracle, MSSQL, Greenplum, Tibero)를 통합 지원하는 **자연어 → SQL 생성 도우미**. SQL을 모르는 현업이 한국어 질문을 입력하면 선택한 DBMS의 방언으로 실행 가능한 SQL을 생성·복사·다운로드한다. PoC는 OpenAI 기반, 최종은 사내 vLLM(`Gemma-4-26B-A4B-it`) 전환.

---

## TL;DR

| 항목 | 내용 |
|------|------|
| **프로젝트** | HWGI Query Assistant |
| **목적** | 보험 도메인 현업의 자연어 질문 → 4 DBMS 방언 SQL 자동 생성 |
| **기술 스택** | Python 3.13 · FastAPI · Pydantic 2 · httpx · SQLite(WAL) · Vanilla HTML/JS · OpenAI Chat (→ vLLM) |
| **MVP 기능** | DBMS 선택, 스키마 직접 입력, 자연어 → SQL 생성, SELECT-only 안전장치, 감사 로그, 복사/다운로드 |
| **작업 관리** | [TODO: 도구 선정 후 링크 추가 — 자매 프로젝트는 Notion 사용] |
| **상세 기획서** | [docs/PLAN.md](../docs/PLAN.md) |
| **자매 프로젝트** | [HWGI Translator](../../HWGI_Translator/) — 동일 인프라 패턴 재사용 |

---

## 프로젝트 구조

> 기획서 6.3 권장안. 본 구현 시작 시 확정.

```
HWGI_Query_Assistant/
├── docs/
│   └── PLAN.md                 # 기획서 (초안)
│
├── backend/                    # [TODO: 구현 예정]
│   ├── README.md
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── __init__.py
│       ├── main.py             # FastAPI 진입점, 정적 페이지 서빙
│       ├── config.py           # Pydantic Settings (.env 검증)
│       └── query_assistant/
│           ├── __init__.py
│           ├── router.py       # /api/query/* 라우트
│           ├── schemas.py      # GenerateRequest, GenerateResponse
│           ├── prompts.py      # DBMS별 시스템 프롬프트, few-shot
│           ├── dialects.py     # DBMS enum + 방언 메타데이터
│           ├── generator.py    # LLM 호출 + 가정/경고 파싱
│           └── safety.py       # SELECT-only 검증, DDL/DML 차단
│
├── hw-query.html               # [TODO: 단일 페이지 UI]
│
└── agent-guide/                # AI 에이전트용 가이드
    ├── GUIDE.md
    ├── PROJECT.md
    └── SESSION.md
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.13 |
| 웹 프레임워크 | FastAPI + uvicorn |
| 검증 | Pydantic 2 + pydantic-settings |
| HTTP 클라이언트 | httpx |
| 데이터베이스 | SQLite(WAL 모드) — 감사 로그·즐겨찾기. 운영은 PostgreSQL 예정 |
| 프론트엔드 | 단일 HTML + Vanilla JS + 임베디드 CSS (한화 디자인 토큰) |
| LLM (PoC) | OpenAI Chat Completions (`gpt-4o-mini` 등) |
| LLM (목표) | 사내 vLLM `gemma-4-26B-A4B-it` (Chat Completions 호환) |
| 대상 DBMS | Oracle, MSSQL, Greenplum, Tibero |
| 인프라 (목표) | 사내망 배포 — 자매 프로젝트의 AWS Private VPC 청사진 재사용 가능 |

---

## 핵심 파일

[TODO: 구현 후 핵심 파일 추가]

> 예정:
> - `backend/app/query_assistant/prompts.py` — DBMS별 방언 가이드(SYSDATE/GETDATE, ROWNUM/TOP/LIMIT 등) 시스템 프롬프트
> - `backend/app/query_assistant/safety.py` — SELECT-only 강제, 식별자 존재 검증
> - `backend/app/query_assistant/generator.py` — LLM 호출 · 환경변수(`BASE_URL`/`MODEL`)로 OpenAI ↔ vLLM 전환

---

## 빠른 시작

[TODO: 환경 설정 확정 후 작성]

> 자매 프로젝트(HWGI Translator) 패턴을 따를 예정:
> ```bash
> cd backend
> python -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> cp .env.example .env  # LLM_API_KEY 등 채우기
> uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
> ```

---

## 상세 참조

| 문서 | 내용 |
|------|------|
| [SESSION.md](SESSION.md) | 현재 상태, 세션 로그, 다음 작업 |
| [GUIDE.md](GUIDE.md) | 작업 원칙, 용어, 체크리스트 |
| [docs/PLAN.md](../docs/PLAN.md) | 기획서 (배경, MVP 범위, DBMS 방언, 로드맵, 리스크) |
| [HWGI_Translator](../../HWGI_Translator/) | 자매 프로젝트 (인프라 패턴·vLLM 전환 사례) |
