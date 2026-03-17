BREAKDOWN_EXPR_MAP = {
  "channel": 'COALESCE(rvc."Channel_Name", \'Unknown\')',
  "input_type": 'COALESCE(rv."Input_Type", \'Unknown\')',
  "language": 'COALESCE(rv."Language", \'Unknown\')',
  "output_type": 'COALESCE(ca."Output_Type", \'Unknown\')',
  "client": 'COALESCE(u."Client_Name", \'Unknown\')',
  "user": 'COALESCE(u."User_Name", \'Unknown\')',
  "team": 'COALESCE(u."Team_Name", \'Unknown\')',
}


def get_video_header_query(filter_data: dict) -> str:
    predicates = ['rv."Video_ID" = $1']
    if filter_data["predicates"]:
        predicates.extend(filter_data["predicates"])

    return f'''
    SELECT rv."Video_ID" AS video_id,
           rv."Headline" AS headline,
           rv."Input_Type" AS input_type,
           rv."Language" AS language,
           rv."Upload_Date" AS upload_date,
           rv."Uploaded_Duration" AS uploaded_duration,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT rvc."Channel_Name"), NULL) AS channels
    FROM raw_videos rv
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    {filter_data["join"]}
    WHERE {' AND '.join(predicates)}
    GROUP BY rv."Video_ID", rv."Headline", rv."Input_Type", rv."Language", rv."Upload_Date", rv."Uploaded_Duration";
  '''


def get_video_assets_query(filter_data: dict) -> str:
    predicates = ['ca."Video_ID" = $1']
    if filter_data["predicates"]:
        predicates.extend(filter_data["predicates"])

    return f'''
    SELECT ca."Asset_ID" AS asset_id,
           ca."Output_Type" AS output_type,
           ca."Create_Date" AS create_date,
           ca."Created_Duration" AS created_duration,
           pp."Post_ID" AS post_id,
           pp."Publish_Date" AS publish_date,
           pp."Published_Duration" AS published_duration,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT pd."Published_Platform"), NULL) AS platforms
    FROM created_assets ca
    JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
    {filter_data["join"]}
    WHERE {' AND '.join(predicates)}
    GROUP BY ca."Asset_ID", ca."Output_Type", ca."Create_Date", ca."Created_Duration", pp."Post_ID", pp."Publish_Date", pp."Published_Duration"
    ORDER BY ca."Asset_ID";
  '''


def get_stage_counts_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    processed AS (
      SELECT DISTINCT ca."Video_ID"
      FROM created_assets ca
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
    ),
    created AS (
      SELECT DISTINCT ca."Asset_ID"
      FROM created_assets ca
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
    ),
    published AS (
      SELECT DISTINCT c."Asset_ID"
      FROM created c
      JOIN published_posts pp ON pp."Asset_ID" = c."Asset_ID"
    )
    SELECT
      (SELECT COUNT(*)::int FROM filtered_videos) AS uploaded_count,
      (SELECT COUNT(*)::int FROM processed) AS processed_count,
      (SELECT COUNT(*)::int FROM created) AS created_count,
      (SELECT COUNT(*)::int FROM published) AS published_count;
  '''


def get_breakdown_query(filter_data: dict, breakdown_dimension: str, locked_value: str | None = None) -> str:
    label_expr = BREAKDOWN_EXPR_MAP[breakdown_dimension]
    lock_where = ""
    if locked_value:
        lock_where = f"WHERE {label_expr} = ${filter_data['next_index']}"

    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT {label_expr} AS label,
      COUNT(DISTINCT rv."Video_ID")::int AS uploaded_count,
      COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
      COUNT(DISTINCT CASE WHEN pp."Post_ID" IS NOT NULL THEN ca."Asset_ID" END)::int AS published_count,
      CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
        ELSE (
          COUNT(DISTINCT CASE WHEN pp."Post_ID" IS NOT NULL THEN ca."Asset_ID" END)::float8
          / COUNT(DISTINCT ca."Asset_ID")
        ) * 100 END AS conversion
    FROM filtered_videos fv
    JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    {lock_where}
    GROUP BY 1
    ORDER BY conversion DESC, uploaded_count DESC;
  '''


