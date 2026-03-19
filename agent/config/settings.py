"""Centralised configuration loaded from environment variables."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All tunables for the agent pipeline, driven by env vars / .env file."""

    # ── LLM ───────────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    FAST_MODEL: str = "claude-haiku-4-5-20251001"
    DEEP_MODEL: str = "claude-sonnet-4-6"

    # ── Database ──────────────────────────────────────────────────────────────
    # DATABASE_URL can be set directly, or it is built from PG* env vars.
    DATABASE_URL: str = ""
    DB_POOL_MIN: int = 5
    DB_POOL_MAX: int = 20
    DB_STATEMENT_TIMEOUT_MS: int = 8000

    # Individual PG vars (read from .env automatically)
    PGHOST: str = "127.0.0.1"
    PGPORT: int = 5432
    PGUSER: str = "postgres"
    PGPASSWORD: str = ""
    PGDATABASE: str = "frammer_database"

    def get_database_url(self) -> str:
        """Return DATABASE_URL, building it from PG* vars if not set directly."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        pw = self.PGPASSWORD
        return f"postgresql://{self.PGUSER}:{pw}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"

    # ── Agent behaviour ───────────────────────────────────────────────────────
    SQL_MAX_RETRIES: int = 3
    SQL_MAX_RESULT_LIMIT: int = 500
    CACHE_TTL_SECONDS: int = 60
    SCHEMA_REFRESH_INTERVAL_SECONDS: int = 600
    ROUTER_MAX_TOKENS: int = 256
    INSIGHT_MAX_TOKENS: int = 512

    # ── Feature flags ─────────────────────────────────────────────────────────
    ENABLE_FORECASTING: bool = False
    ENABLE_ANOMALY_DETECTION: bool = True
    ENABLE_PARALLEL_SQL: bool = True
    ENABLE_EMBEDDING_TABLE_SEARCH: bool = False

    model_config = {"env_file_encoding": "utf-8", "extra": "ignore"}


def _find_env_files() -> list[str]:
    """Return .env paths that exist, in priority order (later overrides earlier)."""
    from pathlib import Path
    candidates = [
        Path(__file__).resolve().parents[2] / ".env",   # gcdata/.env (project root)
        Path(__file__).resolve().parents[1] / ".env",    # agent/.env
        Path(".env"),                                     # cwd/.env
    ]
    return [str(p) for p in candidates if p.exists()]


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return _SETTINGS


# Module-level singleton (loaded once on first import).
# Env vars set by api_server.py's load_dotenv() are already in os.environ,
# but we also scan for .env files so standalone imports work.
_env_files = _find_env_files()
_SETTINGS = Settings(_env_file=_env_files if _env_files else None)
