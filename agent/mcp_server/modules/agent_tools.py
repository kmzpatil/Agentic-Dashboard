"""
agent_tools.py
--------------
MCP Tool Module that exposes all 5 ATLAS tools through the MCP server:
  - get_schema
  - get_metric_definitions
  - search_relevant_schemas
  - run_sql_query
  - build_chart

These are the analytical tools bound to the LLM in agent_groq.py.
Moving them here allows any MCP-compatible client to use them.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP

from ..config import ServerSettings
from ..database import DatabaseClient, QueryValidationError


# ── Shared in-memory query store (per-process, not per-request) ──────────────
# This allows build_chart to reference a prior run_sql_query result.
_query_store: Dict[str, List[Dict[str, Any]]] = {}
_latest_result_id: str = ""


@dataclass
class AgentToolModule:
    db: DatabaseClient
    settings: ServerSettings

    def register(self, mcp: FastMCP) -> None:

        # ── Tool 1: Schema ───────────────────────────────────────────────────
        @mcp.tool()
        def get_schema() -> str:
            """Retrieve the full database schema — all table names, column names, and types.
            ALWAYS call this FIRST before writing any SQL query so you use exact names."""
            try:
                tables = self.db.list_tables()
                schema_lines = []
                for table in tables:
                    details = self.db.describe_table(table)
                    cols = ", ".join(
                        f"{c['name']} ({c['type']})"
                        for c in details.get("columns", [])
                    )
                    schema_lines.append(f"Table: {table}\nColumns: {cols}")
                return "\n\n".join(schema_lines)
            except Exception as exc:
                return f"Error retrieving schema: {exc}"

        # ── Tool 2: Metric Definitions ───────────────────────────────────────
        @mcp.tool()
        def get_metric_definitions(query: str) -> str:
            """Look up business metric definitions, formulas, table names, join paths, and example SQL.
            Call this to understand how to correctly calculate a metric before writing SQL.
            Args:
                query: The user's question or a keyword describing the metric.
            """
            from tools.metric_definitions import retrieve_metric_definitions
            return retrieve_metric_definitions(query)

        # ── Tool 3: Semantic Schema Search ───────────────────────────────────
        @mcp.tool()
        def search_relevant_schemas(query: str, limit: int = 5) -> str:
            """Semantic search for database tables and columns relevant to a question.
            Uses CHESS-style RAG to find the most relevant schema elements.
            Args:
                query: Natural language description of the data you need.
                limit: Number of top-matching schemas to return.
            """
            try:
                results = self.db.search_table_schemas(query, limit=limit)
                return json.dumps(results, indent=2, default=str)
            except Exception as exc:
                return f"Schema search error: {exc}. Use get_schema instead."

        # ── Tool 4: SQL Query ────────────────────────────────────────────────
        @mcp.tool()
        def run_sql_query(sql: str, limit: int = 200) -> str:
            """Execute a read-only PostgreSQL SELECT query and return JSON results.
            Returns row_count, columns, result_id, and sample_rows on success.
            Returns an error on failure — read the error, fix the SQL, and retry.

            SQL RULES:
            - Use ONLY exact table/column names from get_schema()
            - Double-quote mixed-case columns: "Upload_Date", "User_Name"
            - Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')
            - Monthly grouping: date_trunc('month', to_date("Upload_Date",'YYYY-MM-DD'))::date AS month

            Args:
                sql: A valid PostgreSQL SELECT statement.
                limit: Maximum rows to return.
            """
            global _latest_result_id

            safe_limit = self.db.normalise_limit(
                limit,
                self.settings.default_query_limit,
                self.settings.max_query_limit,
            )

            try:
                dataframe = self.db.run_read_only_query(sql, limit=safe_limit)
            except (QueryValidationError, Exception) as exc:
                return f"SQL Error: {exc}\n\nFix the query and call run_sql_query again."

            records = self.db.dataframe_to_records(dataframe)
            result_id = str(uuid.uuid4())[:8]
            _query_store[result_id] = records
            _latest_result_id = result_id

            cols = list(dataframe.columns)
            sample = records[:5]

            return json.dumps({
                "status": "success",
                "result_id": result_id,
                "row_count": len(records),
                "columns": cols,
                "sample_rows": sample,
            }, default=str)

        # ── Tool 5: Build Chart ──────────────────────────────────────────────
        @mcp.tool()
        def build_chart(
            chart_type: str,
            x_column: str,
            y_columns: str,
            title: str,
            result_id: str = "",
        ) -> str:
            """Build a chart from SQL query results. Call AFTER run_sql_query.

            Args:
                chart_type: 'bar', 'line', or 'pie'.
                x_column: Exact column name for the X axis.
                y_columns: Column name(s) for the Y axis, comma-separated.
                title: Short chart title, max 8 words.
                result_id: Optional result_id from a prior run_sql_query. Uses latest if empty.
            """
            from tools.chart import generate_plotly_chart

            records = (
                _query_store.get(result_id)
                or (_latest_result_id and _query_store.get(_latest_result_id))
                or []
            )

            if not records:
                return "No data available. Run a SQL query first."

            attrs = {
                "type": chart_type,
                "x_axis": x_column,
                "y_axis": y_columns,
                "title": title,
            }
            xml = generate_plotly_chart(data_records=records, chart_attributes=attrs)

            if xml and xml.startswith("<?xml"):
                return f"Chart created: {title} ({chart_type}, {len(records)} data points)"

            return f"Chart failed: {xml or 'Unknown error'}"
