from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter, build_funnel_filter
from backend.queries.funnel_queries import (
    get_absolute_waste_query,
    get_breakdown_query,
    get_channel_efficiency_query,
    get_client_outcome_platform_sankey_query,
    get_filter_options_channels_query,
    get_filter_options_clients_query,
    get_filter_options_input_types_query,
    get_filter_options_languages_query,
    get_filter_options_teams_query,
    get_filter_options_users_query,
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


def _collect_filters(
    client: str | None,
    input_type: str | None,
    language: str | None,
    channel: str | None,
    user: str | None,
    team: str | None,
) -> dict[str, str]:
    """Build a {dimension: value} dict from named query params, skipping empties."""
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
    return filters


@router.get("/filter-options")
def get_filter_options(auth: AuthContext = Depends(require_auth)):
    """Return distinct values for each filter dimension so frontend dropdowns are dynamic."""
    try:
        access_filter = build_access_filter(auth, 1, "rv")

        clients_rows = query(get_filter_options_clients_query(access_filter), access_filter["params"]).rows
        input_types_rows = query(get_filter_options_input_types_query(access_filter), access_filter["params"]).rows
        languages_rows = query(get_filter_options_languages_query(access_filter), access_filter["params"]).rows
        channels_rows = query(get_filter_options_channels_query(access_filter), access_filter["params"]).rows
        users_rows = query(get_filter_options_users_query(access_filter), access_filter["params"]).rows
        teams_rows = query(get_filter_options_teams_query(access_filter), access_filter["params"]).rows

        return {
            "clients": [r["value"] for r in clients_rows if r.get("value")],
            "input_types": [r["value"] for r in input_types_rows if r.get("value")],
            "languages": [r["value"] for r in languages_rows if r.get("value")],
            "channels": [r["value"] for r in channels_rows if r.get("value")],
            "users": [r["value"] for r in users_rows if r.get("value")],
            "teams": [r["value"] for r in teams_rows if r.get("value")],
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


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
):
    breakdown_dimension = breakdown if breakdown in {"channel", "input_type", "language", "output_type", "client", "user", "team"} else "channel"
    filters = _collect_filters(client, input_type, language, channel, user, team)
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
                    "client_name": row.get("client_name"),
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
        return JSONResponse(status_code=500, content={"error": str(error)})


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
):
    if auth.role == "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Video details are not available for this role")

    try:
        filters = _collect_filters(client, input_type, language, channel, user, team)
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
        return JSONResponse(status_code=500, content={"error": str(error)})
