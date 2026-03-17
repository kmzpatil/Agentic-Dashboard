from typing import Any
from backend.queries.analytics_shared import build_where_clause

def get_scoped_advanced_ctes(access_filter: dict) -> str:
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

def get_publish_conversion_details_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , user_rates AS (
      SELECT u."User_Name" AS label,
             COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) * 100 AS rate
      FROM scoped_videos sv
      JOIN users u ON u."User_ID" = sv."User_ID"
      LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY u."User_Name" HAVING COUNT(DISTINCT sa."Asset_ID") > 0 ORDER BY rate DESC LIMIT 20
    ),
    channel_rates AS (
      SELECT svc."Channel_Name" AS label,
             COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) * 100 AS rate
      FROM scoped_video_channels svc
      LEFT JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY svc."Channel_Name" HAVING COUNT(DISTINCT sa."Asset_ID") > 0 ORDER BY rate DESC LIMIT 20
    ),
    time_series_rates AS (
      SELECT to_char(to_date(sa."Create_Date", 'YYYY-MM-DD'), 'Mon') AS label,
             COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) * 100 AS rate,
             EXTRACT(MONTH FROM to_date(sa."Create_Date", 'YYYY-MM-DD')) AS m_num
      FROM scoped_assets sa
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY 1, 3 ORDER BY 3 LIMIT 12
    ),
    input_rates AS (
      SELECT sv."Input_Type" AS label,
             COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) * 100 AS rate
      FROM scoped_videos sv
      LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY sv."Input_Type" HAVING COUNT(DISTINCT sa."Asset_ID") > 0 ORDER BY rate DESC LIMIT 5
    ),
    output_rates AS (
      SELECT sa."Output_Type" AS label,
             COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) * 100 AS rate
      FROM scoped_assets sa
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY sa."Output_Type" HAVING COUNT(DISTINCT sa."Asset_ID") > 0 ORDER BY rate DESC LIMIT 5
    )
    SELECT 
      (SELECT json_agg(row_to_json(user_rates)) FROM user_rates) AS users,
      (SELECT json_agg(row_to_json(channel_rates)) FROM channel_rates) AS channels,
      (SELECT json_agg(row_to_json(time_series_rates)) FROM time_series_rates) AS timeseries,
      (SELECT json_agg(row_to_json(input_rates)) FROM input_rates) AS inputs,
      (SELECT json_agg(row_to_json(output_rates)) FROM output_rates) AS outputs;
    '''

def get_roi_matrix_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , global_metrics AS (
        SELECT 
            AVG(ca."Created_Duration") as avg_created,
            COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0) as avg_conversion
        FROM scoped_assets ca
        LEFT JOIN scoped_posts sp ON ca."Asset_ID" = sp."Asset_ID"
    ),
    user_roi AS (
      SELECT 
        u."User_Name" as label,
        COALESCE(AVG(sa."Created_Duration") / NULLIF((SELECT avg_created FROM global_metrics), 0), 0) AS x,
        COALESCE((COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) / NULLIF((SELECT avg_conversion FROM global_metrics), 0), 0) AS y
      FROM scoped_videos sv
      JOIN users u ON u."User_ID" = sv."User_ID"
      JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY u."User_Name"
      HAVING COUNT(DISTINCT sa."Asset_ID") > 5
    ),
    channel_roi AS (
      SELECT 
        svc."Channel_Name" as label,
        COALESCE(AVG(sa."Created_Duration") / NULLIF((SELECT avg_created FROM global_metrics), 0), 0) AS x,
        COALESCE((COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) / NULLIF((SELECT avg_conversion FROM global_metrics), 0), 0) AS y
      FROM scoped_video_channels svc
      JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY svc."Channel_Name"
      HAVING COUNT(DISTINCT sa."Asset_ID") > 5
    )
    SELECT
      (SELECT json_agg(row_to_json(user_roi)) FROM user_roi LIMIT 30) AS users,
      (SELECT json_agg(row_to_json(channel_roi)) FROM channel_roi LIMIT 15) AS channels;
    '''