def get_composition_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    ),
    input_data AS (
      SELECT rv."Input_Type" AS input_type, COUNT(DISTINCT rv."Video_ID")::int AS uploaded_count
      FROM filtered_videos fv
      JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
      GROUP BY rv."Input_Type"
    ),
    input_output AS (
      SELECT rv."Input_Type" AS input_type,
             sa."Output_Type" AS output_type,
             COUNT(DISTINCT sa."Asset_ID")::int AS created_count
      FROM filtered_videos fv
      JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
      JOIN scoped_assets sa ON sa."Video_ID" = rv."Video_ID"
      GROUP BY rv."Input_Type", sa."Output_Type"
    ),
    output_publish AS (
      SELECT sa."Output_Type" AS output_type,
             COUNT(DISTINCT CASE WHEN sp."Post_ID" IS NOT NULL THEN sa."Asset_ID" END)::int AS published_count,
             (
               COUNT(DISTINCT sa."Asset_ID")
               - COUNT(DISTINCT CASE WHEN sp."Post_ID" IS NOT NULL THEN sa."Asset_ID" END)
             )::int AS unpublished_count
      FROM scoped_assets sa
      LEFT JOIN scoped_posts sp ON sp."Asset_ID" = sa."Asset_ID"
      GROUP BY sa."Output_Type"
    )
    SELECT 'uploaded_to_input' AS edge_type,
           'Uploaded' AS edge_from,
           ('Input: ' || COALESCE(input_type, 'Unknown')) AS edge_to,
           uploaded_count::float8 AS flow
    FROM input_data
    UNION ALL
    SELECT 'input_to_output',
           ('Input: ' || COALESCE(input_type, 'Unknown')),
           ('Output: ' || COALESCE(output_type, 'Unknown')),
           created_count::float8
    FROM input_output
    UNION ALL
    SELECT 'output_to_published',
           ('Output: ' || COALESCE(output_type, 'Unknown')),
           'Published',
           published_count::float8
    FROM output_publish
    UNION ALL
    SELECT 'output_to_unpublished',
           ('Output: ' || COALESCE(output_type, 'Unknown')),
           'Not Published',
           unpublished_count::float8
    FROM output_publish;
  '''


def get_journey_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT rv."Video_ID" AS video_id,
           rv."Headline" AS headline,
           rv."Input_Type" AS input_type,
           rv."Language" AS language,
           rv."Upload_Date" AS upload_date,
           COUNT(DISTINCT rvc."Channel_Name")::int AS channel_count,
           COUNT(DISTINCT ca."Asset_ID")::int AS created_assets,
           COUNT(DISTINCT pp."Post_ID")::int AS published_posts,
           CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
             ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
    FROM filtered_videos fv
    JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY rv."Video_ID", rv."Headline", rv."Input_Type", rv."Language", rv."Upload_Date"
    ORDER BY created_assets DESC, published_posts DESC, rv."Video_ID" DESC
    LIMIT 100;
  '''


def get_mix_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    )
    SELECT rv."Video_ID" AS video_id,
           COALESCE(ca."Output_Type", 'Unknown') AS output_type,
           COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
           COUNT(DISTINCT pp."Post_ID")::int AS published_count
    FROM filtered_videos fv
    JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
    LEFT JOIN scoped_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN scoped_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY rv."Video_ID", COALESCE(ca."Output_Type", 'Unknown')
    ORDER BY rv."Video_ID";
  '''


def get_pipeline_strip_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    scoped_assets AS (
      SELECT DISTINCT ca."Asset_ID"
      FROM created_assets ca
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT pp."Post_ID"
      FROM published_posts pp
      JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
    ),
    scoped_distribution AS (
      SELECT pd."Post_ID", pd."Published_Platform"
      FROM post_distribution pd
      JOIN scoped_posts sp ON sp."Post_ID" = pd."Post_ID"
    )
    SELECT
      (SELECT COUNT(*)::int FROM filtered_videos) AS uploads,
      (SELECT COUNT(*)::int FROM scoped_assets) AS assets_created,
      (SELECT COUNT(*)::int FROM scoped_posts) AS posts_published,
      (SELECT COUNT(*)::int FROM scoped_distribution) AS platform_posts,
      CASE
        WHEN (SELECT COUNT(*) FROM filtered_videos) = 0 THEN 0
        ELSE ((SELECT COUNT(*)::float8 FROM scoped_assets) / (SELECT COUNT(*)::float8 FROM filtered_videos))
      END AS assets_multiplier,
      CASE
        WHEN (SELECT COUNT(*) FROM scoped_assets) = 0 THEN 0
        ELSE (1 - ((SELECT COUNT(*)::float8 FROM scoped_posts) / (SELECT COUNT(*)::float8 FROM scoped_assets))) * 100
      END AS not_published_pct,
      CASE
        WHEN (SELECT COUNT(*) FROM scoped_posts) = 0 THEN 0
        ELSE ((SELECT COUNT(*)::float8 FROM scoped_distribution) / (SELECT COUNT(*)::float8 FROM scoped_posts))
      END AS platform_multiplier;
  '''


