"""
analytics_shared.py
-------------------
Shared analytics constants, RBAC filters, and metric queries.
Direct port of backend_legacy/queries/analyticsShared.js.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any


# ── Metric SQL (unscoped — website_admin only) ──────────────────────────────

METRIC_SQL = {
    "uploaded_count": """
        SELECT date_trunc(:granularity, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
        FROM raw_videos GROUP BY 1 ORDER BY 1
    """,
    "created_count": """
        SELECT date_trunc(:granularity, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
        FROM created_assets GROUP BY 1 ORDER BY 1
    """,
    "published_count": """
        SELECT date_trunc(:granularity, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
        FROM published_posts GROUP BY 1 ORDER BY 1
    """,
    "uploaded_duration": """
        SELECT date_trunc(:granularity, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS value
        FROM raw_videos GROUP BY 1 ORDER BY 1
    """,
    "created_duration": """
        SELECT date_trunc(:granularity, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS value
        FROM created_assets GROUP BY 1 ORDER BY 1
    """,
    "published_duration": """
        SELECT date_trunc(:granularity, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS value
        FROM published_posts GROUP BY 1 ORDER BY 1
    """,
}

VALID_METRICS = set(METRIC_SQL) | {
    "publish_conversion_rate", "creation_rate", "processing_efficiency", "waste_index",
}

DIMENSION_MAP = {
    "channel":            'rvc."Channel_Name"',
    "language":           'rv."Language"',
    "input_type":         'rv."Input_Type"',
    "output_type":        'ca."Output_Type"',
    "user":               'u."User_Name"',
    "client":             'COALESCE(ch."Client_Name", u."Client_Name")',
    "published_platform": 'pd."Published_Platform"',
}

MEASURE_MAP = {
    "uploaded_videos": 'COUNT(DISTINCT rv."Video_ID")::float8',
    "created_assets":  'COUNT(DISTINCT ca."Asset_ID")::float8',
    "published_posts": 'COUNT(DISTINCT pp."Post_ID")::float8',
}

DATE_FIELD_MAP = {
    "upload_date":  """to_date(rv."Upload_Date", 'YYYY-MM-DD')""",
    "create_date":  """to_date(ca."Create_Date", 'YYYY-MM-DD')""",
    "publish_date": """to_date(pp."Publish_Date", 'YYYY-MM-DD')""",
}

ANALYTICS_BASE_FROM = """
    FROM raw_videos rv
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
"""


# ── RBAC access filter ──────────────────────────────────────────────────────

@dataclass
class AccessFilter:
    join: str = ""
    predicates: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


def build_access_filter(auth, video_alias: str = "rv") -> AccessFilter:
    """Build RBAC join + predicate fragments. website_admin sees everything."""
    if auth is None or auth.role == "website_admin":
        return AccessFilter()

    if auth.role == "client_admin":
        return AccessFilter(
            join=f"""
                LEFT JOIN users u_scope ON u_scope."User_ID" = {video_alias}."User_ID"
                LEFT JOIN raw_video_channel rvc_scope ON rvc_scope."Video_ID" = {video_alias}."Video_ID"
                LEFT JOIN channels ch_scope ON ch_scope."Channel_Name" = rvc_scope."Channel_Name"
            """,
            predicates=["""COALESCE(ch_scope."Client_Name", u_scope."Client_Name") = :af_client"""],
            params={"af_client": auth.client_name},
        )

    if auth.role == "user":
        return AccessFilter(
            predicates=[f"""{video_alias}."User_ID" = :af_user_id"""],
            params={"af_user_id": auth.user_id},
        )

    return AccessFilter()


def build_where(predicates: list[str]) -> str:
    if not predicates:
        return ""
    return "WHERE " + " AND ".join(predicates)


# ── Scoped metric query (RBAC-aware) ────────────────────────────────────────

def get_scoped_ctes(af: AccessFilter) -> str:
    where = build_where(af.predicates)
    return f"""
        WITH scoped_videos AS (
            SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Upload_Date", rv."Uploaded_Duration"
            FROM raw_videos rv
            {af.join}
            {where}
        ),
        scoped_assets AS (
            SELECT ca.* FROM created_assets ca
            JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
        ),
        scoped_posts AS (
            SELECT pp.* FROM published_posts pp
            JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
        )
    """


def get_metric_query(metric: str, af: AccessFilter) -> str:
    ctes = get_scoped_ctes(af)

    scoped_metrics = {
        "uploaded_count": f"""{ctes}
            SELECT date_trunc(:granularity, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
            FROM scoped_videos sv GROUP BY 1 ORDER BY 1""",
        "created_count": f"""{ctes}
            SELECT date_trunc(:granularity, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
            FROM scoped_assets sa GROUP BY 1 ORDER BY 1""",
        "published_count": f"""{ctes}
            SELECT date_trunc(:granularity, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
            FROM scoped_posts sp GROUP BY 1 ORDER BY 1""",
        "uploaded_duration": f"""{ctes}
            SELECT date_trunc(:granularity, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sv."Uploaded_Duration"), 0)::float8 AS value
            FROM scoped_videos sv GROUP BY 1 ORDER BY 1""",
        "created_duration": f"""{ctes}
            SELECT date_trunc(:granularity, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS value
            FROM scoped_assets sa GROUP BY 1 ORDER BY 1""",
        "published_duration": f"""{ctes}
            SELECT date_trunc(:granularity, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS value
            FROM scoped_posts sp GROUP BY 1 ORDER BY 1""",
        "publish_conversion_rate": f"""{ctes}
            , created AS (
                SELECT date_trunc(:granularity, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
                FROM scoped_assets sa GROUP BY 1
            ),
            published AS (
                SELECT date_trunc(:granularity, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS published_count
                FROM scoped_posts sp GROUP BY 1
            )
            SELECT c.period,
                CASE WHEN c.created_count = 0 THEN 0 ELSE (COALESCE(p.published_count, 0) / c.created_count) * 100 END AS value
            FROM created c LEFT JOIN published p ON p.period = c.period ORDER BY c.period""",
        "creation_rate": f"""{ctes}
            , uploaded AS (
                SELECT date_trunc(:granularity, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
                FROM scoped_videos sv GROUP BY 1
            ),
            created AS (
                SELECT date_trunc(:granularity, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
                FROM scoped_assets sa GROUP BY 1
            )
            SELECT u.period,
                CASE WHEN u.uploaded_count = 0 THEN 0 ELSE (COALESCE(c.created_count, 0) / u.uploaded_count) * 100 END AS value
            FROM uploaded u LEFT JOIN created c ON c.period = u.period ORDER BY u.period""",
        "processing_efficiency": f"""{ctes}
            , created AS (
                SELECT date_trunc(:granularity, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS created_duration
                FROM scoped_assets sa GROUP BY 1
            ),
            published AS (
                SELECT date_trunc(:granularity, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS published_duration
                FROM scoped_posts sp GROUP BY 1
            )
            SELECT c.period,
                CASE WHEN c.created_duration = 0 THEN 0 ELSE (COALESCE(p.published_duration, 0) / c.created_duration) * 100 END AS value
            FROM created c LEFT JOIN published p ON p.period = c.period ORDER BY c.period""",
        "waste_index": f"""{ctes}
            , created AS (
                SELECT date_trunc(:granularity, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period,
                COALESCE(AVG(sa."Created_Duration"), 0)::float8 AS avg_created_duration
                FROM scoped_assets sa GROUP BY 1
            ),
            published AS (
                SELECT date_trunc(:granularity, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period,
                COALESCE(AVG(sp."Published_Duration"), 0)::float8 AS avg_published_duration
                FROM scoped_posts sp GROUP BY 1
            )
            SELECT c.period, (c.avg_created_duration - COALESCE(p.avg_published_duration, 0))::float8 AS value
            FROM created c LEFT JOIN published p ON p.period = c.period ORDER BY c.period""",
    }

    return scoped_metrics.get(metric, scoped_metrics["uploaded_count"])


# ── Trend anomaly detection ─────────────────────────────────────────────────

def get_trend_insights(points: list[dict]) -> list[dict]:
    if len(points) < 3:
        return []

    values = [float(p.get("value", 0)) for p in points]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance)

    scored = []
    for p in points:
        v = float(p.get("value", 0))
        z = 0.0 if std == 0 else (v - mean) / std
        if abs(z) >= 1.5:
            scored.append({
                "period": p["period"],
                "value": round(v, 2),
                "zScore": round(z, 2),
                "severity": "high" if abs(z) >= 2.5 else "medium",
                "direction": "spike" if z > 0 else "drop",
            })

    scored.sort(key=lambda x: abs(x["zScore"]), reverse=True)
    return scored[:8]


# ── Funnel filter ────────────────────────────────────────────────────────────

@dataclass
class FunnelFilter:
    join: str = ""
    where: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def build_funnel_filter(dimension: str | None, value: str | None, auth=None) -> FunnelFilter:
    af = build_access_filter(auth, "rv")
    predicates = list(af.predicates)
    params = dict(af.params)
    joins = [af.join] if af.join else []

    if dimension and value:
        if dimension == "channel":
            joins.append('LEFT JOIN raw_video_channel rvc_filter ON rv."Video_ID" = rvc_filter."Video_ID"')
            predicates.append('rvc_filter."Channel_Name" = :ff_val')
            params["ff_val"] = value
        elif dimension == "input_type":
            predicates.append('rv."Input_Type" = :ff_val')
            params["ff_val"] = value
        elif dimension == "language":
            predicates.append('rv."Language" = :ff_val')
            params["ff_val"] = value
        elif dimension == "user":
            joins.append('LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"')
            predicates.append('u_filter."User_Name" = :ff_val')
            params["ff_val"] = value
        elif dimension == "output_type":
            joins.append('LEFT JOIN created_assets ca_filter ON ca_filter."Video_ID" = rv."Video_ID"')
            predicates.append('ca_filter."Output_Type" = :ff_val')
            params["ff_val"] = value

    return FunnelFilter(
        join="\n".join(joins),
        where=build_where(predicates),
        params=params,
    )
