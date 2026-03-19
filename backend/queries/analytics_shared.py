from math import sqrt
from typing import Any


METRIC_SQL = {
    "uploaded_count": '''
    SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM raw_videos
    GROUP BY 1
    ORDER BY 1;
  ''',
    "created_count": '''
    SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM created_assets
    GROUP BY 1
    ORDER BY 1;
  ''',
    "published_count": '''
    SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM published_posts
    GROUP BY 1
    ORDER BY 1;
  ''',
    "uploaded_duration": '''
    SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS value
    FROM raw_videos
    GROUP BY 1
    ORDER BY 1;
  ''',
    "created_duration": '''
    SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS value
    FROM created_assets
    GROUP BY 1
    ORDER BY 1;
  ''',
    "published_duration": '''
    SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS value
    FROM published_posts
    GROUP BY 1
    ORDER BY 1;
  ''',
    "publish_conversion_rate": '''
    WITH created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS published_count
      FROM published_posts
      GROUP BY 1
    )
    SELECT c.period,
      CASE WHEN c.created_count = 0 THEN 0 ELSE (COALESCE(p.published_count, 0) / c.created_count) * 100 END AS value
    FROM created c
    LEFT JOIN published p ON p.period = c.period
    ORDER BY c.period;
  ''',
    "creation_rate": '''
    WITH uploaded AS (
      SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
      FROM raw_videos
      GROUP BY 1
    ),
    created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
      FROM created_assets
      GROUP BY 1
    )
    SELECT u.period,
      CASE WHEN u.uploaded_count = 0 THEN 0 ELSE (COALESCE(c.created_count, 0) / u.uploaded_count) * 100 END AS value
    FROM uploaded u
    LEFT JOIN created c ON c.period = u.period
    ORDER BY u.period;
  ''',
    "processing_efficiency": '''
    WITH created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS created_duration
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS published_duration
      FROM published_posts
      GROUP BY 1
    )
    SELECT c.period,
      CASE WHEN c.created_duration = 0 THEN 0 ELSE (COALESCE(p.published_duration, 0) / c.created_duration) * 100 END AS value
    FROM created c
    LEFT JOIN published p ON p.period = c.period
    ORDER BY c.period;
  ''',
    "waste_index": '''
    WITH created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period,
      COALESCE(AVG("Created_Duration"), 0)::float8 AS avg_created_duration
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period,
      COALESCE(AVG("Published_Duration"), 0)::float8 AS avg_published_duration
      FROM published_posts
      GROUP BY 1
    )
    SELECT c.period, (c.avg_created_duration - COALESCE(p.avg_published_duration, 0))::float8 AS value
    FROM created c
    LEFT JOIN published p ON p.period = c.period
    ORDER BY c.period;
  ''',
}

DIMENSION_MAP = {
    "channel": 'rvc."Channel_Name"',
    "language": 'rv."Language"',
    "input_type": 'rv."Input_Type"',
    "output_type": 'ca."Output_Type"',
    "user": 'u."User_Name"',
    "client": 'COALESCE(ch."Client_Name", u."Client_Name")',
    "published_platform": 'pd."Published_Platform"',
    "Team_Name": 'u."Team_Name"',
}

MEASURE_MAP = {
    "uploaded_videos": 'COUNT(DISTINCT rv."Video_ID")::float8',
    "created_assets": 'COUNT(DISTINCT ca."Asset_ID")::float8',
    "published_posts": 'COUNT(DISTINCT pp."Post_ID")::float8',
}

DATE_FIELD_MAP = {
    "upload_date": 'to_date(rv."Upload_Date", \'YYYY-MM-DD\')',
    "create_date": 'to_date(ca."Create_Date", \'YYYY-MM-DD\')',
    "publish_date": 'to_date(pp."Publish_Date", \'YYYY-MM-DD\')',
}

ANALYTICS_BASE_FROM = '''
  FROM raw_videos rv
  LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
  LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
  LEFT JOIN users u ON u."User_ID" = rv."User_ID"
  LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
  LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
  LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
'''