def get_kpis_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    ),
    per_video AS (
      SELECT
        fv."Video_ID",
        COUNT(DISTINCT sp."Post_ID")::int AS published_count
      FROM filtered_videos fv
      LEFT JOIN scoped_assets sa ON sa."Video_ID" = fv."Video_ID"
      LEFT JOIN scoped_posts sp ON sp."Asset_ID" = sa."Asset_ID"
      GROUP BY fv."Video_ID"
    )
    SELECT
      CASE
        WHEN (SELECT COUNT(*) FROM scoped_assets) = 0 THEN 0
        ELSE ((SELECT COUNT(*)::float8 FROM scoped_posts) / (SELECT COUNT(*)::float8 FROM scoped_assets)) * 100
      END AS publish_conversion_pct,
      CASE
        WHEN (SELECT COUNT(*) FROM filtered_videos) = 0 THEN 0
        ELSE ((SELECT COUNT(*)::float8 FROM scoped_assets) / (SELECT COUNT(*)::float8 FROM filtered_videos))
      END AS avg_assets_per_upload,
      CASE
        WHEN (SELECT COUNT(*) FROM per_video) = 0 THEN 0
        ELSE ((SELECT COUNT(*)::float8 FROM per_video WHERE published_count = 0) / (SELECT COUNT(*)::float8 FROM per_video)) * 100
      END AS upload_failure_rate,
      (
        COALESCE((SELECT AVG(sa."Created_Duration")::float8 FROM scoped_assets sa), 0)
        - COALESCE((SELECT AVG(sp."Published_Duration")::float8 FROM scoped_posts sp), 0)
      ) AS waste_index_seconds,
      COALESCE(
        (
          SELECT AVG(
            to_date(sp."Publish_Date", 'YYYY-MM-DD')::date - to_date(sa."Create_Date", 'YYYY-MM-DD')::date
          )::float8
          FROM scoped_posts sp
          JOIN scoped_assets sa ON sa."Asset_ID" = sp."Asset_ID"
        ),
        0
      ) AS avg_lag_days;
  '''


def get_channel_efficiency_query(
    filter_data: dict,
    locked_channel: str | None = None,
    locked_client: str | None = None,
) -> str:
    channel_where = []
    next_index = filter_data["next_index"]
    if locked_channel:
        channel_where.append(f'rvc."Channel_Name" = ${next_index}')
        next_index += 1
    if locked_client:
        channel_where.append(f'ch."Client_Name" = ${next_index}')
        next_index += 1
    where_sql = f"WHERE {' AND '.join(channel_where)}" if channel_where else ""

    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    channel_video AS (
      SELECT DISTINCT
        rvc."Channel_Name" AS channel_name,
        ch."Client_Name" AS client_name,
        fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN raw_video_channel rvc ON rvc."Video_ID" = fv."Video_ID"
      JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
      {where_sql}
    ),
    published_video AS (
      SELECT DISTINCT fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
      JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    )
    SELECT
      cv.channel_name,
      cv.client_name,
      COUNT(DISTINCT cv.video_id)::int AS videos_assigned,
      ROUND(
        COUNT(DISTINCT pv.video_id)::numeric
        / NULLIF(COUNT(DISTINCT cv.video_id), 0) * 100, 2
      ) AS yield_pct
    FROM channel_video cv
    LEFT JOIN published_video pv ON pv.video_id = cv.video_id
    GROUP BY cv.channel_name, cv.client_name
    ORDER BY videos_assigned DESC, yield_pct ASC;
  '''