def get_waste_index_details_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , user_waste AS (
      SELECT u."User_Name" AS label,
             -log(GREATEST(1 - ((SUM(sa."Created_Duration") - COALESCE(SUM(sp."Published_Duration"), 0))::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) + 0.001, 0.001)::numeric) AS index
      FROM scoped_videos sv
      JOIN users u ON u."User_ID" = sv."User_ID"
      JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY u."User_Name" HAVING SUM(sa."Created_Duration") > 0 ORDER BY index DESC LIMIT 20
    ),
    channel_waste AS (
      SELECT svc."Channel_Name" AS label,
             -log(GREATEST(1 - ((SUM(sa."Created_Duration") - COALESCE(SUM(sp."Published_Duration"), 0))::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) + 0.001, 0.001)::numeric) AS index,
             SUM(sa."Created_Duration") - COALESCE(SUM(sp."Published_Duration"), 0) AS raw_waste
      FROM scoped_video_channels svc
      JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY svc."Channel_Name" HAVING SUM(sa."Created_Duration") > 0 ORDER BY index DESC LIMIT 20
    ),
    treemap AS (
        SELECT svc."Channel_Name" AS name, (SUM(sa."Created_Duration") - COALESCE(SUM(sp."Published_Duration"), 0)) AS value
        FROM scoped_video_channels svc
        JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY svc."Channel_Name" HAVING (SUM(sa."Created_Duration") - COALESCE(SUM(sp."Published_Duration"), 0)) > 0
        ORDER BY value DESC
    )
    SELECT 
      (SELECT json_agg(row_to_json(user_waste)) FROM user_waste) AS users,
      (SELECT json_agg(row_to_json(channel_waste)) FROM channel_waste) AS channels,
      (SELECT json_agg(row_to_json(treemap)) FROM treemap) AS treemap,
      '{{"labels":[],"datasets":[]}}'::json AS "teamWaste";
    '''
    
def get_interaction_lift_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , total_counts AS (
        SELECT COUNT(DISTINCT sa."Asset_ID") as t_assets, COUNT(DISTINCT sp."Post_ID") as t_posts
        FROM scoped_assets sa LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
    ),
    input_probs AS (
        SELECT sv."Input_Type", COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) AS p_input
        FROM scoped_videos sv 
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sv."Input_Type"
    ),
    output_probs AS (
        SELECT sa."Output_Type", COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) AS p_output
        FROM scoped_assets sa 
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sa."Output_Type"
    ),
    joint_probs AS (
        SELECT sv."Input_Type", sa."Output_Type", COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) AS p_joint
        FROM scoped_videos sv
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sv."Input_Type", sa."Output_Type"
    ),
    lift_matrix AS (
        SELECT j."Input_Type" as x, j."Output_Type" as y,
               CASE WHEN i.p_input = 0 OR o.p_output = 0 OR j.p_joint = 0 THEN 0 
               ELSE log((j.p_joint / (i.p_input * o.p_output))::numeric) END as v
        FROM joint_probs j
        JOIN input_probs i ON i."Input_Type" = j."Input_Type"
        JOIN output_probs o ON o."Output_Type" = j."Output_Type"
        WHERE j."Input_Type" IS NOT NULL AND j."Output_Type" IS NOT NULL
    )
    SELECT json_agg(row_to_json(lift_matrix)) as heatmap FROM lift_matrix;
    '''

def get_cross_dimension_entropy_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , user_totals AS (
        SELECT u."User_Name", SUM(sa."Created_Duration") as total_dur
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        GROUP BY u."User_Name" HAVING SUM(sa."Created_Duration") > 0
    ),
    user_input_totals AS (
        SELECT u."User_Name", sv."Input_Type", SUM(sa."Created_Duration") as input_dur
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY u."User_Name", sv."Input_Type" HAVING SUM(sa."Created_Duration") > 0
    ),
    user_entropy AS (
        SELECT ui."User_Name" as label,
               -SUM((ui.input_dur::float8 / ut.total_dur) * (ln(ui.input_dur::float8 / ut.total_dur)/ln(2))) as entropy
        FROM user_input_totals ui
        JOIN user_totals ut ON ui."User_Name" = ut."User_Name"
        GROUP BY ui."User_Name"
        ORDER BY entropy DESC LIMIT 20
    )
    SELECT json_agg(row_to_json(user_entropy)) as users FROM user_entropy;
    '''

def get_cdas_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , input_durations AS (
        SELECT sv."Input_Type" as label,
               AVG(sa."Created_Duration") as avg_created,
               AVG(sp."Published_Duration") as avg_published,
               1 - ((AVG(sa."Created_Duration") - COALESCE(AVG(sp."Published_Duration"), AVG(sa."Created_Duration"))) / AVG(sa."Created_Duration")) as score
        FROM scoped_videos sv
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY sv."Input_Type"
        HAVING AVG(sa."Created_Duration") > 0
        ORDER BY score DESC
        LIMIT 10
    )
    SELECT json_agg(row_to_json(input_durations)) as inputs FROM input_durations;
    '''

