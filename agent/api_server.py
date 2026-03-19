"""
api_server.py
──────────────
FastAPI server that exposes the Anthropic-powered Frammer analytics agent.

This file preserves ALL existing endpoints and adds the new multi-agent
pipeline, invoked first on /api/chat with a fallback to the legacy agent.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Ensure we load env from the local directory first (agent/.env)
load_dotenv(Path(__file__).resolve().parent / ".env")
# Fallback to root .env
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()

# Make sure agent/ directory is on sys.path so all our modules resolve
_AGENT_DIR = str(Path(__file__).resolve().parent)
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from logger_setup import setup_logging
setup_logging()

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent import run_agent

from conversations import (
    create_conversation, get_conversation, list_conversations,
    append_message, update_working_memory, update_title, delete_conversation,
    ensure_tables,
)
from memory import build_memory_update, generate_title
from tools.schema import get_frammer_schema
from tools.sql_query import execute_sql_query
from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient

from contextlib import asynccontextmanager

# ── Multi-agent orchestrator (lazy import at startup) ────────────────────────

_orchestrator_ready = False


async def _get_orchestrator():
    """Lazy-import and init the orchestrator singleton."""
    from orchestrator.orchestrator import get_orchestrator
    return await get_orchestrator()


async def _shutdown_orchestrator():
    from orchestrator.orchestrator import shutdown_orchestrator
    await shutdown_orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator_ready
    # Existing table bootstrap
    try:
        ensure_tables()
    except Exception as exc:
        logger.warning("Could not ensure conversation tables: %s", exc)

    # Initialise the new orchestrator
    try:
        await _get_orchestrator()
        _orchestrator_ready = True
        logger.info("Multi-agent orchestrator initialised")
    except Exception as exc:
        logger.warning("Orchestrator init failed (non-fatal, legacy agent available): %s", exc)

    yield

    # Shutdown
    if _orchestrator_ready:
        await _shutdown_orchestrator()

app = FastAPI(title="Frammer Analytics API (Anthropic Version)", version="6.0.0-multi-agent", lifespan=lifespan)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("frammer.api_server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings = ServerSettings.from_env()
_db_client = DatabaseClient(
    database_url=_settings.database_url,
    default_schema=_settings.default_schema,
)

# ── Request / response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

class DataRequest(BaseModel):
    sql: str

class ChatRequest(BaseModel):
    message: str
    filters: Optional[dict] = Field(default_factory=dict)
    conversation_id: Optional[str] = Field(default=None)
    mode: Optional[str] = Field(default="auto")  # fast | deep | auto

class QueryResponse(BaseModel):
    question: str
    sql: str
    xml: str
    response: str
    error: str
    chart_data: dict

class ChatResponse(BaseModel):
    response: str
    actions: List[str] = []
    chart_xml: str = ""
    chart_data: dict = {}
    conversation_id: str = ""
    error: str = ""
    # ── New fields consumed by TalkToDataModule / ArtifactCanvas ──
    message: Optional[dict] = None    # {markdown, artifacts, datasets, ...}
    has_charts: bool = False
    path_used: str = ""
    insights: list = []
    confidence: str = ""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/healthz")
async def healthz():
    try:
        overview = _db_client.get_database_overview(schema=_settings.default_schema)
        database = {
            "ok": True,
            "dialect": overview.get("dialect"),
            "database": overview.get("database"),
            "schema": overview.get("schema"),
            "table_count": overview.get("table_count"),
        }
    except Exception as exc:
        database = {"ok": False, "error": str(exc)}

    return {
        "ok": database["ok"],
        "service": "frammer-agent-anthropic",
        "database": database,
        "providers": {
            "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        },
    }

@app.post("/api/query", response_model=QueryResponse)
async def run_query_route(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = await run_agent(req.question)

    return QueryResponse(
        question=req.question,
        sql=result.sql,
        xml=result.chart_xml,
        response=result.response,
        error=result.error,
        chart_data=jsonable_encoder(result.chart_data),
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    logger.info("Chat request: %r (conv=%s, mode=%s)", req.message, req.conversation_id, req.mode)
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    conv_id = req.conversation_id
    conv = get_conversation(conv_id) if conv_id else None
    if not conv:
        conv = create_conversation(title="New conversation (Anthropic)")
        conv_id = conv["id"]
        logger.info("Created conversation %s", conv_id)

    working_mem = conv.get("working_memory", "")
    is_first_message = len(conv.get("messages", [])) == 0

    append_message(conv_id, "user", req.message)

    question = req.message
    if req.filters:
        parts = [f"{k}={v}" for k, v in req.filters.items() if v and v != "All"]
        if parts:
            question = f"[Filters: {', '.join(parts)}] {question}"

    # ── Try new multi-agent pipeline first ────────────────────────────────
    mode = req.mode or "auto"
    if _orchestrator_ready:
        try:
            orchestrator = await _get_orchestrator()
            result = await orchestrator.handle_query(
                query=question,
                conversation_id=conv_id,
                mode=mode,
            )

            summary = result.get("response", "")
            artifacts = result.get("artifacts", [])
            datasets = result.get("datasets", [])
            insights = result.get("insights", [])
            path_used = result.get("path_used", "fast")
            confidence = result.get("confidence", "HIGH")
            has_charts = result.get("has_charts", False)
            query_used = result.get("query_used", "")

            # Build markdown response with insights as bullet points
            md_parts = [summary]
            if insights:
                md_parts.append("")
                for ins in insights:
                    md_parts.append(f"- {ins}")
            if query_used:
                md_parts.append("")
                md_parts.append(f"*SQL: `{query_used}`*")
            markdown = "\n".join(md_parts)

            append_message(conv_id, "assistant", summary, metadata={
                "intent": "multi-agent",
                "actions": [],
                "path_used": path_used,
            })

            new_memory = build_memory_update(working_mem, req.message, [], summary)
            update_working_memory(conv_id, new_memory)

            if is_first_message:
                try:
                    update_title(conv_id, generate_title(req.message))
                except Exception:
                    pass

            return ChatResponse(
                response=summary,
                actions=[],
                chart_xml="",
                chart_data={},
                conversation_id=conv_id,
                error="",
                message={
                    "markdown": markdown,
                    "artifacts": artifacts,
                    "datasets": datasets,
                    "suggested_actions": [],
                    "intent": "analytics",
                },
                has_charts=has_charts,
                path_used=path_used,
                insights=insights,
                confidence=confidence,
            )

        except Exception as exc:
            logger.warning("Multi-agent pipeline failed, falling back to legacy: %s", exc, exc_info=True)

    # ── Fallback: legacy single-agent ─────────────────────────────────────
    try:
        result = await run_agent(question, working_memory=working_mem)
        logger.info("Agent done: intent=%s actions=%d", result.intent, len(result.actions))

        append_message(conv_id, "assistant", result.response, metadata={
            "intent": result.intent,
            "actions": result.actions,
        })

        new_memory = build_memory_update(
            working_mem, req.message, result.actions, result.response,
        )
        update_working_memory(conv_id, new_memory)

        if is_first_message:
            try:
                update_title(conv_id, generate_title(req.message))
            except Exception:
                pass

        return ChatResponse(
            response=result.response,
            actions=result.actions,
            chart_xml=result.chart_xml,
            chart_data=jsonable_encoder(result.chart_data),
            conversation_id=conv_id,
            error=result.error,
        )

    except Exception as exc:
        logger.error("/api/chat error: %s", exc, exc_info=True)
        return ChatResponse(
            response=f"Sorry, I encountered an error: {exc}",
            conversation_id=conv_id,
            error=str(exc),
        )

@app.get("/api/conversations")
async def get_conversations(user_id: Optional[str] = None):
    return {"conversations": list_conversations(user_id=user_id)}

@app.get("/api/conversations/{conv_id}")
async def get_conversation_detail(conv_id: str):
    conv = get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.delete("/api/conversations/{conv_id}")
async def delete_conv(conv_id: str):
    ok = delete_conversation(conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}

@app.post("/api/data")
async def get_data_route(req: DataRequest):
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL cannot be empty.")
    raw = execute_sql_query(req.sql)
    parsed = json.loads(raw)
    if "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return {"records": parsed.get("data", [])}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4001)
