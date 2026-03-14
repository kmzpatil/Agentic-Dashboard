"""
overview.py — Overview KPIs route.
Port of backend_legacy/routes/overview.js.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..dependencies import AuthUser, get_db, require_auth
from ..queries.analytics_shared import build_access_filter
from ..queries.overview import (
    alerts_query,
    channel_top_performer_query,
    input_top_performer_query,
    kpi_query,
    language_top_performer_query,
    output_top_performer_query,
    user_top_performer_query,
)

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("/")
def overview(
    auth: AuthUser = Depends(require_auth),
    conn: Connection = Depends(get_db),
):
    af = build_access_filter(auth, "rv")
    p = af.params

    kpi_row = conn.execute(text(kpi_query(af)), p).mappings().first()
    chan_row = conn.execute(text(channel_top_performer_query(af)), p).mappings().first()
    user_row = conn.execute(text(user_top_performer_query(af)), p).mappings().first()
    input_row = conn.execute(text(input_top_performer_query(af)), p).mappings().first()
    output_row = conn.execute(text(output_top_performer_query(af)), p).mappings().first()
    lang_row = conn.execute(text(language_top_performer_query(af)), p).mappings().first()
    alert_rows = conn.execute(text(alerts_query(af)), p).mappings().all()

    kpis = dict(kpi_row) if kpi_row else {}

    top_performers = []
    for label, row in [
        ("Channel", chan_row), ("User", user_row), ("Input Type", input_row),
        ("Output Type", output_row), ("Language", lang_row),
    ]:
        if row and row.get("label"):
            top_performers.append({"dimension": label, **dict(row)})

    alerts = []
    for r in alert_rows:
        conv = float(r.get("conversion", 0))
        alerts.append({
            "title": f"{r['channel_name']}: {conv:.2f}% conversion",
            "subtitle": f"{r['created_count']} created, {r['published_count']} published",
            "severity": "critical" if conv < 0.5 else "warning",
        })

    return {"kpis": kpis, "topPerformers": top_performers, "alerts": alerts}
