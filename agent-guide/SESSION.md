---
name: session
description: 프로젝트 현재 상태. 세션 시작 시 현재 상태 파악용.
last-updated: 2026-05-29
---

# 세션 상태

> 세션 시작 시 현재 상태를 빠르게 파악하기 위한 문서

---

## 작업 관리

| 항목 | 내용 |
|------|------|
| **작업 관리** | [TODO: 도구 선정 후 링크 추가] |
| **기획서** | [docs/PLAN.md](../docs/PLAN.md) |

> 자매 프로젝트(HWGI Translator)는 Notion(Hanwha General Insurance) 백로그 사용 중. 동일 워크스페이스 연동 시 갱신.

---

## 다음 작업

| 우선순위 | 작업 | 상태 |
|---------|------|------|
| ~~P0~~ | ~~기획서 11번 섹션 미확정 항목 확정~~ | **Done (2026-05-22)** |
| ~~P0~~ | ~~`backend/` 골격 (`config.py`, `query_assistant/{dialects,prompts,generator,schemas}.py`)~~ | **Done (커밋 3ec1889)** |
| ~~P0~~ | ~~DBMS 4종 방언 가이드 시스템 프롬프트 (`prompts.py`)~~ | **Done (커밋 3ec1889)** |
| ~~P0~~ | ~~FastAPI 진입점 (`main.py`, `query_assistant/router.py`) + `/health` + `/api/query/generate`~~ | **Done (2026-05-28)** |
| ~~P1~~ | ~~SELECT-only 사후 검증 (`safety.py`) + router 통합 + 보안 보강~~ | **Done (2026-05-28 오후)** |
| ~~P1~~ | ~~프론트 UI (`static/hw-query.{html,js,css}` 분리 구조 + `/static` mount)~~ | **Done (2026-05-28 저녁)** |
| ~~P1~~ | ~~사내 vLLM Gemma 4(`gemma-4-31B-it`) 게이트웨이 기본 백엔드 전환~~ | **Done (2026-05-29)** |
| P1 | 식별자 후처리 검증 (스키마 텍스트와 SQL 식별자 대조) — `safety.py` 확장 또는 별도 모듈 | Todo |
| P1 | 브라우저 실 동작 검증 (vLLM 기본값으로 4 DBMS 골든셋 일부 시연) | Todo |
| P1 | 감사 로그 SQLite 스키마 설계 + 기록 | Todo |
| P2 | 계리/데이터 부서 검증용 골드셋(30~50문항) 초안 | Todo |
| P2 | 로컬 PoC 기동 가이드 (README + .env.example) | Todo |

---

## 기타 이슈

없음

---

## 최근 세션

### 2026-05-29 — 미커밋 정리 + vLLM Gemma 4 게이트웨이 연동

#### 세션 목표
- (1) 2026-05-28 P0/P1 작업분(미커밋 untracked) 의미 단위 분리 커밋.
- (2) 사내 vLLM Gemma 4(`gemma-4-31B-it`) 게이트웨이를 기본 LLM 백엔드로 연동.

#### 변경 파일

미커밋 정리 (3 커밋):
| 커밋 | 파일 | 요약 |
|------|------|------|
| `0fb0feb` chore | `.gitignore`, `backend/.env.example` | 환경/시크릿 메타 |
| `e65b101` feat | `backend/app/query_assistant/safety.py`, `backend/scripts/try_safety.py` | SELECT-only safety validator + 64 케이스 회귀 |
| `48930c0` feat | `backend/app/main.py`, `backend/app/query_assistant/router.py` | FastAPI 진입점 + 라우터 (safety/generator 통합) |

