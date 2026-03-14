"""
main.py — FastAPI application entry point.
Replaces the NodeJS Express server (backend_legacy/).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import agent, auth, explorer, funnel, health, overview, usage_trends

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("frammer-api")

app = FastAPI(title="Frammer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(overview.router)
app.include_router(usage_trends.router)
app.include_router(funnel.router)
app.include_router(explorer.router)
app.include_router(agent.router)


@app.on_event("startup")
def startup():
    from .dependencies import get_engine
    engine = get_engine()
    log.info("Database engine created: %s", engine.url)
    log.info("Agent proxy target: %s", settings.agent_base_url)
    log.info("Frammer FastAPI ready on port %s", settings.port)
