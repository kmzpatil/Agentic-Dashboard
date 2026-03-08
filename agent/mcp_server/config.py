from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


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
        return cls(
            server_name=os.getenv("MCP_SERVER_NAME", "Frammer Analytics MCP Server"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres",
            ),
            default_schema=os.getenv("DATABASE_SCHEMA", "public"),
            transport=os.getenv("MCP_TRANSPORT", "streamable-http"),
            default_query_limit=_int_env("MCP_DEFAULT_QUERY_LIMIT", 200),
            max_query_limit=_int_env("MCP_MAX_QUERY_LIMIT", 1000),
            default_preview_limit=_int_env("MCP_DEFAULT_PREVIEW_LIMIT", 25),
            max_preview_limit=_int_env("MCP_MAX_PREVIEW_LIMIT", 200),
            default_chart_limit=_int_env("MCP_DEFAULT_CHART_LIMIT", 500),
            max_chart_limit=_int_env("MCP_MAX_CHART_LIMIT", 2000),
        )
