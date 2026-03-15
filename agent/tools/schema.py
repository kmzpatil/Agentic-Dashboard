"""
Tool: get_frammer_schema
Retrieves the live database schema (tables + columns) via the shared MCP
DatabaseClient.  Works with any SQLAlchemy-supported backend.
Always call this before writing SQL to ensure table and column names are correct.
"""

from tools._db import get_db, get_default_schema


def get_frammer_schema() -> str:
    """
    Inspect the database and return a human-readable schema string.

    Uses the shared MCP DatabaseClient so it stays in sync with all
    other tools and benefits from connection pooling.

    Returns:
        A multi-line string listing every table and its columns (with types),
        or an error message if the database cannot be opened.
    """
    try:
        db = get_db()
        schema = get_default_schema()
        tables = db.list_tables(schema=schema)

        if not tables:
            return "No tables found in the database."

        schema_info = "Frammer AI Database Schema:\n"
        for tbl in tables:
            name = tbl["name"]
            try:
                details = db.describe_table(name, schema=schema)
                col_parts = []
                for col in details.get("columns", []):
                    nullable_tag = "" if col.get("nullable", True) else " NOT NULL"
                    col_parts.append(f"{col['name']} ({col['type']}{nullable_tag})")
                schema_info += f"\nTable: {name}\nColumns: {', '.join(col_parts)}\n"
            except Exception:
                schema_info += f"\nTable: {name}\nColumns: (could not inspect)\n"

        return schema_info

    except Exception as exc:
        return f"Error retrieving schema: {exc}"
