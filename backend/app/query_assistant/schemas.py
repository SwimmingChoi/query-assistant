"""Request / Response Pydantic 스키마.

router.py (HTTP) 와 generator.py (LLM 응답 파싱) 가 공유한다.
LLM 출력 검증 실패 시 즉시 ValueError → 라우터에서 502 로 변환.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .dialects import DBMS


class GenerateRequest(BaseModel):
    """`POST /api/query/generate` 입력."""

    dbms: DBMS
    schema_text: str = Field(min_length=1, max_length=20_000)
    question: str = Field(min_length=1, max_length=2_000)

    @field_validator("schema_text", "question")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class GenerateResponse(BaseModel):
    """API 응답. LLM 의 JSON 출력을 검증한 결과."""

    dbms: DBMS
    sql: str = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
