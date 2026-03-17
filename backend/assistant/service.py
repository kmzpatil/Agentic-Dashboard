from __future__ import annotations

import importlib
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.analytics.artifacts import build_assistant_artifacts
from backend.contracts import AssistantMessage, ChatEnvelope, InsightAction
from backend.middleware.auth import AuthContext


AGENT_DIR = Path(__file__).resolve().parents[2] / "agent"


def _normalise_filter_prompt(filters: dict[str, Any] | None) -> str:
    if not filters:
        return ""
    parts = [f"{key}={value}" for key, value in filters.items() if value not in (None, "", "All")]
    if not parts:
        return ""
    return f"[Filters: {', '.join(parts)}] "


@lru_cache(maxsize=1)
def _legacy_modules():
    if str(AGENT_DIR) not in sys.path:
        sys.path.insert(0, str(AGENT_DIR))

    agent = importlib.import_module("agent")
    importlib.reload(agent)
    
    return {
        "agent": agent,
        "conversations": importlib.import_module("conversations"),
        "memory": importlib.import_module("memory"),
    }


def ensure_assistant_tables() -> None:
    _legacy_modules()["conversations"].ensure_tables()


def _conversation_owner_guard(conversation: dict | None, auth: AuthContext) -> None:
    if not conversation:
        return
    owner_id = conversation.get("user_id")
    if owner_id and owner_id != auth.auth_user_id:
        raise PermissionError("Conversation not found")


def _extract_rows(chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(chart_data, dict):
        return []
    for value in chart_data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    return []


def _suggested_actions(message: str, filters: dict[str, Any] | None, artifacts: list[dict[str, Any]]) -> list[InsightAction]:
    actions = [
        InsightAction(
            type="navigate",
            label="Open Trends",
            target="trends",
            filter_state={"view": "trends", "metric": "uploaded_count", "granularity": "month"},
        ),
        InsightAction(
            type="navigate",
            label="Inspect Funnel",
            target="funnel",
            filter_state={"view": "funnel", "breakdown": "channel"},
        ),
    ]

    if "channel" in message.lower():
        actions.insert(
            0,
            InsightAction(
                type="navigate",
                label="Explore Channels",
                target="explorer",
                filter_state={"view": "explorer", "dim1": "channel", "dim2": "language"},
            ),
        )

    if filters:
        actions.append(
            InsightAction(
                type="follow_up",
                label="Ask with current filters",
                target="copilot",
                filter_state={"view": "copilot", "filters": filters},
            )
        )

    return actions[:3]


def _serialize_message(raw_message: dict[str, Any]) -> dict[str, Any]:
    metadata = raw_message.get("metadata") or {}
    return {
        "role": raw_message.get("role"),
        "content": raw_message.get("content") or "",
        "markdown": raw_message.get("content") or "",
        "timestamp": raw_message.get("timestamp"),
        "artifacts": metadata.get("artifacts", []),
        "datasets": metadata.get("datasets", []),
        "suggested_actions": metadata.get("suggested_actions", []),
        "actions": metadata.get("actions", []),
        "intent": metadata.get("intent", "analytics"),
        "error": metadata.get("error", ""),
    }


async def chat(
    *,
    message: str,
    auth: AuthContext,
    filters: dict[str, Any] | None = None,
    conversation_id: str | None = None,
) -> ChatEnvelope:
    modules = _legacy_modules()
    conversation_api = modules["conversations"]
    memory_api = modules["memory"]
    agent_api = modules["agent"]

    ensure_assistant_tables()

    conversation = conversation_api.get_conversation(conversation_id) if conversation_id else None
    _conversation_owner_guard(conversation, auth)
    if not conversation:
        conversation = conversation_api.create_conversation(user_id=auth.auth_user_id, title="New conversation")
        conversation_id = conversation["id"]

    working_memory = conversation.get("working_memory", "")
    is_first_message = len(conversation.get("messages", [])) == 0
    conversation_api.append_message(conversation_id, "user", message)

    scoped_prompt = f"{_normalise_filter_prompt(filters)}{message}"
    result = await agent_api.run_agent(scoped_prompt, auth=auth, working_memory=working_memory)

    rows = _extract_rows(getattr(result, "chart_data", {}) or {})
    datasets, artifacts = build_assistant_artifacts(
        rows,
        sql=getattr(result, "sql", "") or "",
        title="Copilot",
    )
    suggested_actions = _suggested_actions(message, filters, [artifact.model_dump() for artifact in artifacts])

    metadata = {
        "intent": getattr(result, "intent", "analytics"),
        "actions": getattr(result, "actions", []),
        "artifacts": [artifact.model_dump() for artifact in artifacts],
        "datasets": [dataset.model_dump(by_alias=True) for dataset in datasets],
        "suggested_actions": [action.model_dump() for action in suggested_actions],
        "sql": getattr(result, "sql", ""),
        "error": getattr(result, "error", ""),
    }
    conversation_api.append_message(conversation_id, "assistant", getattr(result, "response", ""), metadata=metadata)

    new_memory = memory_api.build_memory_update(
        working_memory,
        message,
        getattr(result, "actions", []),
        getattr(result, "response", ""),
    )
    conversation_api.update_working_memory(conversation_id, new_memory)

    if is_first_message:
        try:
            conversation_api.update_title(conversation_id, memory_api.generate_title(message))
        except Exception:
            pass

    assistant_message = AssistantMessage(
        markdown=getattr(result, "response", ""),
        artifacts=artifacts,
        datasets=datasets,
        suggested_actions=suggested_actions,
        intent=getattr(result, "intent", "analytics"),
        error=getattr(result, "error", ""),
    )

    return ChatEnvelope(
        conversation_id=conversation_id,
        message=assistant_message,
        response=getattr(result, "response", ""),
        actions=getattr(result, "actions", []),
        chart_data=getattr(result, "chart_data", {}) or {},
        chart_xml=getattr(result, "chart_xml", "") or "",
        error=getattr(result, "error", "") or "",
    )


def list_conversations(auth: AuthContext) -> dict[str, Any]:
    conversations = _legacy_modules()["conversations"].list_conversations(user_id=auth.auth_user_id)
    return {
        "conversations": [
            {
                "id": conversation["id"],
                "title": conversation.get("title") or "New conversation",
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at"),
            }
            for conversation in conversations
        ]
    }


def get_conversation(auth: AuthContext, conversation_id: str) -> dict[str, Any]:
    conversation = _legacy_modules()["conversations"].get_conversation(conversation_id)
    _conversation_owner_guard(conversation, auth)
    if not conversation:
        raise LookupError("Conversation not found")

    return {
        **conversation,
        "messages": [_serialize_message(message) for message in conversation.get("messages", [])],
    }


def delete_conversation(auth: AuthContext, conversation_id: str) -> bool:
    conversation = _legacy_modules()["conversations"].get_conversation(conversation_id)
    _conversation_owner_guard(conversation, auth)
    if not conversation:
        return False
    return bool(_legacy_modules()["conversations"].delete_conversation(conversation_id))
