"""
db.py
-----
Shared DatabaseClient singleton for direct in-process database access.
Eliminates the need to spawn an MCP subprocess for same-process API calls.

Usage:
    from db import get_db, db_list_tables, db_describe_table, db_execute_query, db_execute_query_async
"""

import asyncio
from functools import lru_cache
from typing import Any

from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient, QueryValidationError


@lru_cache(maxsize=1)
def _settings() -> ServerSettings:
    return ServerSettings.from_env()


@lru_cache(maxsize=1)
def get_db() -> DatabaseClient:
    """Return (or create) the shared DatabaseClient singleton."""
    s = _settings()
    return DatabaseClient(database_url=s.database_url, default_schema=s.default_schema)


def db_list_tables() -> list[dict[str, Any]]:
    """List all tables in the database. Returns list of dicts."""
    return get_db().list_tables()


def db_describe_table(table_name: str) -> dict[str, Any]:
    """Describe a single table. Returns dict with columns, pk, fks."""
    return get_db().describe_table(table_name)


def db_execute_query(sql: str, limit: int = 5000) -> dict[str, Any]:
    """
    Execute a read-only SQL query (Synchronous).
    Returns {"rows": [...], "row_count": N} on success.
    Returns {"error": "..."} on failure.
    """
    try:
        df = get_db().run_read_only_query(sql, limit=limit)
        records = DatabaseClient.dataframe_to_records(df)
        return {"rows": records, "row_count": len(records)}
    except QueryValidationError as exc:
        return {"error": f"Query validation error: {exc}"}
    except Exception as exc:
        return {"error": f"SQL execution error: {exc}"}


async def db_execute_query_async(sql: str, limit: int = 5000) -> dict[str, Any]:
    """
    Execute a read-only SQL query asynchronously.
    Offloads the synchronous psycopg2 execution to a worker thread to prevent 
    blocking the main async event loop during concurrent chart generation.
    """
    return await asyncio.to_thread(db_execute_query, sql, limit=limit)