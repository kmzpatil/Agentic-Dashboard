"""
mcptest.py — Frammer Analytics MCP Server
──────────────────────────────────────────
Exposes the four analytics tools as MCP endpoints served over streamable-HTTP.
Delegates all business logic to the shared tool modules in tools/ so the same
code path is used whether the agent calls tools directly (main_agent.py) or
through this server.

Database:
  All DB access goes through PostgreSQL. Set the following env vars (or put
  them in a .env file) before starting the server:

    POSTGRES_HOST      = <host>
    POSTGRES_PORT      = 5432        (default)
    POSTGRES_DB        = <dbname>
    POSTGRES_USER      = <user>
    POSTGRES_PASSWORD  = <password>
    POSTGRES_SSLMODE   = prefer      (use "require" for Supabase/Neon/Railway)

Run with:
    python mcptest.py
"""

import json

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env so POSTGRES_* vars are available before any tool import
load_dotenv()

from tools import (
    execute_sql_query,
    generate_plotly_chart,
    get_frammer_schema,
    retrieve_metric_definitions,
)

# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = FastMCP("Frammer_Analytics_Server")

# ── Tool registrations ────────────────────────────────────────────────────────

@mcp.tool()
def tool_retrieve_metric_definitions(search_term: str) -> str:
    """
    Simulates a Vector Search Semantic Layer.
    Look up exact business definitions and formulas for Frammer AI metrics
    (e.g. 'conversion rate', 'drop-off', 'usage hours') before writing SQL.
    """
    return retrieve_metric_definitions(search_term)


@mcp.tool()
def tool_get_frammer_schema() -> str:
    """
    Retrieves the PostgreSQL database schema (tables + columns).
    Always call this before writing a new SQL query to ensure column names
    are correct.
    """
    return get_frammer_schema()


@mcp.tool()
def tool_execute_sql_query(query: str, chart_attributes: str = "{}") -> str:
    """
    Executes a SELECT SQL query against the Frammer PostgreSQL database and
    returns a JSON payload containing the data records and chart attributes.

    Args:
        query:            A valid PostgreSQL SELECT statement.
        chart_attributes: A JSON string with chart config produced by the
                          orchestrator, e.g.
                          '{"type":"bar","x_axis":"month","y_axis":"revenue",
                            "title":"Monthly Revenue"}'.
                          Pass '{}' (default) when no chart config is available.
    """
    try:
        attrs = json.loads(chart_attributes)
    except json.JSONDecodeError:
        attrs = {}
    return execute_sql_query(query, chart_attributes=attrs)


@mcp.tool()
def tool_generate_plotly_chart(query: str) -> str:
    """
    Executes a SELECT SQL query against PostgreSQL and automatically generates
    a Plotly chart. Use when the user asks for a visual, chart, or trend.
    Returns the Plotly figure as a JSON string for the frontend renderer.
    """
    return generate_plotly_chart(query=query)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Frammer Analytics MCP Server (PostgreSQL backend)...")
    mcp.run("streamable-http")