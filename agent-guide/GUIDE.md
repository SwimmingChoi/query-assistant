---
name: guide
description: AI 에이전트 작업 원칙과 세션 시작 체크리스트. 세션 시작 시 가장 먼저 읽기.
last-updated: 2026-05-22
---

# 에이전트 가이드

> AI 에이전트가 세션을 시작할 때 읽는 문서입니다.

---

## 작업 원칙

- 모든 커뮤니케이션은 **한국어**로
- **최소 변경**: 꼭 필요한 범위만 수정
- **근본 원인 해결** 우선, 우회 패치 지양
- 기존 코드 스타일 준수 (자매 프로젝트 `HWGI_Translator` 패턴 참고)
- 커밋 메시지: `feat/fix/docs/refactor/chore` 형태
- **보안 우선**: 보험사 도메인이므로 실 데이터(주민번호·계약자명 등) 외부 LLM 전송 절대 금지

---

## 용어 정리

| 용어 | 설명 |
|------|------|
| **Text-to-SQL** | 자연어 질문을 SQL로 변환하는 본 시스템의 핵심 기능 |
| **방언(Dialect)** | DBMS별 SQL 문법 차이. Oracle/MSSQL/Greenplum/Tibero 4종 지원 |
| **통합 추상화** | 사용자는 DBMS만 선택하고, 내부에서 방언을 분기하는 전략 |
| **DBMS 4종** | Oracle, MSSQL, Greenplum, Tibero (사내 사용 DBMS) |
| **vLLM** | 사내 LLM 추론 서버 (`gemma-4-31B-it` 모델, OpenAI Chat Completions 호환) |
| **현업** | SQL을 모르는 비개발자 사용자 (영업/언더라이팅/계리/마케팅 등) |
| **골드셋** | DBMS별 회귀 테스트용 정답 SQL 셋 |
| **MCP** | Model Context Protocol. AI가 외부 도구와 통신하는 방식 |
| **P0/P1/P2** | 우선순위. P0(긴급) > P1(중요) > P2(보통) |

---

## 세션 시작 체크리스트

1. **프로젝트 파악**: `PROJECT.md` 읽기
2. **현재 상태 파악**: `SESSION.md` 읽기
3. **기획서 확인**: `docs/PLAN.md` 읽기 (확정 사항·미확정 항목 파악)
4. **작업 확인**: [TODO: 작업 관리 도구 연동 후 업데이트 — Notion 사용 시 MCP `get_backlog`]
5. **작업 제안**: 1-3개 제안, 큰 변경은 계획 먼저

---

## MCP 도구

[TODO: MCP 연동 시 도구 목록 추가]

> 자매 프로젝트(HWGI Translator)는 Hanwha General Insurance Notion 워크스페이스를 사용 중. 동일 워크스페이스 합류 시 MCP 연동 가능.

---

## 문서 역할

| 문서 | 갱신 시점 |
|------|----------|
| `SESSION.md` | 세션 종료 시 (오늘 한 일, 이슈) |
| `PROJECT.md` | 범위/아키텍처 변경 시에만 |
| `docs/PLAN.md` | 기획·범위 변경 시 |

---

## 시작 예시

> "현재 상태 요약하고, 오늘 작업 제안해줘"

> "SESSION.md 읽고 이어서 진행하자"

> "기획서 11번 미확정 항목 정리해줘"
