from __future__ import annotations

import json
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from ..config import ServerSettings
from ..database import DatabaseClient
from sqlalchemy import text


@dataclass
class GCDataToolModule:
    """Domain-specific MCP tools for the GCData analytics database."""

    db: DatabaseClient
    settings: ServerSettings

    def register(self, mcp: FastMCP) -> None:

        # ------------------------------------------------------------------ #
        # channel_metrics                                                       #
        # ------------------------------------------------------------------ #

        @mcp.tool()
        def get_channel_metrics(channel: str | None = None) -> str:
            """Return rows from channel_metrics.

            Each row represents a content channel (e.g. A, B, C …) with
            per-platform post counts and total durations.

            Args:
                channel: Optional channel name to filter by (e.g. 'A'). If
                         omitted, all channels are returned.
            """
            try:
                with self.db.engine.connect() as conn:
                    if channel:
                        rows = conn.execute(
                            text(
                                "SELECT * FROM public.channel_metrics "
                                "WHERE channels = :ch ORDER BY channels"
                            ),
                            {"ch": channel},
                        ).mappings().all()
                    else:
                        rows = conn.execute(
                            text(
                                "SELECT * FROM public.channel_metrics "
                                "ORDER BY channels"
                            )
                        ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"

        @mcp.tool()
        def get_top_channels_by_platform(
            platform: str,
            top_n: int = 10,
        ) -> str:
            """Return the top N channels ranked by post count on a given platform.

            Args:
                platform: One of facebook, instagram, linkedin, reels, shorts,
                          x, youtube, threads.
                top_n:    How many channels to return (default 10).
            """
            allowed = {
                "facebook", "instagram", "linkedin", "reels",
                "shorts", "x", "youtube", "threads",
            }
            platform_lower = platform.lower().strip()
            if platform_lower not in allowed:
                return (
                    f"Error: '{platform}' is not a recognised platform. "
                    f"Choose from: {', '.join(sorted(allowed))}."
                )
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            f"SELECT channels, {platform_lower} AS post_count "
                            f"FROM public.channel_metrics "
                            f"WHERE {platform_lower} IS NOT NULL "
                            f"ORDER BY {platform_lower} DESC "
                            f"LIMIT :n"
                        ),
                        {"n": max(1, int(top_n))},
                    ).mappings().all()
                return json.dumps(
                    {"platform": platform_lower, "top_channels": [dict(r) for r in rows]},
                    default=str,
                )
            except Exception as exc:
                return f"Error: {exc}"

        # ------------------------------------------------------------------ #
        # monthly_counts_duration                                               #
        # ------------------------------------------------------------------ #

        @mcp.tool()
        def get_monthly_trend() -> str:
            """Return monthly content volume and duration metrics, ordered chronologically.

            Columns: month, total_uploaded, total_created, total_published,
                     total_uploaded_duration, total_created_duration,
                     total_published_duration.
            """
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT * FROM public.monthly_counts_duration "
                            "ORDER BY month"
                        )
                    ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"

        # ------------------------------------------------------------------ #
        # language_statistics                                                   #
        # ------------------------------------------------------------------ #

        @mcp.tool()
        def get_language_breakdown(sort_by: str = "published_count") -> str:
            """Return language-level upload/create/publish statistics.

            Args:
                sort_by: Column to sort by descending. Options:
                         uploaded_count, created_count, published_count.
                         Defaults to published_count.
            """
            allowed_sorts = {"uploaded_count", "created_count", "published_count"}
            col = sort_by.lower().strip()
            if col not in allowed_sorts:
                col = "published_count"
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            f"SELECT * FROM public.language_statistics "
                            f"ORDER BY {col} DESC NULLS LAST"
                        )
                    ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"

        # ------------------------------------------------------------------ #
        # input_type_metrics                                                    #
        # ------------------------------------------------------------------ #

        @mcp.tool()
        def get_input_type_breakdown(sort_by: str = "published_count") -> str:
            """Return per-input-type upload/create/publish counts and durations.

            Args:
                sort_by: Column to sort by descending. Options:
                         uploaded_count, created_count, published_count.
                         Defaults to published_count.
            """
            allowed_sorts = {"uploaded_count", "created_count", "published_count"}
            col = sort_by.lower().strip()
            if col not in allowed_sorts:
                col = "published_count"
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            f"SELECT * FROM public.input_type_metrics "
                            f"ORDER BY {col} DESC NULLS LAST"
                        )
                    ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"

        # ------------------------------------------------------------------ #
        # output_type_statistics                                                #
        # ------------------------------------------------------------------ #

        @mcp.tool()
        def get_output_type_breakdown(sort_by: str = "published_count") -> str:
            """Return per-output-type upload/create/publish counts and durations.

            Args:
                sort_by: Column to sort by descending. Options:
                         uploaded_count, created_count, published_count.
                         Defaults to published_count.
            """
            allowed_sorts = {"uploaded_count", "created_count", "published_count"}
            col = sort_by.lower().strip()
            if col not in allowed_sorts:
                col = "published_count"
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            f"SELECT * FROM public.output_type_statistics "
                            f"ORDER BY {col} DESC NULLS LAST"
                        )
                    ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"

        # ------------------------------------------------------------------ #
        # video_list_data                                                       #
        # ------------------------------------------------------------------ #

        @mcp.tool()
        def search_videos(
            team_name: str | None = None,
            uploaded_by: str | None = None,
            published_platform: str | None = None,
            source: str | None = None,
            published: int | None = None,
            limit: int | None = None,
        ) -> str:
            """Search video_list_data with optional filters.

            All filters are optional and combined with AND logic. Text filters
            use case-insensitive ILIKE matching.

            Args:
                team_name:          Filter by team name (partial match).
                uploaded_by:        Filter by uploader name (partial match).
                published_platform: Filter by published platform (partial match).
                source:             Filter by source (partial match).
                published:          Filter by published flag (0 or 1).
                limit:              Max rows to return (default 100, max 1000).
            """
            safe_limit = self.db.normalise_limit(
                limit,
                self.settings.default_query_limit,
                self.settings.max_query_limit,
            )
            conditions: list[str] = []
            params: dict = {"limit": safe_limit}

            if team_name:
                conditions.append("team_name ILIKE :team_name")
                params["team_name"] = f"%{team_name}%"
            if uploaded_by:
                conditions.append("uploaded_by ILIKE :uploaded_by")
                params["uploaded_by"] = f"%{uploaded_by}%"
            if published_platform:
                conditions.append("published_platform ILIKE :published_platform")
                params["published_platform"] = f"%{published_platform}%"
            if source:
                conditions.append("source ILIKE :source")
                params["source"] = f"%{source}%"
            if published is not None:
                conditions.append("published = :published")
                params["published"] = int(published)

            where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            sql = (
                f"SELECT * FROM public.video_list_data "
                f"{where_clause} "
                f"ORDER BY video_id "
                f"LIMIT :limit"
            )
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(text(sql), params).mappings().all()
                return json.dumps(
                    {"row_count": len(rows), "rows": [dict(r) for r in rows]},
                    default=str,
                )
            except Exception as exc:
                return f"Error: {exc}"

        @mcp.tool()
        def get_video_stats_by_team() -> str:
            """Aggregate video_list_data by team_name — total and published video counts."""
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT team_name, "
                            "COUNT(*) AS total_videos, "
                            "SUM(published) AS published_videos "
                            "FROM public.video_list_data "
                            "GROUP BY team_name "
                            "ORDER BY total_videos DESC"
                        )
                    ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"

        @mcp.tool()
        def get_video_stats_by_platform() -> str:
            """Aggregate video_list_data by published_platform — total and published video counts."""
            try:
                with self.db.engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT published_platform, "
                            "COUNT(*) AS total_videos, "
                            "SUM(published) AS published_videos "
                            "FROM public.video_list_data "
                            "GROUP BY published_platform "
                            "ORDER BY total_videos DESC"
                        )
                    ).mappings().all()
                return json.dumps([dict(r) for r in rows], default=str)
            except Exception as exc:
                return f"Error: {exc}"
