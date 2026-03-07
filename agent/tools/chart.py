"""
Tool: generate_plotly_chart
Executes a SELECT query and auto-generates a Plotly chart from the result.
Returns the chart as a serialised JSON string ready for a frontend renderer.
"""

import sqlite3
import pandas as pd
import plotly.express as px

DB_PATH = "frammer_analytics.db"

FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"}


def _get_connection() -> sqlite3.Connection:
    """Open a read-only connection to the Frammer database."""
    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def generate_plotly_chart(query: str) -> str:
    """
    Run a SELECT query and return a Plotly chart as a JSON string.

    Heuristics:
    - Column 0  → X axis
    - Column 1  → Y axis (must be numeric)
    - If X column name contains 'date' or 'time', a line chart is used;
      otherwise a bar chart is used.

    Args:
        query: A valid SQLite SELECT statement returning at least 2 columns.

    Returns:
        Plotly figure JSON string on success, or an error message string.
    """
    if any(kw in query.upper() for kw in FORBIDDEN_KEYWORDS):
        return "Error: Only read-only SELECT queries are allowed."

    try:
        conn = _get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty or len(df.columns) < 2:
            return (
                "Error: Query returned insufficient data to plot "
                "(need at least 2 columns)."
            )

        x_col = df.columns[0]
        y_col = df.columns[1]

        if not pd.api.types.is_numeric_dtype(df[y_col]):
            return "Error: Second column must be numeric to generate a meaningful chart."

        is_time_axis = (
            "date" in x_col.lower()
            or "time" in x_col.lower()
            or pd.api.types.is_datetime64_any_dtype(df[x_col])
        )

        if is_time_axis:
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")

        return fig.to_json()

    except Exception as exc:
        return f"Chart Generation Error: {exc}"
