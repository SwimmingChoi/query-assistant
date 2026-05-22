"""LLM 호출 빠른 검증 스크립트 (PoC).

사용 예:
    cd backend && source .venv/bin/activate
    python scripts/try_generate.py                       # 4 DBMS x 샘플 1건 자동 실행
    python scripts/try_generate.py --dbms oracle --question "지난달 강원도 신규 계약 건수와 평균 보험료"
    python scripts/try_generate.py --dbms mssql

샘플 케이스는 보험 도메인 자주 쓰는 패턴 위주. 실제 한화 사내 스키마와 맞지 않을 수 있음.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

# scripts/ 에서 실행되어도 backend.app 을 import 할 수 있도록
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.query_assistant.dialects import DBMS  # noqa: E402
from app.query_assistant.generator import GeneratorError, generate_sql  # noqa: E402


_DEFAULT_SCHEMA = """\
CONTRACT(
  POL_NO       VARCHAR2(20)  PK   -- 증권번호
  REG_DATE     DATE                -- 계약일
  REGION       VARCHAR2(20)        -- 계약 지역
  PRODUCT_CD   VARCHAR2(10)        -- 상품코드
  PREMIUM      NUMBER              -- 보험료
  STATUS       VARCHAR2(10)        -- 계약 상태 (ACTIVE/CANCEL/EXPIRED)
)
"""

_DEFAULT_QUESTION = "지난달 강원도에서 신규 계약된 건수와 평균 보험료를 알려줘."


def _print_result(dbms: DBMS, result) -> None:
    bar = "=" * 70
    print(f"\n{bar}\n[{dbms.value.upper()}]\n{bar}")
    print("-- SQL --")
    print(result.sql)
    if result.assumptions:
        print("\n-- 가정 (assumptions) --")
        for a in result.assumptions:
            print(f"  · {a}")
    if result.warnings:
        print("\n-- 주의 (warnings) --")
        for w in result.warnings:
            print(f"  · {w}")


async def _run_one(client: httpx.AsyncClient, settings, dbms: DBMS, schema: str, question: str) -> None:
    print(f"\n>>> {dbms.value} 호출 중...")
    try:
        result = await generate_sql(
            dbms=dbms,
            schema_text=schema,
            question=question,
            settings=settings,
            client=client,
        )
    except GeneratorError as exc:
        print(f"[!] {dbms.value} 실패: {exc}")
        return
    _print_result(dbms, result)


async def main() -> None:
    parser = argparse.ArgumentParser(description="HWGI Query Assistant — LLM 호출 검증")
    parser.add_argument(
        "--dbms",
        choices=[d.value for d in DBMS],
        help="단일 DBMS만 실행. 미지정 시 4 DBMS 모두 순차 실행.",
    )
    parser.add_argument(
        "--question",
        default=_DEFAULT_QUESTION,
        help="자연어 질문 (기본: 샘플 질문)",
    )
    parser.add_argument(
        "--schema",
        default=_DEFAULT_SCHEMA,
        help="입력 스키마 (기본: CONTRACT 샘플)",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.llm_api_key:
        print(
            "[!] LLM_API_KEY 가 비어 있습니다. backend/.env 를 채워주세요.\n"
            "    예: cp .env.example .env && vi .env",
            file=sys.stderr,
        )
        sys.exit(2)

    targets = [DBMS(args.dbms)] if args.dbms else list(DBMS)

    async with httpx.AsyncClient() as client:
        for dbms in targets:
            await _run_one(client, settings, dbms, args.schema, args.question)


if __name__ == "__main__":
    asyncio.run(main())