def get_generic_trend_query(access_filter: dict, kpi_id: str) -> str:
    # Handle core metrics for detail view: Uploaded, Processed, Created, Published
    metric_map = {
        "uploaded_count": {"table": "scoped_videos", "date_col": '"Upload_Date"', "id_col": '"Video_ID"'},
        "processed_count": {"table": "scoped_assets", "date_col": '"Create_Date"', "id_col": '"Video_ID"'},
        "created_count": {"table": "scoped_assets", "date_col": '"Create_Date"', "id_col": '"Asset_ID"'},
        "published_count": {"table": "scoped_posts", "date_col": '"Publish_Date"', "id_col": '"Post_ID"'}
    }
    
    config = metric_map.get(kpi_id, {"table": "scoped_assets", "date_col": '"Create_Date"', "id_col": '"Asset_ID"'})
    tbl = config["table"]
    dt = config["date_col"]
    id_col = config["id_col"]

    return f'''{get_scoped_advanced_ctes(access_filter)}
    , time_series AS (
      SELECT to_char(to_date({dt}, 'YYYY-MM-DD'), 'Mon DD') AS label,
             COUNT(DISTINCT {id_col})::float8 AS rate,
             to_date({dt}, 'YYYY-MM-DD') AS sort_date
      FROM {tbl}
      GROUP BY 1, 3 ORDER BY 3 DESC LIMIT 30
    ),
    seed_count AS (
      SELECT COUNT(DISTINCT {id_col})::float8 AS val 
      FROM {tbl} 
      WHERE to_date({dt}, 'YYYY-MM-DD') < (SELECT MIN(sort_date) FROM time_series)
    ),
    rev_time_series AS (
      SELECT label, 
             (SELECT val FROM seed_count) + SUM(rate) OVER (ORDER BY sort_date) AS rate,
             sort_date
      FROM time_series
      ORDER BY sort_date ASC
    ),
    user_stats AS (
      SELECT u."User_Name" AS label, COUNT(DISTINCT {"t." + id_col if tbl not in ("scoped_videos", "scoped_posts") else id_col})::float8 AS rate
      FROM scoped_videos sv
      JOIN users u ON u."User_ID" = sv."User_ID"
      {"JOIN " + tbl + " t ON sv.\"Video_ID\" = t.\"Video_ID\"" if tbl not in ("scoped_videos", "scoped_posts") else ""}
      {"JOIN scoped_posts t ON sv.\"Video_ID\" = t.\"Video_ID\"" if tbl == "scoped_posts" else ""}
      GROUP BY 1 ORDER BY rate DESC LIMIT 20
    ),
    channel_stats AS (
      SELECT svc."Channel_Name" AS label, COUNT(DISTINCT {"t." + id_col if tbl not in ("scoped_videos", "scoped_posts") else id_col})::float8 AS rate
      FROM scoped_video_channels svc
      {"JOIN " + tbl + " t ON svc.\"Video_ID\" = t.\"Video_ID\"" if tbl not in ("scoped_videos", "scoped_posts") else ""}
      {"JOIN scoped_posts t ON svc.\"Video_ID\" = t.\"Video_ID\"" if tbl == "scoped_posts" else ""}
      GROUP BY 1 ORDER BY rate DESC LIMIT 20
    ),
    input_stats AS (
      SELECT sv."Input_Type" AS label, COUNT(DISTINCT {"t." + id_col if tbl not in ("scoped_videos", "scoped_posts") else id_col})::float8 AS rate
      FROM scoped_videos sv
      {"JOIN " + tbl + " t ON sv.\"Video_ID\" = t.\"Video_ID\"" if tbl not in ("scoped_videos", "scoped_posts") else ""}
      {"JOIN scoped_posts t ON sv.\"Video_ID\" = t.\"Video_ID\"" if tbl == "scoped_posts" else ""}
      GROUP BY 1 ORDER BY rate DESC LIMIT 10
    )
    SELECT 
      (SELECT json_agg(row_to_json(user_stats)) FROM user_stats) AS users,
      (SELECT json_agg(row_to_json(channel_stats)) FROM channel_stats) AS channels,
      (SELECT json_agg(row_to_json(rev_time_series)) FROM rev_time_series) AS timeseries,
      (SELECT json_agg(row_to_json(input_stats)) FROM input_stats) AS inputs;
    '''

def get_month_by_month_use_rate_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , time_series AS (
        SELECT to_char(to_date(sv."Upload_Date", 'YYYY-MM-DD'), 'Mon') AS label,
               COUNT(DISTINCT sv."Video_ID") AS current_count,
               LAG(COUNT(DISTINCT sv."Video_ID")) OVER (ORDER BY EXTRACT(MONTH FROM to_date(sv."Upload_Date", 'YYYY-MM-DD'))) as prev_count,
               EXTRACT(MONTH FROM to_date(sv."Upload_Date", 'YYYY-MM-DD')) AS m_num
        FROM scoped_videos sv
        GROUP BY 1, 4 ORDER BY 4 LIMIT 12
    ),
    growth_rates AS (
        SELECT label, 
               CASE WHEN prev_count > 0 THEN ((current_count - prev_count)::float8 / prev_count) * 100 ELSE 0 END as rate
        FROM time_series
    ),
    channel_treemap AS (
        SELECT svc."Channel_Name" AS name, COUNT(DISTINCT svc."Video_ID") AS value
        FROM scoped_video_channels svc
        GROUP BY svc."Channel_Name" HAVING COUNT(DISTINCT svc."Video_ID") > 0
    ),
    user_treemap AS (
        SELECT u."User_Name" AS name, COUNT(DISTINCT sv."Video_ID") AS value
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        GROUP BY u."User_Name" HAVING COUNT(DISTINCT sv."Video_ID") > 0
    )
    SELECT 
      (SELECT json_agg(row_to_json(growth_rates)) FROM growth_rates) AS timeseries,
      (SELECT json_agg(row_to_json(channel_treemap)) FROM channel_treemap) AS channel_treemap,
      (SELECT json_agg(row_to_json(user_treemap)) FROM user_treemap) AS user_treemap;
    '''
