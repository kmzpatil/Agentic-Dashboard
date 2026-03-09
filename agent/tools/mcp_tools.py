"""
tools/mcp_tools.py
------------------
LangChain @tool wrappers for every tool registered in the mcp_server.

Provides ALL_MCP_TOOLS – a list ready to be bound to any LangChain LLM:
    llm.bind_tools(ALL_MCP_TOOLS)

Covers:
  - DatabaseToolModule  : list_tables, describe_table, execute_sql
  - GCDataToolModule    : 9 domain analytics tools
"""

import json
from functools import lru_cache
from typing import Optional

from langchain_core.tools import tool

from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient, QueryValidationError
from sqlalchemy import text as _text


@lru_cache(maxsize=1)
def _db() -> DatabaseClient:
    s = ServerSettings.from_env()
    return DatabaseClient(database_url=s.database_url, default_schema=s.default_schema)


# ── Database tools ────────────────────────────────────────────────────────────

@tool
def mcp_list_tables() -> str:
    """List every table available in the GCData analytics database."""
    try:
        return json.dumps(_db().list_tables(), default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_describe_table(table_name: str) -> str:
    """Return the exact column names and types for a table in the GCData database."""
    try:
        return json.dumps(_db().describe_table(table_name), default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_execute_sql(query: str) -> str:
    """Execute a read-only PostgreSQL SELECT query against GCData. Returns JSON rows."""
    try:
        df = _db().run_read_only_query(query, limit=5000)
        return json.dumps({"rows": DatabaseClient.dataframe_to_records(df)}, default=str)
    except QueryValidationError as exc:
        return f"Error (validation): {exc}"
    except Exception as exc:
        return f"Error: {exc}"


# ── GCData analytics domain tools ─────────────────────────────────────────────

@tool
def mcp_get_channel_metrics(channel: Optional[str] = None) -> str:
    """Get per-channel social media post counts and durations from channel_metrics.
    Optionally filter by channel name (e.g. 'A', 'B')."""
    try:
        with _db().engine.connect() as conn:
            if channel:
                rows = conn.execute(
                    _text("SELECT * FROM public.channel_metrics WHERE channels = :ch ORDER BY channels"),
                    {"ch": channel},
                ).mappings().all()
            else:
                rows = conn.execute(
                    _text("SELECT * FROM public.channel_metrics ORDER BY channels")
                ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_top_channels_by_platform(platform: str, top_n: int = 10) -> str:
    """Get the top N channels ranked by post count on a given social platform.
    Platform must be one of: facebook, instagram, linkedin, reels, shorts, x, youtube, threads."""
    allowed = {"facebook", "instagram", "linkedin", "reels", "shorts", "x", "youtube", "threads"}
    p = platform.lower().strip()
    if p not in allowed:
        return f"Error: Unknown platform '{platform}'. Choose from: {', '.join(sorted(allowed))}"
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text(f"SELECT channels, {p} AS post_count FROM public.channel_metrics "
                      f"WHERE {p} IS NOT NULL ORDER BY {p} DESC LIMIT :n"),
                {"n": max(1, int(top_n))},
            ).mappings().all()
        return json.dumps({"platform": p, "top_channels": [dict(r) for r in rows]}, default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_monthly_trend() -> str:
    """Return monthly content volume and duration metrics ordered chronologically.
    Useful for time-series and trend charts."""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT * FROM public.monthly_counts_duration ORDER BY month")
            ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_language_breakdown() -> str:
    """Return per-language upload/create/publish statistics from language_statistics,
    sorted by published_count descending."""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT * FROM public.language_statistics ORDER BY published_count DESC NULLS LAST")
            ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_input_type_breakdown() -> str:
    """Return per-input-type upload/create/publish counts from input_type_metrics,
    sorted by published_count descending."""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT * FROM public.input_type_metrics ORDER BY published_count DESC NULLS LAST")
            ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_output_type_breakdown() -> str:
    """Return per-output-type upload/create/publish stats from output_type_statistics,
    sorted by published_count descending."""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT * FROM public.output_type_statistics ORDER BY published_count DESC NULLS LAST")
            ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_search_videos(
    team_name: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    published_platform: Optional[str] = None,
    limit: int = 50,
) -> str:
    """Search video_list_data with optional filters.
    All filters use case-insensitive partial matching (ILIKE).
    Returns video headline, source, team, type, uploader, platform, and URL."""
    conditions, params = [], {"limit": min(int(limit), 500)}
    if team_name:
        conditions.append("team_name ILIKE :team_name")
        params["team_name"] = f"%{team_name}%"
    if uploaded_by:
        conditions.append("uploaded_by ILIKE :uploaded_by")
        params["uploaded_by"] = f"%{uploaded_by}%"
    if published_platform:
        conditions.append("published_platform ILIKE :published_platform")
        params["published_platform"] = f"%{published_platform}%"
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text(f"SELECT * FROM public.video_list_data {where} ORDER BY video_id LIMIT :limit"),
                params,
            ).mappings().all()
        return json.dumps({"row_count": len(rows), "rows": [dict(r) for r in rows]}, default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_video_stats_by_team() -> str:
    """Aggregate video_list_data by team_name — returns total and published video counts per team."""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT team_name, COUNT(*) AS total_videos, SUM(published) AS published_videos "
                      "FROM public.video_list_data GROUP BY team_name ORDER BY total_videos DESC")
            ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def mcp_get_video_stats_by_platform() -> str:
    """Aggregate video_list_data by published_platform — returns total and published video counts per platform."""
    try:
        with _db().engine.connect() as conn:
            rows = conn.execute(
                _text("SELECT published_platform, COUNT(*) AS total_videos, SUM(published) AS published_videos "
                      "FROM public.video_list_data GROUP BY published_platform ORDER BY total_videos DESC")
            ).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)
    except Exception as exc:
        return f"Error: {exc}"


# ── Exported list ─────────────────────────────────────────────────────────────

ALL_MCP_TOOLS = [
    mcp_list_tables,
    mcp_describe_table,
    mcp_execute_sql,
    mcp_get_channel_metrics,
    mcp_get_top_channels_by_platform,
    mcp_get_monthly_trend,
    mcp_get_language_breakdown,
    mcp_get_input_type_breakdown,
    mcp_get_output_type_breakdown,
    mcp_search_videos,
    mcp_get_video_stats_by_team,
    mcp_get_video_stats_by_platform,
]
