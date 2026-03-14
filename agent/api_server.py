"""
api_server.py
─────────────
FastAPI server that exposes the Frammer analytics agent as a web API.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

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

app = FastAPI(title="Frammer Analytics API", version="5.0.0")


@app.on_event("startup")
async def _startup():
    try:
        ensure_tables()
    except Exception as exc:
        logger.warning("Could not ensure conversation tables: %s", exc)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

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
    filters: Optional[dict] = None
    conversation_id: Optional[str] = None


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
        "service": "frammer-agent",
        "database": database,
        "providers": {
            "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        },
    }


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_path = Path(__file__).parent / "templates" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/query", response_model=QueryResponse)
async def run_query(req: QueryRequest):
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
    """
    AI chat endpoint. Seeds conversation BEFORE running the agent,
    so conversation_id is always available — even on errors.
    """
    logger.info("Chat request: %r (conv=%s)", req.message, req.conversation_id)
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # ── Seed conversation immediately ────────────────────────────────────────
    conv_id = req.conversation_id
    conv = get_conversation(conv_id) if conv_id else None
    if not conv:
        conv = create_conversation(title="New conversation")
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


# ── Conversation endpoints ────────────────────────────────────────────────────


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


# ── Schema / data endpoints ──────────────────────────────────────────────────


@app.get("/api/schema/search")
async def search_schemas(
    q: str = Query(..., description="Natural language query to search schemas"),
    limit: int = Query(5, ge=1, le=20),
):
    try:
        results = _db_client.search_table_schemas(q, limit=limit)
        return {"query": q, "results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/tables")
async def get_schema():
    schema_str = get_frammer_schema()
    tables = {}
    current_table = None
    for line in schema_str.splitlines():
        if line.startswith("Table:"):
            current_table = line.replace("Table:", "").strip()
            tables[current_table] = []
        elif line.startswith("Columns:") and current_table:
            col_part = line.replace("Columns:", "").strip()
            tables[current_table] = [
                c.split("(")[0].strip() for c in col_part.split(",")
            ]
    return {"tables": tables}


@app.post("/api/data")
async def get_data(req: DataRequest):
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL cannot be empty.")
    raw = execute_sql_query(req.sql)
    parsed = json.loads(raw)
    if "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])
    return {"records": parsed.get("data", [])}
