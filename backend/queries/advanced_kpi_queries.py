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
      SELECT to_char(to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'), 'Mon') AS label,
             COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) * 100 AS rate,
             EXTRACT(MONTH FROM to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD')) AS m_num
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
        SELECT u."User_Name", u."Team_Name", SUM(sa."Created_Duration") as total_dur
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        GROUP BY u."User_Name", u."Team_Name" HAVING SUM(sa."Created_Duration") > 0
    ),
    user_input_totals AS (
        SELECT u."User_Name", u."Team_Name", sv."Input_Type", SUM(sa."Created_Duration") as input_dur
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY u."User_Name", u."Team_Name", sv."Input_Type" HAVING SUM(sa."Created_Duration") > 0
    ),
    user_entropy AS (
        SELECT ui."User_Name" as label,
               -SUM((ui.input_dur::float8 / ut.total_dur) * (ln(ui.input_dur::float8 / ut.total_dur)/ln(2))) as entropy
        FROM user_input_totals ui
        JOIN user_totals ut ON ui."User_Name" = ut."User_Name"
        GROUP BY ui."User_Name"
        ORDER BY entropy DESC LIMIT 20
    ),
    team_totals AS (
        SELECT "Team_Name", SUM(total_dur) as total_dur
        FROM user_totals
        WHERE "Team_Name" IS NOT NULL
        GROUP BY "Team_Name"
    ),
    team_input_totals AS (
        SELECT "Team_Name", "Input_Type", SUM(input_dur) as input_dur
        FROM user_input_totals
        WHERE "Team_Name" IS NOT NULL
        GROUP BY "Team_Name", "Input_Type"
    ),
    team_entropy AS (
        SELECT ti."Team_Name" as label,
               -SUM((ti.input_dur::float8 / tt.total_dur) * (ln(ti.input_dur::float8 / tt.total_dur)/ln(2))) as entropy
        FROM team_input_totals ti
        JOIN team_totals tt ON ti."Team_Name" = tt."Team_Name"
        GROUP BY ti."Team_Name"
        ORDER BY entropy DESC LIMIT 20
    ),
    top_user AS (
        SELECT label FROM user_entropy ORDER BY entropy DESC LIMIT 1
    ),
    user_shares AS (
        SELECT ui."Input_Type" as label, ui.input_dur as data
        FROM user_input_totals ui
        JOIN top_user tu ON ui."User_Name" = tu.label
    ),
    top_team AS (
        SELECT label FROM team_entropy ORDER BY entropy DESC LIMIT 1
    ),
    team_shares AS (
        SELECT ti."Input_Type" as label, ti.input_dur as data
        FROM team_input_totals ti
        JOIN top_team tt ON ti."Team_Name" = tt.label
    )
    SELECT 
        (SELECT COALESCE(json_agg(row_to_json(user_entropy)), '[]'::json) FROM user_entropy) as users,
        (SELECT COALESCE(json_agg(row_to_json(team_entropy)), '[]'::json) FROM team_entropy) as teams,
        (SELECT COALESCE(json_agg(row_to_json(user_shares)), '[]'::json) FROM user_shares) as user_shares,
        (SELECT COALESCE(json_agg(row_to_json(team_shares)), '[]'::json) FROM team_shares) as team_shares;
    '''

def get_dfs_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , input_durations AS (
        SELECT sv."Input_Type" as label,
               AVG(sa."Created_Duration") as avg_created,
               AVG(sp."Published_Duration") as avg_published,
               1 - (ABS(AVG(sa."Created_Duration") - COALESCE(AVG(sp."Published_Duration"), 0)) / NULLIF(AVG(sa."Created_Duration"), 0)) as score
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

    count_id_expr = f't.{id_col}' if tbl not in ("scoped_videos", "scoped_posts") else id_col
    user_join = f'JOIN {tbl} t ON sv."Video_ID" = t."Video_ID"' if tbl not in ("scoped_videos", "scoped_posts") else ""
    if tbl == "scoped_posts":
      user_join = 'JOIN scoped_posts t ON sv."Video_ID" = t."Video_ID"'
    channel_join = f'JOIN {tbl} t ON svc."Video_ID" = t."Video_ID"' if tbl not in ("scoped_videos", "scoped_posts") else ""
    if tbl == "scoped_posts":
      channel_join = 'JOIN scoped_posts t ON svc."Video_ID" = t."Video_ID"'
    input_join = f'JOIN {tbl} t ON sv."Video_ID" = t."Video_ID"' if tbl not in ("scoped_videos", "scoped_posts") else ""
    if tbl == "scoped_posts":
      input_join = 'JOIN scoped_posts t ON sv."Video_ID" = t."Video_ID"'

    return f'''{get_scoped_advanced_ctes(access_filter)}
    ,    time_series AS (
      SELECT to_char(to_date(left(({dt})::text, 10), 'YYYY-MM-DD'), 'Mon') AS label,
             COUNT(DISTINCT {id_col})::float8 AS rate,
             EXTRACT(MONTH FROM to_date(left(({dt})::text, 10), 'YYYY-MM-DD')) AS m_num
      FROM {tbl}
      WHERE {dt} IS NOT NULL
      GROUP BY EXTRACT(MONTH FROM to_date(left(({dt})::text, 10), 'YYYY-MM-DD')), to_char(to_date(left(({dt})::text, 10), 'YYYY-MM-DD'), 'Mon')
      ORDER BY m_num LIMIT 12
    ),
    user_stats AS (
      SELECT u."User_Name" AS label, COUNT(DISTINCT {count_id_expr})::float8 AS rate
      FROM scoped_videos sv
      JOIN users u ON u."User_ID" = sv."User_ID"
      {user_join}
      GROUP BY 1 ORDER BY rate DESC LIMIT 20
    ),
    channel_stats AS (
      SELECT svc."Channel_Name" AS label, COUNT(DISTINCT {count_id_expr})::float8 AS rate
      FROM scoped_video_channels svc
      {channel_join}
      GROUP BY 1 ORDER BY rate DESC LIMIT 20
    ),
    input_stats AS (
      SELECT sv."Input_Type" AS label, COUNT(DISTINCT {count_id_expr})::float8 AS rate
      FROM scoped_videos sv
      {input_join}
      GROUP BY 1 ORDER BY rate DESC LIMIT 10
    )
    SELECT 
      (SELECT json_agg(row_to_json(user_stats)) FROM user_stats) AS users,
      (SELECT json_agg(row_to_json(channel_stats)) FROM channel_stats) AS channels,
      (SELECT COALESCE(json_agg(row_to_json(time_series)), '[]'::json) FROM time_series) AS timeseries,
      (SELECT json_agg(row_to_json(input_stats)) FROM input_stats) AS inputs;
    '''

def get_month_by_month_use_rate_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , time_series AS (
        SELECT to_char(to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD'), 'Mon') AS label,
               COUNT(DISTINCT sv."Video_ID") AS current_count,
               LAG(COUNT(DISTINCT sv."Video_ID")) OVER (ORDER BY EXTRACT(MONTH FROM to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD'))) as prev_count,
               EXTRACT(MONTH FROM to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD')) AS m_num
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


def get_processing_efficiency_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , user_eff AS (
      SELECT u."User_Name" AS label,
             COALESCE((SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) * 100, 0) AS rate
      FROM scoped_videos sv
      JOIN users u ON u."User_ID" = sv."User_ID"
      JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY u."User_Name" HAVING SUM(sa."Created_Duration") > 0 ORDER BY rate DESC LIMIT 20
    ),
    channel_eff AS (
      SELECT svc."Channel_Name" AS label,
             COALESCE((SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) * 100, 0) AS rate
      FROM scoped_video_channels svc
      JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY svc."Channel_Name" HAVING SUM(sa."Created_Duration") > 0 ORDER BY rate DESC LIMIT 20
    ),
    time_series_eff AS (
      SELECT to_char(to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'), 'Mon') AS label,
             COALESCE((SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) * 100, 0) AS rate,
             EXTRACT(MONTH FROM to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD')) AS m_num
      FROM scoped_assets sa
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY 1, 3 ORDER BY 3 LIMIT 12
    ),
    input_eff AS (
      SELECT sv."Input_Type" AS label,
             COALESCE((SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) * 100, 0) AS rate
      FROM scoped_videos sv
      JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      WHERE sv."Input_Type" IS NOT NULL
      GROUP BY sv."Input_Type" HAVING SUM(sa."Created_Duration") > 0 ORDER BY rate DESC LIMIT 5
    ),
    output_eff AS (
      SELECT sa."Output_Type" AS label,
             COALESCE((SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)) * 100, 0) AS rate
      FROM scoped_assets sa
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      WHERE sa."Output_Type" IS NOT NULL
      GROUP BY sa."Output_Type" HAVING SUM(sa."Created_Duration") > 0 ORDER BY rate DESC LIMIT 5
    )
    SELECT 
      (SELECT json_agg(row_to_json(user_eff)) FROM user_eff) AS users,
      (SELECT json_agg(row_to_json(channel_eff)) FROM channel_eff) AS channels,
      (SELECT json_agg(row_to_json(time_series_eff)) FROM time_series_eff) AS timeseries,
      (SELECT json_agg(row_to_json(input_eff)) FROM input_eff) AS inputs,
      (SELECT json_agg(row_to_json(output_eff)) FROM output_eff) AS outputs;
    '''

