"""
memory.py
---------
Conversation memory for the multi-agent pipeline.

Provides a lightweight async interface for storing and retrieving
the last N turns so follow-up queries have context.

Falls back to an in-memory LRU dict when PostgreSQL is not available.
Also preserves the legacy helper functions used by the existing api_server.
"""

import logging
from collections import OrderedDict
from typing import Any, List

logger = logging.getLogger("agent.memory")

_MAX_CONVERSATIONS = 200


class ConversationMemory:
    """In-memory conversation context store (LRU, capped at 200 conversations)."""

    def __init__(self) -> None:
        self._store: OrderedDict[str, list[dict]] = OrderedDict()

    async def get_context(self, conversation_id: str, last_n: int = 5) -> list[dict]:
        """Return the last *last_n* turns for a conversation."""
        turns = self._store.get(conversation_id, [])
        return turns[-last_n:]

    async def save(self, conversation_id: str, query: str, response: Any) -> None:
        """Append a turn to the conversation history."""
        summary = getattr(response, "summary", str(response))
        turn = {"query": query, "summary": summary[:500]}
        if conversation_id not in self._store:
            self._store[conversation_id] = []
        self._store[conversation_id].append(turn)
        self._store.move_to_end(conversation_id)
        # Evict oldest if over cap
        while len(self._store) > _MAX_CONVERSATIONS:
            self._store.popitem(last=False)

    async def clear(self, conversation_id: str) -> None:
        """Remove all turns for a conversation."""
        self._store.pop(conversation_id, None)


# ── Legacy helpers (used by existing api_server.py) ──────────────────────────

try:
    from client import LLMClient
    _compactor = LLMClient.fast()
except Exception:
    _compactor = None

MAX_MEMORY_CHARS = 2000


def build_memory_update(
    existing_memory: str,
    user_query: str,
    agent_actions: List[str],
    agent_response: str,
) -> str:
    """Append the latest turn to working memory (legacy interface)."""
    actions_summary = " | ".join(agent_actions) if agent_actions else ""
    response_snippet = agent_response[:300] if agent_response else ""

    new_block = (
        f"\n[User]: {user_query}\n"
        f"[Agent actions]: {actions_summary}\n"
        f"[Agent response snippet]: {response_snippet}\n"
    )

    updated = (existing_memory + new_block).strip()

    if len(updated) > MAX_MEMORY_CHARS:
        logger.info("Memory exceeds %d chars (%d), compacting...", MAX_MEMORY_CHARS, len(updated))
        updated = _compact_memory(updated)
        logger.info("Compacted to %d chars", len(updated))

    return updated


def _compact_memory(memory: str) -> str:
    prompt = (
        "You are a memory compaction agent. Your job is to take a conversation "
        "memory log and compress it into a concise summary that preserves:\n"
        "- Key facts the user has asked about\n"
        "- User preferences and patterns\n"
        "- Important data findings and insights mentioned\n"
        "- Any context needed for follow-up questions\n\n"
        "Drop redundant details, repeated queries, and verbose explanations.\n"
        "Keep the summary under 1500 characters.\n\n"
        f"Memory to compact:\n{memory}\n\n"
        "Compacted memory:"
    )
    try:
        if _compactor is not None:
            resp = _compactor.invoke(prompt, label="memory-compact")
            return resp.content.strip()
    except Exception as exc:
        logger.warning("Memory compaction failed: %s — truncating instead", exc)
    return memory[-2000:]


def generate_title(user_query: str) -> str:
    """Generate a short conversation title from the first user message."""
    prompt = (
        "Generate a concise title (3-6 words) for a conversation that starts with:\n"
        f'"{user_query}"\n\n'
        "Return ONLY the title, no quotes, no punctuation at the end."
    )
    try:
        if _compactor is not None:
            resp = _compactor.invoke(prompt, label="title-gen")
            title = resp.content.strip().strip('"').strip("'")
            return title[:60]
    except Exception:
        pass
    return user_query[:50]
