from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.analytics.overview_service import get_overview_snapshot
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


@router.get("/")
def get_overview(auth: AuthContext = Depends(require_auth)):
    try:
        return get_overview_snapshot(auth)
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
