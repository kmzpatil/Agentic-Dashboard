import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter
from backend.queries.advanced_kpi_queries import (
    get_publish_conversion_details_query,
    get_roi_matrix_query,
    get_waste_index_details_query,
    get_interaction_lift_query,
    get_cross_dimension_entropy_query,
    get_cdas_query,
    get_month_by_month_use_rate_query,
    get_generic_trend_query
)

router = APIRouter()

@router.get("/{kpi_id}")
async def get_advanced_kpi_details(kpi_id: str, auth: AuthContext = Depends(require_auth)):
    try:
        access_filter = build_access_filter(auth, 1, "rv")
        params = access_filter["params"]

        if kpi_id == "publish_conversion" or kpi_id == "processing_efficiency" or kpi_id == "upload_failure_rate":
            sql = get_publish_conversion_details_query(access_filter)
        elif kpi_id == "roi":
            sql = get_roi_matrix_query(access_filter)
        elif kpi_id == "waste_index":
            sql = get_waste_index_details_query(access_filter)
        elif kpi_id in ("interaction_lift", "multidimensional_waste"):
            sql = get_interaction_lift_query(access_filter)
        elif kpi_id == "cross_dimension_entropy":
            sql = get_cross_dimension_entropy_query(access_filter)
        elif kpi_id == "cdas":
            sql = get_cdas_query(access_filter)
        elif kpi_id == "month_by_month_use_rate":
            sql = get_month_by_month_use_rate_query(access_filter)
        else:
            sql = get_generic_trend_query(access_filter, kpi_id)

        result = query(sql, params)
        if not result.rows:
            return {}

        data = result.rows[0]
        
        # Parse nested JSON strings returned by Postgres json_agg
        parsed_data = {}
        for key, value in data.items():
            if value is None:
                parsed_data[key] = []
            elif isinstance(value, str):
                try:
                    parsed_data[key] = json.loads(value)
                except Exception:
                    parsed_data[key] = value
            elif isinstance(value, list):
                parsed_data[key] = value
            else:
                parsed_data[key] = value

        # Format arrays specifically for Chart.js mapped from kpiDefinitions.js formats
        formatted_data = {}
        if kpi_id == "roi":
            formatted_data["users"] = [{"x": float(r["x"] or 0), "y": float(r["y"] or 0), "label": r["label"]} for r in parsed_data.get("users", [])]
            formatted_data["channels"] = [{"x": float(r["x"] or 0), "y": float(r["y"] or 0), "label": r["label"]} for r in parsed_data.get("channels", [])]
        elif kpi_id == "waste_index":
            formatted_data["users"] = {"labels": [r["label"] for r in parsed_data.get("users", [])], "data": [float(r["index"] or 0) for r in parsed_data.get("users", [])]}
            formatted_data["channels"] = {"labels": [r["label"] for r in parsed_data.get("channels", [])], "data": [float(r["index"] or 0) for r in parsed_data.get("channels", [])]}
            formatted_data["channelTreemap"] = [{"name": r["name"], "value": float(r["value"] or 0)} for r in parsed_data.get("treemap", [])]
            formatted_data["teamWaste"] = parsed_data.get("teamWaste", {"labels": [], "datasets": []})
        elif kpi_id in ("interaction_lift", "multidimensional_waste"):
            formatted_data["heatmap"] = parsed_data.get("heatmap", [])
        elif kpi_id == "cross_dimension_entropy":
            formatted_data["users"] = {"labels": [r["label"] for r in parsed_data.get("users", [])], "data": [float(r["entropy"] or 0) for r in parsed_data.get("users", [])]}
        elif kpi_id == "cdas":
            formatted_data["inputs"] = {"labels": [r["label"] for r in parsed_data.get("inputs", [])], "data": [float(r["score"] or 0) for r in parsed_data.get("inputs", [])]}
            formatted_data["durations"] = {
                "labels": [r["label"] for r in parsed_data.get("inputs", [])],
                "datasets": [
                    {"label": "Avg Created (s)", "data": [float(r["avg_created"] or 0) for r in parsed_data.get("inputs", [])]},
                    {"label": "Avg Published (s)", "data": [float(r["avg_published"] or 0) for r in parsed_data.get("inputs", [])]}
                ]
            }
        elif kpi_id == "month_by_month_use_rate":
            formatted_data["timeSeries"] = {"labels": [r["label"] for r in parsed_data.get("timeseries", [])], "data": [float(r["rate"] or 0) for r in parsed_data.get("timeseries", [])]}
            formatted_data["channelTreemap"] = [{"name": r["name"], "value": float(r["value"] or 0)} for r in parsed_data.get("channel_treemap", [])]
            formatted_data["userTreemap"] = [{"name": r["name"], "value": float(r["value"] or 0)} for r in parsed_data.get("user_treemap", [])]
        else:
            # publish_conversion structure (default)
            for k in ["users", "channels", "inputs", "outputs"]:
                formatted_data[k] = {"labels": [r["label"] for r in parsed_data.get(k, [])], "data": [float(r.get("rate") or r.get("score") or r.get("index") or 0) for r in parsed_data.get(k, [])]}
            formatted_data["timeSeries"] = {"labels": [r["label"] for r in parsed_data.get("timeseries", [])], "data": [float(r["rate"] or 0) for r in parsed_data.get("timeseries", [])]}

        return formatted_data

    except Exception as error:
        print(f"Error fetching advanced KPI {kpi_id}: {error}")
        return JSONResponse(status_code=500, content={"error": str(error)})
