"""
Tool: get_frammer_schema
Retrieves the live database schema (tables + columns) from the PostgreSQL
database via the mcp_server DatabaseClient.
Always call this before writing SQL to ensure table and column names are correct.
"""

from functools import lru_cache

from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient


@lru_cache(maxsize=1)
def _get_db() -> DatabaseClient:
    """Return a shared DatabaseClient instance (created once per process)."""
    settings = ServerSettings.from_env()
    return DatabaseClient(
        database_url=settings.database_url,
        default_schema=settings.default_schema,
    )


def get_frammer_schema() -> str:
    """
    Inspect the PostgreSQL database via the MCP server DatabaseClient and
    return a human-readable schema string.

    Returns:
        A multi-line string listing every public table and its columns (with types),
        or an error message if the database cannot be opened.
    """
    try:
        db = _get_db()
        tables = db.list_tables()

        if not tables:
            return "No tables found in the public schema."

        schema_info = "GCData Analytics Database Schema (PostgreSQL / Supabase):\n"

        for table_entry in tables:
            table_name = table_entry["name"]
            try:
                details = db.describe_table(table_name)
                cols = ", ".join(
                    f"{c['name']} ({c['type']})"
                    for c in details.get("columns", [])
                )
                schema_info += f"\nTable: {table_name}\nColumns: {cols}\n"
            except Exception:
                schema_info += f"\nTable: {table_name}\nColumns: (could not be retrieved)\n"

        return schema_info

    except Exception as exc:
        return f"Error retrieving schema: {exc}"
