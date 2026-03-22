"""
service.py
----------
Custom KPI CRUD + execution service.

Responsibilities:
  - ensure_kpi_table()     : Create kpi_definitions table if not present
  - create_kpi()           : Parse → validate → store DSL
  - list_kpis()            : Retrieve all KPI definitions
  - execute_kpi()          : Compile DSL → run SQL → compute insights → cache result
  - compute_insights()     : Deterministic statistics (no LLM at runtime)

Caching:
  - Simple in-memory dict keyed by hash(dsl_json + granularity + auth_scope)
  - Avoids redundant DB queries for the same KPI within a server session
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from backend.db.pool import query
from backend.kpi.compiler import compile_dsl, build_execution_params
from backend.kpi.parser import parse_formula_mode, parse_nl_mode
from backend.kpi.validator import validate_dsl
from backend.queries.analytics_shared import build_access_filter

logger = logging.getLogger("frammer.kpi.service")

# ── In-memory result cache ────────────────────────────────────────────────────
_RESULT_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_MAX = 256  # evict oldest when full


def _cache_key(kpi_id: int, dsl: dict[str, Any], auth_scope: str) -> str:
    payload = json.dumps({"id": kpi_id, "dsl": dsl, "scope": auth_scope}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _cache_get(key: str) -> dict[str, Any] | None:
    return _RESULT_CACHE.get(key)


def _cache_set(key: str, value: dict[str, Any]) -> None:
    if len(_RESULT_CACHE) >= _CACHE_MAX:
        # Remove oldest entry
        oldest = next(iter(_RESULT_CACHE))
        del _RESULT_CACHE[oldest]
    _RESULT_CACHE[key] = value


# ── Table bootstrap ───────────────────────────────────────────────────────────

def ensure_kpi_table() -> None:
    """Create kpi_definitions table if it does not exist yet, and heal any missing columns."""
    # Create table (no-op if already exists)
    query("""
    CREATE TABLE IF NOT EXISTS kpi_definitions (
        id          SERIAL PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT,
        dsl_json    JSONB NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Idempotently add created_by in case the table was created without it
    query("""
    ALTER TABLE kpi_definitions
        ADD COLUMN IF NOT EXISTS created_by TEXT;
    """)
    query("""
    CREATE INDEX IF NOT EXISTS idx_kpi_definitions_created_at
        ON kpi_definitions (created_at DESC);
    """)


# ── Create ────────────────────────────────────────────────────────────────────

def create_kpi(
    name: str,
    mode: str,
    expression: str,
    description: str | None = None,
    time_granularity: str = "month",
    created_by: str | None = None,
) -> dict[str, Any]:
    """
    Full pipeline: parse → validate → persist.

    Args:
        name:             Human-readable KPI name
        mode:             'formula' or 'natural_language'
        expression:       The formula string or NL description
        description:      Optional free-text description
        time_granularity: 'day', 'week', or 'month'
        created_by:       Auth user identifier for audit

    Returns:
        Stored KPI record as dict {id, name, description, dsl_json, created_at}
    """
    # 1. Parse expression → DSL JSON
    if mode == "formula":
        dsl = parse_formula_mode(expression, time_granularity)
    elif mode == "natural_language":
        import sys
        from pathlib import Path
        agent_dir = str(Path(__file__).resolve().parent.parent.parent / "agent")
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        from kpi_generator import generate_kpi_sql
        
        result = generate_kpi_sql(expression, time_granularity)

        dsl = {
            "type": "raw_sql",
            "sql": result["sql"],
            "formula": result.get("formula", expression),
            "time_granularity": time_granularity,
            "filters": []
        }
    else:
        raise ValueError(f"Unknown mode '{mode}'. Must be 'formula' or 'natural_language'.")

    # 2. Validate DSL
    validate_dsl(dsl)

    # 3. Persist to DB
    ensure_kpi_table()
    insert_sql = """
    INSERT INTO kpi_definitions (name, description, dsl_json, created_by)
    VALUES ($1, $2, $3, $4)
    RETURNING id, name, description, dsl_json::text, created_at::text;
    """
    result = query(insert_sql, [name, description, json.dumps(dsl), created_by])
    if not result.rows:
        raise RuntimeError("KPI insert returned no rows.")

    row = result.rows[0]
    stored_dsl = json.loads(row["dsl_json"]) if isinstance(row["dsl_json"], str) else row["dsl_json"]
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "dsl_json": stored_dsl,
        "created_at": row.get("created_at"),
    }


# ── List ──────────────────────────────────────────────────────────────────────

def list_kpis(created_by: str | None = None) -> list[dict[str, Any]]:
    """Return KPI definitions ordered by creation date (newest first).

    Args:
        created_by: If provided, only return KPIs created by this user.
    """
    ensure_kpi_table()
    if created_by:
        sql = """
        SELECT id, name, description, dsl_json::text, created_at::text
        FROM kpi_definitions
        WHERE created_by = $1
        ORDER BY created_at DESC;
        """
        result = query(sql, [created_by])
    else:
        sql = """
        SELECT id, name, description, dsl_json::text, created_at::text
        FROM kpi_definitions
        ORDER BY created_at DESC;
        """
        result = query(sql)
    rows = []
    for row in result.rows:
        dsl = json.loads(row["dsl_json"]) if isinstance(row["dsl_json"], str) else row["dsl_json"]
        rows.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "dsl_json": dsl,
            "created_at": row.get("created_at"),
        })
    return rows


