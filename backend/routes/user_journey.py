from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter, build_where_clause


router = APIRouter()

VALID_GRANULARITIES = {"day", "week", "month", "quarter"}


def _scoped_ctes(access_filter: dict) -> str:
    scoped_videos_where = build_where_clause(access_filter["predicates"])
    return f'''
    WITH scoped_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Upload_Date", rv."Input_Type", rv."Language"
      FROM raw_videos rv
      {access_filter["join"]}
      {scoped_videos_where}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
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


def _summary_query(access_filter: dict) -> str:
    return f'''
    {_scoped_ctes(access_filter)}
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


def _series_query(access_filter: dict) -> str:
    return f'''
    {_scoped_ctes(access_filter)}
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


def _platform_query(access_filter: dict) -> str:
    return f'''
    {_scoped_ctes(access_filter)}
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


def _output_type_query(access_filter: dict) -> str:
    return f'''
    {_scoped_ctes(access_filter)}
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


def _recent_rows_query(access_filter: dict) -> str:
    return f'''
    {_scoped_ctes(access_filter)}
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


@router.get("", include_in_schema=False)
@router.get("/")
def get_user_journey(
    granularity: str = Query(default="week"),
    auth: AuthContext = Depends(require_auth),
):
    safe_granularity = granularity if granularity in VALID_GRANULARITIES else "week"
    # start_index=1 for queries that don't use a leading granularity param
    access_filter = build_access_filter(auth, 1, "rv")
    # start_index=2 for the series query, where granularity occupies $1
    access_filter_series = build_access_filter(auth, 2, "rv")

    try:
        summary_rows = query(_summary_query(access_filter), access_filter["params"]).rows
        summary = summary_rows[0] if summary_rows else {}

        series_rows = query(
            _series_query(access_filter_series),
            [safe_granularity, *access_filter_series["params"]],
        ).rows

        platform_rows = query(_platform_query(access_filter), access_filter["params"]).rows
        output_rows = query(_output_type_query(access_filter), access_filter["params"]).rows
        recent_rows = query(_recent_rows_query(access_filter), access_filter["params"]).rows

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
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
