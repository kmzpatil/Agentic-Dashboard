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
    get_generic_trend_query,
    get_processing_efficiency_query,
    get_creation_rate_query,
    get_upload_failure_rate_query,
    get_multidimensional_waste_query,
    get_publish_dependency_index_query,
    get_point_biserial_query,
    get_ctas_query,
    get_rei_query
)

router = APIRouter()

@router.get("/{kpi_id}")
async def get_advanced_kpi_details(kpi_id: str, auth: AuthContext = Depends(require_auth)):
    try:
        access_filter = build_access_filter(auth, 1, "rv")
        params = access_filter["params"]

        if kpi_id == "publish_conversion":
            sql = get_publish_conversion_details_query(access_filter)
        elif kpi_id == "processing_efficiency":
            sql = get_processing_efficiency_query(access_filter)
        elif kpi_id == "upload_failure_rate":
            sql = get_upload_failure_rate_query(access_filter)
        elif kpi_id == "creation_rate":
            sql = get_creation_rate_query(access_filter)
        elif kpi_id == "multidimensional_waste":
            sql = get_multidimensional_waste_query(access_filter)
        elif kpi_id == "publish_dependency_index":
            sql = get_publish_dependency_index_query(access_filter)
        elif kpi_id == "point_biserial":
            sql = get_point_biserial_query(access_filter)
        elif kpi_id == "ctas":
            sql = get_ctas_query(access_filter)
        elif kpi_id == "rei":
            sql = get_rei_query(access_filter)
        elif kpi_id == "roi":
            sql = get_roi_matrix_query(access_filter)
        elif kpi_id == "waste_index":
            sql = get_waste_index_details_query(access_filter)
        elif kpi_id == "interaction_lift":
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

        formatted_data = {}
        if kpi_id == "roi":
            formatted_data["users"] = [{"x": float(r.get("x") or 0), "y": float(r.get("y") or 0), "label": r.get("label")} for r in parsed_data.get("users", [])]
            formatted_data["channels"] = [{"x": float(r.get("x") or 0), "y": float(r.get("y") or 0), "label": r.get("label")} for r in parsed_data.get("channels", [])]
        elif kpi_id == "waste_index":
            formatted_data["users"] = {"labels": [r["label"] for r in parsed_data.get("users", [])], "data": [float(r.get("index") or 0) for r in parsed_data.get("users", [])]}
            formatted_data["channels"] = {"labels": [r["label"] for r in parsed_data.get("channels", [])], "data": [float(r.get("index") or 0) for r in parsed_data.get("channels", [])]}
            formatted_data["channelTreemap"] = [{"name": r["name"], "value": float(r.get("value") or 0)} for r in parsed_data.get("treemap", [])]
            formatted_data["teamWaste"] = parsed_data.get("teamWaste", {"labels": [], "datasets": []})
        elif kpi_id in ("interaction_lift", "multidimensional_waste"):
            formatted_data["heatmap"] = parsed_data.get("heatmap", [])
        elif kpi_id == "cross_dimension_entropy":
            formatted_data["users"] = {"labels": [r["label"] for r in parsed_data.get("users", [])], "data": [float(r.get("entropy") or 0) for r in parsed_data.get("users", [])]}
            formatted_data["teams"] = {"labels": [r["label"] for r in parsed_data.get("teams", [])], "data": [float(r.get("entropy") or 0) for r in parsed_data.get("teams", [])]}
            formatted_data["userHighestShare"] = {"labels": [r["label"] for r in parsed_data.get("user_shares", [])], "data": [float(r.get("data") or 0) for r in parsed_data.get("user_shares", [])]}
            formatted_data["teamHighestShare"] = {"labels": [r["label"] for r in parsed_data.get("team_shares", [])], "data": [float(r.get("data") or 0) for r in parsed_data.get("team_shares", [])]}
        elif kpi_id == "cdas":
            formatted_data["inputs"] = {"labels": [r["label"] for r in parsed_data.get("inputs", [])], "data": [float(r.get("score") or 0) for r in parsed_data.get("inputs", [])]}
            formatted_data["durations"] = {
                "labels": [r["label"] for r in parsed_data.get("inputs", [])],
                "datasets": [
                    {"label": "Avg Created (s)", "data": [float(r.get("avg_created") or 0) for r in parsed_data.get("inputs", [])]},
                    {"label": "Avg Published (s)", "data": [float(r.get("avg_published") or 0) for r in parsed_data.get("inputs", [])]}
                ]
            }
        elif kpi_id == "month_by_month_use_rate":
            formatted_data["timeSeries"] = {"labels": [r["label"] for r in parsed_data.get("timeseries", [])], "data": [float(r.get("rate") or 0) for r in parsed_data.get("timeseries", [])]}
            formatted_data["channelTreemap"] = [{"name": r["name"], "value": float(r.get("value") or 0)} for r in parsed_data.get("channel_treemap", [])]
            formatted_data["userTreemap"] = [{"name": r["name"], "value": float(r.get("value") or 0)} for r in parsed_data.get("user_treemap", [])]
        elif kpi_id == "publish_dependency_index":
            formatted_data["sectors"] = {"labels": [r["label"] for r in parsed_data.get("sectors", [])], "data": [float(r.get("score") or 0) for r in parsed_data.get("sectors", [])]}
            formatted_data["categories"] = {
                "userId": {"labels": [r["label"] for r in parsed_data.get("users", [])], "data": [float(r.get("rate") or 0) for r in parsed_data.get("users", [])]},
                "inputType": {"labels": [r["label"] for r in parsed_data.get("inputs", [])], "data": [float(r.get("rate") or 0) for r in parsed_data.get("inputs", [])]},
                "outputType": {"labels": [r["label"] for r in parsed_data.get("outputs", [])], "data": [float(r.get("rate") or 0) for r in parsed_data.get("outputs", [])]},
                "language": {"labels": [r["label"] for r in parsed_data.get("languages", [])], "data": [float(r.get("rate") or 0) for r in parsed_data.get("languages", [])]}
            }
        elif kpi_id == "point_biserial":
            formatted_data["correlations"] = {"labels": [r["label"] for r in parsed_data.get("correlations", [])], "data": [float(r.get("score") or 0) for r in parsed_data.get("correlations", [])]}
            formatted_data["createdDurations"] = {
                "labels": [r["label"] for r in parsed_data.get("stats", [])],
                "datasets": [{"label": "Created Duration", "data": [float(r.get("avg_created") or 0) for r in parsed_data.get("stats", [])]}]
            }
            formatted_data["uploadedDurations"] = {
                "labels": [r["label"] for r in parsed_data.get("stats", [])],
                "datasets": [{"label": "Uploaded Duration", "data": [float(r.get("avg_uploaded") or 0) for r in parsed_data.get("stats", [])]}]
            }
        elif kpi_id == "ctas":
            formatted_data["channels"] = {"labels": [r["label"] for r in parsed_data.get("channels", [])], "data": [float(r.get("score") or 0) for r in parsed_data.get("channels", [])]}
            formatted_data["userUploaded"] = {"labels": [r["label"] for r in parsed_data.get("top_users", [])], "data": [float(r.get("c_assets") or 0) for r in parsed_data.get("top_users", [])]}
            formatted_data["userPublished"] = {"labels": [r["label"] for r in parsed_data.get("top_users", [])], "data": [float(r.get("c_posts") or 0) for r in parsed_data.get("top_users", [])]}
        elif kpi_id == "rei":
            formatted_data["users"] = {"labels": [r["label"] for r in parsed_data.get("users", [])], "data": [float(r.get("score") or 0) for r in parsed_data.get("users", [])]}
            formatted_data["doubleBar"] = {
                "labels": [r["label"] for r in parsed_data.get("top_user_inputs", [])],
                "datasets": [
                    {"label": "User Conversion", "data": [float(r.get("user_conv") or 0) for r in parsed_data.get("top_user_inputs", [])]},
                    {"label": "Global Baseline", "data": [float(r.get("global_conv") or 0) for r in parsed_data.get("top_user_inputs", [])]}
                ]
            }
        else:
            for k in ["users", "channels", "inputs", "outputs"]:
                formatted_data[k] = {"labels": [r["label"] for r in parsed_data.get(k, [])], "data": [float(r.get("rate") or r.get("score") or r.get("index") or 0) for r in parsed_data.get(k, [])]}
            formatted_data["timeSeries"] = {"labels": [r["label"] for r in parsed_data.get("timeseries", [])], "data": [float(r.get("rate") or 0) for r in parsed_data.get("timeseries", [])]}

        return formatted_data

    except Exception as error:
        print(f"Error fetching advanced KPI {kpi_id}: {error}")
        return JSONResponse(status_code=500, content={"error": str(error)})
