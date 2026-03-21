from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter, build_where_clause


router = APIRouter()

VALID_GRANULARITIES = {"day", "week", "month", "quarter"}


def _is_active(vals: Optional[List[str]]) -> bool:
    """Return True if the filter list contains real (non-'All') values."""
    if not vals:
        return False
    return not any(v.strip().lower() in ("all", "") for v in vals)


def _build_journey_filter(
    auth,
    start_index: int,
    *,
    company: Optional[List[str]] = None,
    channel: Optional[List[str]] = None,
    user: Optional[List[str]] = None,
    language: Optional[List[str]] = None,
    input_type: Optional[List[str]] = None,
    output_type: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    Build combined access + dimension filter for the scoped_videos CTE.
    Returns {join, predicates, params, next_index, output_type_where}.
    """
    access = build_access_filter(auth, start_index, "rv")
    joins = []
    predicates = list(access["predicates"])
    params = list(access["params"])
    idx = access["next_index"]

    if access["join"]:
        joins.append(access["join"])

    has_user_join = False
    has_rvc_join = False

    if _is_active(company):
        joins.append('LEFT JOIN users u_f ON rv."User_ID" = u_f."User_ID"')
        joins.append('LEFT JOIN raw_video_channel rvc_f ON rv."Video_ID" = rvc_f."Video_ID"')
        joins.append('LEFT JOIN channels ch_f ON ch_f."Channel_Name" = rvc_f."Channel_Name"')
        has_user_join = True
        has_rvc_join = True
        placeholders = ", ".join(f"${idx + i}" for i in range(len(company)))
        predicates.append(
            f'COALESCE(ch_f."Client_Name", u_f."Client_Name") IN ({placeholders})'
        )
        params.extend(company)
        idx += len(company)

    if _is_active(channel):
        if not has_rvc_join:
            joins.append('LEFT JOIN raw_video_channel rvc_f ON rv."Video_ID" = rvc_f."Video_ID"')
            has_rvc_join = True
        placeholders = ", ".join(f"${idx + i}" for i in range(len(channel)))
        predicates.append(f'rvc_f."Channel_Name" IN ({placeholders})')
        params.extend(channel)
        idx += len(channel)

    if _is_active(user):
        if not has_user_join:
            joins.append('LEFT JOIN users u_f ON rv."User_ID" = u_f."User_ID"')
            has_user_join = True
        placeholders = ", ".join(f"${idx + i}" for i in range(len(user)))
        predicates.append(f'u_f."User_Name" IN ({placeholders})')
        params.extend(user)
        idx += len(user)

    if _is_active(language):
        placeholders = ", ".join(f"${idx + i}" for i in range(len(language)))
        predicates.append(f'rv."Language" IN ({placeholders})')
        params.extend(language)
        idx += len(language)

    if _is_active(input_type):
        placeholders = ", ".join(f"${idx + i}" for i in range(len(input_type)))
        predicates.append(f'rv."Input_Type" IN ({placeholders})')
        params.extend(input_type)
        idx += len(input_type)

    if date_from:
        predicates.append(f'rv."Upload_Date" >= ${idx}')
        params.append(date_from)
        idx += 1

    if date_to:
        predicates.append(f'rv."Upload_Date" <= ${idx}')
        params.append(date_to)
        idx += 1

    # Output type filtering happens at the scoped_assets level
    output_type_where = ""
    if _is_active(output_type):
        placeholders = ", ".join(f"${idx + i}" for i in range(len(output_type)))
        output_type_where = f'AND ca."Output_Type" IN ({placeholders})'
        params.extend(output_type)
        idx += len(output_type)

    return {
        "join": "\n".join(joins),
        "predicates": predicates,
        "params": params,
        "next_index": idx,
        "output_type_where": output_type_where,
    }


def _scoped_ctes(filt: dict) -> str:
    scoped_videos_where = build_where_clause(filt["predicates"])
    ot_where = filt.get("output_type_where", "")
    return f'''
    WITH scoped_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Upload_Date", rv."Input_Type", rv."Language"
      FROM raw_videos rv
      {filt["join"]}
      {scoped_videos_where}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
      WHERE 1=1 {ot_where}
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    ),
    scoped_distribution AS (
      SELECT DISTINCT ON (pd."Distribution_ID")
        pd."Distribution_ID",
        pd."Post_ID",
        pd."Channel_Name",
        pd."Published_Platform",
        sp."Asset_ID",
        sp."Publish_Date",
        COALESCE(ds."Likes", 0)::bigint AS likes,
        COALESCE(ds."Comments", 0)::bigint AS comments,
        COALESCE(ds."Shares", 0)::bigint AS shares,
        COALESCE(ds."Views", 0)::bigint AS views
      FROM post_distribution pd
      JOIN scoped_posts sp ON sp."Post_ID" = pd."Post_ID"
      LEFT JOIN distribution_stats ds ON ds."Distribution_ID" = pd."Distribution_ID"
      ORDER BY pd."Distribution_ID"
    )
    '''


def _summary_query(filt: dict) -> str:
    return f'''
    {_scoped_ctes(filt)}
    SELECT
      (SELECT COUNT(*) FROM scoped_videos)::bigint AS uploaded_videos,
      (SELECT COUNT(*) FROM scoped_assets)::bigint AS created_assets,
      (SELECT COUNT(*) FROM scoped_posts)::bigint AS published_posts,
      (SELECT COUNT(DISTINCT "Post_ID") FROM scoped_distribution)::bigint AS distributed_posts,
      (SELECT COUNT(*) FROM scoped_distribution)::bigint AS distributions,
      (SELECT COALESCE(SUM(views), 0) FROM scoped_distribution)::bigint AS views,
      (SELECT COALESCE(SUM(likes), 0) FROM scoped_distribution)::bigint AS likes,
      (SELECT COALESCE(SUM(comments), 0) FROM scoped_distribution)::bigint AS comments,
      (SELECT COALESCE(SUM(shares), 0) FROM scoped_distribution)::bigint AS shares;
    '''


def _series_query(filt: dict) -> str:
    return f'''
    {_scoped_ctes(filt)}
    , upload_periods AS (
      SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period,
             COUNT(*)::bigint AS uploaded_videos
      FROM scoped_videos
      GROUP BY 1
    ),
    publish_periods AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period,
             COUNT(*)::bigint AS published_posts
      FROM scoped_posts
      GROUP BY 1
    ),
    distribution_periods AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period,
             COUNT(DISTINCT "Distribution_ID")::bigint AS distributions,
             COALESCE(SUM(views), 0)::bigint AS views,
             COALESCE(SUM(likes), 0)::bigint AS likes,
             COALESCE(SUM(comments), 0)::bigint AS comments,
             COALESCE(SUM(shares), 0)::bigint AS shares
      FROM scoped_distribution
      GROUP BY 1
    )
    SELECT
      COALESCE(u.period, p.period, d.period) AS period,
      COALESCE(u.uploaded_videos, 0)::bigint AS uploaded_videos,
      COALESCE(p.published_posts, 0)::bigint AS published_posts,
      COALESCE(d.distributions, 0)::bigint AS distributions,
      COALESCE(d.views, 0)::bigint AS views,
      COALESCE(d.likes, 0)::bigint AS likes,
      COALESCE(d.comments, 0)::bigint AS comments,
      COALESCE(d.shares, 0)::bigint AS shares,
      CASE
        WHEN COALESCE(d.views, 0) = 0 THEN 0
        ELSE ROUND(((COALESCE(d.likes, 0) + COALESCE(d.comments, 0) + COALESCE(d.shares, 0))::numeric / d.views::numeric) * 100, 2)
      END AS engagement_rate_pct
    FROM upload_periods u
    FULL OUTER JOIN publish_periods p ON p.period = u.period
    FULL OUTER JOIN distribution_periods d ON d.period = COALESCE(u.period, p.period)
    ORDER BY 1;
    '''


def _platform_query(filt: dict) -> str:
    return f'''
    {_scoped_ctes(filt)}
    SELECT
      COALESCE("Published_Platform", 'Unknown') AS platform,
      COUNT(DISTINCT "Distribution_ID")::bigint AS distributions,
      COUNT(DISTINCT "Post_ID")::bigint AS posts,
      COALESCE(SUM(views), 0)::bigint AS views,
      COALESCE(SUM(likes), 0)::bigint AS likes,
      COALESCE(SUM(comments), 0)::bigint AS comments,
      COALESCE(SUM(shares), 0)::bigint AS shares,
      CASE
        WHEN COALESCE(SUM(views), 0) = 0 THEN 0
        ELSE ROUND(((COALESCE(SUM(likes), 0) + COALESCE(SUM(comments), 0) + COALESCE(SUM(shares), 0))::numeric / SUM(views)::numeric) * 100, 2)
      END AS engagement_rate_pct
    FROM scoped_distribution
    GROUP BY 1
    ORDER BY views DESC
    LIMIT 10;
    '''


def _output_type_query(filt: dict) -> str:
    return f'''
    {_scoped_ctes(filt)}
    SELECT
      COALESCE(sa."Output_Type", 'Unknown') AS output_type,
      COUNT(DISTINCT sa."Asset_ID")::bigint AS assets_created,
      COUNT(DISTINCT sd."Post_ID")::bigint AS posts_distributed,
      COALESCE(SUM(sd.views), 0)::bigint AS views,
      COALESCE(SUM(sd.likes + sd.comments + sd.shares), 0)::bigint AS interactions,
      CASE
        WHEN COUNT(DISTINCT sd."Post_ID") = 0 THEN 0
        ELSE ROUND((COALESCE(SUM(sd.views), 0)::numeric / COUNT(DISTINCT sd."Post_ID")::numeric), 2)
      END AS views_per_post
    FROM scoped_assets sa
    LEFT JOIN scoped_distribution sd ON sd."Asset_ID" = sa."Asset_ID"
    GROUP BY 1
    ORDER BY views DESC
    LIMIT 10;
    '''


def _recent_rows_query(filt: dict) -> str:
    return f'''
    {_scoped_ctes(filt)}
    SELECT
      sd."Distribution_ID" AS distribution_id,
      sd."Post_ID" AS post_id,
      to_date(sd."Publish_Date", 'YYYY-MM-DD')::date AS publish_date,
      COALESCE(sd."Published_Platform", 'Unknown') AS platform,
      COALESCE(sd."Channel_Name", 'Unknown') AS channel_name,
      COALESCE(sa."Output_Type", 'Unknown') AS output_type,
      COALESCE(rv."Input_Type", 'Unknown') AS input_type,
      COALESCE(rv."Language", 'Unknown') AS language,
      COALESCE(u."User_Name", 'Unknown') AS user_name,
      COALESCE(u."Client_Name", 'Unknown') AS client_name,
      sd.views,
      sd.likes,
      sd.comments,
      sd.shares,
      CASE
        WHEN sd.views = 0 THEN 0
        ELSE ROUND(((sd.likes + sd.comments + sd.shares)::numeric / sd.views::numeric) * 100, 2)
      END AS engagement_rate_pct
    FROM scoped_distribution sd
    LEFT JOIN scoped_assets sa ON sa."Asset_ID" = sd."Asset_ID"
    LEFT JOIN scoped_videos rv ON rv."Video_ID" = sa."Video_ID"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    ORDER BY publish_date DESC NULLS LAST, sd.views DESC
    LIMIT 50;
    '''


_KPI_DEFINITIONS = {
    # Engagement
    "views": {
        "definition": "Total number of views across all distributed posts.",
        "formula": "SUM(views) from distributions",
        "query": "SELECT COALESCE(SUM(views), 0) FROM scoped_distribution",
    },
    "interactions": {
        "definition": "Total likes, comments, and shares across all distributed posts.",
        "formula": "SUM(likes) + SUM(comments) + SUM(shares)",
        "query": "SELECT COALESCE(SUM(likes),0) + COALESCE(SUM(comments),0) + COALESCE(SUM(shares),0) FROM scoped_distribution",
    },
    "er": {
        "definition": "Ratio of total interactions to total views.",
        "formula": "(likes + comments + shares) / views × 100",
        "query": "ROUND(((SUM(likes) + SUM(comments) + SUM(shares)) / SUM(views)) × 100, 2)",
    },
    "virality": {
        "definition": "Share-driven reach as a percentage of total views.",
        "formula": "(shares / views) × 100",
        "query": "ROUND((SUM(shares) / SUM(views)) × 100, 2)",
    },
    "likes": {
        "definition": "Total number of likes across all distributed posts.",
        "formula": "SUM(likes)",
        "query": "SELECT COALESCE(SUM(likes), 0) FROM scoped_distribution",
    },
    "comments": {
        "definition": "Total number of comments across all distributed posts.",
        "formula": "SUM(comments)",
        "query": "SELECT COALESCE(SUM(comments), 0) FROM scoped_distribution",
    },
    "shares": {
        "definition": "Total number of shares across all distributed posts.",
        "formula": "SUM(shares)",
        "query": "SELECT COALESCE(SUM(shares), 0) FROM scoped_distribution",
    },
    "likeRate": {
        "definition": "Percentage of views that resulted in a like.",
        "formula": "(likes / views) × 100",
        "query": "ROUND((SUM(likes) / SUM(views)) × 100, 2)",
    },
    "commentRate": {
        "definition": "Percentage of views that resulted in a comment.",
        "formula": "(comments / views) × 100",
        "query": "ROUND((SUM(comments) / SUM(views)) × 100, 2)",
    },
    "shareRate": {
        "definition": "Percentage of views that resulted in a share.",
        "formula": "(shares / views) × 100",
        "query": "ROUND((SUM(shares) / SUM(views)) × 100, 2)",
    },
    "likeToComment": {
        "definition": "Ratio of likes to comments, indicating sentiment balance.",
        "formula": "likes / comments",
        "query": "SUM(likes) / NULLIF(SUM(comments), 0)",
    },
    # Pipeline
    "uploaded": {
        "definition": "Total number of raw videos uploaded into the pipeline.",
        "formula": "COUNT(scoped_videos)",
        "query": "SELECT COUNT(*) FROM scoped_videos",
    },
    "published": {
        "definition": "Total number of posts published from created assets.",
        "formula": "COUNT(scoped_posts)",
        "query": "SELECT COUNT(*) FROM scoped_posts",
    },
    "distributions": {
        "definition": "Total number of platform distributions of published posts.",
        "formula": "COUNT(scoped_distribution)",
        "query": "SELECT COUNT(*) FROM scoped_distribution",
    },
    "avgvdist": {
        "definition": "Average number of views per distribution placement.",
        "formula": "SUM(views) / COUNT(distributions)",
        "query": "COALESCE(SUM(views), 0) / NULLIF(COUNT(*), 0) FROM scoped_distribution",
    },
    "publishRate": {
        "definition": "Percentage of uploaded videos that resulted in a published post.",
        "formula": "(published_posts / uploaded_videos) × 100",
        "query": "ROUND((COUNT(scoped_posts) / COUNT(scoped_videos)) × 100, 1)",
    },
    "distRate": {
        "definition": "Percentage of published posts that were distributed to platforms.",
        "formula": "(distributed_posts / published_posts) × 100",
        "query": "ROUND((COUNT(DISTINCT distributed Post_ID) / COUNT(scoped_posts)) × 100, 1)",
    },
    "contentYield": {
        "definition": "Average number of distributions generated per uploaded video.",
        "formula": "distributions / uploaded_videos",
        "query": "COUNT(scoped_distribution) / NULLIF(COUNT(scoped_videos), 0)",
    },
    # Reach & Efficiency
    "interactPerView": {
        "definition": "Average number of interactions generated per view.",
        "formula": "(likes + comments + shares) / views",
        "query": "(SUM(likes) + SUM(comments) + SUM(shares)) / NULLIF(SUM(views), 0)",
    },
    "interactPerDist": {
        "definition": "Average interactions generated per distribution placement.",
        "formula": "(likes + comments + shares) / distributions",
        "query": "(SUM(likes) + SUM(comments) + SUM(shares)) / NULLIF(COUNT(*), 0) FROM scoped_distribution",
    },
    "amplification": {
        "definition": "Projected reach from shares, based on average views per distribution.",
        "formula": "shares × avg_views_per_distribution",
        "query": "SUM(shares) × (SUM(views) / NULLIF(COUNT(*), 0))",
    },
}


@router.get("", include_in_schema=False)
@router.get("/")
def get_user_journey(
    granularity: str = Query(default="week"),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type: Optional[List[str]] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    auth: AuthContext = Depends(require_auth),
):
    safe_granularity = granularity if granularity in VALID_GRANULARITIES else "week"

    # Build filter for queries that DON'T have granularity as $1
    filt = _build_journey_filter(
        auth, 1,
        company=company, channel=channel, user=user,
        language=language, input_type=input_type, output_type=output_type,
        date_from=date_from, date_to=date_to,
    )

    # Build filter for the series query where granularity occupies $1
    filt_series = _build_journey_filter(
        auth, 2,
        company=company, channel=channel, user=user,
        language=language, input_type=input_type, output_type=output_type,
        date_from=date_from, date_to=date_to,
    )

    try:
        summary_rows = query(_summary_query(filt), filt["params"]).rows
        summary = summary_rows[0] if summary_rows else {}

        series_rows = query(
            _series_query(filt_series),
            [safe_granularity, *filt_series["params"]],
        ).rows

        platform_rows = query(_platform_query(filt), filt["params"]).rows
        output_rows = query(_output_type_query(filt), filt["params"]).rows
        recent_rows = query(_recent_rows_query(filt), filt["params"]).rows

        uploaded = int(summary.get("uploaded_videos") or 0)
        published = int(summary.get("published_posts") or 0)
        distributed_posts = int(summary.get("distributed_posts") or 0)
        views = int(summary.get("views") or 0)
        interactions = int(summary.get("likes") or 0) + int(summary.get("comments") or 0) + int(summary.get("shares") or 0)

        return {
            "granularity": safe_granularity,
            "summary": {
                **summary,
                "publish_from_upload_pct": round((published / uploaded) * 100, 2) if uploaded else 0,
                "distribution_from_publish_pct": round((distributed_posts / published) * 100, 2) if published else 0,
                "interaction_rate_pct": round((interactions / views) * 100, 2) if views else 0,
            },
            "timeseries": [
                {
                    **row,
                    "period": str(row.get("period")) if row.get("period") is not None else None,
                }
                for row in series_rows
            ],
            "platform_breakdown": platform_rows,
            "output_type_breakdown": output_rows,
            "recent_journey": recent_rows,
            "kpiDefinitions": _KPI_DEFINITIONS,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
