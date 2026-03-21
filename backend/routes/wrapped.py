"""
routes/wrapped.py
-----------------
Aggregated endpoint for the "Year Wrapped" feature.

GET /api/wrapped   Returns all KPI data needed for the wrapped slides,
                   scoped by the authenticated user's role.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter
from backend.queries.advanced_kpi_queries import get_scoped_advanced_ctes
from backend.queries.overview_queries import get_kpi_query

logger = logging.getLogger("frammer.routes.wrapped")

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def _pj(value):
    """Parse a JSON field that may arrive as a string, list, or None."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    if isinstance(value, list):
        return value
    return []


def _sf(v, default: float = 0.0) -> float:
    try:
        return float(v or default)
    except (TypeError, ValueError):
        return default


# ── query builders ────────────────────────────────────────────────────────────

def _platform_dist_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , platform_dist AS (
        SELECT COALESCE(pd."Published_Platform", 'Other') AS platform,
               COUNT(DISTINCT sp."Post_ID")::float8 AS cnt
        FROM scoped_posts sp
        LEFT JOIN post_distribution pd ON pd."Post_ID" = sp."Post_ID"
        GROUP BY pd."Published_Platform"
        ORDER BY cnt DESC
        LIMIT 8
    )
    SELECT COALESCE(json_agg(row_to_json(platform_dist)), '[]'::json) AS platforms
    FROM platform_dist;
    """


def _overall_entropy_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , input_counts AS (
        SELECT sv."Input_Type",
               COUNT(DISTINCT sa."Asset_ID")::float8 AS cnt
        FROM scoped_videos sv
        JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY sv."Input_Type"
    ),
    output_counts AS (
        SELECT sa."Output_Type",
               COUNT(DISTINCT sa."Asset_ID")::float8 AS cnt
        FROM scoped_assets sa
        WHERE sa."Output_Type" IS NOT NULL
        GROUP BY sa."Output_Type"
    ),
    input_total  AS (SELECT COALESCE(SUM(cnt), 1)::float8 AS total FROM input_counts),
    output_total AS (SELECT COALESCE(SUM(cnt), 1)::float8 AS total FROM output_counts),
    in_h AS (
        SELECT COALESCE(-SUM((cnt / t.total) * (ln(cnt / t.total) / ln(2))), 0)::float8 AS h
        FROM input_counts, input_total t WHERE t.total > 0
    ),
    out_h AS (
        SELECT COALESCE(-SUM((cnt / t.total) * (ln(cnt / t.total) / ln(2))), 0)::float8 AS h
        FROM output_counts, output_total t WHERE t.total > 0
    )
    SELECT
        (SELECT h FROM in_h)  AS input_entropy,
        (SELECT h FROM out_h) AS output_entropy,
        ((SELECT h FROM in_h) + (SELECT h FROM out_h)) / 2.0 AS combined_entropy;
    """


def _best_lift_pair_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , input_probs AS (
        SELECT sv."Input_Type",
               COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) AS p_input
        FROM scoped_videos sv
        JOIN  scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sv."Input_Type"
    ),
    output_probs AS (
        SELECT sa."Output_Type",
               COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) AS p_output
        FROM scoped_assets sa
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sa."Output_Type"
    ),
    joint_probs AS (
        SELECT sv."Input_Type", sa."Output_Type",
               COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0) AS p_joint,
               COUNT(DISTINCT sa."Asset_ID") AS pair_count
        FROM scoped_videos sv
        JOIN  scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        GROUP BY sv."Input_Type", sa."Output_Type"
        HAVING COUNT(DISTINCT sa."Asset_ID") >= 3
    ),
    lift_scores AS (
        SELECT j."Input_Type" AS input_type,
               j."Output_Type" AS output_type,
               CASE WHEN i.p_input = 0 OR o.p_output = 0 OR j.p_joint = 0 THEN 0
                    ELSE log((j.p_joint / NULLIF(i.p_input * o.p_output, 0))::numeric)
               END AS lift
        FROM joint_probs j
        JOIN input_probs  i ON i."Input_Type"  = j."Input_Type"
        JOIN output_probs o ON o."Output_Type" = j."Output_Type"
        WHERE j."Input_Type" IS NOT NULL AND j."Output_Type" IS NOT NULL
    )
    SELECT input_type,
           output_type,
           ROUND(lift::numeric, 2) AS lift_score
    FROM lift_scores
    ORDER BY lift DESC
    LIMIT 1;
    """


def _best_month_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , monthly AS (
        SELECT to_char(to_date(sv."Upload_Date", 'YYYY-MM-DD'), 'FMMonth') AS month_name,
               EXTRACT(MONTH FROM to_date(sv."Upload_Date", 'YYYY-MM-DD'))  AS m_num,
               COUNT(DISTINCT sv."Video_ID") AS uploads
        FROM scoped_videos sv
        WHERE sv."Upload_Date" IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 2
    ),
    with_lag AS (
        SELECT month_name, uploads,
               LAG(uploads) OVER (ORDER BY m_num) AS prev_uploads
        FROM monthly
    ),
    with_growth AS (
        SELECT month_name, uploads,
               CASE WHEN prev_uploads > 0
                    THEN ROUND(((uploads - prev_uploads)::float8 / prev_uploads * 100)::numeric, 1)
                    ELSE 0
               END AS growth_pct
        FROM with_lag
    )
    SELECT month_name, uploads, growth_pct
    FROM with_growth
    ORDER BY growth_pct DESC
    LIMIT 1;
    """



