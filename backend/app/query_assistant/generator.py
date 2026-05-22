"""LLM 호출 + JSON 파싱.

설계 의도:
- OpenAI Chat Completions 호환 인터페이스만 사용 (vLLM 도 동일 형식 제공).
- 응답은 항상 JSON ({sql, assumptions, warnings}). 마크다운 코드블록이 섞여
  들어와도 견디도록 파싱에 fallback 1단계를 둔다.
- httpx.AsyncClient 는 호출자 수명주기에 맞춰 외부에서 주입.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import ValidationError

from ..config import Settings
from .dialects import DBMS
from .prompts import build_system_prompt, build_user_prompt
from .schemas import GenerateResponse


log = logging.getLogger(__name__)


class GeneratorError(RuntimeError):
    """LLM 호출/파싱 실패."""


# JSON 코드블록(``` ... ```) 안에 들어 있을 때 추출하는 fallback 정규식.
_CODEBLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


async def generate_sql(
    *,
    dbms: DBMS,
    schema_text: str,
    question: str,
    settings: Settings,
    client: httpx.AsyncClient,
) -> GenerateResponse:
    """자연어 질문 → SQL 생성. 검증된 GenerateResponse 반환."""

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    body: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": build_system_prompt(dbms)},
            {"role": "user", "content": build_user_prompt(dbms, schema_text, question)},
        ],
        "temperature": settings.llm_temperature,
        # OpenAI 의 JSON 모드. vLLM 일부 버전은 무시할 수 있으므로 파싱은 견고하게.
        "response_format": {"type": "json_object"},
    }

    try:
        resp = await client.post(
            url, headers=headers, json=body, timeout=settings.llm_timeout_seconds
        )
    except httpx.HTTPError as exc:
        raise GeneratorError(f"LLM 요청 실패: {exc}") from exc

    if resp.status_code >= 400:
        raise GeneratorError(
            f"LLM 응답 오류 {resp.status_code}: {resp.text[:500]}"
        )

    payload = resp.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeneratorError(f"LLM 응답 형식 이상: {payload!r}") from exc
    if not isinstance(content, str):
        raise GeneratorError(f"LLM content 비문자열: {content!r}")

    parsed = _parse_json_content(content)

    # GenerateResponse 검증 (dbms 는 요청 측 값을 신뢰)
    try:
        return GenerateResponse(
            dbms=dbms,
            sql=parsed.get("sql", ""),
            assumptions=parsed.get("assumptions", []) or [],
            warnings=parsed.get("warnings", []) or [],
        )
    except ValidationError as exc:
        raise GeneratorError(f"LLM JSON 스키마 불일치: {exc}") from exc


def _parse_json_content(content: str) -> dict[str, Any]:
    """LLM 출력 문자열을 JSON dict 로 파싱.

    1차: content 전체를 그대로 json.loads
    2차: 코드블록(```json ... ```) 안의 객체만 추출해 재시도
    """
    text = content.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        match = _CODEBLOCK_RE.search(text)
        if not match:
            raise GeneratorError(f"LLM 출력이 JSON 이 아님:\n{text[:500]}")
        try:
            obj = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise GeneratorError(
                f"코드블록 안 JSON 파싱 실패: {exc}\n{text[:500]}"
            ) from exc

    if not isinstance(obj, dict):
        raise GeneratorError(f"LLM 출력이 JSON 객체가 아님: {type(obj).__name__}")
    return obj
