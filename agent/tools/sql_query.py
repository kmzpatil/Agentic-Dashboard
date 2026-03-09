"""
Tool: execute_sql_query
Executes a read-only SELECT query against the Frammer SQLite database
and returns the result as a JSON string (list of row objects).
"""

import sqlite3
import pandas as pd

DB_PATH = "frammer_analytics.db"

# Mutations that are never allowed
FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"}


def _get_connection() -> sqlite3.Connection:
    """Open a read-only connection to the Frammer database."""
    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def execute_sql_query(query: str) -> str:
    """
    Execute a SELECT SQL query and return the results as a JSON string.

    Args:
        query: A valid SQLite SELECT statement.

    Returns:
        JSON string (list of records) on success, or an error message string.
    """
    # Guard against write operations
    if any(kw in query.upper() for kw in FORBIDDEN_KEYWORDS):
        return "Error: Only read-only SELECT queries are allowed."

    try:
        conn = _get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_json(orient="records")

    except Exception as exc:
        return f"SQL Execution Error: {exc}"