vLLM Gemma 4 연동 (3 커밋):
| 커밋 | 파일 | 요약 |
|------|------|------|
| `8c237e0` feat | `backend/app/config.py`, `.env.example`, `main.py`, `scripts/try_generate.py` | 기본 백엔드 vLLM 게이트웨이(`http://3.38.195.121:5015/v1`, `gemma-4-31B-it`) 로 전환. OpenAI 는 `.env` 옵션. 인증 헤더는 base_url 분기로 자동 처리. |
| `ba8f212` docs | `docs/VLLM_API_GUIDE.md` | vLLM SLM 게이트웨이 사용자용 가이드 추가(661행) |
| `8ad5171` docs | `agent-guide/{GUIDE,PROJECT}.md`, `docs/PLAN.md` | 옛 표기 `Gemma-4-26B-A4B-it` → `gemma-4-31B-it` 통일. PROJECT.md 도 "PoC OpenAI → 최종 vLLM" 에서 "PoC 부터 vLLM 기본" 으로 갱신. |

#### 결정 사항
- **분리 커밋 단위**: untracked 6 파일을 의존성 순서로 (메타 → safety → API) 3 커밋. import 가 깨지지 않도록 safety 가 router 보다 먼저.
- **기본 백엔드를 vLLM 으로**: PROJECT.md/PLAN.md 의 "PoC OpenAI → 최종 vLLM" 방향과 일치, 실제 vLLM 게이트웨이가 가용하고 인증 불필요라 진입장벽이 낮음. OpenAI 는 `.env` 만 교체하면 그대로 동작하는 옵션으로 유지.
- **`generator.py` 무수정**: OpenAI Chat Completions 100% 호환이라 base_url + model 토글로 충분. 가이드의 vLLM 특화 옵션(`chat_template_kwargs`, `extra_body`)은 SQL 생성에 불필요하므로 도입 보류.
- **인증 헤더 분기**: `generator.py` 가 이미 `if settings.llm_api_key:` 조건으로 헤더 추가 — vLLM 은 키 빈 문자열로 헤더 누락, OpenAI 는 키 채워서 Bearer 헤더 추가. 그대로 사용.
- **부팅 경고 분기**: `main.py` 에 `_requires_api_key()` 헬퍼 — `api.openai.com` 일 때만 키 누락 경고. vLLM 사용 시 무경고 부팅.
- **`try_generate.py` 가드 분기**: OpenAI base_url 일 때만 `sys.exit(2)`. vLLM 은 키 없이 통과.
- **SQL temperature 0.1 유지**: Gemma 4 모델카드 권장 1.0은 일반 대화용. 결정적 출력을 위해 0.1 유지. `.env.example` 에 사유 메모.
- **VLLM_API_GUIDE.md §4.4 모델명 정정**: 권장 샘플링 표의 `Gemma 4 26B-A4B` → `gemma-4-31B-it` (사용자 확인 후 일괄 정정).

#### 검증
- `GET /health` (vLLM) → HTTP 200, 7ms.
- `GET /v1/models` → `gemma-4-31B-it`, `max_model_len: 32768`.
- `POST /v1/chat/completions` JSON 모드 (`response_format: {"type":"json_object"}`) sanity → `{"ok": true}` 정확히 반환.
- `try_generate.py --dbms oracle` → `TRUNC(ADD_MONTHS(SYSDATE,-1),'MM')` 정확한 Oracle 지난달 표현, 한국어 별칭 `"신규계약건수"`/`"평균보험료"`, safety 통과.
- `try_generate.py --dbms mssql` → `TOP 10` + `[대괄호 식별자]` + `N'강원도'` + `DATEFROMPARTS`/`DATEADD`/`GETDATE` 정확한 MSSQL 방언, safety 통과.

#### 다음 작업 추천
- **P1 식별자 후처리 검증**: LLM 환각으로 스키마에 없는 컬럼/테이블이 생성되는 경우 차단. `safety.py` 확장 또는 별도 모듈. Gemma 4의 정확도 검증과도 맞물림.
- **P1 감사 로그 SQLite**: DBMS/질문/생성SQL/safety 결과/타임스탬프 비동기 기록. 운영 가시성.
- **P1 4 DBMS 브라우저 시연**: Greenplum/Tibero 도 골든셋 1건씩 brower 에서 실제 호출.

### 2026-05-28 (저녁 — 프론트 UI)