def get_absolute_waste_query(
    filter_data: dict,
    locked_channel: str | None = None,
    locked_client: str | None = None,
) -> str:
    channel_where = []
    next_index = filter_data["next_index"]
    if locked_channel:
        channel_where.append(f'rvc."Channel_Name" = ${next_index}')
        next_index += 1
    if locked_client:
        channel_where.append(f'ch."Client_Name" = ${next_index}')
        next_index += 1
    where_sql = f"WHERE {' AND '.join(channel_where)}" if channel_where else ""

    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    channel_video AS (
      SELECT DISTINCT
        rvc."Channel_Name" AS channel_name,
        ch."Client_Name" AS client_name,
        fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN raw_video_channel rvc ON rvc."Video_ID" = fv."Video_ID"
      JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
      {where_sql}
    ),
    published_video AS (
      SELECT DISTINCT fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
      JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    )
    SELECT
      cv.channel_name,
      cv.client_name,
      COUNT(DISTINCT cv.video_id)::int AS videos_assigned,
      ROUND(
        COUNT(DISTINCT pv.video_id)::numeric
        / NULLIF(COUNT(DISTINCT cv.video_id), 0) * 100, 2
      ) AS yield_pct,
      (COUNT(DISTINCT cv.video_id) - COUNT(DISTINCT pv.video_id))::int AS waste_slots
    FROM channel_video cv
    LEFT JOIN published_video pv ON pv.video_id = cv.video_id
    GROUP BY cv.channel_name, cv.client_name
    ORDER BY waste_slots DESC
    LIMIT 10;
  '''


def get_publish_lag_distribution_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    lag_data AS (
      SELECT
        pp."Post_ID",
        (to_date(pp."Publish_Date", 'YYYY-MM-DD')::date - to_date(ca."Create_Date", 'YYYY-MM-DD')::date) AS lag_days
      FROM published_posts pp
      JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
      JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
    )
    SELECT
      CASE
        WHEN lag_days <= 1  THEN '0-1d'
        WHEN lag_days <= 2  THEN '1-2d'
        WHEN lag_days <= 3  THEN '2-3d'
        WHEN lag_days <= 5  THEN '3-5d'
        WHEN lag_days <= 10 THEN '5-10d'
        WHEN lag_days <= 20 THEN '10-20d'
        ELSE '20d+'
      END AS lag_bucket,
      COUNT(*)::int AS post_count,
      MIN(lag_days) AS sort_key
    FROM lag_data
    GROUP BY lag_bucket
    ORDER BY sort_key;
  '''


def get_team_efficiency_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT
      u."Team_Name" AS team_name,
      ROUND(
        COUNT(DISTINCT ca."Asset_ID")::numeric
        / NULLIF(COUNT(DISTINCT fv."Video_ID"), 0), 2
      ) AS upload_to_asset_ratio,
      ROUND(
        COUNT(DISTINCT pp."Post_ID")::numeric
        / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0) * 100, 2
      ) AS asset_to_publish_ratio_x100
    FROM filtered_videos fv
    JOIN users u ON u."User_ID" = fv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY u."Team_Name"
    ORDER BY upload_to_asset_ratio DESC;
  '''


def get_team_volume_yield_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    team_video AS (
      SELECT DISTINCT
        COALESCE(u."Team_Name", 'Unknown') AS team_name,
        fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN users u ON u."User_ID" = fv."User_ID"
    ),
    published_video AS (
      SELECT DISTINCT fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
      JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    )
    SELECT
      tv.team_name,
      COUNT(DISTINCT tv.video_id)::int AS videos_assigned,
      ROUND(
        COUNT(DISTINCT pv.video_id)::numeric
        / NULLIF(COUNT(DISTINCT tv.video_id), 0) * 100, 2
      ) AS yield_pct
    FROM team_video tv
    LEFT JOIN published_video pv ON pv.video_id = tv.video_id
    GROUP BY tv.team_name
    ORDER BY videos_assigned DESC, yield_pct ASC;
  '''


