"""
agent.py — Agent proxy routes.
Port of backend_legacy/routes/agent.js.
Proxies requests to the Python agent service on port 8000.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ..config import settings
from ..dependencies import AuthUser, require_auth

router = APIRouter(tags=["agent"])

_TIMEOUT = httpx.Timeout(timeout=settings.agent_timeout_s)


async def _proxy(method: str, path: str, body: dict | None = None, query: dict | None = None):
    """Forward a request to the agent service."""
    url = f"{settings.agent_base_url}{path}"
    clean_query = {k: v for k, v in (query or {}).items() if v is not None and v != ""}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.request(
                method, url,
                json=body if body else None,
                params=clean_query if clean_query else None,
            )

        try:
            payload = resp.json()
        except Exception:
            payload = {"raw": resp.text} if resp.text else None

        if resp.status_code >= 400:
            detail = payload.get("detail") or payload.get("error") or resp.reason_phrase or "Agent request failed"
            raise HTTPException(resp.status_code, detail)

        return JSONResponse(content=payload, status_code=resp.status_code)

    except httpx.TimeoutException:
        raise HTTPException(504, "Timed out while waiting for the agent service.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Agent service unavailable: {e}")


@router.get("/api/agent/health")
async def agent_health(auth: AuthUser = Depends(require_auth)):
    return await _proxy("GET", "/healthz")


@router.post("/api/chat")
async def chat(request: Request, auth: AuthUser = Depends(require_auth)):
    body = await request.json()
    return await _proxy("POST", "/api/chat", body=body)


@router.post("/api/query")
async def query(request: Request, auth: AuthUser = Depends(require_auth)):
    body = await request.json()
    return await _proxy("POST", "/api/query", body=body)


@router.get("/api/agent/tables")
async def agent_tables(auth: AuthUser = Depends(require_auth)):
    return await _proxy("GET", "/api/tables")


@router.get("/api/agent/schema/search")
async def schema_search(
    q: str = Query(""),
    limit: int | None = Query(None),
    auth: AuthUser = Depends(require_auth),
):
    return await _proxy("GET", "/api/schema/search", query={"q": q, "limit": str(limit) if limit else ""})


@router.get("/api/conversations")
async def list_conversations(
    user_id: str | None = Query(None),
    auth: AuthUser = Depends(require_auth),
):
    return await _proxy("GET", "/api/conversations", query={"user_id": user_id or ""})


@router.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str, auth: AuthUser = Depends(require_auth)):
    return await _proxy("GET", f"/api/conversations/{conv_id}")


@router.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str, auth: AuthUser = Depends(require_auth)):
    return await _proxy("DELETE", f"/api/conversations/{conv_id}")
