from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.middleware.auth import AuthContext, require_auth
from backend.routes.usage_trends import forecast_all_clients, forecast_client_chronos


router = APIRouter()


@router.get("/forecast/client-chronos")
def labs_forecast_client(
    client_name: str = Query(...),
    metric: str = Query("uploaded_count"),
    granularity: str = Query("day"),
    prediction_length: int = Query(7, ge=1, le=90),
    _auth: AuthContext = Depends(require_auth),
):
    return forecast_client_chronos(
        client_name=client_name,
        metric=metric,
        granularity=granularity,
        prediction_length=prediction_length,
    )


@router.get("/forecast/all-clients")
def labs_forecast_all(
    metric: str = Query("uploaded_count"),
    granularity: str = Query("day"),
    prediction_length: int = Query(7, ge=1, le=90),
    _auth: AuthContext = Depends(require_auth),
):
    return forecast_all_clients(
        metric=metric,
        granularity=granularity,
        prediction_length=prediction_length,
    )
