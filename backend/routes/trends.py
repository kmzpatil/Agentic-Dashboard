from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.analytics.trends_service import get_trends_snapshot
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


@router.get("")
def get_trends(
    metric: str = Query(default="uploaded_count"),
    granularity: str = Query(default="month"),
    auth: AuthContext = Depends(require_auth),
):
    try:
        return get_trends_snapshot(auth, metric=metric, granularity=granularity)
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
