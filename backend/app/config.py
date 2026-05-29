"""환경 변수 로드.

`.env`를 읽어 Pydantic Settings 로 검증한다.
실패 시 앱이 부팅되지 않도록 모듈 import 시점에 즉시 검증한다.

자매 프로젝트(HWGI_Translator) 의 `config.py` 와 동일 패턴.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# 프로젝트 루트(= backend의 부모 디렉토리)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8090

    # LLM — 기본값은 사내 vLLM Gemma 게이트웨이(인증 불필요).
    # OpenAI 로 전환하려면 .env 에 LLM_BASE_URL=https://api.openai.com/v1,
    # LLM_MODEL=gpt-4o-mini, LLM_API_KEY=sk-... 를 설정.
    # vLLM 도 OpenAI Chat Completions 100% 호환이므로 generator 코드는 동일.
    llm_base_url: str = "http://3.38.195.121:5015/v1"
    llm_model: str = "gemma-4-31B-it"
    llm_api_key: str = ""
    # SQL 생성은 결정적 출력이 중요 — Gemma 4 모델카드 권장값(1.0)이 아닌 0.1 유지.
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    # 사내 실 분석 쿼리는 200줄 / 12KB 수준도 흔함. 60초로는 부족할 수 있어 120 으로 상향.
    llm_timeout_seconds: float = Field(default=120.0, gt=0.0)
    # 출력 토큰 상한. 12KB 쿼리 ≈ 3~4K 토큰 + assumptions/warnings 여유 → 8000.
    # Gemma 4 max_model_len 32768 안에서 입력(스키마+질문+시스템) 24K 까지 여유.
    llm_max_tokens: int = Field(default=8000, gt=0)

    # Audit log (SQLite)
    database_path: str = "./data/audit.sqlite3"

    @property
    def resolved_database_path(self) -> Path:
        p = Path(self.database_path)
        return p if p.is_absolute() else PROJECT_ROOT / "backend" / p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
