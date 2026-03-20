import logging
import threading
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import pandas as pd
import numpy as np

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_funnel_filter
from backend.queries.funnel_queries import (
    get_absolute_waste_query,
    get_breakdown_query,
    get_channel_efficiency_query,
    get_client_outcome_platform_sankey_query,
    get_heatmap_query,
    get_journey_query,
    get_mix_query,
    get_output_type_survival_query,
    get_pipeline_strip_query,
    get_publish_by_client_query,
    get_publish_lag_distribution_query,
    get_kpis_query,
    get_stage_counts_query,
    get_team_efficiency_query,
    get_team_absolute_waste_query,
    get_team_volume_yield_query,
    get_video_assets_query,
    get_video_header_query,
)


router = APIRouter()
logger = logging.getLogger(__name__)


class PredictorTrainingError(Exception):
    pass


@dataclass
class _PredictorArtifacts:
    rf_model: Any
    feature_columns: list[str]
    training_rows: int
    train_rows: int


_PREDICTOR_ARTIFACTS: _PredictorArtifacts | None = None
_PREDICTOR_LOCK = threading.Lock()


def _load_predictor_training_dataframe() -> pd.DataFrame:
    training_rows = query(
        '''
        SELECT
          COALESCE(NULLIF(BTRIM(ch."Client_Name"), ''), NULLIF(BTRIM(u."Client_Name"), ''), 'Unknown') AS "Client_Name",
          COALESCE(NULLIF(BTRIM(rvc."Channel_Name"), ''), 'Unknown') AS "Assigned_Channel",
          COALESCE(NULLIF(BTRIM(rv."Input_Type"), ''), 'Unknown') AS "Input_Type",
          COALESCE(NULLIF(BTRIM(rv."Language"), ''), 'Unknown') AS "Language",
          rv."Uploaded_Duration"::float8 AS "Uploaded_Duration",
          COALESCE(NULLIF(BTRIM(ca."Output_Type"), ''), 'Unknown') AS "Output_Type",
          ca."Created_Duration"::float8 AS "Created_Duration",
          to_date(rv."Upload_Date", 'YYYY-MM-DD') AS "Upload_Date",
          to_date(ca."Create_Date", 'YYYY-MM-DD') AS "Create_Date",
          to_date(pp."Publish_Date", 'YYYY-MM-DD') AS "Publish_Date",
          pp."Post_ID" AS "Post_ID",
          pd."Published_URL" AS "Published_URL"
        FROM raw_videos rv
        LEFT JOIN users u ON u."User_ID" = rv."User_ID"
        LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
        LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
        LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
        LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
        LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID";
        ''',
        [],
    ).rows

    if not training_rows:
        raise PredictorTrainingError("No data available for predictor training")

    df = pd.DataFrame(training_rows)
    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].apply(lambda value: value.strip() if isinstance(value, str) else value)

    df = df.dropna(subset=["Uploaded_Duration", "Created_Duration", "Upload_Date", "Create_Date"]).copy()
    if df.empty:
        raise PredictorTrainingError("Insufficient feature rows for predictor")

    df["Upload_Date"] = pd.to_datetime(df["Upload_Date"], errors="coerce")
    df["Create_Date"] = pd.to_datetime(df["Create_Date"], errors="coerce")
    df["Publish_Date"] = pd.to_datetime(df["Publish_Date"], errors="coerce")
    df = df.dropna(subset=["Upload_Date", "Create_Date"]).copy()
    if df.empty:
        raise PredictorTrainingError("Invalid date rows for predictor")

    return df


