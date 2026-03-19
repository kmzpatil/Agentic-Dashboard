from __future__ import annotations

import re
import threading
from functools import cached_property
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
import time
import logging

logger = logging.getLogger("frammer.database")

# Heavy imports moved to properties to avoid startup hang
SentenceTransformer = None
cosine = None



FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|MERGE|"
    r"CALL|EXECUTE|VACUUM|ANALYZE|COPY|COMMENT|ATTACH|DETACH|app_users)\b",
    re.IGNORECASE,
)
ALLOWED_PREFIXES = ("SELECT", "WITH")

# ── Thread-safe shared schema index ──────────────────────────────────────────
_schema_lock = threading.Lock()
_shared_schema_index: list | None = None

# ── Thread-safe shared schema profile (column value discovery) ────────────────
_profile_lock = threading.Lock()
_shared_schema_profile: dict | None = None


class QueryValidationError(ValueError):
    """Raised when a query is not safe for read-only execution."""


class DatabaseClient:
    def __init__(self, database_url: str, default_schema: str) -> None:
        self.database_url = database_url
        self.default_schema = default_schema
        self._schema_index = None

    @cached_property
    def embedding_model(self) -> Any:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers is not installed")
        # Initialize a very small and fast embedding model
        return SentenceTransformer("all-MiniLM-L6-v2")

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

    def _resolve_schema(self, schema: str | None) -> str | None:
        if schema:
            return schema
        if self.dialect_name == "postgresql":
            return self.default_schema
        return None

    def resolve_schema(self, schema: str | None) -> str | None:
        return self._resolve_schema(schema)

    def _quote_identifier(self, name: str) -> str:
        return self.engine.dialect.identifier_preparer.quote_identifier(name)

    def _qualified_name(self, table_name: str, schema: str | None) -> str:
        if schema:
            return f"{self._quote_identifier(schema)}.{self._quote_identifier(table_name)}"
        return self._quote_identifier(table_name)

    @staticmethod
    def _strip_comments(query: str) -> str:
        """Remove SQL comments to prevent validation bypass and false positives."""
        query = re.sub(r'--[^\n]*', '', query)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        return query.strip()

    def _clean_query(self, query: str) -> str:
        cleaned = self._strip_comments(query.strip().rstrip(";"))
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
        inspector = self._inspector()
        table_names = inspector.get_table_names(schema=target_schema)
        view_names = inspector.get_view_names(schema=target_schema)

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
                    "column_count": len(
                        inspector.get_columns(table_name, schema=target_schema)
                    ),
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
        inspector = self._inspector()
        resources: list[dict[str, Any]] = []

        for table_name in inspector.get_table_names(schema=target_schema):
            resources.append(
                {
                    "name": table_name,
                    "schema": target_schema,
                    "kind": "table",
                    "column_count": len(
                        inspector.get_columns(table_name, schema=target_schema)
                    ),
                }
            )

        for view_name in inspector.get_view_names(schema=target_schema):
            resources.append(
                {
                    "name": view_name,
                    "schema": target_schema,
                    "kind": "view",
                    "column_count": len(
                        inspector.get_columns(view_name, schema=target_schema)
                    ),
                }
            )

        return sorted(resources, key=lambda item: (item["kind"], item["name"]))

    def describe_table(self, table_name: str, schema: str | None = None) -> dict[str, Any]:
        target_schema = self._resolve_schema(schema)
        inspector = self._inspector()
        available_tables = set(inspector.get_table_names(schema=target_schema))
        available_views = set(inspector.get_view_names(schema=target_schema))

        if table_name not in available_tables and table_name not in available_views:
            raise ValueError(
                f"Table or view '{table_name}' was not found in schema '{target_schema}'."
            )

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
                for column in inspector.get_columns(table_name, schema=target_schema)
            ],
            "primary_key": inspector.get_pk_constraint(
                table_name, schema=target_schema
            ).get("constrained_columns", []),
            "foreign_keys": inspector.get_foreign_keys(
                table_name, schema=target_schema
            ),
        }

    def build_schema_profile(self, schema: str | None = None) -> None:
        """Build a one-time cached profile of distinct values for low-cardinality text columns.
        Thread-safe; runs exactly once per process lifetime."""
        global _shared_schema_profile
        with _profile_lock:
            if _shared_schema_profile is not None:
                return
            target_schema = self._resolve_schema(schema)
            TEXT_TYPES = {"text", "character varying", "varchar", "char", "character"}
            profile: dict = {}
            tables = self.list_tables(schema=schema)
            for tbl in tables:
                table_name = tbl["name"]
                try:
                    details = self.describe_table(table_name, schema)
                except Exception:
                    continue
                qualified = self._qualified_name(table_name, target_schema)
                profile[table_name] = {}
                for col in details.get("columns", []):
                    col_name = col["name"]
                    raw_type = str(col["type"]).lower().split("(")[0].strip()
                    profile[table_name][col_name] = {"type": str(col["type"]), "values": None}
                    if raw_type not in TEXT_TYPES:
                        continue
                    qcol = self._quote_identifier(col_name)
                    try:
                        with self.engine.connect() as conn:
                            count = conn.execute(
                                text(f"SELECT COUNT(DISTINCT {qcol}) FROM {qualified}")
                            ).scalar()
                        if count is None or count > 50:
                            continue
                        with self.engine.connect() as conn:
                            rows = conn.execute(
                                text(
                                    f"SELECT DISTINCT {qcol} FROM {qualified} "
                                    f"WHERE {qcol} IS NOT NULL ORDER BY {qcol} LIMIT 50"
                                )
                            ).fetchall()
                        profile[table_name][col_name]["values"] = [
                            r[0] for r in rows if r[0] is not None
                        ]
                    except Exception:
                        continue
            _shared_schema_profile = profile
            logger.info("[db] Schema profile built: %d tables", len(profile))

    def get_schema_profile(self, schema: str | None = None) -> dict:
        """Return the cached schema profile, building it on first call."""
        global _shared_schema_profile
        if _shared_schema_profile is None:
            self.build_schema_profile(schema=schema)
        return _shared_schema_profile or {}

    def build_schema_index(self, schema: str | None = None) -> None:
        global _shared_schema_index
        with _schema_lock:
            if _shared_schema_index is not None:
                self._schema_index = _shared_schema_index
                return

            profile = self.get_schema_profile(schema=schema)
            tables = self.list_tables(schema=schema)
            index = []
            for tbl in tables:
                name = tbl["name"]
                kind = tbl["kind"]
                try:
                    details = self.describe_table(name, schema)
                    table_profile = profile.get(name, {})
                    cols_parts = []
                    for c in details.get("columns", []):
                        part = f"{c['name']} ({c['type']})"
                        vals = table_profile.get(c["name"], {}).get("values")
                        if vals:
                            part += f" [values: {', '.join(str(v) for v in vals)}]"
                        cols_parts.append(part)
                    cols_repr = ", ".join(cols_parts)
                    text_repr = f"{kind.capitalize()} {name}: columns are {cols_repr}."
                    sample_values_map = {
                        col_name: info["values"]
                        for col_name, info in table_profile.items()
                        if info.get("values")
                    }
                    index.append({
                        "name": name,
                        "kind": kind,
                        "text": text_repr,
                        "details": details,
                        "sample_values": sample_values_map,
                    })
                except Exception:
                    continue

            if not index:
                self._schema_index = []
                _shared_schema_index = []
                return

            texts = [item["text"] for item in index]
            embeddings = self.embedding_model.encode(texts)

            for i, item in enumerate(index):
                item["embedding"] = embeddings[i]

            _shared_schema_index = index
            self._schema_index = index

    def search_table_schemas(self, query: str, schema: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Search the table schemas using RAG and sentence-transformers."""
        if self._schema_index is None:
            self.build_schema_index(schema=schema)

        if not self._schema_index:
            return []

        from scipy.spatial.distance import cosine
        query_embedding = self.embedding_model.encode([query])[0]
        results = []
        for item in self._schema_index:
            dist = cosine(query_embedding, item["embedding"])
            similarity = 1 - dist
            results.append((similarity, item))

        results.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "name": item["name"],
                "kind": item["kind"],
                "similarity": float(sim),
                "details": item["details"],
                "sample_values": item.get("sample_values", {}),
            }
            for sim, item in results[:limit]
        ]

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

    def run_read_only_query(self, query: str, limit: int, auth: Any = None) -> pd.DataFrame:
        cleaned_query = self._strip_comments(query.strip().rstrip(";"))
        
        # Determine enforcement needs
        role = getattr(auth, "role", "website_admin")
        client_name = getattr(auth, "client_name", None)
        user_id = getattr(auth, "user_id", None)

        if role != "website_admin" and (client_name or user_id):
            # PROACTIVE SCOPING: We inject CTEs for core tables that are pre-filtered
            # by the user's client or user ID. This ensures that even if the agent
            # generates "SELECT * FROM raw_videos", it only sees allowed rows.
            
            scoping_ctes = []
            
            if client_name:
                # Filter for client_admin or restricted role by client_name
                client_filter = f"'{client_name}'"
                
                # Scope raw_videos
                scoping_ctes.append(f"""
                scoped_videos AS (
                    SELECT rv.* FROM raw_videos rv
                    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
                    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
                    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
                    WHERE COALESCE(ch."Client_Name", u."Client_Name") = {client_filter}
                )""")
                
                # Scope channels
                scoping_ctes.append(f"scoped_channels AS (SELECT * FROM channels WHERE \"Client_Name\" = {client_filter})")
                
                # Scope users
                scoping_ctes.append(f"scoped_users AS (SELECT * FROM users WHERE \"Client_Name\" = {client_filter})")
                
            elif role == "user" and user_id:
                # Filter for individual user
                scoping_ctes.append(f"scoped_videos AS (SELECT * FROM raw_videos WHERE \"User_ID\" = {user_id})")
                scoping_ctes.append(f"scoped_users AS (SELECT * FROM users WHERE \"User_ID\" = {user_id})")

            if scoping_ctes:
                # We rename the original tables in the user's query to use our scoped CTEs
                # This is done by adding more CTEs that alias the original names.
                # Note: DuckDB allows "with raw_videos as (...)" to override the physical table.
                
                final_scoping = ",\n".join(scoping_ctes)
                
                # We add aliases to override the physical tables with our scoped versions
                aliases = []
                if "scoped_videos" in final_scoping:
                    aliases.append("raw_videos AS (SELECT * FROM scoped_videos)")
                    aliases.append("created_assets AS (SELECT ca.* FROM created_assets ca JOIN scoped_videos sv ON sv.\"Video_ID\" = ca.\"Video_ID\")")
                    # FIX: Correct join for published_posts (pp does not have Video_ID, bridge via ca)
                    aliases.append("published_posts AS (SELECT pp.* FROM published_posts pp JOIN created_assets ca ON ca.\"Asset_ID\" = pp.\"Asset_ID\" JOIN scoped_videos sv ON sv.\"Video_ID\" = ca.\"Video_ID\")")
                    # NEW: Scope post_distribution and raw_video_channel
                    aliases.append("post_distribution AS (SELECT pd.* FROM post_distribution pd JOIN published_posts pp ON pp.\"Post_ID\" = pd.\"Post_ID\")")
                    aliases.append("raw_video_channel AS (SELECT rvc.* FROM raw_video_channel rvc JOIN scoped_videos sv ON sv.\"Video_ID\" = rvc.\"Video_ID\")")
                if "scoped_channels" in final_scoping:
                    aliases.append("channels AS (SELECT * FROM scoped_channels)")
                if "scoped_users" in final_scoping:
                    aliases.append("users AS (SELECT * FROM scoped_users)")
                
                full_cte_block = "WITH " + final_scoping + ",\n" + ",\n".join(aliases)
                
                # Now we wrap the user query. We need to handle if the user query 
                # ALREADY starts with WITH.
                if cleaned_query.upper().startswith("WITH"):
                    # We merge the WITH blocks
                    # "WITH user_cte as (...) SELECT ..." -> "WITH scoped_ctes..., user_cte as (...) SELECT ..."
                    # We strip the "WITH " from the user query
                    user_query_no_with = cleaned_query[4:].strip()
                    query = f"{full_cte_block},\n{user_query_no_with}"
                else:
                    query = f"{full_cte_block}\n{cleaned_query}"

        # Final validation and execution
        validated_query = self._clean_query(query)
        statement = text(
            f"WITH mcp_cte AS ({validated_query}) SELECT * FROM mcp_cte LIMIT :limit"
        )
        
        start_time = time.time()
        logger.info("Executing scoped SQL query...")
        
        with self.engine.connect() as connection:
            df = pd.read_sql_query(statement, connection, params={"limit": limit})
            duration = time.time() - start_time
            logger.info("SQL Execution COMPLETE. Duration: %.2fs. Rows: %d", duration, len(df))
            return df

    @staticmethod
    def dataframe_to_records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
        return dataframe.where(pd.notnull(dataframe), None).to_dict(orient="records")

    @staticmethod
    def dataframe_column_types(dataframe: pd.DataFrame) -> list[dict[str, str]]:
        return [
            {"name": column_name, "dtype": str(dtype)}
            for column_name, dtype in dataframe.dtypes.items()
        ]
