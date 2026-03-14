"""
funnel.py — Funnel analytics routes.
Port of backend_legacy/routes/funnel.js.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..dependencies import AuthUser, get_db, require_auth
from ..queries.analytics_shared import build_access_filter, build_funnel_filter
from ..queries.funnel import (
    breakdown_query,
    composition_query,
    journey_query,
    mix_query,
    stage_counts_query,
    video_assets_query,
    video_header_query,
)

router = APIRouter(prefix="/api/funnel", tags=["funnel"])

VALID_BREAKDOWNS = {"channel", "input_type", "language", "output_type"}


@router.get("/")
def funnel(
    dimension: str | None = Query(None),
    value: str | None = Query(None),
    breakdown: str = Query("channel"),
    auth: AuthUser = Depends(require_auth),
    conn: Connection = Depends(get_db),
):
    if breakdown not in VALID_BREAKDOWNS:
        breakdown = "channel"

    ff = build_funnel_filter(dimension, value, auth)
    p = ff.params

    stage_row = conn.execute(text(stage_counts_query(ff)), p).mappings().first()
    stage = dict(stage_row) if stage_row else {
        "uploaded_count": 0, "processed_count": 0, "created_count": 0, "published_count": 0,
    }

    bd_rows = conn.execute(text(breakdown_query(ff, breakdown)), p).mappings().all()
    bd = [{**dict(r), "conversion": round(float(r.get("conversion", 0)), 2)} for r in bd_rows]

    comp_rows = conn.execute(text(composition_query(ff)), p).mappings().all()
    comp_links = sorted(
        [r for r in comp_rows if float(r.get("flow", 0)) > 0],
        key=lambda r: float(r["flow"]),
        reverse=True,
    )[:120]
    comp_links = [
        {"from": r["edge_from"], "to": r["edge_to"], "flow": float(r["flow"]), "edgeType": r["edge_type"]}
        for r in comp_links
    ]

    j_rows = conn.execute(text(journey_query(ff)), p).mappings().all()
    m_rows = conn.execute(text(mix_query(ff)), p).mappings().all()

    mix_by_video: dict[int, list[str]] = defaultdict(list)
    for r in m_rows:
        mix_by_video[int(r["video_id"])].append(f"{r['output_type']}: {r['published_count']}/{r['created_count']}")

    journey_videos = []
    for r in j_rows:
        vid = int(r["video_id"])
        journey_videos.append({
            **dict(r),
            "conversion": round(float(r.get("conversion", 0)), 2),
            "output_mix": mix_by_video.get(vid, [])[:4],
        })

    sankey = [
        {"from": "Uploaded",  "to": "Processed", "flow": int(stage["processed_count"])},
        {"from": "Processed", "to": "Created",   "flow": int(stage["created_count"])},
        {"from": "Created",   "to": "Published", "flow": int(stage["published_count"])},
    ]

    return {
        "filter": {"dimension": dimension, "value": value},
        "stageCounts": stage,
        "sankeyLinks": sankey,
        "compositionLinks": comp_links,
        "breakdownDimension": breakdown,
        "breakdown": bd,
        "journeyVideos": journey_videos,
    }


@router.get("/video/{video_id}")
def video_detail(
    video_id: int,
    auth: AuthUser = Depends(require_auth),
    conn: Connection = Depends(get_db),
):
    af = build_access_filter(auth, "rv")
    p = {"video_id": video_id, **af.params}

    header = conn.execute(text(video_header_query(af)), p).mappings().first()
    if not header:
        raise HTTPException(404, "Video not found")

    assets = conn.execute(text(video_assets_query(af)), p).mappings().all()

    return {"video": dict(header), "assets": [dict(a) for a in assets]}
