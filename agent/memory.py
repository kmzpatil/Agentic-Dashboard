"""
memory.py
---------
Working memory management for Frammer AI conversations.

Each conversation accumulates a working memory block:
  mem = mem + latest_user_query + agent_thinking_summary

When the memory exceeds a token threshold, a compaction LLM call
summarizes it into a shorter block, preserving key context.
"""

import logging
from typing import Dict, List, Optional

try:
    from client import LLMClient
except ImportError:
    from agent.client import LLMClient

logger = logging.getLogger("frammer.memory")

_compactor = LLMClient.fast()

MAX_MEMORY_CHARS = 8000


def build_memory_update(
    existing_memory: str,
    user_query: str,
    agent_actions: List[str],
    agent_response: str,
) -> str:
    """
    Append the latest turn to working memory.

    Returns the updated memory string. If it exceeds the threshold,
    triggers compaction.
    """
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
        "Keep the summary under 6000 characters.\n\n"
        f"Memory to compact:\n{memory}\n\n"
        "Compacted memory:"
    )
    try:
        resp = _compactor.invoke(prompt, label="memory-compact")
        return resp.content.strip()
    except Exception as exc:
        logger.warning("Memory compaction failed: %s — truncating instead", exc)
        return memory[-8000:]


def generate_title(user_query: str) -> str:
    """Generate a short conversation title from the first user message."""
    prompt = (
        "Generate a concise title (3-6 words) for a conversation that starts with:\n"
        f'"{user_query}"\n\n'
        "Return ONLY the title, no quotes, no punctuation at the end."
    )
    try:
        resp = _compactor.invoke(prompt, label="title-gen")
        title = resp.content.strip().strip('"').strip("'")
        return title[:60]
    except Exception:
        return user_query[:50]
