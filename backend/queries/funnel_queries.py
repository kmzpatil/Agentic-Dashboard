BREAKDOWN_EXPR_MAP = {
    "channel": 'rvc."Channel_Name"',
    "input_type": 'rv."Input_Type"',
    "language": 'rv."Language"',
    "output_type": 'ca."Output_Type"',
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
      SELECT DISTINCT pp."Post_ID"
      FROM published_posts pp
      JOIN created c ON c."Asset_ID" = pp."Asset_ID"
    )
    SELECT
      (SELECT COUNT(*)::int FROM filtered_videos) AS uploaded_count,
      (SELECT COUNT(*)::int FROM processed) AS processed_count,
      (SELECT COUNT(*)::int FROM created) AS created_count,
      (SELECT COUNT(*)::int FROM published) AS published_count;
  '''


def get_breakdown_query(filter_data: dict, breakdown_dimension: str) -> str:
    return f'''
    WITH filtered_videos AS (
      SELECT DISTINCT rv."Video_ID"
      FROM raw_videos rv
      {filter_data["join"]}
      {filter_data["where"]}
    )
    SELECT {BREAKDOWN_EXPR_MAP[breakdown_dimension]} AS label,
      COUNT(DISTINCT rv."Video_ID")::int AS uploaded_count,
      COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
      COUNT(DISTINCT pp."Post_ID")::int AS published_count,
      CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
        ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
    FROM filtered_videos fv
    JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    GROUP BY 1
    ORDER BY conversion DESC, uploaded_count DESC
    LIMIT 30;
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
