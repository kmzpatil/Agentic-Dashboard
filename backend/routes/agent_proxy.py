"""
agent_proxy.py
──────────────
Reverse-proxy routes that forward /api/chat and /api/conversations
requests from the backend (port 4000) to the agent server (port 8000).
"""

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
