"""
explorer.py — Explorer SQL queries.
Port of backend_legacy/queries/explorerQueries.js.
"""

TABLES_QUERY = """
    SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename
"""

TABLE_EXISTS_QUERY = """
    SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = :tbl
"""

TABLE_COLUMNS_QUERY = """
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = :tbl
    ORDER BY ordinal_position
"""


def matrix_query(dim1_expr: str, dim2_expr: str, measure_expr: str,
                 scope_join: str, where_clause: str) -> str:
    return f"""
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
        {where_clause}
        GROUP BY 1, 2
        ORDER BY value DESC
        LIMIT 600
    """


def time_series_query(date_expr: str, dim2_expr: str, measure_expr: str,
                      scope_join: str, where_parts: list[str]) -> str:
    where = " AND ".join(where_parts) if where_parts else "TRUE"
    return f"""
        SELECT date_trunc(:ts_grain, {date_expr})::date AS period,
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
        WHERE {where}
        GROUP BY 1, 2
        ORDER BY 1, 2
    """


def table_data_query(table_name: str, limit: int) -> str:
    safe = table_name.replace('"', '""')
    return f'SELECT * FROM "{safe}" LIMIT {limit}'


def sum_chart_query(table: str, x: str, y: str) -> str:
    t = table.replace('"', '""')
    xc = x.replace('"', '""')
    yc = y.replace('"', '""')
    return f"""
        SELECT "{xc}"::text AS label, COALESCE(SUM("{yc}"), 0)::float8 AS value
        FROM "{t}" GROUP BY 1 ORDER BY value DESC LIMIT 30
    """


def count_chart_query(table: str, x: str) -> str:
    t = table.replace('"', '""')
    xc = x.replace('"', '""')
    return f"""
        SELECT "{xc}"::text AS label, COUNT(*)::float8 AS value
        FROM "{t}" GROUP BY 1 ORDER BY value DESC LIMIT 30
    """
