"""
conversations.py
-----------------
Conversation persistence and working memory for the Frammer AI agent.

Stores conversations in PostgreSQL (same DB as analytics data).
Implements a rolling working-memory window that compacts older turns
via an LLM summarization call, keeping context manageable.

Messages are stored in a dedicated append-only table for O(1) inserts
instead of re-serializing a full JSON blob on every append.
"""

import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text,
    create_engine, text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

try:
    from mcp_server.config import resolve_database_url
except ImportError:
    from agent.mcp_server.config import resolve_database_url

logger = logging.getLogger("frammer.conversations")

Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(128), nullable=True, index=True)
    title = Column(String(256), nullable=False, default="New conversation")
    messages_json = Column(Text, nullable=False, default="[]")  # deprecated — kept for backward compat
    working_memory = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


_engine = None
_SessionLocal = None


def _init_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = resolve_database_url()
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine)


@contextmanager
def _session_scope():
    """Context manager that commits on success, rolls back on failure."""
    _init_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_conversation(user_id: Optional[str] = None, title: str = "New conversation") -> Dict:
    with _session_scope() as session:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
        )
        session.add(conv)
        session.flush()
        return _to_dict(conv, messages=[])


def get_conversation(conversation_id: str) -> Optional[Dict]:
    with _session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            return None
        messages = _load_messages(session, conversation_id)
        return _to_dict(conv, messages=messages)


def list_conversations(user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    with _session_scope() as session:
        q = session.query(Conversation)
        if user_id:
            q = q.filter(Conversation.user_id == user_id)
        rows = q.order_by(Conversation.updated_at.desc()).limit(limit).all()
        return [_to_dict(r, messages=[]) for r in rows]


def append_message(conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> Dict:
    """Append a message via an O(1) INSERT into conversation_messages."""
    with _session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata, default=str) if metadata else None,
        )
        session.add(msg)

        conv.updated_at = datetime.utcnow()
        session.flush()

        messages = _load_messages(session, conversation_id)
        return _to_dict(conv, messages=messages)


def update_working_memory(conversation_id: str, memory: str) -> None:
    with _session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv:
            conv.working_memory = memory
            conv.updated_at = datetime.utcnow()


def update_title(conversation_id: str, title: str) -> None:
    with _session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv:
            conv.title = title
            conv.updated_at = datetime.utcnow()


def delete_conversation(conversation_id: str) -> bool:
    with _session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv:
            # Delete messages first (cascade may handle this, but be explicit)
            session.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).delete()
            session.delete(conv)
            return True
        return False


def _load_messages(session: Session, conversation_id: str) -> List[Dict]:
    """Load messages from the append-only table, ordered by creation time."""
    rows = (
        session.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    return [
        {
            "role": row.role,
            "content": row.content,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
            **({"metadata": json.loads(row.metadata_json)} if row.metadata_json else {}),
        }
        for row in rows
    ]


def _to_dict(conv: Conversation, messages: List[Dict] | None = None) -> Dict:
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "messages": messages if messages is not None else [],
        "working_memory": conv.working_memory or "",
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def ensure_tables():
    """Create the conversations + conversation_messages tables if they don't exist."""
    _init_engine()
    logger.info("Conversations tables ready.")
