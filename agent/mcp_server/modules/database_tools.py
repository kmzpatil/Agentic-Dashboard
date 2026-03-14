from __future__ import annotations

import json
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from ..config import ServerSettings
from ..database import DatabaseClient, QueryValidationError


@dataclass
class DatabaseToolModule:
    db: DatabaseClient
    settings: ServerSettings

    def register(self, mcp: FastMCP) -> None:
        @mcp.tool()
        def get_database_overview(schema: str | None = None) -> str:
            """Return a compact overview of the connected database, schema, tables, and views."""
            try:
                overview = self.db.get_database_overview(schema=schema)
            except Exception as exc:
                return f"Error: {exc}"
            return json.dumps(overview, indent=2, default=str)

        @mcp.tool()
        def list_tables(schema: str | None = None) -> str:
            """List tables and views available to the agent in the configured database schema."""
            try:
                tables = self.db.list_tables(schema=schema)
            except Exception as exc:
                return f"Error: {exc}"
            return json.dumps(tables, indent=2, default=str)

        @mcp.tool()
        def describe_table(table_name: str, schema: str | None = None) -> str:
            """Describe a table or view, including columns, primary keys, and foreign keys."""
            try:
                table_details = self.db.describe_table(table_name, schema=schema)
            except Exception as exc:
                return f"Error: {exc}"
            return json.dumps(table_details, indent=2, default=str)

        @mcp.tool()
        def search_table_schemas(query: str, schema: str | None = None, limit: int = 5) -> str:
            """Search for relevant table schemas based on a natural language query using RAG."""
            try:
                results = self.db.search_table_schemas(query, schema=schema, limit=limit)
            except Exception as exc:
                return f"Error: {exc}"
            return json.dumps(results, indent=2, default=str)


        @mcp.tool()
        def preview_table(
            table_name: str,
            schema: str | None = None,
            limit: int | None = None,
        ) -> str:
            """Return sample rows from a table or view without mutating the database."""
            safe_limit = self.db.normalise_limit(
                limit,
                self.settings.default_preview_limit,
                self.settings.max_preview_limit,
            )
            try:
                dataframe = self.db.preview_table(
                    table_name,
                    schema=schema,
                    limit=safe_limit,
                )
            except Exception as exc:
                return f"Error: {exc}"
            payload = {
                "table": table_name,
                "schema": self.db.resolve_schema(schema),
                "row_count": len(dataframe.index),
                "columns": self.db.dataframe_column_types(dataframe),
                "rows": self.db.dataframe_to_records(dataframe),
            }
            return json.dumps(payload, indent=2, default=str)

        @mcp.tool()
        def execute_sql_query(query: str, limit: int | None = None) -> str:
            """Execute a read-only SQL query and return JSON rows capped by the requested limit."""
            safe_limit = self.db.normalise_limit(
                limit,
                self.settings.default_query_limit,
                self.settings.max_query_limit,
            )
            try:
                dataframe = self.db.run_read_only_query(query, limit=safe_limit)
            except (QueryValidationError, Exception) as exc:
                return f"Error: {exc}"
            payload = {
                "row_count": len(dataframe.index),
                "limit_applied": safe_limit,
                "columns": self.db.dataframe_column_types(dataframe),
                "rows": self.db.dataframe_to_records(dataframe),
            }
            return json.dumps(payload, indent=2, default=str)
