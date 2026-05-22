# 보험사 전사 쿼리 생성 도우미 — 기획서 (초안)

> 코드명(작업명): **HWGI Query Assistant** (가칭)
> 작성일: 2026-05-22
> 작성자: AI 협업 초안 (사용자 확정 필요)

---

## 1. 배경 (Context)

### 1.1 왜 만드는가
- 한화손해보험은 사내에서 **Oracle, MSSQL, Greenplum, Tibero** 등 4종의 DBMS를 혼용한다.
- 현업(영업/언더라이팅/계리/마케팅 등)은 데이터 조회 요구가 많지만 SQL을 직접 작성하지 못해 IT/데이터 부서에 의존한다.
- 이로 인해 (1) 데이터 부서의 운영 부담 증가, (2) 현업의 의사결정 속도 저하, (3) DBMS별 방언 차이로 인한 쿼리 재작성 비용이 반복 발생한다.

### 1.2 기존 자산
- **HWGI Translator**(현 프로젝트)에서 이미 FastAPI + OpenAI Chat 인프라와 사내 vLLM(`Gemma-4-26B-A4B-it`) 전환 경로를 검증해두었다.
- 같은 인프라 패턴(OpenAI 우선 → vLLM 전환)을 재사용하면 PoC를 빠르게 띄울 수 있다.

### 1.3 의도한 결과
- 현업이 한국어로 질문하면, **선택한 DBMS의 방언으로 실행 가능한 SQL**을 자동 생성해 복사/다운로드한다.
- 단계적으로 4개 DBMS 모두를 안정적으로 커버하고, 향후 사내 DBMS 메타데이터 연동·도메인 용어집 결합으로 정확도를 높인다.

---

## 2. 사용자 결정 사항 (확정)

| 항목 | 결정 | 비고 |
|------|------|------|
| 주 사용자 | **현업 (비개발자)** | SQL 지식이 거의 없는 사용자 중심 UX |
| 핵심 기능 | **자연어 → SQL 생성 (Text-to-SQL)** | 1차 스코프 한정 |
| DBMS 전략 | **통합 추상화** | 사용자는 DBMS만 선택, 내부에서 방언 분기 |
| LLM 백엔드 | **OpenAI 우선 (PoC) → vLLM 전환** | `BASE_URL`/`MODEL` 환경변수 토글 |
| 실행 범위 | **SQL만 생성 (복사·다운로드)** | DBMS 직접 실행 없음. 보안·구현 부담 최소 |
| 메타데이터 | **사용자 직접 입력 (MVP) → 추후 DBMS 자동 수집** | 컬럼·스키마를 사용자가 폼/텍스트로 입력 |
| MVP DBMS 범위 | **4개 동시 지원** | Oracle, MSSQL, Greenplum, Tibero. 사용자 입력 스키마 기반이라 동시 지원 부담 낮음 |
| 스키마 입력 UX | **자유 텍스트 + 예시 템플릿** | 다행 텍스트에리어 + DBMS별 예시 스니펫 제공. 붙여넣기 친화적 |
| 배포 환경 | **로컬 PoC 먼저** | 개발자 PC에서 안정화 → 사내 배포는 검증 후 결정 |
| OpenAI 사용 승인 | **자매 프로젝트(HWGI Translator) 승인 범위에 포함** | 보험 도메인 텍스트 처리 용도로 동일 간주. 보안팀 추가 고지만 진행 |
| 파일럿 사용자 그룹 | **계리/데이터 부서** | SQL 검증 능력 보유 → 정확도/안전성 광범위 검증에 적합 |

---

## 3. 사용자 시나리오

### 시나리오 A — 영업 담당자 (현업)
> "지난달 강원도 지역에서 신규 계약 건수와 평균 보험료를 알고 싶다."

