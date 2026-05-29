from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed config bound from the environment / .env file.

    The closest .NET analogue is IOptions<T> bound from appsettings: declare the
    shape, get validation for free, fail fast at startup if something's missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str
    anthropic_model: str = "claude-haiku-4-5-20251001"

    notion_api_key: str
    notion_database_id: str


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so config is read once. Lazy, so code paths that don't
    need secrets (e.g. the extractor unit tests) don't trip on a missing .env."""
    return Settings()
