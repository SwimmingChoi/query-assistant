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
    # schema_text: 사내 실제 분석 쿼리는 다중 테이블(M_CCR_*, INS_* 등) 정의 +
    # 코드 매핑(CA00003=개인용, CCA00194=ECO특약 등 수십~수백 항목)을 함께 붙여
    # 넣을 수 있어 40KB 까지 허용. 그 이상은 LLM 비용/지연 폭주 + safety 의
    # 50KB SQL 길이 가드와 균형 맞춘 상한.
    schema_text: str = Field(min_length=1, max_length=40_000)
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
