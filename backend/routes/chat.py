from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.assistant.service import chat as assistant_chat
from backend.contracts import ChatEnvelope
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    filters: dict[str, Any] | None = None
    conversation_id: str | None = None


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
    )
