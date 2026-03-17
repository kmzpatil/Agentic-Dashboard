from __future__ import annotations

from backend.db.pool import query
from backend.middleware.auth import AuthContext
from backend.queries.analytics_shared import build_access_filter
from backend.queries.overview_queries import (
    get_alerts_query,
    get_channel_top_performer_query,
    get_input_top_performer_query,
    get_kpi_query,
    get_language_top_performer_query,
    get_output_top_performer_query,
    get_user_top_performer_query,
    get_output_type_stats_query,
    get_kpi_sparklines_query
)


def get_overview_snapshot(auth: AuthContext) -> dict:
    access_filter = build_access_filter(auth, 1, "rv")
    params = access_filter["params"]

    kpi_result = query(get_kpi_query(access_filter), params)
    channel_result = query(get_channel_top_performer_query(access_filter), params)
    user_result = query(get_user_top_performer_query(access_filter), params)
    input_result = query(get_input_top_performer_query(access_filter), params)
    output_result = query(get_output_top_performer_query(access_filter), params)
    language_result = query(get_language_top_performer_query(access_filter), params)
    alert_result = query(get_alerts_query(access_filter), params)
    output_types_result = query(get_output_type_stats_query(access_filter), params)
    sparkline_result = query(get_kpi_sparklines_query(access_filter), params)

    kpis = kpi_result.rows[0] if kpi_result.rows else {}
    
    # Format sparkline data
    sparklines = {
        "uploaded": [float(r["uploaded"]) for r in sparkline_result.rows],
        "processed": [float(r["processed"]) for r in sparkline_result.rows],
        "created": [float(r["created"]) for r in sparkline_result.rows],
        "published": [float(r["published"]) for r in sparkline_result.rows]
    }

    top_performers = [
        {"dimension": "Channel", **(channel_result.rows[0] if channel_result.rows else {})},
        {"dimension": "User", **(user_result.rows[0] if user_result.rows else {})},
        {"dimension": "Input Type", **(input_result.rows[0] if input_result.rows else {})},
        {"dimension": "Output Type", **(output_result.rows[0] if output_result.rows else {})},
        {"dimension": "Language", **(language_result.rows[0] if language_result.rows else {})},
    ]
    top_performers = [item for item in top_performers if item.get("label")]

    alerts = []
    for row in alert_result.rows:
        conversion = round(float(row.get("conversion") or 0), 2)
        severity = "critical" if conversion < 50 else "warning"
        alerts.append(
            {
                "title": f"{row['channel_name']}: {conversion:.2f}% conversion",
                "subtitle": f"{row['created_count']} created, {row['published_count']} published",
                "severity": severity,
                "dimension": "channel",
                "value": row["channel_name"],
            }
        )

    return {
        "kpis": kpis,
        "sparklines": sparklines,
        "pipeline": [
            {"id": "uploaded", "label": "Uploaded", "count": kpis.get("uploaded_count", 0), "duration": kpis.get("uploaded_duration", 0)},
            {"id": "processed", "label": "Processed", "count": kpis.get("processed_count", 0), "duration": kpis.get("created_duration", 0)},
            {"id": "created", "label": "Created", "count": kpis.get("created_count", 0), "duration": kpis.get("created_duration", 0)},
            {"id": "published", "label": "Published", "count": kpis.get("published_count", 0), "duration": kpis.get("published_duration", 0)},
        ],
        "outputStats": output_types_result.rows if output_types_result.rows else [],
        "topPerformers": top_performers,
        "alerts": alerts,
    }
