from fastapi import APIRouter

from backend.routes.explorer import router as explorer_router
from backend.routes.funnel import router as funnel_router
from backend.routes.insights import router as insights_router
from backend.routes.overview import router as overview_router
from backend.routes.trends import router as trends_router
from backend.routes.usage_trends import router as usage_trends_router


router = APIRouter()

router.include_router(overview_router, prefix="/overview")
router.include_router(trends_router, prefix="/trends")
router.include_router(usage_trends_router, prefix="/usage-trends")
router.include_router(funnel_router, prefix="/funnel")
router.include_router(explorer_router, prefix="/explorer")
router.include_router(insights_router, prefix="/insights")