1. 사용자는 화면에서 **DBMS = Oracle** 선택
2. **테이블/컬럼 정보**를 입력 (예: `CONTRACT(계약일, 지역, 보험료)`)
3. 자연어로 질문 입력 → "지역별 신규 계약 + 평균 보험료 (지난달)"
4. 시스템이 Oracle 방언 SQL을 생성, 주석으로 가정·해석을 명시
5. 사용자는 SQL을 복사해 사내 Toad/SQL Developer 등에서 실행

### 시나리오 B — 데이터 분석가 (보조 사용자)
> 같은 질문을 Greenplum 환경에서도 돌려보고 싶다.

1. DBMS만 **Greenplum**으로 변경 후 동일 질문 재요청
2. `MONTHS_BETWEEN` 같은 Oracle 함수가 아닌 Greenplum 호환 함수로 자동 생성

---

## 4. MVP 범위 (Phase 1)

### 4.1 In Scope
- 단일 화면 웹 UI (`hw-query.html` 신규)
  - DBMS 선택 (Oracle / MSSQL / Greenplum / Tibero)
  - 스키마 입력 영역 (테이블·컬럼·간단 설명을 사용자가 직접 입력 — JSON 또는 가벼운 폼)
  - 자연어 질문 입력 영역
  - 생성된 SQL 출력 + **복사** / **.sql 다운로드** 버튼
  - 가정/주의사항 패널 (LLM이 추정한 컬럼 매핑, 모호한 부분 등)
- 백엔드 API
  - `POST /api/query/generate` — 입력: `{dbms, schema, question}` → 출력: `{sql, assumptions, warnings}`
  - `GET /health` — 설정/모델 확인
- DBMS 방언 처리
  - **통합 추상화 1단계**: 시스템 프롬프트에 DBMS별 방언 가이드(함수·페이징·문자열 처리)를 주입
  - 4종 모두 1차 지원 (사용자 입력 스키마이므로 메타데이터 의존 없음 → 동시 지원 부담이 낮음)
- 안전 장치
  - **읽기 전용 강제**: SELECT 외 DML/DDL이 생성되면 경고 + 출력 차단
  - 입력/출력 감사 로그(SQLite)

### 4.2 Out of Scope (MVP 이후)
- DBMS 직접 연동 (드라이버, 커넥션, 권한 관리)
- 자동 스키마 수집·시각화
- 쿼리 실행 결과 표시
- SQL 방언 간 자동 변환 (예: Oracle SQL → MSSQL)
- 보험 도메인 용어집/RAG 결합
- SSO·역할 기반 권한

---

## 5. 기능 명세

### 5.1 입력
| 필드 | 형식 | 예시 |
|------|------|------|
| `dbms` | enum | `oracle` \| `mssql` \| `greenplum` \| `tibero` |
| `schema` | 텍스트 또는 구조화 JSON | `CONTRACT(POL_NO PK, REG_DATE DATE, REGION VARCHAR2(20), PREMIUM NUMBER)` |
| `question` | 자유 한국어 | "지난달 강원도 신규 계약 건수와 평균 보험료" |

### 5.2 출력
| 필드 | 설명 |
|------|------|
| `sql` | DBMS 방언으로 생성된 SQL (SELECT 한정) |
| `assumptions` | LLM이 가정한 항목 (예: "지난달 = `ADD_MONTHS(SYSDATE,-1)` 기준") |
| `warnings` | 모호한 부분, 누락된 정보, 검토 권고 |

### 5.3 DBMS 방언 가이드 (시스템 프롬프트에 주입할 핵심 차이)
| 영역 | Oracle | MSSQL | Greenplum | Tibero |
|------|--------|-------|-----------|--------|
| 현재 시각 | `SYSDATE` | `GETDATE()` | `NOW()` / `CURRENT_TIMESTAMP` | `SYSDATE` (Oracle 호환) |
| 페이징 | `ROWNUM` / `FETCH FIRST` | `TOP` / `OFFSET ... FETCH` | `LIMIT ... OFFSET` | `ROWNUM` |
| 문자열 연결 | `||` | `+` / `CONCAT` | `||` | `||` |
| 월 차이 | `MONTHS_BETWEEN` | `DATEDIFF(month,...)` | `EXTRACT + age()` | `MONTHS_BETWEEN` |
| NULL 처리 | `NVL` | `ISNULL` | `COALESCE` | `NVL` |
| 식별자 인용 | `"..."` | `[...]` / `"..."` | `"..."` | `"..."` |

