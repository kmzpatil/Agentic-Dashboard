from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus, urlencode

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _first_env(*names: str) -> str | None:
    for name in names:
        value = _env(name)
        if value is not None:
            return value
    return None


def _build_postgres_url() -> str | None:
    explicit_url = _first_env("POSTGRES_URL", "PGDATABASE_URL")
    if explicit_url:
        return explicit_url

    host = _first_env("PGHOST", "POSTGRES_HOST")
    user = _first_env("PGUSER", "POSTGRES_USER")
    database = _first_env("PGDATABASE", "POSTGRES_DB")

    if not host or not user or not database:
        return None

    password = _first_env("PGPASSWORD", "POSTGRES_PASSWORD")
    port = _first_env("PGPORT", "POSTGRES_PORT") or "5432"
    sslmode = _first_env("PGSSLMODE", "POSTGRES_SSLMODE", "DB_SSLMODE")

    credentials = quote_plus(user)
    if password is not None:
        credentials = f"{credentials}:{quote_plus(password)}"

    query: dict[str, str] = {}
    target_host = host
    if host.startswith("/"):
        target_host = "localhost"
        query["host"] = host
    if sslmode:
        query["sslmode"] = sslmode

    query_string = f"?{urlencode(query)}" if query else ""
    return (
        f"postgresql+psycopg2://{credentials}@{target_host}:{port}/"
        f"{quote_plus(database)}{query_string}"
    )


def resolve_database_url() -> str:
    postgres_url = _build_postgres_url()
    if postgres_url:
        return postgres_url

    database_url = _first_env("DATABASE_URL")
    if database_url:
        return database_url

    return f"sqlite:///{ROOT_DIR / 'database' / 'actual_db.sqlite'}"


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
        database_url = resolve_database_url()

        return cls(
            server_name=os.getenv("MCP_SERVER_NAME", "ATLAS MCP Server"),
            database_url=database_url,
            default_schema=os.getenv(
                "DATABASE_SCHEMA",
                "public" if database_url.startswith("postgresql") else "main",
            ),
            transport=os.getenv("MCP_TRANSPORT", "streamable-http"),
            default_query_limit=_int_env("MCP_DEFAULT_QUERY_LIMIT", 200),
            max_query_limit=_int_env("MCP_MAX_QUERY_LIMIT", 1000),
            default_preview_limit=_int_env("MCP_DEFAULT_PREVIEW_LIMIT", 25),
            max_preview_limit=_int_env("MCP_MAX_PREVIEW_LIMIT", 200),
            default_chart_limit=_int_env("MCP_DEFAULT_CHART_LIMIT", 500),
            max_chart_limit=_int_env("MCP_MAX_CHART_LIMIT", 2000),
        )
