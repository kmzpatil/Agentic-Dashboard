from backend.queries.analytics_shared import build_where_clause

def get_scoped_ctes(access_filter: dict) -> str:
    where_clause = build_where_clause(access_filter["predicates"])
    return f'''
    WITH scoped_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Input_Type", rv."Language", rv."Upload_Date", rv."Uploaded_Duration"
      FROM raw_videos rv
      {access_filter["join"]}
      {where_clause}
    ),
    scoped_video_channels AS (
      SELECT DISTINCT rvc."Video_ID", rvc."Channel_Name"
      FROM raw_video_channel rvc
      JOIN scoped_videos sv ON sv."Video_ID" = rvc."Video_ID"
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*, sa."Video_ID"
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    )
  '''


def get_kpi_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
    , uploaded AS (
      SELECT COUNT(*)::int AS count, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS duration
      FROM scoped_videos
    ),
    processed AS (
      SELECT COUNT(DISTINCT "Video_ID")::int AS count
      FROM scoped_assets
    ),
    created AS (
      SELECT COUNT(DISTINCT "Asset_ID")::int AS count, COALESCE(SUM("Created_Duration"), 0)::float8 AS duration, COALESCE(AVG("Created_Duration"), 0)::float8 AS avg_duration
      FROM scoped_assets
    ),
    published AS (
      SELECT COUNT(DISTINCT "Post_ID")::int AS count, COALESCE(SUM("Published_Duration"), 0)::float8 AS duration, COALESCE(AVG("Published_Duration"), 0)::float8 AS avg_duration
      FROM scoped_posts
    )
    SELECT
      u.count AS uploaded_count,
      u.duration AS uploaded_duration,
      p.count AS processed_count,
      c.count AS created_count,
      c.duration AS created_duration,
      pb.count AS published_count,
      pb.duration AS published_duration,
      CASE WHEN c.count = 0 THEN 0 ELSE (pb.count::float8 / c.count) * 100 END AS publish_conversion_rate,
      CASE WHEN c.duration = 0 THEN 0 ELSE (pb.duration / c.duration) * 100 END AS processing_efficiency,
      CASE WHEN u.count = 0 THEN 0 ELSE (c.count::float8 / u.count) * 100 END AS creation_rate,
      (c.avg_duration - pb.avg_duration) AS waste_index
    FROM uploaded u, processed p, created c, published pb;
  '''


def get_channel_top_performer_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
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
    LIMIT 1;
  '''


def get_user_top_performer_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
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
    LIMIT 1;
  '''


def get_input_top_performer_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
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
    LIMIT 1;
  '''


def get_output_top_performer_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
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
    LIMIT 1;
  '''


def get_language_top_performer_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
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
    LIMIT 1;
  '''


def get_alerts_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
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
    LIMIT 5;
  '''

def get_output_type_stats_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
    , output_stats AS (
        SELECT 
            sa."Output_Type" as label,
            COUNT(DISTINCT sv."Video_ID")::int as total_uploaded_count,
            COALESCE(SUM(sv."Uploaded_Duration"), 0)::float8 as total_uploaded_duration,
            COUNT(DISTINCT sa."Asset_ID")::int as total_created_count,
            COALESCE(SUM(sa."Created_Duration"), 0)::float8 as total_created_duration,
            COUNT(DISTINCT sp."Post_ID")::int as total_published_count,
            COALESCE(SUM(sp."Published_Duration"), 0)::float8 as total_published_duration
        FROM scoped_assets sa
        JOIN scoped_videos sv ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sa."Output_Type" IS NOT NULL
        GROUP BY sa."Output_Type"
    )
    SELECT * FROM output_stats ORDER BY total_created_count DESC;
    '''
def get_kpi_sparklines_query(access_filter: dict) -> str:
    return f'''{get_scoped_ctes(access_filter)}
    , daily_uploaded AS (
      SELECT to_date("Upload_Date", 'YYYY-MM-DD') AS dt, COUNT(*)::float8 AS val FROM scoped_videos GROUP BY 1
    ),
    daily_processed AS (
      SELECT to_date("Create_Date", 'YYYY-MM-DD') AS dt, COUNT(DISTINCT "Video_ID")::float8 AS val FROM scoped_assets GROUP BY 1
    ),
    daily_created AS (
      SELECT to_date("Create_Date", 'YYYY-MM-DD') AS dt, COUNT(*)::float8 AS val FROM scoped_assets GROUP BY 1
    ),
    daily_published AS (
      SELECT to_date("Publish_Date", 'YYYY-MM-DD') AS dt, COUNT(*)::float8 AS val FROM scoped_posts GROUP BY 1
    ),
    all_dates AS (
      SELECT generate_series(CURRENT_DATE - INTERVAL '13 days', CURRENT_DATE, '1 day')::date AS dt
    ),
    seed_counts AS (
      SELECT
        (SELECT COUNT(*)::float8 FROM scoped_videos WHERE to_date("Upload_Date", 'YYYY-MM-DD') < CURRENT_DATE - INTERVAL '13 days') as uploaded_seed,
        (SELECT COUNT(DISTINCT "Video_ID")::float8 FROM scoped_assets WHERE to_date("Create_Date", 'YYYY-MM-DD') < CURRENT_DATE - INTERVAL '13 days') as processed_seed,
        (SELECT COUNT(*)::float8 FROM scoped_assets WHERE to_date("Create_Date", 'YYYY-MM-DD') < CURRENT_DATE - INTERVAL '13 days') as created_seed,
        (SELECT COUNT(*)::float8 FROM scoped_posts WHERE to_date("Publish_Date", 'YYYY-MM-DD') < CURRENT_DATE - INTERVAL '13 days') as published_seed
    )
    SELECT 
      ad.dt,
      COALESCE(sc.uploaded_seed, 0) + SUM(COALESCE(du.val, 0)) OVER (ORDER BY ad.dt) as uploaded,
      COALESCE(sc.processed_seed, 0) + SUM(COALESCE(dp.val, 0)) OVER (ORDER BY ad.dt) as processed,
      COALESCE(sc.created_seed, 0) + SUM(COALESCE(dc.val, 0)) OVER (ORDER BY ad.dt) as created,
      COALESCE(sc.published_seed, 0) + SUM(COALESCE(dpb.val, 0)) OVER (ORDER BY ad.dt) as published
    FROM all_dates ad
    LEFT JOIN daily_uploaded du ON ad.dt = du.dt
    LEFT JOIN daily_processed dp ON ad.dt = dp.dt
    LEFT JOIN daily_created dc ON ad.dt = dc.dt
    LEFT JOIN daily_published dpb ON ad.dt = dpb.dt
    CROSS JOIN seed_counts sc
    ORDER BY ad.dt ASC;
    '''