#### 세션 목표
- P1: 현업 데모용 프론트 UI. 사용자 요청에 따라 **단일 HTML 임베디드가 아닌 HTML/JS/CSS 분리** 구조.

#### 변경 파일
| 파일 | 변경 유형 | 요약 |
|------|----------|------|
| `static/hw-query.html` | 추가 | 의미적 마크업 셸. nav, 입력 카드(DBMS 세그먼트·스키마·질문·생성/비우기), 결과 카드(SQL/가정/주의·복사·다운로드), 토스트. |
| `static/hw-query.css` | 추가 | 자매 프로젝트(HWGI Translator) 디자인 토큰(3-Layer) 복사 + Query Assistant 전용 컴포넌트. 폰트 임베드 없이 시스템 폰트 폴백. |
| `static/hw-query.js` | 추가 | Vanilla JS IIFE. DBMS별 예시 스키마 4종, `/health`/`/api/query/generate` 호출, 422/502/network 에러 분기, 복사(clipboard API + fallback), `.sql` 다운로드, Ctrl/Cmd+Enter 단축키, 토스트. |
| `backend/app/main.py` | 갱신 | `PROJECT_ROOT/static/` 만 `/static` 으로 mount(다른 디렉토리 노출 방지), `GET /` → `static/hw-query.html` 반환. |

#### 결정 사항
- **분리 vs 단일 HTML**: 사용자 선택으로 분리. 자매 프로젝트는 단일 HTML 임베디드 패턴(폰트 base64 포함 1.6MB)이지만 본 프로젝트는 캐싱/리뷰성/유지보수성을 위해 분리.
- **mount 범위**: `PROJECT_ROOT` 전체가 아니라 `PROJECT_ROOT/static/` 만 `/static` 으로 mount. `backend/`/`docs/`/`agent-guide/` 노출 차단.
- **디자인 토큰**: 자매 프로젝트의 Layer 1(한화 브랜드 컬러: `#F37321` 오렌지 + `#1A2B4A` 네이비) + Layer 2(role-based aliases) 그대로 복사. 폰트는 시스템 폴백.
- **에러 UX**: 422(검증) → 필드 위치 + 메시지. 502(LLM/safety) → 사용자 친화적 안내 + `detail` 표시. 네트워크 실패 → "백엔드 연결 실패" 명시.
- **클립보드**: `navigator.clipboard.writeText` 우선, 권한 없으면 임시 textarea + `execCommand` fallback.
- **XSS 방어**: 모든 응답 데이터는 `textContent` 로만 삽입 (`innerHTML` 사용 금지).
- **PROJECT.md 권장안 변경**: 원래 `hw-query.html` 을 프로젝트 루트에 두는 안이었으나, 실제 구조는 `static/` 디렉토리. 다음 세션에 PROJECT.md 동기화 필요.

#### 검증
- `GET /` → 200 `text/html` (5.6KB).
- `GET /static/hw-query.css` → 200 `text/css` (17.6KB).
- `GET /static/hw-query.js` → 200 `text/javascript` (11.9KB).
- `GET /static/없는파일` → 404.
- `GET /static/../backend/app/main.py` 경로 탈출 시도 → 404 (StaticFiles 자체 방어).
- HTML 안 `<link>`/`<script>` 가 `/static/...` 으로 정확히 참조됨.
- 브라우저 실제 시연(SQL 생성)은 `LLM_API_KEY` 설정 시점에 별도 검증 필요.

#### 다음 작업 추천
- 브라우저 실 동작 검증 (LLM 키 설정 후 4 DBMS 골든셋 일부).
- 감사 로그 SQLite 또는 sqlglot 기반 검증 전환.

> **PROJECT.md 동기화 완료 (2026-05-28 저녁 후속)**: 구조/핵심 파일/빠른 시작/기술 스택 모두 실제 구현에 맞춰 갱신.

### 2026-05-28 (오후 — safety 보강)

