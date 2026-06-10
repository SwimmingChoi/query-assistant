"""HTTP 라우트 — `/api/query/*`.

설계 의도:
- `httpx.AsyncClient` 와 `Settings` 는 lifespan 에서 생성해 `app.state` 에 저장한
  단일 인스턴스를 재사용한다 (요청마다 클라이언트 생성 금지).
- LLM 외부 의존 실패(`GeneratorError`)는 502 로 매핑해 입력 오류(422)와 구분.
- 감사 로그는 BackgroundTasks 로 응답 전송 후 비동기 기록 (응답 지연 없음).
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..audit_logger import log_query
from ..config import Settings
from .generator import GeneratorError, generate_sql
from .safety import SafetyViolation, validate_sql
from .schemas import GenerateRequest, GenerateResponse


log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: GenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> GenerateResponse:
    settings: Settings = request.app.state.settings
    client = request.app.state.http
    db_path = request.app.state.db_path
    t0 = time.monotonic()

    try:
        result = await generate_sql(
            dbms=req.dbms,
            schema_text=req.schema_text,
            question=req.question,
            settings=settings,
            client=client,
        )
        validate_sql(result.sql)
        background_tasks.add_task(
            log_query,
            db_path,
            dbms=req.dbms.value,
            question=req.question,
            schema_text=req.schema_text,
            sql=result.sql,
            assumptions=result.assumptions or [],
            warnings=result.warnings or [],
            success=True,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
        return result
    except GeneratorError as exc:
        log.warning("generate 실패 (dbms=%s): %s", req.dbms.value, exc)
        background_tasks.add_task(
            log_query,
            db_path,
            dbms=req.dbms.value,
            question=req.question,
            schema_text=req.schema_text,
            sql=None,
            assumptions=[],
            warnings=[],
            success=False,
            error_type="GeneratorError",
            error_msg=str(exc),
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except SafetyViolation as exc:
        # LLM 이 절대 규칙(SELECT-only)을 위반한 출력 — 외부 의존 출력 오류로 분류해 502.
        log.warning("safety 위반 (dbms=%s): %s", req.dbms.value, exc)
        background_tasks.add_task(
            log_query,
            db_path,
            dbms=req.dbms.value,
            question=req.question,
            schema_text=req.schema_text,
            sql=None,
            assumptions=[],
            warnings=[],
            success=False,
            error_type="SafetyViolation",
            error_msg=str(exc),
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
        raise HTTPException(
            status_code=502, detail=f"안전 검증 실패: {exc}"
        ) from exc