def _train_predictor_once() -> _PredictorArtifacts:
    global _PREDICTOR_ARTIFACTS
    if _PREDICTOR_ARTIFACTS is not None:
        return _PREDICTOR_ARTIFACTS

    with _PREDICTOR_LOCK:
        if _PREDICTOR_ARTIFACTS is not None:
            return _PREDICTOR_ARTIFACTS

        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
        except ImportError as import_error:
            raise RuntimeError("scikit-learn is required for predictor endpoint") from import_error

        df = _load_predictor_training_dataframe()

        df["Is_Published"] = df["Published_URL"].notna()
        df["Days_to_Publish"] = (df["Publish_Date"] - df["Create_Date"]).dt.total_seconds() / (24 * 3600)
        df["Upload_to_Create_Days"] = (df["Create_Date"] - df["Upload_Date"]).dt.total_seconds() / (24 * 3600)
        df["Upload_to_Create_Days"] = df["Upload_to_Create_Days"].clip(lower=0).fillna(0)
        df["Publish_Timeframe"] = df.apply(
            lambda row: _categorize_publish_time(bool(row["Is_Published"]), row.get("Days_to_Publish")),
            axis=1,
        )

        drop_cols = [
            "Publish_Timeframe", "Is_Published", "Publish_Date",
            "Days_to_Publish", "Create_Date", "Upload_Date",
            "Published_Platform", "Post_ID", "Published_URL",
        ]
        feature_df = df.drop(columns=[column for column in drop_cols if column in df.columns])
        X = pd.get_dummies(feature_df, drop_first=True)
        y = df["Publish_Timeframe"]

        if X.empty or y.nunique() < 2:
            raise PredictorTrainingError("Not enough class diversity to train predictor")

        X_train, _, y_train, _ = train_test_split(
            X, y, test_size=0.2, random_state=42,
        )

        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=None,
            min_samples_split=2,
            class_weight="balanced",
            random_state=42,
        )
        rf_model.fit(X_train, y_train)

        _PREDICTOR_ARTIFACTS = _PredictorArtifacts(
            rf_model=rf_model,
            feature_columns=list(X_train.columns),
            training_rows=int(len(df)),
            train_rows=int(len(X_train)),
        )
        return _PREDICTOR_ARTIFACTS


