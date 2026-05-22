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

    # LLM (OpenAI 호환. vLLM 도 동일 URL 형식)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_timeout_seconds: float = Field(default=60.0, gt=0.0)

    # Audit log (SQLite)
    database_path: str = "./data/audit.sqlite3"

    @property
    def resolved_database_path(self) -> Path:
        p = Path(self.database_path)
        return p if p.is_absolute() else PROJECT_ROOT / "backend" / p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