#### 세션 목표
- security-reviewer 가 지적한 P0/P1 보안 우회 벡터 즉시 반영.

#### 변경 파일
| 파일 | 변경 유형 | 요약 |
|------|----------|------|
| `backend/app/query_assistant/safety.py` | 갱신 | 유니코드 NFKC 정규화 + 비ASCII 공백 일반화, Oracle Q-quote/PG dollar-quote 정제, 운영 키워드 14종(`COPY`,`VACUUM`,`ANALYZE`,`REINDEX`,`CLUSTER`,`REFRESH`,`BACKUP`,`RESTORE`,`SHUTDOWN`,`KILL`,`SET`,`RESET`,`DISCARD`,`DO`) 추가, 50KB 길이 가드. |
| `backend/scripts/try_safety.py` | 갱신 | 회귀 케이스 39 → 64개. 통과 케이스에 Q-quote/dollar-quote/힌트 주석/WITH 중첩/윈도우 함수, 차단 케이스에 운영 명령 14종 + ZWSP/NBSP 우회 + 길이 초과 + DO + RETURNING. |

#### 결정 사항
- **Q-quote**: Oracle/Tibero 의 `q'[...]'` `q'(...)'` `q'{...}'` `q'<...>'` `q'X...X'` 패턴을 정제. 메모에 `DROP` 같은 단어가 들어가도 false positive 회피.
- **Dollar-quote**: `$$...$$` 와 `$tag$...$tag$` 분리 정규식. Python `re` 가 optional 그룹 backreference 가 None 이 되는 한계 회피.
- **유니코드 공백**: ZWSP(`​`), NBSP(` `), IDEOGRAPHIC SPACE(`　`), BOM(`﻿`) 등을 ASCII space 로 치환. `\b` 단어 경계가 ASCII 만 인식하는 우회 차단.
- **운영 키워드 우선순위**: `COPY` (PG/Greenplum 서버측 파일 I/O — 보안 P0), 나머지는 가용성 위협. `SET`/`RESET`/`DISCARD` 는 정상 SELECT 본문 등장 케이스가 거의 없어 차단해도 false positive 위험 낮음.
- **길이 가드 50KB**: 4 DBMS 정상 케이스가 수 KB 수준. LLM 폭주 출력 시 정규식 절대 시간 방어 (ReDoS 는 polynomial 안전이지만 보수적 가드).
- **예외 메시지 정책**: SafetyViolation 메시지는 키워드명/문장 수/카테고리만. SQL 본문/PII/스키마는 절대 포함 금지 (모듈 docstring 명시).
- **INTO 정밀화 보류**: reviewer P0-3. 현재 컨텍스트에서 false positive 사례가 명확히 보고된 적 없고, INSERT INTO 는 INSERT 가 먼저 차단되므로 위험 낮음. sqlglot 도입 시 함께 정밀화.

#### 검증
- `python scripts/try_safety.py` → **64/64 케이스 통과** (통과 19 + 차단 45).
- 부팅 + `/health`/422/502 회귀 통과.

#### 추가 위협 모델 확인
- ✅ Greenplum 우회 (`$$DROP$$`, `COPY`, `DO`) — 차단.
- ✅ Oracle 우회 (`q'[DROP]'`, `SHUTDOWN`) — 차단/정제.
- ✅ 유니코드 ZWSP/NBSP 우회 — 정규화 후 다중 문장으로 차단.
- ✅ 정상 SELECT (Q-quote 메모, dollar-quote 메모, 힌트 주석, WITH 중첩, 윈도우 함수) — 통과.

#### 다음 작업 추천
- P1 `hw-query.html` UI (현업 데모 가능).
- P2 sqlglot AST 기반 검증 전환 검토 (deny-list 본질적 한계 해소).
- 응답 페이로드에 구조화된 `error_code` 추가 (운영 가시성).

### 2026-05-28 (오후)

#### 세션 목표
- P1: `safety.py` — LLM 출력 SQL의 사후 SELECT-only 검증. router 통합.

