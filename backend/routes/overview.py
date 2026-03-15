from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter
from backend.queries.overview_queries import (
    get_alerts_query,
    get_channel_top_performer_query,
    get_input_top_performer_query,
    get_kpi_query,
    get_language_top_performer_query,
    get_output_top_performer_query,
    get_user_top_performer_query,
)


router = APIRouter()


@router.get("/")
def get_overview(auth: AuthContext = Depends(require_auth)):
    try:
        access_filter = build_access_filter(auth, 1, "rv")
        params = access_filter["params"]

        kpi_result = query(get_kpi_query(access_filter), params)
        channel_result = query(get_channel_top_performer_query(access_filter), params)
        user_result = query(get_user_top_performer_query(access_filter), params)
        input_result = query(get_input_top_performer_query(access_filter), params)
        output_result = query(get_output_top_performer_query(access_filter), params)
        lang_result = query(get_language_top_performer_query(access_filter), params)
        alert_result = query(get_alerts_query(access_filter), params)

        kpis = kpi_result.rows[0] if kpi_result.rows else {}

        top_performers = [
            {"dimension": "Channel", **(channel_result.rows[0] if channel_result.rows else {})},
            {"dimension": "User", **(user_result.rows[0] if user_result.rows else {})},
            {"dimension": "Input Type", **(input_result.rows[0] if input_result.rows else {})},
            {"dimension": "Output Type", **(output_result.rows[0] if output_result.rows else {})},
            {"dimension": "Language", **(lang_result.rows[0] if lang_result.rows else {})},
        ]
        top_performers = [item for item in top_performers if item.get("label")]

        alerts = [
            {
                "title": f"{row['channel_name']}: {float(row['conversion']):.2f}% conversion",
                "subtitle": f"{row['created_count']} created, {row['published_count']} published",
                "severity": "critical" if float(row["conversion"]) < 0.5 else "warning",
            }
            for row in alert_result.rows
        ]

        return {"kpis": kpis, "topPerformers": top_performers, "alerts": alerts}
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
