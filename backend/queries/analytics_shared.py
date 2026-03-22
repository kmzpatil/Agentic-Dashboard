from math import sqrt
from typing import Any

import numpy as np
import pandas as pd


METRIC_SQL = {
    "uploaded_count": '''
    SELECT date_trunc($1, to_date(left(("Upload_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM raw_videos
    GROUP BY 1
    ORDER BY 1;
  ''',
    "created_count": '''
    SELECT date_trunc($1, to_date(left(("Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM created_assets
    GROUP BY 1
    ORDER BY 1;
  ''',
    "published_count": '''
    SELECT date_trunc($1, to_date(left(("Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM published_posts
    GROUP BY 1
    ORDER BY 1;
  ''',
    "uploaded_duration": '''
    SELECT date_trunc($1, to_date(left(("Upload_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS value
    FROM raw_videos
    GROUP BY 1
    ORDER BY 1;
  ''',
    "created_duration": '''
    SELECT date_trunc($1, to_date(left(("Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS value
    FROM created_assets
    GROUP BY 1
    ORDER BY 1;
  ''',
    "published_duration": '''
    SELECT date_trunc($1, to_date(left(("Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS value
    FROM published_posts
    GROUP BY 1
    ORDER BY 1;
  ''',
    "publish_conversion_rate": '''
    WITH created AS (
      SELECT date_trunc($1, to_date(left(("Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date(left(("Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS published_count
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
      SELECT date_trunc($1, to_date(left(("Upload_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
      FROM raw_videos
      GROUP BY 1
    ),
    created AS (
      SELECT date_trunc($1, to_date(left(("Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
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
      SELECT date_trunc($1, to_date(left(("Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS created_duration
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date(left(("Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS published_duration
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
      SELECT date_trunc($1, to_date(left(("Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period,
      COALESCE(AVG("Created_Duration"), 0)::float8 AS avg_created_duration
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date(left(("Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period,
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
    if len(points) < 6:
        return []

    periods = [str(point.get("period")) for point in points]
    values = np.array([float(point.get("value") or 0) for point in points], dtype=float)

    # Infer granularity period for STL from date spacing.
    parsed_periods = pd.to_datetime(periods, errors="coerce")
    valid_periods = parsed_periods.dropna()
    stl_period = 12
    if len(valid_periods) >= 3:
        day_deltas = np.diff(valid_periods.values.astype("datetime64[D]")).astype(int)
        positive_deltas = day_deltas[day_deltas > 0]
        if positive_deltas.size:
            median_delta = float(np.median(positive_deltas))
            if median_delta <= 2:
                stl_period = 7
            elif median_delta <= 10:
                stl_period = 8
            elif median_delta <= 40:
                stl_period = 12
            else:
                stl_period = 4

    # Decompose into trend/seasonal/residual using STL when available.
    trend = values.copy()
    seasonal = np.zeros_like(values)
    residual = np.zeros_like(values)
    if len(values) >= max(stl_period * 2, 8):
        try:
            seasonal_mod = __import__("statsmodels.tsa.seasonal", fromlist=["STL"])
            STL = getattr(seasonal_mod, "STL")

            fit = STL(values, period=stl_period, robust=True).fit()
            trend = np.asarray(fit.trend, dtype=float)
            seasonal = np.asarray(fit.seasonal, dtype=float)
            residual = np.asarray(fit.resid, dtype=float)
        except Exception:
            # Lightweight fallback if STL is unavailable in environment.
            window = min(max(stl_period, 3), len(values))
            trend = (
                pd.Series(values)
                .rolling(window=window, center=True, min_periods=1)
                .mean()
                .to_numpy(dtype=float)
            )
            detrended = values - trend
            if stl_period > 1 and len(values) >= stl_period:
                index_mod = np.arange(len(values)) % stl_period
                seasonal_means = np.zeros(stl_period, dtype=float)
                for i in range(stl_period):
                    bucket = detrended[index_mod == i]
                    seasonal_means[i] = float(bucket.mean()) if bucket.size else 0.0
                seasonal = seasonal_means[index_mod]
                seasonal = seasonal - float(np.mean(seasonal))
            residual = values - trend - seasonal

    anomalies: list[dict[str, Any]] = []

    # 1) Global z-score anomalies (existing behavior retained).
    mean = float(values.mean())
    std = float(values.std())
    if std > 0:
        z_scores = (values - mean) / std
        for idx, z_score in enumerate(z_scores):
            if abs(z_score) >= 1.5:
                anomalies.append(
                    {
                        "period": periods[idx],
                        "value": round(float(values[idx]), 2),
                        "zScore": round(float(z_score), 2),
                        "severity": "high" if abs(z_score) >= 2.5 else "medium",
                        "direction": "spike" if z_score > 0 else "drop",
                        "method": "zscore",
                    }
                )

    # 2) Seasonal deviation anomalies from STL residuals.
    residual_std = float(np.std(residual))
    if residual_std > 0:
        residual_z = residual / residual_std
        for idx, score in enumerate(residual_z):
            if abs(score) >= 2.0:
                anomalies.append(
                    {
                        "period": periods[idx],
                        "value": round(float(values[idx]), 2),
                        "zScore": round(float(score), 2),
                        "severity": "high" if abs(score) >= 3.0 else "medium",
                        "direction": "spike" if score > 0 else "drop",
                        "method": "seasonal_deviation",
                    }
                )

    # 3) Trend reversal anomalies from trend derivative sign changes.
    if len(trend) >= 4:
        slope = np.diff(trend)
        if slope.size >= 3:
            slope_scale = float(np.std(slope))
            if slope_scale > 0:
                for i in range(1, len(slope)):
                    prev_s = float(slope[i - 1])
                    curr_s = float(slope[i])
                    # Significant sign change: rising->falling or falling->rising.
                    if prev_s == 0 or curr_s == 0 or np.sign(prev_s) == np.sign(curr_s):
                        continue
                    if abs(prev_s) < (0.35 * slope_scale) and abs(curr_s) < (0.35 * slope_scale):
                        continue

                    reversal_strength = abs(curr_s - prev_s) / slope_scale
                    if reversal_strength < 1.2:
                        continue

                    point_idx = i  # slope[i] is between point i and i+1, reversal centered at i
                    turning_direction = "drop" if prev_s > 0 and curr_s < 0 else "spike"
                    anomalies.append(
                        {
                            "period": periods[point_idx],
                            "value": round(float(values[point_idx]), 2),
                            "zScore": round(float(reversal_strength), 2),
                            "severity": "high" if reversal_strength >= 2.2 else "medium",
                            "direction": turning_direction,
                            "method": "trend_reversal",
                        }
                    )

    anomalies.sort(key=lambda item: abs(float(item.get("zScore") or 0)), reverse=True)
    return anomalies[:8]


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
      SELECT date_trunc($1, to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
      FROM scoped_videos sv
      GROUP BY 1
      ORDER BY 1;
    ''',
        "created_count": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sa."Asset_ID")::float8 AS value
      FROM scoped_assets sa
      GROUP BY 1
      ORDER BY 1;
    ''',
        "published_count": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(left((sp."Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sp."Post_ID")::float8 AS value
      FROM scoped_posts sp
      GROUP BY 1
      ORDER BY 1;
    ''',
        "uploaded_duration": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sv."Uploaded_Duration"), 0)::float8 AS value
      FROM scoped_videos sv
      GROUP BY 1
      ORDER BY 1;
    ''',
        "created_duration": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS value
      FROM scoped_assets sa
      GROUP BY 1
      ORDER BY 1;
    ''',
        "published_duration": f'''{scoped_videos_cte}
      SELECT date_trunc($1, to_date(left((sp."Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS value
      FROM scoped_posts sp
      GROUP BY 1
      ORDER BY 1;
    ''',
        "publish_conversion_rate": f'''{scoped_videos_cte}
      , created AS (
        SELECT date_trunc($1, to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sa."Asset_ID")::float8 AS created_count
        FROM scoped_assets sa
        GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(left((sp."Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sp."Post_ID")::float8 AS published_count
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
        SELECT date_trunc($1, to_date(left((sv."Upload_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
        FROM scoped_videos sv
        GROUP BY 1
      ),
      created AS (
        SELECT date_trunc($1, to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COUNT(DISTINCT sa."Asset_ID")::float8 AS created_count
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
        SELECT date_trunc($1, to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS created_duration
        FROM scoped_assets sa
        GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(left((sp."Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS published_duration
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
        SELECT date_trunc($1, to_date(left((sa."Create_Date")::text, 10), 'YYYY-MM-DD'))::date AS period,
        COALESCE(AVG(sa."Created_Duration"), 0)::float8 AS avg_created_duration
        FROM scoped_assets sa
        GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(left((sp."Publish_Date")::text, 10), 'YYYY-MM-DD'))::date AS period,
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
