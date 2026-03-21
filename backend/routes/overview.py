from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend.analytics.overview_service import get_overview_snapshot
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


@router.get("", include_in_schema=False)
@router.get("/")
def get_overview(auth: AuthContext = Depends(require_auth)):
    if auth.role == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mission Control is restricted for user role",
        )

    try:
        return get_overview_snapshot(auth)
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
