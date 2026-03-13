from __future__ import annotations

import re
from functools import cached_property
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|MERGE|"
    r"CALL|EXECUTE|VACUUM|ANALYZE|COPY|COMMENT|ATTACH|DETACH)\b",
    re.IGNORECASE,
)
ALLOWED_PREFIXES = ("SELECT", "WITH")


class QueryValidationError(ValueError):
    """Raised when a query is not safe for read-only execution."""


class DatabaseClient:
    def __init__(self, database_url: str, default_schema: str) -> None:
        self.database_url = database_url
        self.default_schema = default_schema
        self._table_names: dict[str, list[str]] = {}
        self._view_names: dict[str, list[str]] = {}
        self._column_details: dict[str, list[dict[str, Any]]] = {}

    @cached_property
    def engine(self) -> Engine:
        return create_engine(self.database_url, pool_pre_ping=True, future=True)

    @cached_property
    def dialect_name(self) -> str:
        return self.engine.dialect.name

    def normalise_limit(self, requested: int | None, default: int, maximum: int) -> int:
        if requested is None:
            return default
        return max(1, min(int(requested), maximum))

    def _inspector(self):
        return inspect(self.engine)

    def _get_table_names(self, schema: str | None) -> list[str]:
        target = schema or "None"
        if target not in self._table_names:
            if self.dialect_name == "duckdb":
                with self.engine.connect() as conn:
                    res = conn.execute(text("SHOW TABLES")).fetchall()
                    self._table_names[target] = [row[0] for row in res]
            else:
                self._table_names[target] = self._inspector().get_table_names(schema=schema)
        return self._table_names[target]

    def _get_view_names(self, schema: str | None) -> list[str]:
        target = schema or "None"
        if target not in self._view_names:
            if self.dialect_name == "duckdb":
                # For simplicity, we'll treat all as tables in SHOW TABLES
                # DuckDB doesn't separate them as clearly in a simple SHOW TABLES
                self._view_names[target] = []
            else:
                self._view_names[target] = self._inspector().get_view_names(schema=schema)
        return self._view_names[target]

    def _get_columns(self, table_name: str, schema: str | None) -> list[dict[str, Any]]:
        key = f"{schema or 'None'}.{table_name}"
        if key not in self._column_details:
            if self.dialect_name == "duckdb":
                with self.engine.connect() as conn:
                    # DuckDB's PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
                    res = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
                    self._column_details[key] = [
                        {
                            "name": row[1],
                            "type": row[2],
                            "nullable": not row[3],
                            "default": row[4],
                            "primary_key": row[5]
                        }
                        for row in res
                    ]
            else:
                self._column_details[key] = self._inspector().get_columns(table_name, schema=schema)
        return self._column_details[key]

    def _resolve_schema(self, schema: str | None) -> str | None:
        if schema:
            return schema
        if self.dialect_name == "postgresql":
            return self.default_schema
        if self.dialect_name == "duckdb":
            return None
        return None

    def resolve_schema(self, schema: str | None) -> str | None:
        return self._resolve_schema(schema)

    def _quote_identifier(self, name: str) -> str:
        return self.engine.dialect.identifier_preparer.quote_identifier(name)

    def _qualified_name(self, table_name: str, schema: str | None) -> str:
        if schema:
            return f"{self._quote_identifier(schema)}.{self._quote_identifier(table_name)}"
        return self._quote_identifier(table_name)

    def _clean_query(self, query: str) -> str:
        cleaned = query.strip().rstrip(";")
        if not cleaned:
            raise QueryValidationError("Query must not be empty.")
        if ";" in cleaned:
            raise QueryValidationError("Only a single SQL statement is allowed.")
        if not cleaned.upper().startswith(ALLOWED_PREFIXES):
            raise QueryValidationError("Only SELECT queries and CTEs are allowed.")
        if FORBIDDEN_SQL_PATTERN.search(cleaned):
            raise QueryValidationError("Query contains a forbidden SQL keyword.")
        return cleaned

    def get_database_overview(self, schema: str | None = None) -> dict[str, Any]:
        target_schema = self._resolve_schema(schema)
        table_names = self._get_table_names(schema=target_schema)
        view_names = self._get_view_names(schema=target_schema)

        return {
            "dialect": self.dialect_name,
            "database": self.engine.url.database,
            "schema": target_schema,
            "table_count": len(table_names),
            "view_count": len(view_names),
            "tables": [
                {
                    "name": table_name,
                    "schema": target_schema,
                    "column_count": len(self._get_columns(table_name, schema=target_schema)),
                }
                for table_name in table_names
            ],
            "views": [
                {"name": view_name, "schema": target_schema}
                for view_name in view_names
            ],
        }

    def list_tables(self, schema: str | None = None) -> list[dict[str, Any]]:
        target_schema = self._resolve_schema(schema)
        table_names = self._get_table_names(schema=target_schema)
        view_names = self._get_view_names(schema=target_schema)
        resources: list[dict[str, Any]] = []

        for table_name in table_names:
            resources.append(
                {
                    "name": table_name,
                    "schema": target_schema,
                    "kind": "table",
                    "column_count": len(self._get_columns(table_name, schema=target_schema)),
                }
            )

        for view_name in view_names:
            resources.append(
                {
                    "name": view_name,
                    "schema": target_schema,
                    "kind": "view",
                    "column_count": len(self._get_columns(view_name, schema=target_schema)),
                }
            )

        return sorted(resources, key=lambda item: (item["kind"], item["name"]))

    def describe_table(self, table_name: str, schema: str | None = None) -> dict[str, Any]:
        target_schema = self._resolve_schema(schema)
        available_tables = self._get_table_names(schema=target_schema)
        available_views = self._get_view_names(schema=target_schema)

        if table_name not in available_tables and table_name not in available_views:
            raise ValueError(
                f"Table or view '{table_name}' was not found in schema '{target_schema}'."
            )

        if self.dialect_name == "duckdb":
            cols = self._get_columns(table_name, schema=target_schema)
            return {
                "name": table_name,
                "schema": target_schema,
                "kind": "table", # default to table for duckdb
                "columns": [
                    {
                        "name": c["name"],
                        "type": str(c["type"]),
                        "nullable": c["nullable"],
                        "default": str(c["default"]) if c["default"] is not None else None,
                    }
                    for c in cols
                ],
                "primary_key": [c["name"] for c in cols if c.get("primary_key")],
                "foreign_keys": [], # DuckDB doesn't easily expose FKs via simple PRAGMA
            }

        inspector = self._inspector()
        return {
            "name": table_name,
            "schema": target_schema,
            "kind": "view" if table_name in available_views else "table",
            "columns": [
                {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column.get("nullable", True),
                    "default": str(column.get("default"))
                    if column.get("default") is not None
                    else None,
                }
                for column in self._get_columns(table_name, schema=target_schema)
            ],
            "primary_key": inspector.get_pk_constraint(
                table_name, schema=target_schema
            ).get("constrained_columns", []),
            "foreign_keys": inspector.get_foreign_keys(
                table_name, schema=target_schema
            ),
        }

    def preview_table(
        self,
        table_name: str,
        schema: str | None = None,
        limit: int = 25,
    ) -> pd.DataFrame:
        self.describe_table(table_name, schema=schema)
        target_schema = self._resolve_schema(schema)
        qualified_name = self._qualified_name(table_name, target_schema)
        statement = text(f"SELECT * FROM {qualified_name} LIMIT :limit")
        with self.engine.connect() as connection:
            return pd.read_sql_query(statement, connection, params={"limit": limit})

    def run_read_only_query(self, query: str, limit: int) -> pd.DataFrame:
        cleaned_query = self._clean_query(query)
        statement = text(
            f"SELECT * FROM ({cleaned_query}) AS mcp_query_result LIMIT :limit"
        )
        with self.engine.connect() as connection:
            return pd.read_sql_query(statement, connection, params={"limit": limit})

    @staticmethod
    def dataframe_to_records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
        return dataframe.where(pd.notnull(dataframe), None).to_dict(orient="records")

    @staticmethod
    def dataframe_column_types(dataframe: pd.DataFrame) -> list[dict[str, str]]:
        return [
            {"name": column_name, "dtype": str(dtype)}
            for column_name, dtype in dataframe.dtypes.items()
        ]
