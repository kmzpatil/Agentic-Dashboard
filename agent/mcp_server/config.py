from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class ServerSettings:
    server_name: str
    database_url: str
    default_schema: str
    transport: str
    default_query_limit: int
    max_query_limit: int
    default_preview_limit: int
    max_preview_limit: int
    default_chart_limit: int
    max_chart_limit: int

    @classmethod
    def from_env(cls) -> "ServerSettings":
        # Build DATABASE_URL from components if not provided directly
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            user = os.getenv("POSTGRES_USER", "postgres")
            pw = os.getenv("POSTGRES_PASSWORD", "postgres")
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            db = os.getenv("POSTGRES_DB", "postgres")
            ssl = os.getenv("POSTGRES_SSLMODE", "prefer")
            db_url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}?sslmode={ssl}"

        return cls(
            server_name=os.getenv("MCP_SERVER_NAME", "Frammer Analytics MCP Server"),
            database_url=db_url,
            default_schema=os.getenv("DATABASE_SCHEMA", "public"),
            transport=os.getenv("MCP_TRANSPORT", "stdio"), # default to stdio
            default_query_limit=_int_env("MCP_DEFAULT_QUERY_LIMIT", 200),
            max_query_limit=_int_env("MCP_MAX_QUERY_LIMIT", 1000),
            default_preview_limit=_int_env("MCP_DEFAULT_PREVIEW_LIMIT", 25),
            max_preview_limit=_int_env("MCP_MAX_PREVIEW_LIMIT", 200),
            default_chart_limit=_int_env("MCP_DEFAULT_CHART_LIMIT", 500),
            max_chart_limit=_int_env("MCP_MAX_CHART_LIMIT", 2000),
        )
