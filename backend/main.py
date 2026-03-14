from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.env import get_config
from backend.db.pool import close_pool, init_pool
from backend.routes.agent_proxy import router as agent_proxy_router
from backend.routes.api import router as api_router
from backend.routes.auth import router as auth_router
from backend.routes.health import router as health_router


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config = get_config()
    init_pool(config.db)
    try:
        yield
    finally:
        close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_proxy_router, prefix="/api", tags=["agent-proxy"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(api_router, prefix="/api", tags=["analytics"])
