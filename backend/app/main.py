"""FastAPI 진입점.

엔드포인트:
  GET  /health                       부팅·LLM 설정 점검
  POST /api/query/generate           자연어 → SQL 생성

정적:
  GET  /                             hw-query.html (없으면 안내 텍스트)

설계 의도:
- `httpx.AsyncClient` 는 lifespan 에서 단일 인스턴스를 만들어 `app.state.http` 로
  공유. 요청마다 client 생성 시 커넥션 풀/세션 비효율 + LLM 의 keep-alive 미활용.
- `LLM_API_KEY` 가 비어 있어도 부팅은 허용 (사내 vLLM 은 키 없이 동작 가능).
  실제 호출 시 외부에서 401 가 오면 generator 가 502 로 변환한다.

자매 프로젝트(`HWGI_Translator/backend/app/main.py`) 의 lifespan + `app.state`
패턴을 따른다.

한계 (P1 작업으로 후속 진행):
- SELECT-only 사후 검증(`safety.py`) 미적용 — 현재는 시스템 프롬프트의
  "절대 규칙 1" 만으로 DDL/DML 을 막고 있음. LLM 출력 신뢰는 부분적.
- 감사 로그(SQLite) 미적용.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .config import PROJECT_ROOT, get_settings
from .query_assistant.dialects import DBMS
from .query_assistant.router import router as query_router


log = logging.getLogger("hw_query")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def _requires_api_key(base_url: str) -> bool:
    """OpenAI 처럼 인증이 필수인 base_url 인지 판별.

    사내 vLLM(`3.38.195.121` 등) 은 인증 불필요. OpenAI 호스트만 명시적으로
    `True` 를 반환해, 새로운 인증 호스트가 들어와도 안전하게 무경고로 통과.
    필요해지면 호스트 화이트리스트를 추가한다.
    """
    return "api.openai.com" in base_url


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # 개별 요청 timeout 은 generator 가 settings.llm_timeout_seconds 로 지정하므로
    # client 자체에는 기본 timeout 을 두지 않는다.
    client = httpx.AsyncClient(timeout=None)

    app.state.settings = settings
    app.state.http = client

    # 인증이 필요한 base_url(예: OpenAI) 인데 키가 비어있을 때만 경고.
    # 사내 vLLM 은 인증 불필요(docs/VLLM_API_GUIDE.md) 이라 키 없이 정상 동작.
    if not settings.llm_api_key and _requires_api_key(settings.llm_base_url):
        log.warning(
            "LLM_API_KEY 가 비어 있습니다. base_url=%s 는 인증이 필요해 401 예상.",
            settings.llm_base_url,
        )
    log.info(
        "app ready (model=%s, base_url=%s, dbms=%s)",
        settings.llm_model,
        settings.llm_base_url,
        ",".join(d.value for d in DBMS),
    )
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title="HWGI Query Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(query_router, prefix="/api/query", tags=["query"])


# ─── Health ─────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    s = app.state.settings
    return {
        "ok": True,
        "model": s.llm_model,
        "base_url": s.llm_base_url,
        "dbms": [d.value for d in DBMS],
    }


# ─── 정적 페이지 ─────────────────────────────────────────────

# 프로젝트 루트의 `static/` 디렉토리에 hw-query.{html,js,css} 가 함께 위치.
# StaticFiles mount 대상은 이 디렉토리 하나로 한정해 PROJECT_ROOT 의 다른 파일
# (`backend/`, `docs/`, `agent-guide/` 등) 노출을 막는다.
_STATIC_ROOT = PROJECT_ROOT / "static"
_UI_PATH = _STATIC_ROOT / "hw-query.html"
_UI_ABSENT_NOTICE = (
    "HWGI Query Assistant API.\n"
    "정적 UI(static/hw-query.html)를 찾을 수 없습니다.\n"
    "API 문서: /docs · 헬스: /health"
)

if _STATIC_ROOT.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_ROOT)), name="static")


@app.get("/", include_in_schema=False)
async def root_page():
    if _UI_PATH.exists():
        return FileResponse(_UI_PATH)
    return PlainTextResponse(_UI_ABSENT_NOTICE)