def get_trend_insights(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(points) < 3:
        return []

    values = [float(point.get("value") or 0) for point in points]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = sqrt(variance)

    ranked = []
    for point in points:
        value = float(point.get("value") or 0)
        z_score = 0 if std == 0 else (value - mean) / std
        ranked.append({"period": point.get("period"), "value": value, "z": z_score})

    ranked = [point for point in ranked if abs(point["z"]) >= 1.5]
    ranked.sort(key=lambda item: abs(item["z"]), reverse=True)

    return [
        {
            "period": point["period"],
            "value": round(point["value"], 2),
            "zScore": round(point["z"], 2),
            "severity": "high" if abs(point["z"]) >= 2.5 else "medium",
            "direction": "spike" if point["z"] > 0 else "drop",
        }
        for point in ranked[:8]
    ]


def build_where_clause(predicates: list[str]) -> str:
    if not predicates:
        return ""
    return f"WHERE {' AND '.join(predicates)}"


def build_client_name_expr(channel_alias: str, user_alias: str, include_unknown: bool = False) -> str:
  base = f'COALESCE({channel_alias}."Client_Name", {user_alias}."Client_Name")'
  if include_unknown:
    return f"COALESCE({base}, 'Unknown')"
  return base


def build_access_filter(auth: Any, start_index: int = 1, video_alias: str = "rv") -> dict[str, Any]:
    if not auth or auth.role == "website_admin":
        return {
            "join": "",
            "predicates": [],
            "params": [],
            "next_index": start_index,
        }

    if auth.role == "client_admin":
        scoped_client_expr = build_client_name_expr("ch_scope", "u_scope")
        return {
            "join": f'''
        LEFT JOIN users u_scope ON u_scope."User_ID" = {video_alias}."User_ID"
        LEFT JOIN raw_video_channel rvc_scope ON rvc_scope."Video_ID" = {video_alias}."Video_ID"
        LEFT JOIN channels ch_scope ON ch_scope."Channel_Name" = rvc_scope."Channel_Name"
      ''',
            "predicates": [f'{scoped_client_expr} = ${start_index}'],
            "params": [auth.client_name],
            "next_index": start_index + 1,
        }

    if auth.role == "user":
        return {
            "join": "",
            "predicates": [f'{video_alias}."User_ID" = ${start_index}'],
            "params": [auth.user_id],
            "next_index": start_index + 1,
        }

    return {
        "join": "",
        "predicates": [],
        "params": [],
        "next_index": start_index,
    }


def get_metric_query(
    metric: str,
    access_filter: dict[str, Any],
    asset_predicates: list[str] | None = None,
) -> str:
    scoped_videos_where = build_where_clause(access_filter["predicates"])
    scoped_assets_where = build_where_clause(asset_predicates or [])
    scoped_videos_cte = f'''
    WITH scoped_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Upload_Date", rv."Uploaded_Duration"
      FROM raw_videos rv
      {access_filter["join"]}
      {scoped_videos_where}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
      {scoped_assets_where}
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    )
  '''

    metric_sql = {
        "uploaded_count": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
      FROM scoped_videos sv
      GROUP BY 1
      ORDER BY 1;
    ''',
        "created_count": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sa."Asset_ID")::float8 AS value
      FROM scoped_assets sa
      GROUP BY 1
      ORDER BY 1;
    ''',
        "published_count": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sp."Post_ID")::float8 AS value
      FROM scoped_posts sp
      GROUP BY 1
      ORDER BY 1;
    ''',
        "uploaded_duration": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sv."Uploaded_Duration"), 0)::float8 AS value
      FROM scoped_videos sv
      GROUP BY 1
      ORDER BY 1;
    ''',
        "created_duration": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS value
      FROM scoped_assets sa
      GROUP BY 1
      ORDER BY 1;
    ''',
        "published_duration": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS value
      FROM scoped_posts sp
      GROUP BY 1
      ORDER BY 1;
    ''',
        "publish_conversion_rate": f'''{scoped_videos_cte}
      , created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sa."Asset_ID")::float8 AS created_count
        FROM scoped_assets sa
        GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sp."Post_ID")::float8 AS published_count
        FROM scoped_posts sp
        GROUP BY 1
      )
      SELECT c.period,
        CASE WHEN c.created_count = 0 THEN 0 ELSE (COALESCE(p.published_count, 0) / c.created_count) * 100 END AS value
      FROM created c
      LEFT JOIN published p ON p.period = c.period
      ORDER BY c.period;
    ''',
        "creation_rate": f'''{scoped_videos_cte}
      , uploaded AS (
        SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
        FROM scoped_videos sv
        GROUP BY 1
      ),
      created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sa."Asset_ID")::float8 AS created_count
        FROM scoped_assets sa
        GROUP BY 1
      )
      SELECT u.period,
        CASE WHEN u.uploaded_count = 0 THEN 0 ELSE (COALESCE(c.created_count, 0) / u.uploaded_count) * 100 END AS value
      FROM uploaded u
      LEFT JOIN created c ON c.period = u.period
      ORDER BY u.period;
    ''',
        "processing_efficiency": f'''{scoped_videos_cte}
      , created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS created_duration
        FROM scoped_assets sa
        GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS published_duration
        FROM scoped_posts sp
        GROUP BY 1
      )
      SELECT c.period,
        CASE WHEN c.created_duration = 0 THEN 0 ELSE (COALESCE(p.published_duration, 0) / c.created_duration) * 100 END AS value
      FROM created c
      LEFT JOIN published p ON p.period = c.period
      ORDER BY c.period;
    ''',
        "waste_index": f'''{scoped_videos_cte}
      , created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period,
        COALESCE(AVG(sa."Created_Duration"), 0)::float8 AS avg_created_duration
        FROM scoped_assets sa
        GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period,
        COALESCE(AVG(sp."Published_Duration"), 0)::float8 AS avg_published_duration
        FROM scoped_posts sp
        GROUP BY 1
      )
      SELECT c.period, (c.avg_created_duration - COALESCE(p.avg_published_duration, 0))::float8 AS value
      FROM created c
      LEFT JOIN published p ON p.period = c.period
      ORDER BY c.period;
    ''',
    }

    return metric_sql.get(metric, metric_sql["uploaded_count"])


