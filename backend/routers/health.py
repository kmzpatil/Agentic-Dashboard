"""
health.py — Health check route.
Port of backend_legacy/routes/health.js.
"""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..config import settings
from ..dependencies import get_db

router = APIRouter(prefix="/api/health", tags=["health"])

REQUIRED_TABLES = [
    "channels", "clients", "created_assets", "post_distribution",
    "published_posts", "raw_video_channel", "raw_videos", "users",
]


@router.get("/")
def health(conn: Connection = Depends(get_db)):
    response = {"ok": False, "services": {}, "schema": {}}

    try:
        info = conn.execute(text("SELECT current_database() AS db, current_user AS usr")).mappings().first()
        tables_rows = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        ).mappings().all()

        available = [r["tablename"] for r in tables_rows]
        missing = [t for t in REQUIRED_TABLES if t not in available]

        response["services"]["database"] = {
            "ok": len(missing) == 0,
            "database": info["db"] if info else None,
            "user": info["usr"] if info else None,
            "tables": len(available),
            "missingTables": missing,
        }
        response["schema"] = {
            "requiredTables": REQUIRED_TABLES,
            "availableTables": available,
        }
    except Exception as e:
        response["services"]["database"] = {"ok": False, "error": str(e)}

    try:
        r = httpx.get(f"{settings.agent_base_url}/healthz", timeout=5)
        payload = r.json() if r.status_code == 200 else {}
        response["services"]["agent"] = {"ok": bool(payload.get("ok")), **payload}
    except Exception as e:
        response["services"]["agent"] = {"ok": False, "error": str(e), "status": 503, "service": "agent"}

    response["ok"] = bool(
        response["services"].get("database", {}).get("ok")
        and response["services"].get("agent", {}).get("ok")
    )
    return response
