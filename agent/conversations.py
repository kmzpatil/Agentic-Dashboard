"""
conversations.py
-----------------
Conversation persistence and working memory for the Frammer AI agent.

Stores conversations in PostgreSQL (same DB as analytics data).
Implements a rolling working-memory window that compacts older turns
via an LLM summarization call, keeping context manageable.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import (
    Column, DateTime, String, Text, create_engine, text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

from mcp_server.config import resolve_database_url

logger = logging.getLogger("frammer.conversations")

Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(128), nullable=True, index=True)
    title = Column(String(256), nullable=False, default="New conversation")
    messages_json = Column(Text, nullable=False, default="[]")
    working_memory = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


_engine = None
_SessionLocal = None


def _get_session() -> Session:
    global _engine, _SessionLocal
    if _engine is None:
        url = resolve_database_url()
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal()


def create_conversation(user_id: Optional[str] = None, title: str = "New conversation") -> Dict:
    session = _get_session()
    try:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
        )
        session.add(conv)
        session.commit()
        return _to_dict(conv)
    finally:
        session.close()


def get_conversation(conversation_id: str) -> Optional[Dict]:
    session = _get_session()
    try:
        conv = session.get(Conversation, conversation_id)
        return _to_dict(conv) if conv else None
    finally:
        session.close()


def list_conversations(user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    session = _get_session()
    try:
        q = session.query(Conversation)
        if user_id:
            q = q.filter(Conversation.user_id == user_id)
        rows = q.order_by(Conversation.updated_at.desc()).limit(limit).all()
        return [_to_dict(r) for r in rows]
    finally:
        session.close()


def append_message(conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> Dict:
    """Append a message to a conversation and return the updated conversation."""
    session = _get_session()
    try:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        messages = json.loads(conv.messages_json or "[]")
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            msg["metadata"] = metadata
        messages.append(msg)

        conv.messages_json = json.dumps(messages, default=str)
        conv.updated_at = datetime.utcnow()
        session.commit()
        return _to_dict(conv)
    finally:
        session.close()


def update_working_memory(conversation_id: str, memory: str) -> None:
    session = _get_session()
    try:
        conv = session.get(Conversation, conversation_id)
        if conv:
            conv.working_memory = memory
            conv.updated_at = datetime.utcnow()
            session.commit()
    finally:
        session.close()


def update_title(conversation_id: str, title: str) -> None:
    session = _get_session()
    try:
        conv = session.get(Conversation, conversation_id)
        if conv:
            conv.title = title
            conv.updated_at = datetime.utcnow()
            session.commit()
    finally:
        session.close()


def delete_conversation(conversation_id: str) -> bool:
    session = _get_session()
    try:
        conv = session.get(Conversation, conversation_id)
        if conv:
            session.delete(conv)
            session.commit()
            return True
        return False
    finally:
        session.close()


def _to_dict(conv: Conversation) -> Dict:
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "messages": json.loads(conv.messages_json or "[]"),
        "working_memory": conv.working_memory or "",
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def ensure_tables():
    """Create the conversations table if it doesn't exist."""
    _get_session().close()
    logger.info("Conversations table ready.")