> Tibero는 Oracle 호환이 매우 높아 Oracle 프롬프트를 베이스로 작은 차이만 분기하는 전략을 권장.

---

## 6. 기술 아키텍처

### 6.1 스택 (기존 자산 재사용)
- **언어/프레임워크**: Python 3.13 + FastAPI (HWGI Translator 동일)
- **검증**: Pydantic 2 (request/response 스키마)
- **LLM 클라이언트**: httpx + OpenAI Chat Completions 호환 인터페이스
- **저장소**: SQLite (감사 로그·즐겨찾기 등). 운영 단계는 PostgreSQL 전환
- **프론트엔드**: 단일 HTML + Vanilla JS (기존 `hw-translator.html` 패턴 동일)

### 6.2 LLM 추상화
```
LLM_BASE_URL   = https://api.openai.com/v1     # PoC
LLM_MODEL      = gpt-4o-mini                   # PoC
LLM_API_KEY    = sk-...

# 추후 vLLM 전환 시:
LLM_BASE_URL   = http://<vllm-host>:5015/v1
LLM_MODEL      = gemma-4-26B-A4B-it
LLM_API_KEY    =
```
- HWGI Translator의 `pipeline.py` 패턴과 동일하게 `BASE_URL` + `MODEL`만 교체하면 백엔드 전환 가능하도록 설계.

### 6.3 권장 폴더 구조 (HWGI_Translator 내 신규 모듈)
```
backend/app/query_assistant/
├── __init__.py
├── router.py          # /api/query/* 라우트
├── schemas.py         # GenerateRequest, GenerateResponse
├── prompts.py         # DBMS별 시스템 프롬프트·few-shot
├── dialects.py        # DBMS enum + 방언 메타데이터
├── generator.py       # LLM 호출 + 가정/경고 파싱
└── safety.py          # SELECT-only 검증, DDL/DML 차단
```
프론트는 `hw-query.html`로 추가, `main.py`에서 `/query` 경로에 마운트.

---

## 7. 비기능 요구사항

| 항목 | 목표 |
|------|------|
| **보안** | 사내망 전용(추후). MVP는 OpenAI 호출 시 컬럼명/도메인 용어만 전송, **실 데이터는 절대 전송 금지** |
| **감사** | 모든 질문/SQL/사용자 식별자(추후) SQLite에 기록 |
| **응답시간** | p50 5초 이내 (OpenAI 기준) |
| **안전성** | SELECT 외 구문 차단. 생성 SQL에 `LIMIT/ROWNUM` 자동 권고 |
| **이식성** | LLM 백엔드 환경변수 1줄 교체로 vLLM 전환 |

---

## 8. 단계별 로드맵

| Phase | 기간(목표) | 내용 |
|-------|-----------|------|
| **Phase 1 — MVP** | 2~3주 | 4개 DBMS 방언 지원, 사용자 직접 스키마 입력, OpenAI 기반 |
| **Phase 2 — 정확도 강화** | +3~4주 | 보험 도메인 용어집(소규모 RAG), 즐겨찾기/히스토리, 결과 평가 피드백 수집 |
| **Phase 3 — DBMS 연동** | +4주~ | 읽기 전용 계정으로 DBMS 자동 스키마 수집, 메타데이터 캐싱 |
| **Phase 4 — vLLM 전환 & 사내 배포** | +2주 | 사내 vLLM 엔드포인트로 교체, 감사 로그/권한 강화 |

---

## 9. 리스크 및 가정

