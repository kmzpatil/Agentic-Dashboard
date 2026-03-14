"""
Tool: get_frammer_schema
Retrieves the live database schema (tables + columns) using SQLAlchemy.
Works with any SQLAlchemy-supported backend (SQLite, PostgreSQL, etc.).
Always call this before writing SQL to ensure table and column names are correct.
"""

from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

# Load env so DATABASE_URL (or fallback) is available
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

from mcp_server.config import ServerSettings


def _get_engine():
    """Create an SQLAlchemy engine from the shared ServerSettings."""
    settings = ServerSettings.from_env()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def get_frammer_schema() -> str:
    """
    Inspect the database and return a human-readable schema string.

    Uses SQLAlchemy's inspector so it works with SQLite, PostgreSQL, etc.

    Returns:
        A multi-line string listing every table and its columns (with types),
        or an error message if the database cannot be opened.
    """
    try:
        engine = _get_engine()
        inspector = inspect(engine)
        settings = ServerSettings.from_env()

        # Resolve schema — None for SQLite, 'public' for Postgres, etc.
        schema = settings.default_schema if engine.dialect.name == "postgresql" else None

        table_names = inspector.get_table_names(schema=schema)
        view_names = inspector.get_view_names(schema=schema)
        all_names = sorted(set(table_names + view_names))

        if not all_names:
            return "No tables found in the database."

        schema_info = "Frammer AI Database Schema:\n"
        for table_name in all_names:
            columns = inspector.get_columns(table_name, schema=schema)
            col_parts = []
            for col in columns:
                nullable_tag = "" if col.get("nullable", True) else " NOT NULL"
                col_parts.append(f"{col['name']} ({col['type']}{nullable_tag})")
            schema_info += f"\nTable: {table_name}\nColumns: {', '.join(col_parts)}\n"

        return schema_info

    except Exception as exc:
        return f"Error retrieving schema: {exc}"