def get_team_absolute_waste_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    team_video AS (
      SELECT DISTINCT
        COALESCE(u."Team_Name", 'Unknown') AS team_name,
        fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN users u ON u."User_ID" = fv."User_ID"
    ),
    published_video AS (
      SELECT DISTINCT fv."Video_ID" AS video_id
      FROM filtered_videos fv
      JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
      JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    )
    SELECT
      tv.team_name,
      COUNT(DISTINCT tv.video_id)::int AS videos_assigned,
      ROUND(
        COUNT(DISTINCT pv.video_id)::numeric
        / NULLIF(COUNT(DISTINCT tv.video_id), 0) * 100, 2
      ) AS yield_pct,
      (COUNT(DISTINCT tv.video_id) - COUNT(DISTINCT pv.video_id))::int AS waste_slots
    FROM team_video tv
    LEFT JOIN published_video pv ON pv.video_id = tv.video_id
    GROUP BY tv.team_name
    ORDER BY waste_slots DESC
    LIMIT 10;
  '''


def get_heatmap_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."Input_Type", rv."User_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT
      fv."Input_Type" AS input_type,
      u."Client_Name" AS client_name,
      COUNT(DISTINCT fv."Video_ID")::int AS videos_uploaded,
      COUNT(DISTINCT ca."Asset_ID")::int AS assets_created,
      COUNT(DISTINCT pp."Post_ID")::int AS posts_published,
      ROUND(
        COALESCE(
          COUNT(DISTINCT pp."Post_ID")::numeric
          / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0) * 100,
          0
        ),
        2
      ) AS conversion_pct
    FROM filtered_videos fv
    JOIN users u ON u."User_ID" = fv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY fv."Input_Type", u."Client_Name"
    ORDER BY fv."Input_Type", u."Client_Name";
  '''


def get_output_type_survival_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT
      ca."Output_Type" AS output_type,
      COUNT(DISTINCT ca."Asset_ID")::int AS total_created,
      COUNT(DISTINCT pp."Post_ID")::int AS total_published,
      ROUND(
        COUNT(DISTINCT pp."Post_ID")::numeric
        / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0) * 100, 2
      ) AS survival_rate_pct
    FROM created_assets ca
    JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY ca."Output_Type"
    ORDER BY survival_rate_pct DESC;
  '''


def get_publish_by_client_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT
      u."Client_Name" AS client_name,
      COUNT(DISTINCT ca."Asset_ID")::int AS assets_created,
      COUNT(DISTINCT pp."Post_ID")::int AS posts_published,
      ROUND(
        COUNT(DISTINCT pp."Post_ID")::numeric
        / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0) * 100, 2
      ) AS conversion_pct
    FROM filtered_videos fv
    JOIN users u ON u."User_ID" = fv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY u."Client_Name"
    ORDER BY conversion_pct;
  '''