def get_creation_rate_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , input_cr AS (
      SELECT sv."Input_Type" AS label,
             COUNT(DISTINCT sa."Asset_ID")::float8 / NULLIF(COUNT(DISTINCT sv."Video_ID"), 0) AS rate
      FROM scoped_videos sv
      LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      WHERE sv."Input_Type" IS NOT NULL
      GROUP BY sv."Input_Type" HAVING COUNT(DISTINCT sv."Video_ID") > 0 ORDER BY rate DESC LIMIT 7
    ),
    channel_cr AS (
      SELECT svc."Channel_Name" AS label,
             COUNT(DISTINCT sa."Asset_ID")::float8 / NULLIF(COUNT(DISTINCT svc."Video_ID"), 0) AS rate
      FROM scoped_video_channels svc
      LEFT JOIN scoped_assets sa ON svc."Video_ID" = sa."Video_ID"
      GROUP BY svc."Channel_Name" HAVING COUNT(DISTINCT svc."Video_ID") > 0 ORDER BY rate DESC LIMIT 20
    ),
    time_series_cr AS (
      SELECT to_char(to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD'), 'Mon') AS label,
             COUNT(DISTINCT sa."Asset_ID")::float8 / NULLIF(COUNT(DISTINCT sv."Video_ID"), 0) AS rate,
             EXTRACT(MONTH FROM to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD')) AS m_num
      FROM scoped_videos sv
      LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      GROUP BY 1, 3 ORDER BY 3 LIMIT 12
    )
    SELECT 
      (SELECT json_agg(row_to_json(input_cr)) FROM input_cr) AS inputs,
      (SELECT json_agg(row_to_json(channel_cr)) FROM channel_cr) AS channels,
      (SELECT json_agg(row_to_json(time_series_cr)) FROM time_series_cr) AS timeseries;
    '''

def get_upload_failure_rate_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , video_success AS (
      SELECT sv."Video_ID", sv."User_ID", MAX(sv."Upload_Date") as "Upload_Date",
             COUNT(DISTINCT sp."Post_ID") as posts
      FROM scoped_videos sv
      LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
      LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
      GROUP BY sv."Video_ID", sv."User_ID"
    ),
    user_fail AS (
      SELECT u."User_Name" AS label,
             1000 * POWER((SUM(CASE WHEN vs.posts = 0 THEN 1 ELSE 0 END)::float8 / NULLIF(COUNT(*), 0)), 1.5) AS rate
      FROM video_success vs
      JOIN users u ON u."User_ID" = vs."User_ID"
      GROUP BY u."User_Name" HAVING COUNT(*) > 0 ORDER BY rate DESC LIMIT 15
    ),
    channel_fail AS (
      SELECT svc."Channel_Name" AS label,
             1000 * POWER((SUM(CASE WHEN vs.posts = 0 THEN 1 ELSE 0 END)::float8 / NULLIF(COUNT(*), 0)), 1.5) AS rate
      FROM video_success vs
      JOIN scoped_video_channels svc ON svc."Video_ID" = vs."Video_ID"
      GROUP BY svc."Channel_Name" HAVING COUNT(*) > 0 ORDER BY rate DESC LIMIT 15
    ),
    time_series_fail AS (
      SELECT to_char(to_date(left((vs."Upload_Date")::text, 10), 'YYYY-MM-DD'), 'Mon') AS label,
             1000 * POWER((SUM(CASE WHEN vs.posts = 0 THEN 1 ELSE 0 END)::float8 / NULLIF(COUNT(*), 0)), 1.5) AS rate,
             EXTRACT(MONTH FROM to_date(left((vs."Upload_Date")::text, 10), 'YYYY-MM-DD')) AS m_num
      FROM video_success vs
      WHERE vs."Upload_Date" IS NOT NULL
      GROUP BY EXTRACT(MONTH FROM to_date(left((vs."Upload_Date")::text, 10), 'YYYY-MM-DD')), to_char(to_date(left((vs."Upload_Date")::text, 10), 'YYYY-MM-DD'), 'Mon')
      ORDER BY m_num LIMIT 12
    )
    SELECT 
      (SELECT json_agg(row_to_json(user_fail)) FROM user_fail) AS users,
      (SELECT json_agg(row_to_json(channel_fail)) FROM channel_fail) AS channels,
      (SELECT json_agg(row_to_json(time_series_fail)) FROM time_series_fail) AS timeseries;
    '''

def get_multidimensional_waste_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , global_waste AS (
        SELECT COALESCE(1.0 - (SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)), 1.0) as expected_waste
        FROM scoped_assets sa
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
    ),
    joint_waste AS (
        SELECT sv."Input_Type" as x, sa."Output_Type" as y,
               COALESCE(1.0 - (SUM(sp."Published_Duration")::float8 / NULLIF(SUM(sa."Created_Duration"), 0)), 1.0) as actual_waste
        FROM scoped_videos sv
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL AND sa."Output_Type" IS NOT NULL
        GROUP BY sv."Input_Type", sa."Output_Type"
    ),
    waste_matrix AS (
        SELECT j.x, j.y,
               j.actual_waste / NULLIF((SELECT expected_waste FROM global_waste), 0) as v
        FROM joint_waste j
    )
    SELECT json_agg(row_to_json(waste_matrix)) as heatmap FROM waste_matrix;
    '''



def get_publish_dependency_index_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , user_rates AS (
        SELECT u."User_Name" as label,
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) * 100 as rate
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY u."User_Name" HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    input_rates AS (
        SELECT sv."Input_Type" as label,
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) * 100 as rate
        FROM scoped_videos sv
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY sv."Input_Type" HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    output_rates AS (
        SELECT sa."Output_Type" as label,
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) * 100 as rate
        FROM scoped_assets sa
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sa."Output_Type" IS NOT NULL
        GROUP BY sa."Output_Type" HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    language_rates AS (
        SELECT sv."Language" as label,
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) * 100 as rate
        FROM scoped_videos sv
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Language" IS NOT NULL
        GROUP BY sv."Language" HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    sectors AS (
        SELECT 'User ID' as label, COALESCE(stddev(rate)/100.0, 0) as score FROM user_rates
        UNION ALL
        SELECT 'Input Type' as label, COALESCE(stddev(rate)/100.0, 0) as score FROM input_rates
        UNION ALL
        SELECT 'Output Type' as label, COALESCE(stddev(rate)/100.0, 0) as score FROM output_rates
        UNION ALL
        SELECT 'Language' as label, COALESCE(stddev(rate)/100.0, 0) as score FROM language_rates
    )
    SELECT
        (SELECT COALESCE(json_agg(row_to_json(sectors)), '[]'::json) FROM sectors) as sectors,
        (SELECT COALESCE(json_agg(row_to_json(user_rates)), '[]'::json) FROM user_rates) as users,
        (SELECT COALESCE(json_agg(row_to_json(input_rates)), '[]'::json) FROM input_rates) as inputs,
        (SELECT COALESCE(json_agg(row_to_json(output_rates)), '[]'::json) FROM output_rates) as outputs,
        (SELECT COALESCE(json_agg(row_to_json(language_rates)), '[]'::json) FROM language_rates) as languages;
    '''

def get_point_biserial_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , asset_success AS (
        SELECT sa."Asset_ID",
               MAX(sv."Uploaded_Duration") as uploaded_dur,
               MAX(sa."Created_Duration") as created_dur,
               COUNT(DISTINCT sp."Post_ID") as published_count
        FROM scoped_assets sa
        JOIN scoped_videos sv ON sa."Video_ID" = sv."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sa."Asset_ID"
    ),
    success_stats AS (
        SELECT CASE WHEN published_count > 0 THEN 'Published' ELSE 'Not Published' END as label,
               AVG(uploaded_dur) as avg_uploaded,
               AVG(created_dur) as avg_created,
               COUNT(*) as obs_count
        FROM asset_success
        GROUP BY 1
    ),
    global_stats AS (
        SELECT stddev(uploaded_dur) as std_upload,
               stddev(created_dur) as std_create,
               (SUM(CASE WHEN published_count > 0 THEN 1 ELSE 0 END)::float8 / NULLIF(COUNT(*), 0)) as p
        FROM asset_success
    ),
    correlations AS (
        SELECT 'Uploaded Duration' as label,
               CASE WHEN g.std_upload > 0 THEN
                 (COALESCE(MAX(CASE WHEN s.label='Published' THEN s.avg_uploaded ELSE 0 END), 0) -
                  COALESCE(MAX(CASE WHEN s.label='Not Published' THEN s.avg_uploaded ELSE 0 END), 0)) / g.std_upload * sqrt(g.p * (1-g.p))
               ELSE 0 END as score
        FROM success_stats s CROSS JOIN global_stats g GROUP BY g.std_upload, g.p
        UNION ALL
        SELECT 'Created Duration' as label,
               CASE WHEN g.std_create > 0 THEN
                 (COALESCE(MAX(CASE WHEN s.label='Published' THEN s.avg_created ELSE 0 END), 0) -
                  COALESCE(MAX(CASE WHEN s.label='Not Published' THEN s.avg_created ELSE 0 END), 0)) / g.std_create * sqrt(g.p * (1-g.p))
               ELSE 0 END as score
        FROM success_stats s CROSS JOIN global_stats g GROUP BY g.std_create, g.p
    )
    SELECT
        (SELECT COALESCE(json_agg(row_to_json(correlations)), '[]'::json) FROM correlations) as correlations,
        (SELECT COALESCE(json_agg(row_to_json(success_stats)), '[]'::json) FROM success_stats) as stats;
    '''

def get_ctas_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , global_expected AS (
        SELECT (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) as p_expected
        FROM scoped_assets sa
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
    ),
    channel_user_stats AS (
        SELECT svc."Channel_Name", u."User_Name",
               COUNT(DISTINCT sa."Asset_ID") as c_assets,
               COUNT(DISTINCT sp."Post_ID") as c_posts
        FROM scoped_video_channels svc
        JOIN scoped_videos sv ON svc."Video_ID" = sv."Video_ID"
        JOIN users u ON u."User_ID" = sv."User_ID"
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY svc."Channel_Name", u."User_Name"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    channel_totals AS (
        SELECT "Channel_Name", SUM(c_assets) as t_assets
        FROM channel_user_stats
        GROUP BY "Channel_Name"
    ),
    ctas_scores AS (
        SELECT cu."Channel_Name" as label,
               SUM((cu.c_assets::float8 / NULLIF(ct.t_assets, 0)) *
                   ((cu.c_posts::float8 / NULLIF(cu.c_assets, 0)) / NULLIF((SELECT p_expected FROM global_expected), 0))) as score
        FROM channel_user_stats cu
        JOIN channel_totals ct ON cu."Channel_Name" = ct."Channel_Name"
        GROUP BY cu."Channel_Name"
        ORDER BY score DESC LIMIT 20
    ),
    top_channel_name AS (
        SELECT label FROM ctas_scores ORDER BY score DESC LIMIT 1
    ),
    top_channel_users AS (
        SELECT cu."User_Name" as label, cu.c_assets, cu.c_posts
        FROM channel_user_stats cu
        JOIN top_channel_name tc ON cu."Channel_Name" = tc.label
        ORDER BY cu.c_assets DESC LIMIT 10
    )
    SELECT
        (SELECT COALESCE(json_agg(row_to_json(ctas_scores)), '[]'::json) FROM ctas_scores) as channels,
        (SELECT COALESCE(json_agg(row_to_json(top_channel_users)), '[]'::json) FROM top_channel_users) as top_users;
    '''

def get_rei_query(access_filter: dict) -> str:
    return f'''{get_scoped_advanced_ctes(access_filter)}
    , global_input_conv AS (
        SELECT sv."Input_Type",
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) as g_rate
        FROM scoped_videos sv
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY sv."Input_Type"
    ),
    user_input_conv AS (
        SELECT u."User_Name", sv."Input_Type",
               COUNT(DISTINCT sa."Asset_ID") as c_assets,
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) as u_rate
        FROM scoped_videos sv
        JOIN users u ON u."User_ID" = sv."User_ID"
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY u."User_Name", sv."Input_Type"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    user_totals AS (
        SELECT "User_Name", SUM(c_assets) as t_assets
        FROM user_input_conv
        GROUP BY "User_Name"
    ),
    user_rei AS (
        SELECT uic."User_Name" as label,
               SUM((uic.c_assets::float8 / NULLIF(ut.t_assets, 0)) * (uic.u_rate / NULLIF(gic.g_rate, 0))) as score
        FROM user_input_conv uic
        JOIN user_totals ut ON uic."User_Name" = ut."User_Name"
        JOIN global_input_conv gic ON uic."Input_Type" = gic."Input_Type"
        GROUP BY uic."User_Name"
        ORDER BY score DESC LIMIT 20
    ),
    top_user AS (
        SELECT label FROM user_rei ORDER BY score DESC LIMIT 1
    ),
    top_user_details AS (
        SELECT uic."Input_Type" as label, uic.u_rate * 100 as user_conv, gic.g_rate * 100 as global_conv
        FROM user_input_conv uic
        JOIN top_user tu ON uic."User_Name" = tu.label
        JOIN global_input_conv gic ON uic."Input_Type" = gic."Input_Type"
    )
    SELECT
        (SELECT COALESCE(json_agg(row_to_json(user_rei)), '[]'::json) FROM user_rei) as users,
        (SELECT COALESCE(json_agg(row_to_json(top_user_details)), '[]'::json) FROM top_user_details) as top_user_inputs;
    '''
