from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.insights.service import build_insights
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


@router.get("")
def get_insights(
    surface: str = Query(default="mission-control"),
    limit: int = Query(default=6, ge=1, le=12),
    auth: AuthContext = Depends(require_auth),
):
    try:
        return {"insights": [card.model_dump() for card in build_insights(auth, surface=surface, limit=limit)]}
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
