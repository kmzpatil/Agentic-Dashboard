from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.analytics.trends_service import get_trends_snapshot
from backend.middleware.auth import AuthContext, require_auth

router = APIRouter()


@router.get("", include_in_schema=False)
@router.get("/")
def get_trends(
    metric: str = Query(default="uploaded_count"),
    granularity: str = Query(default="month"),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type: Optional[List[str]] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    auth: AuthContext = Depends(require_auth),
):
    """
    Main trends endpoint for the Mission Control dashboard.
    Fetches historical data points for various volume and efficiency metrics.
    """
    try:
        return get_trends_snapshot(
            auth,
            metric=metric,
            granularity=granularity,
            company=company,
            channel=channel,
            user=user,
            language=language,
            input_type=input_type,
            output_type=output_type,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