#### 변경 파일
| 파일 | 변경 유형 | 요약 |
|------|----------|------|
| `backend/app/query_assistant/safety.py` | 추가 | 정규식 기반 사후 검증. 39 케이스 매트릭스로 회귀 방지. |
| `backend/app/query_assistant/router.py` | 갱신 | `generate_sql()` 직후 `validate_sql()` 호출, `SafetyViolation → 502`. |
| `backend/scripts/try_safety.py` | 추가 | 정상 12 + 차단 27 케이스 검증 스크립트. |

#### 결정 사항
- **외부 의존성 없이 정규식 deny-list**: `sqlparse` 등 추가 의존성 회피. PoC 단계에서 충분.
- **보수적 차단**: false negative 보다 false positive 우선. 현업 차단은 보고로 회복 가능, DROP 통과는 사고.
- **정제 후 검사**: 주석 → 작은따옴표 문자열 → 큰따옴표/대괄호 식별자 제거 후 키워드 검사. 이중 작은따옴표 이스케이프(`''`) 처리.
- **다중 문장 차단**: `SELECT 1; DROP TABLE x` 같은 합성 우회. 정제 후 세미콜론으로 split → 의미 있는 토큰 2개 이상이면 거부.
- **첫 토큰 화이트리스트**: SELECT, WITH 만 허용. WITH 절 안 INSERT 같은 합성 우회는 본문 키워드 검사가 추가로 차단.
- **차단 시 응답 코드**: 502 (LLM 외부 의존 출력 오류로 분류). 사용자 입력 잘못이 아님을 422와 구분.
- **식별자 후처리 검증은 별도 작업**: 사용자 스키마 텍스트가 자유 형식이라 식별자 추출이 별도 파싱·정확도 트레이드오프 필요. SELECT-only 검증과 분리.

#### 검증
- `python scripts/try_safety.py`: **39/39 케이스 통과** (정상 12 + 차단 27).
- 차단 카테고리: DML (INSERT/UPDATE/DELETE/MERGE), DDL (CREATE/DROP/ALTER/TRUNCATE/RENAME), 권한 (GRANT/REVOKE), 실행 (EXEC/CALL), 블록 (BEGIN/DECLARE), 트랜잭션 (COMMIT/ROLLBACK), SELECT INTO, LOCK, 다중 문장, 주석 위장, 빈/공백/세미콜론만.
- 통과 카테고리: 4 DBMS few-shot 패턴, WITH CTE, 문자열·식별자 안 키워드 단어, 한국어 별칭, 라인/블록 주석, 이중 작은따옴표 이스케이프, 컬럼명에 키워드 포함(`INSERT_DATE`).
- 부팅 후 OpenAPI 경로 확인: `['/api/query/generate', '/health']`.

#### 현재 상태
- 출력 신뢰 경계 확보. 사내 배포 전 P0 보안 요건 충족.
- 다음: `hw-query.html` UI (현업 데모) 또는 감사 로그 SQLite.

### 2026-05-28

#### 세션 목표
- P0: FastAPI 진입점 구축 — `uvicorn app.main:app` 부팅 가능, `/api/query/generate` HTTP 노출

#### 변경 파일
| 파일 | 변경 유형 | 요약 |
|------|----------|------|
| `backend/app/main.py` | 추가 | FastAPI 앱, lifespan(httpx client 단일 관리), `/health`, `/` 정적 페이지 안내 |
| `backend/app/query_assistant/router.py` | 추가 | `APIRouter` — `POST /generate`, `GeneratorError` → 502 매핑 |
| `agent-guide/SESSION.md` | 갱신 | backend 진척 반영, 다음 우선순위 정리 |