def get_client_outcome_platform_sankey_query(filter_data: dict) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    ),
    scoped_assets AS (
      SELECT
        DISTINCT ca."Asset_ID" AS asset_id,
        fv."User_ID" AS user_id
      FROM filtered_videos fv
      JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
    ),
    published_assets AS (
      SELECT DISTINCT sa.asset_id
      FROM scoped_assets sa
      JOIN published_posts pp ON pp."Asset_ID" = sa.asset_id
    ),
    published_by_client AS (
      SELECT
        u."Client_Name" AS client_name,
        COUNT(DISTINCT sa.asset_id)::int AS flow
      FROM scoped_assets sa
      JOIN users u ON u."User_ID" = sa.user_id
      JOIN published_assets pa ON pa.asset_id = sa.asset_id
      GROUP BY u."Client_Name"
    ),
    not_published_by_client AS (
      SELECT
        u."Client_Name" AS client_name,
        COUNT(DISTINCT sa.asset_id)::int AS flow
      FROM scoped_assets sa
      JOIN users u ON u."User_ID" = sa.user_id
      LEFT JOIN published_assets pa ON pa.asset_id = sa.asset_id
      WHERE pa.asset_id IS NULL
      GROUP BY u."Client_Name"
    ),
    published_asset_platforms AS (
      SELECT DISTINCT
        sa.asset_id,
        pd."Published_Platform" AS platform
      FROM scoped_assets sa
      JOIN published_posts pp ON pp."Asset_ID" = sa.asset_id
      JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
      WHERE pd."Published_Platform" IS NOT NULL
    ),
    asset_platform_weights AS (
      SELECT
        asset_id,
        platform,
        1::float8 / NULLIF(COUNT(*) OVER (PARTITION BY asset_id), 0)::float8 AS platform_weight
      FROM published_asset_platforms
    ),
    platform_counts AS (
      SELECT
        platform,
        SUM(platform_weight)::float8 AS flow
      FROM asset_platform_weights
      GROUP BY platform
    )
    SELECT
      'client_to_published' AS edge_type,
      client_name AS edge_from,
      'Published' AS edge_to,
      flow::float8 AS flow
    FROM published_by_client
    UNION ALL
    SELECT
      'client_to_not_published',
      client_name,
      'Not Published',
      flow::float8
    FROM not_published_by_client
    UNION ALL
    SELECT
      'published_to_platform',
      'Published',
      platform,
      flow::float8
    FROM platform_counts;
  '''


def get_filter_options_clients_query(access_filter: dict) -> str:
    where = ""
    if access_filter.get("predicates"):
        preds = [p.replace("rv.", "u.").replace("u_scope.", "u.").replace("ch_scope.", "ch.") for p in access_filter["predicates"]]
        where = f"WHERE {' AND '.join(preds)}"
    return f'''
    SELECT DISTINCT c."Client_Name" AS value
    FROM clients c
    LEFT JOIN users u ON u."Client_Name" = c."Client_Name"
    LEFT JOIN channels ch ON ch."Client_Name" = c."Client_Name"
    {where}
    ORDER BY 1;
  '''


def get_filter_options_input_types_query(access_filter: dict = None) -> str:
    if access_filter and access_filter.get("predicates"):
        return f'''
        SELECT DISTINCT rv."Input_Type" AS value
        FROM raw_videos rv
        {access_filter["join"]}
        WHERE rv."Input_Type" IS NOT NULL
          AND {' AND '.join(access_filter["predicates"])}
        ORDER BY 1;
      '''
    return '''
    SELECT DISTINCT "Input_Type" AS value
    FROM raw_videos
    WHERE "Input_Type" IS NOT NULL
    ORDER BY 1;
  '''


def get_filter_options_languages_query(access_filter: dict = None) -> str:
    if access_filter and access_filter.get("predicates"):
        return f'''
        SELECT DISTINCT rv."Language" AS value
        FROM raw_videos rv
        {access_filter["join"]}
        WHERE rv."Language" IS NOT NULL
          AND {' AND '.join(access_filter["predicates"])}
        ORDER BY 1;
      '''
    return '''
    SELECT DISTINCT "Language" AS value
    FROM raw_videos
    WHERE "Language" IS NOT NULL
    ORDER BY 1;
  '''


def get_filter_options_channels_query(access_filter: dict = None) -> str:
    if access_filter and access_filter.get("predicates"):
        preds = [p.replace("rv.", "rvc.").replace("u_scope.", "u.").replace("ch_scope.", "ch.") for p in access_filter["predicates"]]
        where = f"WHERE {' AND '.join(preds)}"
        return f'''
        SELECT DISTINCT ch."Channel_Name" AS value
        FROM channels ch
        LEFT JOIN users u ON u."Client_Name" = ch."Client_Name"
        LEFT JOIN raw_video_channel rvc ON rvc."Channel_Name" = ch."Channel_Name"
        {where}
        ORDER BY 1;
      '''
    return '''
    SELECT DISTINCT "Channel_Name" AS value
    FROM channels
    ORDER BY 1;
  '''


def get_filter_options_users_query(access_filter: dict = None) -> str:
    if access_filter and access_filter.get("predicates"):
        preds = [p.replace("rv.", "u.").replace("u_scope.", "u.").replace("ch_scope.", "ch.") for p in access_filter["predicates"]]
        where = f"AND {' AND '.join(preds)}"
        return f'''
        SELECT DISTINCT u."User_Name" AS value
        FROM users u
        LEFT JOIN channels ch ON ch."Client_Name" = u."Client_Name"
        WHERE u."User_Name" IS NOT NULL {where}
        ORDER BY 1;
      '''
    return '''
    SELECT DISTINCT "User_Name" AS value
    FROM users
    WHERE "User_Name" IS NOT NULL
    ORDER BY 1;
  '''


def get_filter_options_teams_query(access_filter: dict = None) -> str:
    if access_filter and access_filter.get("predicates"):
        preds = [p.replace("rv.", "u.").replace("u_scope.", "u.").replace("ch_scope.", "ch.") for p in access_filter["predicates"]]
        where = f"AND {' AND '.join(preds)}"
        return f'''
        SELECT DISTINCT u."Team_Name" AS value
        FROM users u
        LEFT JOIN channels ch ON ch."Client_Name" = u."Client_Name"
        WHERE u."Team_Name" IS NOT NULL {where}
        ORDER BY 1;
      '''
    return '''
    SELECT DISTINCT "Team_Name" AS value
    FROM users
    WHERE "Team_Name" IS NOT NULL
    ORDER BY 1;
  '''
