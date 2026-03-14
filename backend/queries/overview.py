"""
overview.py — Overview KPI and top-performer SQL queries.
Port of backend_legacy/queries/overviewQueries.js.
"""

from .analytics_shared import AccessFilter, build_where


def _scoped_ctes(af: AccessFilter) -> str:
    where = build_where(af.predicates)
    return f"""
        WITH scoped_videos AS (
            SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Input_Type", rv."Language",
                   rv."Upload_Date", rv."Uploaded_Duration"
            FROM raw_videos rv {af.join} {where}
        ),
        scoped_video_channels AS (
            SELECT DISTINCT rvc."Video_ID", rvc."Channel_Name"
            FROM raw_video_channel rvc
            JOIN scoped_videos sv ON sv."Video_ID" = rvc."Video_ID"
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


def kpi_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        , uploaded AS (
            SELECT COUNT(*)::int AS count, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS duration
            FROM scoped_videos
        ),
        processed AS (
            SELECT COUNT(DISTINCT "Video_ID")::int AS count FROM scoped_assets
        ),
        created AS (
            SELECT COUNT(*)::int AS count, COALESCE(SUM("Created_Duration"), 0)::float8 AS duration,
                   COALESCE(AVG("Created_Duration"), 0)::float8 AS avg_duration
            FROM scoped_assets
        ),
        published AS (
            SELECT COUNT(*)::int AS count, COALESCE(SUM("Published_Duration"), 0)::float8 AS duration,
                   COALESCE(AVG("Published_Duration"), 0)::float8 AS avg_duration
            FROM scoped_posts
        )
        SELECT
            u.count AS uploaded_count, u.duration AS uploaded_duration,
            p.count AS processed_count,
            c.count AS created_count, c.duration AS created_duration,
            pb.count AS published_count, pb.duration AS published_duration,
            CASE WHEN c.count = 0 THEN 0 ELSE (pb.count::float8 / c.count) * 100 END AS publish_conversion_rate,
            CASE WHEN c.duration = 0 THEN 0 ELSE (pb.duration / c.duration) * 100 END AS processing_efficiency,
            CASE WHEN u.count = 0 THEN 0 ELSE (c.count::float8 / u.count) * 100 END AS creation_rate,
            (c.avg_duration - pb.avg_duration) AS waste_index
        FROM uploaded u, processed p, created c, published pb
    """


def channel_top_performer_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        SELECT svc."Channel_Name" AS label,
               COUNT(DISTINCT sa."Asset_ID")::int AS created_count,
               COUNT(DISTINCT sp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT sa."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT sp."Post_ID")::float8 / COUNT(DISTINCT sa."Asset_ID")) * 100 END AS conversion
        FROM scoped_video_channels svc
        LEFT JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY svc."Channel_Name"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1
    """


def user_top_performer_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        SELECT u."User_Name" AS label,
               COUNT(DISTINCT sa."Asset_ID")::int AS created_count,
               COUNT(DISTINCT sp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT sa."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT sp."Post_ID")::float8 / COUNT(DISTINCT sa."Asset_ID")) * 100 END AS conversion
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY u."User_Name"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1
    """


def input_top_performer_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        SELECT sv."Input_Type" AS label,
               COUNT(DISTINCT sa."Asset_ID")::int AS created_count,
               COUNT(DISTINCT sp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT sa."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT sp."Post_ID")::float8 / COUNT(DISTINCT sa."Asset_ID")) * 100 END AS conversion
        FROM scoped_videos sv
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sv."Input_Type"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1
    """


def output_top_performer_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        SELECT sa."Output_Type" AS label,
               COUNT(DISTINCT sa."Asset_ID")::int AS created_count,
               COUNT(DISTINCT sp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT sa."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT sp."Post_ID")::float8 / COUNT(DISTINCT sa."Asset_ID")) * 100 END AS conversion
        FROM scoped_assets sa
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sa."Output_Type"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1
    """


def language_top_performer_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        SELECT sv."Language" AS label,
               COUNT(DISTINCT sa."Asset_ID")::int AS created_count,
               COUNT(DISTINCT sp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT sa."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT sp."Post_ID")::float8 / COUNT(DISTINCT sa."Asset_ID")) * 100 END AS conversion
        FROM scoped_videos sv
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sv."Language"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1
    """


def alerts_query(af: AccessFilter) -> str:
    return f"""{_scoped_ctes(af)}
        SELECT svc."Channel_Name" AS channel_name,
               COUNT(DISTINCT sa."Asset_ID")::int AS created_count,
               COUNT(DISTINCT sp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT sa."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT sp."Post_ID")::float8 / COUNT(DISTINCT sa."Asset_ID")) * 100 END AS conversion
        FROM scoped_video_channels svc
        LEFT JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY svc."Channel_Name"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 5
        ORDER BY conversion ASC, created_count DESC
        LIMIT 5
    """