#### 결정 사항
- **httpx.AsyncClient 수명주기**: `lifespan` 에서 단일 인스턴스 → `app.state.http`. 요청별 클라이언트 생성 금지(커넥션 풀/keep-alive 효율).
- **client 기본 timeout = None**: 호출별 timeout 은 `generator.generate_sql` 이 `settings.llm_timeout_seconds` 로 명시 지정.
- **LLM_API_KEY 없어도 부팅 허용**: 사내 vLLM 은 키 없이 동작 가능. 외부 OpenAI 401 발생 시 generator 가 502 로 변환.
- **에러 매핑**: 입력 검증 실패 → 422(FastAPI 자동), LLM 외부 의존 실패 → 502, 그 외는 기본.
- **`safety.py` 자리**: router 의 `try` 블록 안 한 줄만 추가하면 끼워넣을 수 있는 구조 유지 (이번 범위 외).

#### 검증
- 부팅: `uvicorn app.main:app --port 8090` 성공, `app ready (model=..., base_url=..., dbms=oracle,mssql,greenplum,tibero)` 로그.
- `GET /health` → `{"ok":true,"model":"gpt-4o-mini","base_url":"...","dbms":["oracle","mssql","greenplum","tibero"]}` 200.
- `GET /` (UI 없음) → 안내 텍스트 200.
- `POST /api/query/generate` `dbms:"mysql"` → 422.
- `POST /api/query/generate` `schema_text:""` → 422.
- `POST /api/query/generate` (API_KEY 없는 상태) → 502 + `detail: "LLM 응답 오류 401: ..."`.

#### 현재 상태
- HTTP API 동작 가능. P1 작업(`safety.py` → 라우터 연결 → `hw-query.html` UI → 감사 로그) 진행 준비 완료.
- 다음 단계 추천: `safety.py` 먼저 (출력 신뢰 경계 확보) → `hw-query.html` (사용자 데모) → 감사 로그.

### 2026-05-22

#### 세션 목표
- 프로젝트 기획서 작성
- 새 프로젝트 폴더 분리 (`HWGI_Translator`에서 독립)
- agent-guide 3종 파일 생성

#### 변경 파일
| 파일 | 변경 유형 | 요약 |
|------|----------|------|
| `docs/PLAN.md` | 추가 | 기획서 초안 (배경/MVP/방언/로드맵/리스크/검증) |
| `agent-guide/GUIDE.md` | 추가 | 작업 원칙, 보험 도메인 용어, 세션 체크리스트 |
| `agent-guide/PROJECT.md` | 추가 | 프로젝트 개요, 기술 스택, 권장 구조 |
| `agent-guide/SESSION.md` | 추가 | 세션 상태 초기화 |

#### 결정 사항
- **주 사용자**: 현업 (비개발자)
- **핵심 기능**: 자연어 → SQL 생성 (Text-to-SQL)
- **DBMS 전략**: 통합 추상화 (사용자는 DBMS만 선택)
- **LLM 백엔드**: OpenAI 우선 (PoC) → 사내 vLLM 전환
- **실행 범위**: SQL만 생성 (복사·다운로드). DBMS 직접 실행 없음
- **메타데이터**: 사용자 직접 입력 (MVP) → 추후 DBMS 자동 수집
- **자매 프로젝트와 분리**: `/workspace/HWGI_Query_Assistant/` 독립 디렉토리로 운영

#### 추가 확정 사항 (오후 세션)
- **MVP DBMS**: 4개 동시 지원 (Oracle / MSSQL / Greenplum / Tibero)
- **스키마 입력 UX**: 자유 텍스트 + 예시 템플릿 (DBMS별 스니펫)
- **배포 환경**: 로컬 PoC 먼저 → 안정화 후 사내 배포 결정
- **OpenAI 사용 승인**: 자매 프로젝트 승인 범위에 포함 (보안팀 추가 고지만)
- **파일럿 사용자 그룹**: 계리/데이터 부서 3~5명 → Phase 2에서 영업/언더라이팅으로 확대

#### 현재 상태
- 기획서 11번 미확정 항목 5건 **모두 확정 완료**
- 다음: `backend/app/query_assistant/` 모듈 골격 + `hw-query.html` UI 동시 진행 가능
- 로컬 PoC 목표이므로 사내망 의존성 없이 개발자 PC에서 기동 가능한 형태로 우선 구현
