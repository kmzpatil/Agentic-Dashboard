"""
_db.py
------
Shared DatabaseClient singleton for all agent tools.

Every tool that needs database access imports `get_db()` from this module
instead of creating its own SQLAlchemy engine or psycopg2 connection.
This ensures all DB access routes through the MCP DatabaseClient, which
provides query validation, proper error handling, and CHESS-style RAG.
"""

from functools import lru_cache

from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient


@lru_cache(maxsize=1)
def _settings() -> ServerSettings:
    return ServerSettings.from_env()


@lru_cache(maxsize=1)
def get_db() -> DatabaseClient:
    """Return the shared DatabaseClient singleton."""
    s = _settings()
    return DatabaseClient(database_url=s.database_url, default_schema=s.default_schema)


def get_default_schema() -> str | None:
    """Return the default schema for the current database."""
    return _settings().default_schema


# Default query/chart limits (from ServerSettings)
DEFAULT_QUERY_LIMIT = _settings().default_query_limit
MAX_QUERY_LIMIT     = _settings().max_query_limit
