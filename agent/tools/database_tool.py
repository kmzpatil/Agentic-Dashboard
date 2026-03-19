"""Async PostgreSQL execution layer with validation, caching, and timeouts."""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Any, Optional

import asyncpg

from config.settings import get_settings
from models.schemas import AgentError, QueryResult, ValidationResult
from tools.sql_validator import SQLValidator

logger = logging.getLogger("agent.database_tool")


class _LRUCache:
    """Simple thread-unsafe LRU cache with TTL."""

    def __init__(self, maxsize: int = 256, ttl_seconds: int = 60):
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key in self._store:
            ts, val = self._store[key]
            if time.time() - ts < self._ttl:
                self._store.move_to_end(key)
                return val
            del self._store[key]
        return None

    def put(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)


class DatabaseTool:
    """Execute validated SQL against PostgreSQL via asyncpg."""

    def __init__(self, pool: asyncpg.Pool, validator: SQLValidator) -> None:
        self._pool = pool
        self._validator = validator
        settings = get_settings()
        self._cache = _LRUCache(maxsize=256, ttl_seconds=settings.CACHE_TTL_SECONDS)
        self._timeout_ms = settings.DB_STATEMENT_TIMEOUT_MS

    async def execute(self, sql: str, timeout_ms: int | None = None, use_cache: bool = True) -> QueryResult:
        """Validate, optionally cache-check, and execute SQL."""
        timeout = timeout_ms or self._timeout_ms

        # 1. Validate
        schema = self._validator._schema  # uses validator's current schema
        result = self._validator.validate(sql, schema)
        if not result.valid:
            raise AgentError(
                message=f"SQL validation failed: {result.error}",
                agent="DatabaseTool",
                recoverable=True,
                user_message="The generated query had an issue. Retrying...",
            )
        exec_sql = result.fixed_sql or sql

        # 2. Cache check
        cache_key = hashlib.sha256(exec_sql.encode()).hexdigest()
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.info("Cache HIT for query (hash=%s)", cache_key[:12])
                return cached

        # 3. Execute with timeout
        start = time.time()
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(f"SET statement_timeout = {timeout}")
                rows = await conn.fetch(exec_sql)
        except asyncpg.exceptions.QueryCanceledError:
            raise AgentError(
                message=f"Query timed out after {timeout}ms",
                agent="DatabaseTool",
                recoverable=True,
                user_message="The query took too long. Try a simpler question.",
            )
        except Exception as exc:
            logger.error("DB execute error: %s | sql=%s", exc, exec_sql[:200])
            raise AgentError(
                message=str(exc),
                agent="DatabaseTool",
                recoverable=False,
                user_message="Database error. Please try again.",
            )
        elapsed_ms = int((time.time() - start) * 1000)

        if not rows:
            qr = QueryResult(columns=[], rows=[], row_count=0, execution_ms=elapsed_ms)
        else:
            columns = list(rows[0].keys())
            data = [list(r.values()) for r in rows]
            qr = QueryResult(columns=columns, rows=data, row_count=len(data), execution_ms=elapsed_ms)

        logger.info("Query executed in %dms, %d rows returned | sql=%s", elapsed_ms, qr.row_count, exec_sql[:120])

        # 4. Cache result
        if use_cache:
            self._cache.put(cache_key, qr)

        return qr

    async def explain(self, sql: str) -> dict:
        """Run EXPLAIN (FORMAT JSON) and return the plan."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"EXPLAIN (FORMAT JSON) {sql}")
            if rows:
                return rows[0][0]
            return {}

    async def get_table_sample(self, table: str, n: int = 5) -> QueryResult:
        """Fetch a small sample from a table (validated table name)."""
        if not table.isidentifier():
            raise AgentError(message="Invalid table name", agent="DatabaseTool", user_message="Invalid table.")
        sql = f"SELECT * FROM {table} LIMIT {n}"
        # We bypass SELECT * check here intentionally for sampling
        start = time.time()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql)
        elapsed_ms = int((time.time() - start) * 1000)
        if not rows:
            return QueryResult(columns=[], rows=[], row_count=0, execution_ms=elapsed_ms)
        columns = list(rows[0].keys())
        data = [list(r.values()) for r in rows]
        return QueryResult(columns=columns, rows=data, row_count=len(data), execution_ms=elapsed_ms)
