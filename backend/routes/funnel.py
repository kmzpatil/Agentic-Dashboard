from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import build_access_filter, build_funnel_filter
from backend.queries.funnel_queries import (
    get_breakdown_query,
    get_composition_query,
    get_journey_query,
    get_mix_query,
    get_stage_counts_query,
    get_video_assets_query,
    get_video_header_query,
)


router = APIRouter()


@router.get("", include_in_schema=False)
@router.get("/")
def get_funnel(
    auth: AuthContext = Depends(require_auth),
    dimension: str | None = Query(default=None),
    value: str | None = Query(default=None),
    breakdown: str = Query(default="channel"),
):
    breakdown_dimension = breakdown if breakdown in {"channel", "input_type", "language", "output_type"} else "channel"
    filter_data = build_funnel_filter(dimension, value, 1, auth)

    try:
        stage_counts_result = query(get_stage_counts_query(filter_data), filter_data["params"])
        stage_counts = stage_counts_result.rows[0] if stage_counts_result.rows else {}

        breakdown_rows = query(get_breakdown_query(filter_data, breakdown_dimension), filter_data["params"]).rows
        breakdown_data = [
            {
                **row,
                "conversion": round(float(row.get("conversion") or 0), 2),
            }
            for row in breakdown_rows
        ]

        composition_edges_raw = query(get_composition_query(filter_data), filter_data["params"]).rows
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
                "output_mix": (mix_by_video.get(int(row["video_id"])) or [])[:4],
            }
            for row in journey_rows
        ]

        return {
            "filter": {"dimension": dimension or None, "value": value or None},
            "stageCounts": stage_counts,
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
            "journeyVideos": journey_videos,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@router.get("/video/{video_id}")
def get_video_details(video_id: int = Path(...), auth: AuthContext = Depends(require_auth)):
    try:
        access_filter = build_access_filter(auth, 2, "rv")
        access_params = [video_id, *access_filter["params"]]

        header_result = query(get_video_header_query(access_filter), access_params)
        if header_result.row_count == 0:
            return JSONResponse(status_code=404, content={"error": "Video not found"})

        assets_result = query(get_video_assets_query(access_filter), access_params)

        return {
            "video": header_result.rows[0],
            "assets": assets_result.rows,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