| 리스크 | 영향 | 대응 |
|--------|------|------|
| LLM이 존재하지 않는 컬럼명을 만들어냄(hallucination) | 잘못된 SQL 실행 위험 | 사용자가 입력한 스키마만 참조하도록 시스템 프롬프트로 강하게 제약 + 출력 SQL의 식별자가 입력 스키마에 존재하는지 후처리 검증 |
| 보험 도메인 용어(원수/수재/손해율 등) 오해석 | 정확도 저하 | Phase 2에서 도메인 용어집 추가, MVP에는 사용자가 설명을 함께 입력 |
| 4개 DBMS 방언 차이로 인한 미세 오류 | 실행 실패 | Phase 1에서 DBMS별 회귀 테스트셋(30~50문항) 운영 |
| OpenAI 외부 호출 정책 | 사내 보안 검토 필요 | 컬럼명/스키마만 송신·실 데이터 금지를 강제. 추후 vLLM 전환으로 완화 |

---

## 10. 검증 방안

### 10.1 기능 검증
- DBMS별 골드셋 테스트: 동일 자연어 질문 30~50개 × 4 DBMS = 120~200 쿼리
- 자동 검증: 생성 SQL을 각 DBMS에 대해 **EXPLAIN/PARSE만 수행**(실행하지 않음)해 구문 오류 비율 측정
- 수동 검증: 데이터 부서 1~2명이 정답 SQL과 비교 (정확도·가정 적절성)

### 10.2 사용자 검증
- **계리/데이터 부서** 파일럿(3~5명): 실제 업무 질문 입력 → 만족도·수정 횟수·구문 정확도 측정
- 계리/데이터 부서는 SQL을 직접 검증할 수 있어 PoC 정확도 평가에 최적
- 성공 지표(예시): "복사 후 1회 이내 수정으로 실행 성공"률 ≥ 70%
- Phase 2 진입 후 영업·언더라이팅 등 비개발자 그룹으로 확대

### 10.3 보안 검증
- 입력에 실 데이터(주민번호·계약자명 등) 포함 시 차단 또는 마스킹 동작 확인
- SELECT 외 구문 생성 시 차단 동작 확인

---

## 11. 다음 단계 (확정 완료)

> 2026-05-22 사용자와의 협의를 통해 아래 5개 항목 모두 확정. 이제 구현 단계로 진입합니다.

| 항목 | 확정 |
|------|------|
| MVP DBMS 우선순위 | **4개 동시 지원** (Oracle / MSSQL / Greenplum / Tibero) |
| 스키마 입력 UX | **자유 텍스트 + 예시 템플릿** (DBMS별 스니펫 제공) |
| 배포 환경 | **로컬 PoC 먼저** → 안정화 후 사내 배포 결정 |
| OpenAI 사용 승인 | **자매 프로젝트(HWGI Translator) 승인 범위에 포함** — 보안팀에는 추가 고지만 진행 |
| 파일럿 사용자 그룹 | **계리/데이터 부서 3~5명** → Phase 2에서 영업·언더라이팅 등으로 확대 |

### 즉시 착수 가능한 작업 (Phase 1)

1. `backend/app/query_assistant/` 모듈 골격 (`schemas.py`, `dialects.py`, `prompts.py`, `safety.py`, `generator.py`, `router.py`)
2. `backend/app/main.py` + `config.py` (FastAPI 진입점, `.env` 검증)
3. 단일 페이지 UI `hw-query.html` (DBMS 선택·자유 텍스트 스키마 입력·예시 템플릿 버튼·결과 출력)
4. DBMS별 시스템 프롬프트 (방언 가이드: SYSDATE/GETDATE/NOW, ROWNUM/TOP/LIMIT, NVL/ISNULL/COALESCE, 문자열 연결)
5. SELECT-only 검증 + 식별자 후처리 검증
6. SQLite 감사 로그 스키마
7. 계리/데이터 부서 검증용 골드셋(30~50문항) 초안

---

*위 작업은 `agent-guide/SESSION.md`의 P0/P1 작업 목록과 연동됩니다.*
