"""
usage_trends.py — Usage trends route.
Port of backend_legacy/routes/usageTrends.js.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..dependencies import AuthUser, get_db, require_auth
from ..queries.analytics_shared import (
    VALID_METRICS,
    build_access_filter,
    get_metric_query,
    get_trend_insights,
)

router = APIRouter(prefix="/api/usage-trends", tags=["usage-trends"])

VALID_GRANULARITIES = {"day", "week", "month", "quarter"}


@router.get("/")
def usage_trends(
    granularity: str = Query("month"),
    metric: str = Query("uploaded_count"),
    auth: AuthUser = Depends(require_auth),
    conn: Connection = Depends(get_db),
):
    if granularity not in VALID_GRANULARITIES:
        granularity = "month"
    if metric not in VALID_METRICS:
        metric = "uploaded_count"

    af = build_access_filter(auth, "rv")
    sql = get_metric_query(metric, af)
    params = {"granularity": granularity, **af.params}

    rows = conn.execute(text(sql), params).mappings().all()
    points = [{"period": str(r["period"]), "value": float(r.get("value", 0))} for r in rows]

    latest = points[-1] if points else None
    previous = points[-2] if len(points) >= 2 else None
    delta_pct = None
    if latest and previous and previous["value"] != 0:
        delta_pct = round(((latest["value"] - previous["value"]) / previous["value"]) * 100, 2)

    return {
        "metric": metric,
        "granularity": granularity,
        "series": points,
        "summary": {
            "latestValue": round(latest["value"], 2) if latest else 0,
            "latestPeriod": latest["period"] if latest else None,
            "deltaVsPreviousPct": delta_pct,
        },
        "anomalies": get_trend_insights(points),
    }
