---
name: session
description: 프로젝트 현재 상태. 세션 시작 시 현재 상태 파악용.
last-updated: 2026-05-22 (오후)
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
| P0 | `backend/` 골격 구축 (`app/query_assistant/` 모듈 6종 + `main.py` + `config.py`) | Todo |
| P0 | DBMS 4종 방언 가이드 시스템 프롬프트 작성 (`prompts.py`) | Todo |
| P1 | `hw-query.html` 단일 페이지 UI (DBMS 선택·자유 텍스트 스키마 입력·예시 템플릿 버튼·결과 출력) | Todo |
| P1 | SELECT-only 검증 + 식별자 후처리 검증 (`safety.py`) | Todo |
| P1 | 감사 로그 SQLite 스키마 설계 + 기록 | Todo |
| P2 | 계리/데이터 부서 검증용 골드셋(30~50문항) 초안 | Todo |
| P2 | 로컬 PoC 기동 가이드 (README + .env.example) | Todo |

---

## 기타 이슈

없음

---

## 최근 세션

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