# ── Execute ───────────────────────────────────────────────────────────────────

def execute_kpi(kpi_id: int, auth: Any) -> dict[str, Any]:
    """
    Retrieve a KPI by ID, compile its DSL to SQL, run it, and return
    time-series data plus deterministic insights.

    Args:
        kpi_id: ID of the kpi_definitions row
        auth:   AuthContext from require_auth (used for role-scoped filtering)

    Returns:
        {id, name, dsl_json, time_series: [{period, value}], insights: {...}}
    """
    ensure_kpi_table()

    # Fetch KPI definition
    fetch_sql = """
    SELECT id, name, description, dsl_json::text, created_at::text
    FROM kpi_definitions
    WHERE id = $1;
    """
    result = query(fetch_sql, [kpi_id])
    if not result.rows:
        raise ValueError(f"KPI with id={kpi_id} not found.")

    row = result.rows[0]
    dsl = json.loads(row["dsl_json"]) if isinstance(row["dsl_json"], str) else row["dsl_json"]

    # Build auth scope string for cache key
    auth_scope = _auth_scope_str(auth)
    cache_key = _cache_key(kpi_id, dsl, auth_scope)

    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("KPI %d result served from cache.", kpi_id)
        return cached

    # Build access filter — granularity uses $1, auth params start at $2
    access_filter = build_access_filter(auth, start_index=2, video_alias="rv")

    # Compile DSL → SQL
    sql = compile_dsl(dsl, access_filter)
    params = build_execution_params(dsl, access_filter)

    # Execute
    logger.info("Executing custom KPI id=%d (type=%s)", kpi_id, dsl.get("type"))
    exec_result = query(sql, params)

    # Normalise rows to [{period, value}]
    time_series = [
        {
            "period": str(r["period"]) if r.get("period") is not None else None,
            "value": float(r["value"]) if r.get("value") is not None else 0.0,
        }
        for r in exec_result.rows
        if r.get("period") is not None
    ]

    # Strip trailing zero-value periods — these are empty future/boundary dates
    # that produce misleading "last value = 0" on the card and in insights.
    # We keep at least one data point even if all are zero.
    while len(time_series) > 1 and time_series[-1]["value"] == 0.0:
        time_series.pop()

    insights = compute_insights(time_series, row["name"])

    response = {
        "id": row["id"],
        "name": row["name"],
        "description": row.get("description"),
        "dsl_json": dsl,
        "time_series": time_series,
        "insights": insights,
    }

    _cache_set(cache_key, response)
    return response


# ── Insights ──────────────────────────────────────────────────────────────────

def compute_insights(time_series: list[dict[str, Any]], kpi_name: str = "") -> dict[str, Any]:
    """
    Compute deterministic statistical insights from time-series data.
    NO LLM is used — all calculations are pure Python.

    Returns:
        {trend, percentage_change, max_point, min_point, summary}
    """
    if not time_series:
        return {
            "trend": "no_data",
            "percentage_change": 0.0,
            "max_point": None,
            "min_point": None,
            "summary": "No data available for this KPI.",
        }

    values = [float(p.get("value") or 0) for p in time_series]

    # Percentage change: compare average of last 3 periods vs first 3
    window = min(3, len(values))
    earlier_avg = sum(values[:window]) / window
    recent_avg = sum(values[-window:]) / window

    if earlier_avg == 0:
        pct_change = 0.0
    else:
        pct_change = round(((recent_avg - earlier_avg) / abs(earlier_avg)) * 100, 2)

    if pct_change > 5:
        trend = "up"
    elif pct_change < -5:
        trend = "down"
    else:
        trend = "stable"

    max_point = max(time_series, key=lambda x: float(x.get("value") or 0))
    min_point = min(time_series, key=lambda x: float(x.get("value") or 0))

    # Human-readable 1-line summary (deterministic, no LLM)
    direction_word = {"up": "increased", "down": "decreased", "stable": "remained stable"}[trend]
    if trend == "stable":
        summary = f"{kpi_name or 'This KPI'} has remained stable over the analyzed period."
    else:
        summary = (
            f"{kpi_name or 'This KPI'} has {direction_word} by "
            f"{abs(pct_change):.1f}% over the analyzed period. "
            f"Peak was {float(max_point.get('value', 0)):.2f} on {max_point.get('period')}."
        )

    return {
        "trend": trend,
        "percentage_change": pct_change,
        "max_point": {
            "period": str(max_point.get("period")),
            "value": float(max_point.get("value") or 0),
        },
        "min_point": {
            "period": str(min_point.get("period")),
            "value": float(min_point.get("value") or 0),
        },
        "summary": summary,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_scope_str(auth: Any) -> str:
    """Produce a stable cache-key fragment from the auth context."""
    if auth is None:
        return "no_auth"
    role = getattr(auth, "role", "unknown")
    client = getattr(auth, "client_name", None) or ""
    user_id = getattr(auth, "user_id", None) or ""
    return f"{role}:{client}:{user_id}"
