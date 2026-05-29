"""HTTP 라우트 — `/api/query/*`.

설계 의도:
- `httpx.AsyncClient` 와 `Settings` 는 lifespan 에서 생성해 `app.state` 에 저장한
  단일 인스턴스를 재사용한다 (요청마다 클라이언트 생성 금지).
- LLM 외부 의존 실패(`GeneratorError`)는 502 로 매핑해 입력 오류(422)와 구분.
- 후속(P1)에서 `safety.py` 의 SELECT-only 검증은 `generate_sql()` 직후 한 줄로
  끼워넣을 수 있도록 단일 try 블록 구조를 유지한다.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from ..config import Settings
from .generator import GeneratorError, generate_sql
from .safety import SafetyViolation, validate_sql
from .schemas import GenerateRequest, GenerateResponse


log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, request: Request) -> GenerateResponse:
    settings: Settings = request.app.state.settings
    client = request.app.state.http
    try:
        result = await generate_sql(
            dbms=req.dbms,
            schema_text=req.schema_text,
            question=req.question,
            settings=settings,
            client=client,
        )
        validate_sql(result.sql)
        return result
    except GeneratorError as exc:
        log.warning("generate 실패 (dbms=%s): %s", req.dbms.value, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except SafetyViolation as exc:
        # LLM 이 절대 규칙(SELECT-only)을 위반한 출력 — 외부 의존 출력 오류로 분류해 502.
        log.warning("safety 위반 (dbms=%s): %s", req.dbms.value, exc)
        raise HTTPException(
            status_code=502, detail=f"안전 검증 실패: {exc}"
        ) from exc
