from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.db.pool import query


router = APIRouter()


@router.get("/")
def health_check():
    try:
        query("SELECT 1")
        return {"ok": True}
    except Exception as error:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(error)})
