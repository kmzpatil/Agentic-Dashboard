"""
Tool: get_frammer_schema
Retrieves the live database schema (tables + columns) from the SQLite database.
Always call this before writing SQL to ensure column names are correct.
"""

import sqlite3

DB_PATH = "frammer_analytics.db"


def _get_connection() -> sqlite3.Connection:
    """Open a read-only connection to the Frammer database."""
    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def get_frammer_schema() -> str:
    """
    Inspect the database and return a human-readable schema string.

    Returns:
        A multi-line string listing every table and its columns (with types),
        or an error message if the database cannot be opened.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema_info = "Frammer AI Database Schema:\n"
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            col_details = [f"{col[1]} ({col[2]})" for col in columns]
            schema_info += (
                f"\nTable: {table_name}\n"
                f"Columns: {', '.join(col_details)}\n"
            )

        conn.close()
        return schema_info

    except Exception as exc:
        return f"Error retrieving schema: {exc}"
