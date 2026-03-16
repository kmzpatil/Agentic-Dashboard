from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load env vars FIRST before any module that reads them at import time
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.assistant.service import ensure_assistant_tables
from backend.config.env import get_config
from backend.db.pool import close_pool, init_pool
from backend.routes.api import router as api_router
from backend.routes.auth import router as auth_router
from backend.routes.chat import router as chat_router
from backend.routes.conversations import router as conversations_router
from backend.routes.health import router as health_router
from backend.routes.labs import router as labs_router
from backend.mcp2.server import build_mcp_server
from database.simulator.router import router as simulator_router


BACKEND_DIR = _BACKEND_DIR
PROJECT_ROOT = _PROJECT_ROOT


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config = get_config()
    init_pool(config.db)
    try:
        ensure_assistant_tables()
    except Exception:
        # Health exposes this status explicitly; startup should stay resilient.
        pass
    try:
        yield
    finally:
        close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_config().cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(api_router, prefix="/api", tags=["analytics"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(conversations_router, prefix="/api/conversations", tags=["conversations"])
app.include_router(labs_router, prefix="/api/labs", tags=["labs"])
app.include_router(simulator_router, prefix="/api/simulator", tags=["simulator"])
app.include_router(simulator_router, prefix="/api/labs/simulator", tags=["labs-simulator"])

if get_config().features.mcp_enabled:
    app.mount("/mcp", build_mcp_server().streamable_http_app())
