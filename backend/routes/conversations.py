from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.assistant.service import delete_conversation, get_conversation, list_conversations
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


@router.get("")
def conversations(auth: AuthContext = Depends(require_auth)):
    return list_conversations(auth)


@router.get("/{conversation_id}")
def conversation_detail(conversation_id: str, auth: AuthContext = Depends(require_auth)):
    try:
        return get_conversation(auth, conversation_id)
    except (LookupError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}")
def remove_conversation(conversation_id: str, auth: AuthContext = Depends(require_auth)):
    try:
        deleted = delete_conversation(auth, conversation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}
