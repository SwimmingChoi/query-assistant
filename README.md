# HWGI Query Assistant

> 보험 도메인 현업을 위한 자연어 → SQL 생성 도우미. 사내 4종 DBMS(Oracle / MSSQL / Greenplum / Tibero) 방언을 통합 지원합니다.

SQL 지식이 없어도 한국어로 데이터 조회 질문을 입력하면, 선택한 DBMS 방언으로 실행 가능한 **SELECT 문**을 생성·복사·다운로드할 수 있도록 돕는 사내 PoC 입니다.

---

## 주요 기능

- **자연어 → SQL 변환 (Text-to-SQL)** — OpenAI 호환 LLM 기반
- **4 DBMS 방언 통합 지원** — Oracle / MSSQL / Greenplum / Tibero
- **사용자 입력 스키마 기반** — 별도 DBMS 직접 연동 없이 사용자가 테이블·컬럼 정보를 직접 제공 (추후 자동 수집 예정)
- **안전장치** — SELECT 외 구문 차단, 사용자 입력 스키마 외 식별자 사용 금지
- **LLM 백엔드 토글** — OpenAI(PoC) ↔ 사내 vLLM 환경변수 1줄 교체

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.10+ |
| 웹 프레임워크 | FastAPI + uvicorn |
| 검증 | Pydantic 2 + pydantic-settings |
| HTTP 클라이언트 | httpx |
| 데이터베이스 | SQLite (감사 로그) |
| LLM (PoC) | OpenAI Chat Completions |
| LLM (목표) | 사내 vLLM (Chat Completions 호환) |
| 프론트엔드 (예정) | 단일 HTML + Vanilla JS |

---

## 빠른 시작

### 1. 의존성 설치

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 LLM_API_KEY 를 채워주세요
```

`.env` 핵심 항목:

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
```

사내 vLLM 으로 전환할 때:

```env
LLM_BASE_URL=http://<vllm-host>:<port>/v1
LLM_MODEL=<사내 모델명>
LLM_API_KEY=
```

### 3. LLM 호출 검증 (CLI)

```bash
# 4 DBMS 모두 자동 실행 (샘플 질문)
python scripts/try_generate.py

# 단일 DBMS + 질문 직접 지정
python scripts/try_generate.py --dbms oracle \
  --question "지난달 강원도에서 신규 계약된 건수와 평균 보험료"
```

---

## 프로젝트 구조

```
HWGI_Query_Assistant/
├── README.md
├── docs/
│   └── PLAN.md                     # 기획서 (배경 · MVP · 방언 · 로드맵)
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   ├── app/
│   │   ├── config.py               # Pydantic Settings (.env 검증)
│   │   └── query_assistant/
│   │       ├── dialects.py         # 4 DBMS 방언 메타데이터
│   │       ├── prompts.py          # 시스템·사용자 프롬프트 조립
│   │       ├── schemas.py          # Request / Response Pydantic 모델
│   │       └── generator.py        # LLM 호출 + JSON 파싱
│   └── scripts/
│       └── try_generate.py         # LLM 호출 검증 CLI
│
└── agent-guide/                    # AI 에이전트 협업용 가이드
    ├── GUIDE.md
    ├── PROJECT.md
    └── SESSION.md
```

---

## DBMS 방언 지원 범위

각 DBMS의 핵심 문법 차이를 시스템 프롬프트에 주입합니다.

| 영역 | Oracle | MSSQL | Greenplum | Tibero |
|------|--------|-------|-----------|--------|
| 현재 시각 | `SYSDATE` | `GETDATE()` | `NOW()` | `SYSDATE` |
| 페이징 | `ROWNUM` / `FETCH FIRST` | `TOP` / `OFFSET` | `LIMIT OFFSET` | `ROWNUM` |
| 문자열 연결 | `\|\|` | `+` / `CONCAT` | `\|\|` | `\|\|` |
| NULL 처리 | `NVL` / `COALESCE` | `ISNULL` / `COALESCE` | `COALESCE` | `NVL` |
| 식별자 인용 | `"..."` | `[...]` | `"..."` | `"..."` |
| 월 차이 | `MONTHS_BETWEEN` | `DATEDIFF(month,...)` | `EXTRACT + age()` | `MONTHS_BETWEEN` |

세부 사항은 [`backend/app/query_assistant/dialects.py`](backend/app/query_assistant/dialects.py) 참고.

---

## 보안 / 운영 원칙

- **시크릿 비커밋**: `.env` 는 `.gitignore` 에 포함. API 키는 절대 커밋하지 않습니다.
- **실 데이터 외부 송신 금지**: LLM 호출 시 사용자가 입력한 **스키마 텍스트·자연어 질문**만 전송됩니다. 실제 계약자/주민번호/금액 등은 송신하지 않도록 시스템 프롬프트로 강제합니다.
- **SELECT 전용**: 생성 SQL 은 SELECT 한정. INSERT / UPDATE / DELETE / DDL 은 차단합니다.
- **감사 로그**: 모든 요청·응답을 SQLite 에 기록 (예정).

---

## 로드맵

| Phase | 내용 |
|-------|------|
| **Phase 1 — MVP** (진행 중) | 4 DBMS 방언 지원, 사용자 직접 스키마 입력, OpenAI 기반 |
| **Phase 2 — 정확도 강화** | 보험 도메인 용어집, 즐겨찾기/히스토리, 피드백 수집 |
| **Phase 3 — DBMS 연동** | 읽기 전용 계정으로 스키마 자동 수집, 메타데이터 캐싱 |
| **Phase 4 — vLLM 전환 & 사내 배포** | 사내 vLLM 엔드포인트 교체, 감사 로그 / 권한 강화 |

상세는 [`docs/PLAN.md`](docs/PLAN.md) 참고.

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [`docs/PLAN.md`](docs/PLAN.md) | 기획서 (배경 · MVP · 방언 · 로드맵 · 리스크 · 검증 방안) |
| [`agent-guide/GUIDE.md`](agent-guide/GUIDE.md) | AI 에이전트 협업 원칙 · 도메인 용어집 |
| [`agent-guide/PROJECT.md`](agent-guide/PROJECT.md) | 프로젝트 개요 · 기술 스택 · 권장 구조 |
| [`agent-guide/SESSION.md`](agent-guide/SESSION.md) | 현재 세션 상태 · 다음 작업 |
