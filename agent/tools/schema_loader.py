"""Live PostgreSQL schema introspection with caching and relevance search."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

import asyncpg

from config.settings import get_settings

logger = logging.getLogger("agent.schema_loader")

# Ground-truth tables expected in the frammer schema.
_KNOWN_TABLES = {
    "channels", "clients", "created_assets", "output_types", "subscription_plans",
    "client_subscriptions", "asset_metrics", "usage_logs", "billing_events",
    "campaigns", "campaign_assets", "team_members", "workspaces", "workspace_members",
    "notifications", "audit_logs", "api_keys", "webhooks", "integrations",
}


class SchemaLoader:
    """Introspects the live PostgreSQL database and caches schema metadata."""

    def __init__(self) -> None:
        self._schema: dict[str, list[str]] = {}
        self._foreign_keys: dict[str, list[dict[str, str]]] = {}
        self._row_counts: dict[str, int] = {}
        self._loaded = False
        self._pool: Optional[asyncpg.Pool] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def init(self, pool: asyncpg.Pool | None = None) -> None:
        """Load schema from the live database (call once at startup)."""
        settings = get_settings()
        if pool is not None:
            self._pool = pool
        elif self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=settings.get_database_url(),
                min_size=1,
                max_size=3,
            )
        await self._introspect()
        self._loaded = True
        logger.info("SchemaLoader initialised – %d tables loaded", len(self._schema))

    async def refresh(self) -> None:
        """Re-introspect (called periodically by the orchestrator)."""
        await self._introspect()
        logger.info("Schema refreshed – %d tables", len(self._schema))

    # ── Public API ────────────────────────────────────────────────────────────

    def load_schema(self) -> dict[str, list[str]]:
        """Return the full schema dict {table_name: [columns]}."""
        return dict(self._schema)

    def get_compressed_schema(self) -> str:
        """Compact string for fast-path prompts (table + columns, no extras)."""
        lines: list[str] = []
        for table, cols in sorted(self._schema.items()):
            lines.append(f"{table}({', '.join(cols)})")
        return "\n".join(lines)

    def get_rich_schema(self) -> str:
        """Detailed string for deep-path prompts (includes FKs and row counts)."""
        lines: list[str] = []
        for table, cols in sorted(self._schema.items()):
            rc = self._row_counts.get(table, "?")
            lines.append(f"TABLE {table}  (~{rc} rows)")
            for col in cols:
                lines.append(f"  - {col}")
            fks = self._foreign_keys.get(table, [])
            for fk in fks:
                lines.append(
                    f"  FK: {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                )
            lines.append("")
        return "\n".join(lines)

    def get_relevant_tables(self, query: str) -> list[str]:
        """Return tables most likely relevant to *query* using keyword matching."""
        query_lower = query.lower()
        query_tokens = set(re.findall(r"[a-z_]+", query_lower))
        scored: list[tuple[str, float]] = []
        for table, cols in self._schema.items():
            score = 0.0
            # Exact table name mention
            if table.lower() in query_lower:
                score += 5.0
            # Singular/partial match
            for token in query_tokens:
                if token in table.lower() or table.lower().startswith(token):
                    score += 2.0
                for col in cols:
                    if token in col.lower():
                        score += 1.0
            if score > 0:
                scored.append((table, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        # Always return at least the top tables, and anything with score > 0
        result = [t for t, _ in scored[:8]]
        if not result:
            # Fallback: return core tables
            result = [t for t in ["clients", "created_assets", "billing_events", "asset_metrics", "channels"] if t in self._schema]
        return result

    def validate_table(self, table: str) -> bool:
        return table.lower() in {t.lower() for t in self._schema}

    def validate_column(self, table: str, col: str) -> bool:
        cols = self._schema.get(table, [])
        return col.lower() in {c.lower() for c in cols}

    def get_foreign_keys(self) -> dict[str, list[dict[str, str]]]:
        return dict(self._foreign_keys)

    # ── Private introspection ─────────────────────────────────────────────────

    async def _introspect(self) -> None:
        assert self._pool is not None, "Pool not initialised – call init() first"
        async with self._pool.acquire() as conn:
            # Columns
            rows = await conn.fetch(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
                """
            )
            schema: dict[str, list[str]] = {}
            for r in rows:
                schema.setdefault(r["table_name"], []).append(r["column_name"])
            self._schema = schema

            # Foreign keys
            fk_rows = await conn.fetch(
                """
                SELECT
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name  AS referenced_table,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                """
            )
            fks: dict[str, list[dict[str, str]]] = {}
            for r in fk_rows:
                fks.setdefault(r["table_name"], []).append({
                    "column": r["column_name"],
                    "referenced_table": r["referenced_table"],
                    "referenced_column": r["referenced_column"],
                })
            self._foreign_keys = fks

            # Row counts (approximate via pg_stat)
            count_rows = await conn.fetch(
                """
                SELECT relname AS table_name, n_live_tup AS row_count
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                """
            )
            self._row_counts = {r["table_name"]: r["row_count"] for r in count_rows}
