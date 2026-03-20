from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.assistant.service import chat as assistant_chat, chat_stream as assistant_chat_stream
from backend.contracts import ChatEnvelope
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    filters: dict[str, Any] | None = None
    conversation_id: str | None = None
    mode: str = "normal"  # "normal" | "report"


@router.post("", response_model=ChatEnvelope)
async def chat(payload: ChatRequest, auth: AuthContext = Depends(require_auth)):
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return await assistant_chat(
        message=message,
        auth=auth,
        filters=payload.filters or {},
        conversation_id=payload.conversation_id,
        mode=payload.mode,
    )


@router.post("/stream")
async def chat_stream(payload: ChatRequest, auth: AuthContext = Depends(require_auth)):
    """SSE streaming endpoint. Yields progressive events as the agent works."""
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    async def event_generator():
        async for event in assistant_chat_stream(
            message=message,
            auth=auth,
            filters=payload.filters or {},
            conversation_id=payload.conversation_id,
            mode=payload.mode,
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