def build_funnel_filter(filters: dict[str, str] | None = None, start_index: int = 1, auth: Any = None) -> dict[str, Any]:
  """Build filter clauses from a dict of {dimension: value} pairs.

  Supports simultaneous filters, e.g. {"client": "X", "input_type": "Interview", "language": "EN"}.
  Backward-compatible: also accepts legacy (dimension, value) via build_funnel_filter_legacy.
  """
  access_filter = build_access_filter(auth, start_index, "rv")
  params = [*access_filter["params"]]
  predicates = [*access_filter["predicates"]]
  join_parts: list[str] = []

  if access_filter["join"]:
    join_parts.append(access_filter["join"])

  next_index = access_filter["next_index"]
  needs_user_join = False
  needs_channel_join = False

  if filters:
    for dimension, value in filters.items():
      if not value:
        continue

      if dimension == "channel":
        if not needs_channel_join:
          join_parts.append('LEFT JOIN raw_video_channel rvc_filter ON rv."Video_ID" = rvc_filter."Video_ID"')
          needs_channel_join = True
        predicates.append(f'rvc_filter."Channel_Name" = ${next_index}')
        params.append(value)
        next_index += 1

      elif dimension == "client":
        if not needs_user_join:
          join_parts.append('LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"')
          needs_user_join = True
        if not needs_channel_join:
          join_parts.append('LEFT JOIN raw_video_channel rvc_filter ON rv."Video_ID" = rvc_filter."Video_ID"')
          needs_channel_join = True
        join_parts.append('LEFT JOIN channels ch_filter ON ch_filter."Channel_Name" = rvc_filter."Channel_Name"')
        predicates.append(f'{build_client_name_expr("ch_filter", "u_filter")} = ${next_index}')
        params.append(value)
        next_index += 1

      elif dimension == "input_type":
        predicates.append(f'rv."Input_Type" = ${next_index}')
        params.append(value)
        next_index += 1

      elif dimension == "language":
        predicates.append(f'rv."Language" = ${next_index}')
        params.append(value)
        next_index += 1

      elif dimension == "user":
        if not needs_user_join:
          join_parts.append('LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"')
          needs_user_join = True
        predicates.append(f'u_filter."User_Name" = ${next_index}')
        params.append(value)
        next_index += 1

      elif dimension == "team":
        if not needs_user_join:
          join_parts.append('LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"')
          needs_user_join = True
        predicates.append(f'u_filter."Team_Name" = ${next_index}')
        params.append(value)
        next_index += 1

      elif dimension == "output_type":
        join_parts.append('LEFT JOIN created_assets ca_filter ON ca_filter."Video_ID" = rv."Video_ID"')
        predicates.append(f'ca_filter."Output_Type" = ${next_index}')
        params.append(value)
        next_index += 1

  return {
    "join": "\n".join(join_parts),
    "where": build_where_clause(predicates),
    "predicates": predicates,
    "params": params,
    "next_index": next_index,
  }
