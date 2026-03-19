"""
agent_proxy.py
──────────────
Reverse-proxy routes that forward /api/chat and /api/conversations
requests from the backend (port 4000) to the agent server (port 8000).

Also proxies the new /agent/query endpoint for the multi-agent pipeline,
injecting the ``mode`` field from the request body.
"""

import json
import os

import httpx
from fastapi import APIRouter, Request, Response

AGENT_BASE = os.getenv("AGENT_BASE_URL", "http://localhost:8000")

router = APIRouter()

_client = httpx.AsyncClient(base_url=AGENT_BASE, timeout=120.0)


async def _proxy(method: str, path: str, request: Request) -> Response:
    """Forward an incoming request to the agent and relay the response."""
    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    # Inject mode passthrough for chat/query endpoints
    if method == "POST" and body:
        try:
            payload = json.loads(body)
            if "mode" not in payload:
                payload["mode"] = "auto"
            body = json.dumps(payload).encode()
        except (json.JSONDecodeError, TypeError):
            pass

    agent_resp = await _client.request(
        method,
        path,
        content=body,
        headers=headers,
        params=dict(request.query_params),
    )

    return Response(
        content=agent_resp.content,
        status_code=agent_resp.status_code,
        headers=dict(agent_resp.headers),
        media_type=agent_resp.headers.get("content-type"),
    )


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def proxy_chat(request: Request):
    return await _proxy("POST", "/api/chat", request)


# ── Multi-agent query ────────────────────────────────────────────────────────

@router.post("/agent/query")
async def proxy_agent_query(request: Request):
    """Forward to the new multi-agent pipeline endpoint."""
    return await _proxy("POST", "/agent/query", request)


# ── Conversations ────────────────────────────────────────────────────────────

@router.get("/conversations")
async def proxy_list_conversations(request: Request):
    return await _proxy("GET", "/api/conversations", request)


@router.get("/conversations/{conv_id}")
async def proxy_get_conversation(conv_id: str, request: Request):
    return await _proxy("GET", f"/api/conversations/{conv_id}", request)


@router.delete("/conversations/{conv_id}")
async def proxy_delete_conversation(conv_id: str, request: Request):
    return await _proxy("DELETE", f"/api/conversations/{conv_id}", request)
