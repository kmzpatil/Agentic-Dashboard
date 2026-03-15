TABLES_QUERY = '''
  SELECT tablename
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY tablename;
'''

TABLE_EXISTS_QUERY = "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = $1"
TABLE_COLUMNS_QUERY = "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position"


def get_matrix_query(dim1_expr: str, dim2_expr: str, measure_expr: str, scope_join: str, matrix_where_clause: str) -> str:
    return f'''
    SELECT COALESCE({dim1_expr}::text, 'Unknown') AS dim1,
           COALESCE({dim2_expr}::text, 'Unknown') AS dim2,
           {measure_expr} AS value
    FROM raw_videos rv
    {scope_join}
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
    {matrix_where_clause}
    GROUP BY 1, 2
    ORDER BY value DESC
    LIMIT 600;
  '''


def get_time_series_query(date_expr: str, dim2_expr: str, measure_expr: str, scope_join: str, ts_where_clause: str) -> str:
    return f'''
    SELECT date_trunc($1, {date_expr})::date AS period,
           COALESCE({dim2_expr}::text, 'Unknown') AS dim2,
           {measure_expr} AS value
    FROM raw_videos rv
    {scope_join}
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
    WHERE {ts_where_clause}
    GROUP BY 1, 2
    ORDER BY 1, 2;
  '''


def get_table_data_query(table_name: str, limit: int) -> str:
    quoted_table_name = table_name.replace('"', '""')
    return f'SELECT * FROM "{quoted_table_name}" LIMIT {limit}'


def get_sum_chart_query(table: str, x: str, y: str) -> str:
    safe_x = x.replace('"', '""')
    safe_y = y.replace('"', '""')
    safe_table = table.replace('"', '""')
    return f'''
    SELECT "{safe_x}"::text AS label,
           COALESCE(SUM("{safe_y}"), 0)::float8 AS value
    FROM "{safe_table}"
    GROUP BY 1
    ORDER BY value DESC
    LIMIT 30;
  '''


def get_count_chart_query(table: str, x: str) -> str:
    safe_x = x.replace('"', '""')
    safe_table = table.replace('"', '""')
    return f'''
    SELECT "{safe_x}"::text AS label,
           COUNT(*)::float8 AS value
    FROM "{safe_table}"
    GROUP BY 1
    ORDER BY value DESC
    LIMIT 30;
  '''