def _top_channels_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , global_expected AS (
        SELECT (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) AS p_expected
        FROM scoped_assets sa
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
    ),
    channel_user_stats AS (
        SELECT svc."Channel_Name", u."User_Name",
               COUNT(DISTINCT sa."Asset_ID") AS c_assets,
               COUNT(DISTINCT sp."Post_ID")  AS c_posts
        FROM scoped_video_channels svc
        JOIN  scoped_videos sv ON svc."Video_ID" = sv."Video_ID"
        JOIN  users u ON u."User_ID" = sv."User_ID"
        LEFT JOIN scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID"  = sp."Asset_ID"
        GROUP BY svc."Channel_Name", u."User_Name"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    channel_totals AS (
        SELECT "Channel_Name", SUM(c_assets) AS t_assets
        FROM channel_user_stats
        GROUP BY "Channel_Name"
    ),
    ctas_scores AS (
        SELECT cu."Channel_Name" AS channel_name,
               ROUND(
                   (SUM((cu.c_assets::float8 / NULLIF(ct.t_assets, 0)) *
                        ((cu.c_posts::float8 / NULLIF(cu.c_assets, 0)) /
                         NULLIF((SELECT p_expected FROM global_expected), 0))))::numeric * 100,
               0) AS alignment_score
        FROM channel_user_stats cu
        JOIN channel_totals ct ON cu."Channel_Name" = ct."Channel_Name"
        GROUP BY cu."Channel_Name"
        ORDER BY alignment_score DESC
        LIMIT 5
    ),
    top_creator_per_channel AS (
        SELECT DISTINCT ON (cu."Channel_Name")
               cu."Channel_Name", cu."User_Name" AS top_creator
        FROM channel_user_stats cu
        ORDER BY cu."Channel_Name", cu.c_assets DESC
    )
    SELECT cs.channel_name,
           cs.alignment_score,
           tc.top_creator
    FROM ctas_scores cs
    LEFT JOIN top_creator_per_channel tc ON tc."Channel_Name" = cs.channel_name
    ORDER BY cs.alignment_score DESC;
    """


def _rei_scores_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , global_input_conv AS (
        SELECT sv."Input_Type",
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) AS g_rate
        FROM scoped_videos sv
        JOIN  scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY sv."Input_Type"
    ),
    user_input_conv AS (
        SELECT u."User_Name", sv."Input_Type",
               COUNT(DISTINCT sa."Asset_ID") AS c_assets,
               (COUNT(DISTINCT sp."Post_ID")::float8 / NULLIF(COUNT(DISTINCT sa."Asset_ID"), 0)) AS u_rate
        FROM scoped_videos sv
        JOIN  users u ON u."User_ID" = sv."User_ID"
        JOIN  scoped_assets sa ON sv."Video_ID" = sa."Video_ID"
        LEFT JOIN scoped_posts sp ON sa."Asset_ID" = sp."Asset_ID"
        WHERE sv."Input_Type" IS NOT NULL
        GROUP BY u."User_Name", sv."Input_Type"
        HAVING COUNT(DISTINCT sa."Asset_ID") > 0
    ),
    user_totals AS (
        SELECT "User_Name", SUM(c_assets) AS t_assets
        FROM user_input_conv
        GROUP BY "User_Name"
    ),
    user_rei AS (
        SELECT uic."User_Name" AS user_name,
               ROUND(
                   SUM((uic.c_assets::float8 / NULLIF(ut.t_assets, 0)) *
                       (uic.u_rate / NULLIF(gic.g_rate, 0)))::numeric,
               2) AS rei_score
        FROM user_input_conv uic
        JOIN user_totals ut      ON uic."User_Name"  = ut."User_Name"
        JOIN global_input_conv gic ON gic."Input_Type" = uic."Input_Type"
        GROUP BY uic."User_Name"
        ORDER BY rei_score DESC
        LIMIT 20
    )
    SELECT user_name, rei_score FROM user_rei;
    """


def _monthly_timeline_query(access_filter: dict) -> str:
    ctes = get_scoped_advanced_ctes(access_filter)
    return f"""{ctes}
    , uploaded_m AS (
        SELECT EXTRACT(MONTH FROM to_date(sv."Upload_Date",  'YYYY-MM-DD'))::int AS m,
               to_char(to_date(sv."Upload_Date",  'YYYY-MM-DD'), 'Mon') AS lbl,
               COUNT(DISTINCT sv."Video_ID") AS cnt
        FROM scoped_videos sv WHERE sv."Upload_Date"  IS NOT NULL GROUP BY 1, 2
    ),
    created_m AS (
        SELECT EXTRACT(MONTH FROM to_date(sa."Create_Date",  'YYYY-MM-DD'))::int AS m,
               to_char(to_date(sa."Create_Date",  'YYYY-MM-DD'), 'Mon') AS lbl,
               COUNT(DISTINCT sa."Asset_ID") AS cnt
        FROM scoped_assets sa WHERE sa."Create_Date"  IS NOT NULL GROUP BY 1, 2
    ),
    published_m AS (
        SELECT EXTRACT(MONTH FROM to_date(sp."Publish_Date", 'YYYY-MM-DD'))::int AS m,
               to_char(to_date(sp."Publish_Date", 'YYYY-MM-DD'), 'Mon') AS lbl,
               COUNT(DISTINCT sp."Post_ID") AS cnt
        FROM scoped_posts sp WHERE sp."Publish_Date" IS NOT NULL GROUP BY 1, 2
    ),
    all_months AS (
        SELECT m, lbl FROM uploaded_m
        UNION SELECT m, lbl FROM created_m
        UNION SELECT m, lbl FROM published_m
    )
    SELECT am.lbl                        AS label,
           COALESCE(u.cnt, 0)::int       AS uploaded,
           COALESCE(c.cnt, 0)::int       AS created,
           COALESCE(p.cnt, 0)::int       AS published
    FROM all_months am
    LEFT JOIN uploaded_m  u ON u.m = am.m
    LEFT JOIN created_m   c ON c.m = am.m
    LEFT JOIN published_m p ON p.m = am.m
    ORDER BY am.m;
    """


def _user_share_query(user_id: int) -> tuple[str, list]:
    sql = """
    WITH all_user_counts AS (
        SELECT rv."User_ID",
               COUNT(DISTINCT rv."Video_ID")::float8 AS uploads
        FROM raw_videos rv
        GROUP BY rv."User_ID"
    ),
    stats AS (
        SELECT
            COALESCE(SUM(uploads), 0)                                               AS total_uploads,
            COALESCE(MAX(CASE WHEN "User_ID" = $1 THEN uploads ELSE 0 END), 0)      AS my_uploads,
            COUNT(*)                                                                 AS total_users,
            SUM(CASE
                    WHEN uploads >= COALESCE(
                        (SELECT uploads FROM all_user_counts WHERE "User_ID" = $1), 0)
                    THEN 1 ELSE 0
                END)                                                                AS users_at_or_above
        FROM all_user_counts
    )
    SELECT
        my_uploads,
        total_uploads,
        ROUND((my_uploads / NULLIF(total_uploads, 0) * 100)::numeric, 1)            AS share_pct,
        ROUND((users_at_or_above::float8 / NULLIF(total_users, 0) * 100)::numeric, 1) AS top_pct
    FROM stats;
    """
    return sql, [user_id]


# ── endpoint ──────────────────────────────────────────────────────────────────

@router.get("", include_in_schema=False)
@router.get("/")
async def get_wrapped(auth: AuthContext = Depends(require_auth)):
    """Aggregated KPI data for the Year Wrapped feature."""
    try:
        access_filter = build_access_filter(auth, 1, "rv")
        params = access_filter["params"]

        # Run all shared queries
        kpi_res       = query(get_kpi_query(access_filter), params)
        month_res     = query(_best_month_query(access_filter), params)
        entropy_res   = query(_overall_entropy_query(access_filter), params)
        platform_res  = query(_platform_dist_query(access_filter), params)
        lift_res      = query(_best_lift_pair_query(access_filter), params)
        timeline_res  = query(_monthly_timeline_query(access_filter), params)

        kpis         = kpi_res.rows[0]      if kpi_res.rows      else {}
        month_row    = month_res.rows[0]    if month_res.rows    else {}
        entropy_row  = entropy_res.rows[0]  if entropy_res.rows  else {}
        platform_row = platform_res.rows[0] if platform_res.rows else {}
        lift_row     = lift_res.rows[0]     if lift_res.rows     else {}
        monthly_timeline = [
            {"label": r["label"], "uploaded": int(r["uploaded"]), "created": int(r["created"]), "published": int(r["published"])}
            for r in timeline_res.rows
        ]

        platforms = _pj(platform_row.get("platforms", []))

        # Entropy → 0-10 score
        raw_entropy = _sf(entropy_row.get("combined_entropy", 0))
        MAX_ENTROPY = 3.5
        entropy_score = round(min(raw_entropy / MAX_ENTROPY * 10, 10.0), 1)

        if entropy_score >= 8.0:
            personality = "Omnichannel Explorer"
        elif entropy_score >= 6.0:
            personality = "Platform Specialist"
        elif entropy_score >= 4.0:
            personality = "Channel Focused"
        else:
            personality = "Platform Pioneer"

        result = {
            "role_type": "client" if auth.role in ("website_admin", "client_admin") else "user",
            "username": auth.username,
            # Pipeline counts
            "uploaded_count":         int(_sf(kpis.get("uploaded_count", 0))),
            "created_count":          int(_sf(kpis.get("created_count", 0))),
            "published_count":        int(_sf(kpis.get("published_count", 0))),
            "processing_efficiency":  round(_sf(kpis.get("processing_efficiency", 0)), 1),
            "publish_conversion_rate": round(_sf(kpis.get("publish_conversion_rate", 0)), 1),
            "cdas_score":             round(_sf(kpis.get("cdas", 0)) * 100, 1),
            # Momentum
            "best_month":     str(month_row.get("month_name") or "").strip() or "—",
            "best_month_pct": _sf(month_row.get("growth_pct", 0)),
            # Content DNA
            "entropy_score": entropy_score,
            "personality":   personality,
            "platforms":     platforms,
            # Funnel
            "best_lift_input":  str(lift_row.get("input_type")  or "—"),
            "best_lift_output": str(lift_row.get("output_type") or "—"),
            "best_lift_score":  _sf(lift_row.get("lift_score", 0)),
            # Timeline
            "monthly_timeline": monthly_timeline,
        }

        # ── client-only ───────────────────────────────────────────────────────
        if auth.role in ("website_admin", "client_admin"):
            ch_res   = query(_top_channels_query(access_filter), params)
            rei_res  = query(_rei_scores_query(access_filter), params)

            result["top_channels"] = [
                {
                    "name":        str(r.get("channel_name") or ""),
                    "score":       int(_sf(r.get("alignment_score", 0))),
                    "top_creator": str(r.get("top_creator") or ""),
                }
                for r in ch_res.rows
            ]
            result["top_users"] = [
                {
                    "name":  str(r.get("user_name") or ""),
                    "score": round(_sf(r.get("rei_score", 0)), 2),
                }
                for r in rei_res.rows[:5]
            ]

        # ── user-only ─────────────────────────────────────────────────────────
        elif auth.role == "user" and auth.user_id:
            rei_res  = query(_rei_scores_query(access_filter), params)
            my_rei   = rei_res.rows[0] if rei_res.rows else {}
            result["rei_score"] = round(_sf(my_rei.get("rei_score", 0)), 2)

            share_sql, share_params = _user_share_query(auth.user_id)
            share_res = query(share_sql, share_params)
            share_row = share_res.rows[0] if share_res.rows else {}
            result["my_uploads"]    = int(_sf(share_row.get("my_uploads", 0)))
            result["total_uploads"] = int(_sf(share_row.get("total_uploads", 0)))
            result["share_pct"]     = _sf(share_row.get("share_pct", 0))
            result["top_pct"]       = _sf(share_row.get("top_pct", 0))

        return result

    except Exception as error:
        logger.error("Wrapped endpoint error: %s", error, exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(error)})