def _collect_filters(
    client: str | None,
    input_type: str | None,
    language: str | None,
    channel: str | None,
    user: str | None,
    team: str | None,
    output_type: str | None = None,
) -> dict[str, str]:
    """Build a {dimension: value} dict from named query params, skipping empties."""
    def normalize(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    client = normalize(client)
    input_type = normalize(input_type)
    language = normalize(language)
    channel = normalize(channel)
    user = normalize(user)
    team = normalize(team)
    output_type = normalize(output_type)

    filters: dict[str, str] = {}
    if client:
        filters["client"] = client
    if input_type:
        filters["input_type"] = input_type
    if language:
        filters["language"] = language
    if channel:
        filters["channel"] = channel
    if user:
        filters["user"] = user
    if team:
        filters["team"] = team
    if output_type:
        filters["output_type"] = output_type
    return filters


@router.get("/filter-options")
def get_filter_options(
    auth: AuthContext = Depends(require_auth),
    client: str | None = Query(default=None),
    input_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    user: str | None = Query(default=None),
    team: str | None = Query(default=None),
    output_type: str | None = Query(default=None),
):
    """Return distinct values for each filter dimension so frontend dropdowns are dynamic."""
    try:
        selected = _collect_filters(client, input_type, language, channel, user, team, output_type)
        filter_data = build_funnel_filter(selected, 1, auth)

        scoped_cte = f'''
        WITH scoped_rows AS (
          SELECT DISTINCT
            BTRIM(COALESCE(ch."Client_Name", u."Client_Name")) AS client,
            BTRIM(rv."Input_Type") AS input_type,
            BTRIM(rv."Language") AS language,
            BTRIM(rvc."Channel_Name") AS channel,
            BTRIM(u."User_Name") AS user_name,
            BTRIM(u."Team_Name") AS team_name,
            BTRIM(ca."Output_Type") AS output_type
          FROM raw_videos rv
          LEFT JOIN users u ON u."User_ID" = rv."User_ID"
          LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
          LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
          LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
          {filter_data["join"]}
          {filter_data["where"]}
        )
        '''

        clients_rows = query(
            scoped_cte + "SELECT DISTINCT client AS value FROM scoped_rows WHERE NULLIF(client, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows
        input_types_rows = query(
            scoped_cte + "SELECT DISTINCT input_type AS value FROM scoped_rows WHERE NULLIF(input_type, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows
        languages_rows = query(
            scoped_cte + "SELECT DISTINCT language AS value FROM scoped_rows WHERE NULLIF(language, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows
        channels_rows = query(
            scoped_cte + "SELECT DISTINCT channel AS value FROM scoped_rows WHERE NULLIF(channel, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows
        users_rows = query(
            scoped_cte + "SELECT DISTINCT user_name AS value FROM scoped_rows WHERE NULLIF(user_name, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows
        teams_rows = query(
            scoped_cte + "SELECT DISTINCT team_name AS value FROM scoped_rows WHERE NULLIF(team_name, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows
        output_types_rows = query(
            scoped_cte + "SELECT DISTINCT output_type AS value FROM scoped_rows WHERE NULLIF(output_type, '') IS NOT NULL ORDER BY 1;",
            filter_data["params"],
        ).rows

        return {
            "clients": [r["value"] for r in clients_rows if r.get("value")],
            "input_types": [r["value"] for r in input_types_rows if r.get("value")],
            "languages": [r["value"] for r in languages_rows if r.get("value")],
            "channels": [r["value"] for r in channels_rows if r.get("value")],
            "users": [r["value"] for r in users_rows if r.get("value")],
            "teams": [r["value"] for r in teams_rows if r.get("value")],
            "output_types": [r["value"] for r in output_types_rows if r.get("value")],
        }
    except Exception as error:
        logger.exception("Failed to load funnel filter options", exc_info=error)
        return JSONResponse(status_code=500, content={"error": "Failed to load funnel filter options"})


@router.get("", include_in_schema=False)
@router.get("/")
def get_funnel(
    auth: AuthContext = Depends(require_auth),
    breakdown: str = Query(default="channel"),
    client: str | None = Query(default=None),
    input_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    user: str | None = Query(default=None),
    team: str | None = Query(default=None),
    output_type: str | None = Query(default=None),
):
    breakdown_dimension = breakdown if breakdown in {"channel", "input_type", "language", "output_type", "client", "user", "team"} else "channel"
    filters = _collect_filters(client, input_type, language, channel, user, team, output_type)
    filter_data = build_funnel_filter(filters, 1, auth)
    is_website_admin = auth.role == "website_admin"
    can_inspect_raw_journey = auth.role in {"website_admin", "client_admin"}

    try:
        stage_counts_result = query(get_stage_counts_query(filter_data), filter_data["params"])
        stage_counts = stage_counts_result.rows[0] if stage_counts_result.rows else {}

        pipeline_strip_result = query(get_pipeline_strip_query(filter_data), filter_data["params"])
        pipeline_strip = pipeline_strip_result.rows[0] if pipeline_strip_result.rows else {}

        kpis_result = query(get_kpis_query(filter_data), filter_data["params"])
        kpis = kpis_result.rows[0] if kpis_result.rows else {}

        locked_breakdown_value = filters.get(breakdown_dimension)
        breakdown_params = filter_data["params"]
        if locked_breakdown_value:
            breakdown_params = [*filter_data["params"], locked_breakdown_value]

        breakdown_rows = query(
            get_breakdown_query(filter_data, breakdown_dimension, locked_breakdown_value),
            breakdown_params,
        ).rows
        breakdown_data = [
            {
                **row,
                "conversion": round(float(row.get("conversion") or 0), 2),
            }
            for row in breakdown_rows
        ]

        composition_edges_raw = query(get_client_outcome_platform_sankey_query(filter_data), filter_data["params"]).rows
        composition_links = [
            {
                "from": row["edge_from"],
                "to": row["edge_to"],
                "flow": float(row["flow"]),
                "edgeType": row["edge_type"],
            }
            for row in composition_edges_raw
            if float(row.get("flow") or 0) > 0
        ]
        composition_links.sort(key=lambda item: item["flow"], reverse=True)
        composition_links = composition_links[:120]

        locked_channel_value = filters.get("channel")
        locked_client_value = filters.get("client")

        channel_params = [*filter_data["params"]]
        if locked_channel_value:
            channel_params.append(locked_channel_value)
        if locked_client_value:
            channel_params.append(locked_client_value)

        channel_efficiency = query(
            get_channel_efficiency_query(filter_data, locked_channel_value, locked_client_value),
            channel_params,
        ).rows
        absolute_waste = query(
            get_absolute_waste_query(filter_data, locked_channel_value, locked_client_value),
            channel_params,
        ).rows
        publish_lag_distribution = query(get_publish_lag_distribution_query(filter_data), filter_data["params"]).rows
        team_efficiency = query(get_team_efficiency_query(filter_data), filter_data["params"]).rows
        team_volume_yield = query(get_team_volume_yield_query(filter_data), filter_data["params"]).rows
        team_absolute_waste = query(get_team_absolute_waste_query(filter_data), filter_data["params"]).rows
        output_type_survival = query(get_output_type_survival_query(filter_data), filter_data["params"]).rows
        publish_by_client = query(get_publish_by_client_query(filter_data), filter_data["params"]).rows

        heatmap_rows = query(get_heatmap_query(filter_data), filter_data["params"]).rows
        heatmap_clients = sorted({(row.get("client_name") or "Unknown") for row in heatmap_rows})
        input_types = sorted({(row.get("input_type") or "Unknown") for row in heatmap_rows})
        heatmap_lookup = {}
        heatmap_created_lookup = {}
        heatmap_published_lookup = {}
        for row in heatmap_rows:
            input_type_key = row.get("input_type") or "Unknown"
            client_key = row.get("client_name") or "Unknown"
            key = (input_type_key, client_key)
            conversion_value = row.get("conversion_pct")
            heatmap_lookup[key] = round(float(conversion_value or 0), 2)
            heatmap_created_lookup[key] = int(row.get("assets_created") or 0)
            heatmap_published_lookup[key] = int(row.get("posts_published") or 0)
        input_type_client_heatmap = [
            {
                "input_type": it,
                "clients": [
                    {
                        "client_name": cl,
                        "conversion_pct": heatmap_lookup.get((it, cl), 0),
                        "assets_created": heatmap_created_lookup.get((it, cl), 0),
                        "posts_published": heatmap_published_lookup.get((it, cl), 0),
                    }
                    for cl in heatmap_clients
                ],
            }
            for it in input_types
        ]

        journey_rows = query(get_journey_query(filter_data), filter_data["params"]).rows
        mix_rows = query(get_mix_query(filter_data), filter_data["params"]).rows

        mix_by_video: dict[int, list[str]] = {}
        for row in mix_rows:
            key = int(row["video_id"])
            mix_by_video.setdefault(key, []).append(
                f"{row['output_type']}: {row['published_count']}/{row['created_count']}"
            )

        journey_videos = [
            {
                **row,
                "conversion": round(float(row.get("conversion") or 0), 2),
                "output_mix": (mix_by_video.get(int(row["video_id"])) or []),
            }
            for row in journey_rows
        ]

        return {
            "filters": filters,
            "stageCounts": stage_counts,
            "pipelineStrip": {
                "uploads": int(pipeline_strip.get("uploads") or 0),
                "assets_created": int(pipeline_strip.get("assets_created") or 0),
                "posts_published": int(pipeline_strip.get("posts_published") or 0),
                "platform_posts": int(pipeline_strip.get("platform_posts") or 0),
                "assets_multiplier": round(float(pipeline_strip.get("assets_multiplier") or 0), 2),
                "not_published_pct": round(float(pipeline_strip.get("not_published_pct") or 0), 1),
                "platform_multiplier": round(float(pipeline_strip.get("platform_multiplier") or 0), 2),
            },
            "kpis": {
                "publish_conversion_pct": round(float(kpis.get("publish_conversion_pct") or 0), 2),
                "avg_assets_per_upload": round(float(kpis.get("avg_assets_per_upload") or 0), 2),
                "upload_failure_rate": round(float(kpis.get("upload_failure_rate") or 0), 1),
                "waste_index_seconds": round(float(kpis.get("waste_index_seconds") or 0), 1),
                "avg_lag_days": round(float(kpis.get("avg_lag_days") or 0), 2),
            },
            "sankeyLinks": [
                {
                    "from": "Uploaded",
                    "to": "Processed",
                    "flow": float(stage_counts.get("processed_count") or 0),
                },
                {
                    "from": "Processed",
                    "to": "Created",
                    "flow": float(stage_counts.get("created_count") or 0),
                },
                {
                    "from": "Created",
                    "to": "Published",
                    "flow": float(stage_counts.get("published_count") or 0),
                },
            ],
            "compositionLinks": composition_links,
            "breakdownDimension": breakdown_dimension,
            "breakdown": breakdown_data,
            "channelEfficiency": [
                {
                    "channel_name": row.get("channel_name"),
                    "client_name": row.get("client_name") if is_website_admin else None,
                    "videos_assigned": int(row.get("videos_assigned") or 0),
                    "yield_pct": float(row.get("yield_pct") or 0),
                }
                for row in channel_efficiency
            ],
            "absoluteWasteTopChannels": [
                {
                    "channel_name": row.get("channel_name"),
                    "client_name": row.get("client_name") if is_website_admin else None,
                    "videos_assigned": int(row.get("videos_assigned") or 0),
                    "yield_pct": float(row.get("yield_pct") or 0),
                    "waste_slots": int(row.get("waste_slots") or 0),
                }
                for row in absolute_waste
            ],
            "publishLagDistribution": [
                {
                    "lag_bucket": row.get("lag_bucket"),
                    "post_count": int(row.get("post_count") or 0),
                }
                for row in publish_lag_distribution
            ],
            "teamEfficiency": [
                {
                    "team_name": row.get("team_name") or "Unknown",
                    "upload_to_asset_ratio": float(row.get("upload_to_asset_ratio") or 0),
                    "asset_to_publish_ratio_x100": float(row.get("asset_to_publish_ratio_x100") or 0),
                }
                for row in team_efficiency
            ] if can_inspect_raw_journey else [],
            "teamVolumeYield": [
                {
                    "team_name": row.get("team_name") or "Unknown",
                    "videos_assigned": int(row.get("videos_assigned") or 0),
                    "yield_pct": float(row.get("yield_pct") or 0),
                }
                for row in team_volume_yield
            ] if can_inspect_raw_journey else [],
            "absoluteWasteTopTeams": [
                {
                    "team_name": row.get("team_name") or "Unknown",
                    "videos_assigned": int(row.get("videos_assigned") or 0),
                    "yield_pct": float(row.get("yield_pct") or 0),
                    "waste_slots": int(row.get("waste_slots") or 0),
                }
                for row in team_absolute_waste
            ] if can_inspect_raw_journey else [],
            "heatmapClients": heatmap_clients if is_website_admin else [],
            "inputTypeClientHeatmap": input_type_client_heatmap if is_website_admin else [],
            "outputTypeSurvival": [
                {
                    "output_type": row.get("output_type") or "Unknown",
                    "total_created": int(row.get("total_created") or 0),
                    "total_published": int(row.get("total_published") or 0),
                    "survival_rate_pct": float(row.get("survival_rate_pct") or 0),
                }
                for row in output_type_survival
            ],
            "publishByClient": [
                {
                    "client_name": row.get("client_name") or "Unknown",
                    "assets_created": int(row.get("assets_created") or 0),
                    "posts_published": int(row.get("posts_published") or 0),
                    "conversion_pct": float(row.get("conversion_pct") or 0),
                }
                for row in publish_by_client
            ] if is_website_admin else [],
            "journeyVideos": journey_videos if can_inspect_raw_journey else [],
        }
    except Exception as error:
        logger.exception("Failed to load funnel data", exc_info=error)
        return JSONResponse(status_code=500, content={"error": "Failed to load funnel data"})


@router.get("/video/{video_id}")
def get_video_details(
    video_id: int = Path(...),
    auth: AuthContext = Depends(require_auth),
    client: str | None = Query(default=None),
    input_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    user: str | None = Query(default=None),
    team: str | None = Query(default=None),
    output_type: str | None = Query(default=None),
):
    if auth.role == "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Video details are not available for this role")

    try:
        filters = _collect_filters(client, input_type, language, channel, user, team, output_type)
        filter_data = build_funnel_filter(filters, 2, auth)
        params = [video_id, *filter_data["params"]]

        header_result = query(get_video_header_query(filter_data), params)
        if header_result.row_count == 0:
            return JSONResponse(status_code=404, content={"error": "Video not found"})

        assets_result = query(get_video_assets_query(filter_data), params)

        return {
            "video": header_result.rows[0],
            "assets": assets_result.rows,
        }
    except Exception as error:
        logger.exception("Failed to load funnel video details", exc_info=error)
        return JSONResponse(status_code=500, content={"error": "Failed to load funnel video details"})


class PredictorRequest(BaseModel):
    client: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    input_type: str = Field(min_length=1)
    language: str = Field(min_length=1)
    output_type: str = Field(min_length=1)
    uploaded_duration: float = Field(gt=0)
    created_duration: float = Field(gt=0)
    upload_to_create_days: float = Field(ge=0)


def _categorize_publish_time(is_published: bool, days_to_publish: float | None) -> str:
    if not is_published:
        return "0_Never"

    days = float(days_to_publish or 0)
    if days <= 1.0:
        return "1_Within_1_Day"
    if days <= 2.0:
        return "2_Within_2_Days"
    if days <= 3.0:
        return "3_Within_3_Days"
    return "4_More_than_3_Days"


def _prediction_label(predicted_class: str) -> str:
    labels = {
        "0_Never": "Likely Not Published",
        "1_Within_1_Day": "Likely Published within 1 day",
        "2_Within_2_Days": "Likely Published within 2 days",
        "3_Within_3_Days": "Likely Published within 3 days",
        "4_More_than_3_Days": "Likely Published after 3 days",
    }
    return labels.get(predicted_class, "Unknown")


@router.post("/predictor/predict")
def predict_publish_likelihood(payload: PredictorRequest, _auth: AuthContext = Depends(require_auth)):
    try:
        artifacts = _train_predictor_once()

        sample_df = pd.DataFrame(
            {
                "Client_Name": [payload.client],
                "Assigned_Channel": [payload.channel],
                "Input_Type": [payload.input_type],
                "Language": [payload.language],
                "Uploaded_Duration": [payload.uploaded_duration],
                "Output_Type": [payload.output_type],
                "Created_Duration": [payload.created_duration],
                "Upload_to_Create_Days": [payload.upload_to_create_days],
            }
        )

        sample_X = pd.get_dummies(sample_df).reindex(columns=artifacts.feature_columns, fill_value=0)

        rf_model = artifacts.rf_model
        final_pred = str(rf_model.predict(sample_X)[0])

        def get_publish_confidence(model: Any, feature_vector: pd.DataFrame, n_days: int) -> float:
            class_probs = model.predict_proba(feature_vector)[0]
            classes = model.classes_

            confidence = 0.0
            if n_days == 0:
                idx = np.where(classes == "0_Never")[0]
                if len(idx) > 0:
                    confidence = class_probs[idx[0]]
                    return round(confidence * 100, 2)
                return 0.0

            if n_days >= 1:
                idx = np.where(classes == "1_Within_1_Day")[0]
                if len(idx) > 0:
                    confidence += class_probs[idx[0]]
            if n_days >= 2:
                idx = np.where(classes == "2_Within_2_Days")[0]
                if len(idx) > 0:
                    confidence += class_probs[idx[0]]
            if n_days >= 3:
                idx = np.where(classes == "3_Within_3_Days")[0]
                if len(idx) > 0:
                    confidence += class_probs[idx[0]]
            if n_days > 3:
                idx = np.where(classes == "4_More_than_3_Days")[0]
                if len(idx) > 0:
                    confidence += class_probs[idx[0]]

            return round(confidence * 100, 2)

        confidence_by_n = {
            "0": get_publish_confidence(rf_model, sample_X, 0),
            "1": get_publish_confidence(rf_model, sample_X, 1),
            "2": get_publish_confidence(rf_model, sample_X, 2),
            "3": get_publish_confidence(rf_model, sample_X, 3),
            "4+": get_publish_confidence(rf_model, sample_X, 4),
        }

        if final_pred == "0_Never":
            confidence_pct = confidence_by_n["0"]
        elif final_pred == "1_Within_1_Day":
            confidence_pct = confidence_by_n["1"]
        elif final_pred == "2_Within_2_Days":
            confidence_pct = confidence_by_n["2"]
        elif final_pred == "3_Within_3_Days":
            confidence_pct = confidence_by_n["3"]
        else:
            confidence_pct = confidence_by_n["4+"]

        return {
            "prediction": _prediction_label(final_pred),
            "predicted_class": final_pred,
            "probability_pct": confidence_pct,
            "confidence_pct": confidence_pct,
            "publish_timeframe_bucket": final_pred,
            "confidence_by_n": confidence_by_n,
            "hyperparams": {
                "n_estimators": 100,
                "max_depth": "None",
                "min_samples_split": 2,
                "class_weight": "balanced",
            },
            "support": {
                "training_rows": artifacts.training_rows,
                "train_rows": artifacts.train_rows,
            },
        }
    except PredictorTrainingError as error:
        return JSONResponse(status_code=422, content={"error": str(error)})
    except Exception as error:
        logger.exception("Failed to compute publish predictor", exc_info=error)
        return JSONResponse(status_code=500, content={"error": "Failed to compute predictor"})