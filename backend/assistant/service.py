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

    return {
        "agent": agent,
        "conversations": importlib.import_module("conversations"),
        "memory": importlib.import_module("memory"),
    }


def ensure_assistant_tables() -> None:
    _legacy_modules()["conversations"].ensure_tables()
    # Pre-warm the schema profile cache so the first agent request pays no init cost
    try:
        from tools._db import get_db as _get_agent_db
        _get_agent_db().get_schema_profile()
    except Exception:
        pass


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
    content = raw_message.get("content") or ""
    intent = metadata.get("intent", "analytics")
    is_report = intent == "report"
    return {
        "role": raw_message.get("role"),
        "content": content,
        "markdown": "" if is_report else content,
        "timestamp": raw_message.get("timestamp"),
        "artifacts": metadata.get("artifacts", []),
        "datasets": metadata.get("datasets", []),
        "suggested_actions": metadata.get("suggested_actions", []),
        "actions": metadata.get("actions", []),
        "intent": intent,
        "sql": metadata.get("sql", ""),
        "error": metadata.get("error", ""),
        "report_html": content if is_report else "",
    }


async def chat(
    *,
    message: str,
    auth: AuthContext,
    filters: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    mode: str = "normal",
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

    # Check for stored agent state (clarification resumption)
    agent_state = conversation.get("agent_state")

    scoped_prompt = f"{_normalise_filter_prompt(filters)}{message}"
    prior_messages = conversation.get("messages", [])
    result = await agent_api.run_agent(
        scoped_prompt, auth=auth, working_memory=working_memory,
        history=prior_messages, mode=mode, agent_state=agent_state,
    )

    # Handle clarification — store state and return the clarification as the response
    if getattr(result, "clarification", None):
        conversation_api.update_agent_state(conversation_id, getattr(result, "agent_state", None))
        conversation_api.append_message(conversation_id, "assistant", result.clarification)
        assistant_message = AssistantMessage(
            markdown=result.clarification,
            intent="clarification",
        )
        return ChatEnvelope(
            conversation_id=conversation_id,
            message=assistant_message,
            response=result.clarification,
            actions=getattr(result, "actions", []),
        )

    # Clear agent state if we were resuming
    if agent_state:
        conversation_api.update_agent_state(conversation_id, None)

    # Build artifacts from multiple charts (new architecture) or fall back to legacy single chart
    all_datasets = []
    all_artifacts = []
    agent_charts = getattr(result, "charts", []) or []

    if agent_charts:
        for i, chart in enumerate(agent_charts):
            _ga = lambda obj, key, default="": getattr(obj, key, default) if hasattr(obj, key) else obj.get(key, default)
            chart_rows = _ga(chart, "data_records", [])
            chart_sql = _ga(chart, "sql", "")
            chart_title = _ga(chart, "title", f"Analysis {i+1}")
            chart_type = _ga(chart, "chart_type", None) or None
            size_col = _ga(chart, "size_column", "")
            group_col = _ga(chart, "group_column", "")
            valid_types = _ga(chart, "valid_types", [])

            extra_spec = {}
            if size_col:
                extra_spec["sizeField"] = size_col
            if group_col:
                extra_spec["groupField"] = group_col

            if chart_rows:
                ds, arts = build_assistant_artifacts(
                    chart_rows,
                    sql=chart_sql,
                    dataset_id=f"query_result_{i}",
                    title=chart_title,
                    chart_type_hint=chart_type,
                    extra_spec=extra_spec if extra_spec else None,
                    valid_chart_types=valid_types,
                )
                all_datasets.extend(ds)
                all_artifacts.extend(arts)

    # Fallback to legacy single chart_data if no structured charts
    if not all_artifacts:
        rows = _extract_rows(getattr(result, "chart_data", {}) or {})
        if rows:
            ds, arts = build_assistant_artifacts(
                rows,
                sql=getattr(result, "sql", "") or "",
                title="Copilot",
            )
            all_datasets.extend(ds)
            all_artifacts.extend(arts)

    datasets = all_datasets
    artifacts = all_artifacts
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
        sql=getattr(result, "sql", "") or "",
        error=getattr(result, "error", ""),
    )

    # Collect all chart XMLs
    chart_xmls = []
    for chart in agent_charts:
        xml = getattr(chart, "chart_xml", "") if hasattr(chart, "chart_xml") else chart.get("chart_xml", "")
        if xml:
            chart_xmls.append(xml)

    return ChatEnvelope(
        conversation_id=conversation_id,
        message=assistant_message,
        response=getattr(result, "response", ""),
        actions=getattr(result, "actions", []),
        chart_data=getattr(result, "chart_data", {}) or {},
        chart_xml=chart_xmls[0] if chart_xmls else (getattr(result, "chart_xml", "") or ""),
        chart_xmls=chart_xmls,
        error=getattr(result, "error", "") or "",
    )


async def chat_stream(
    *,
    message: str,
    auth: AuthContext,
    filters: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    mode: str = "normal",
) -> Any:
    """
    Streaming version of chat(). Yields SSE event dicts as the agent progresses.
    Persists conversation only after the final 'complete' event.
    """
    import json as _json

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

    # Check for stored agent state (clarification resumption)
    agent_state = conversation.get("agent_state")

    scoped_prompt = f"{_normalise_filter_prompt(filters)}{message}"
    prior_messages = conversation.get("messages", [])

    # Yield conversation_id first so frontend can track it
    yield {"type": "init", "conversation_id": conversation_id}

    # Stream agent events
    final_message = None
    async for event in agent_api.run_agent_stream(
        scoped_prompt, auth=auth, working_memory=working_memory,
        history=prior_messages, mode=mode, agent_state=agent_state,
    ):
        if event.get("type") == "complete":
            final_message = event.get("message", {})
            # Clear agent state if we were resuming from clarification
            if agent_state:
                conversation_api.update_agent_state(conversation_id, None)
            # Build artifacts for the final message
            agent_charts = final_message.get("charts", [])
            all_datasets = []
            all_artifacts = []
            for i, chart in enumerate(agent_charts):
                chart_rows = chart.get("data_records", [])
                chart_type = chart.get("chart_type") or None
                extra_spec = {}
                if chart.get("size_column"):
                    extra_spec["sizeField"] = chart["size_column"]
                if chart.get("group_column"):
                    extra_spec["groupField"] = chart["group_column"]
                valid_types = chart.get("valid_types", [])
                if chart_rows:
                    ds, arts = build_assistant_artifacts(
                        chart_rows,
                        sql=chart.get("sql", ""),
                        dataset_id=f"query_result_{i}",
                        title=chart.get("title", f"Analysis {i+1}"),
                        chart_type_hint=chart_type,
                        extra_spec=extra_spec if extra_spec else None,
                        valid_chart_types=valid_types,
                    )
                    all_datasets.extend(ds)
                    all_artifacts.extend(arts)

            # Persist to conversation
            metadata = {
                "intent": final_message.get("intent", "analytics"),
                "actions": final_message.get("actions", []),
                "artifacts": [a.model_dump() for a in all_artifacts],
                "datasets": [d.model_dump(by_alias=True) for d in all_datasets],
                "suggested_actions": [a.model_dump() for a in _suggested_actions(message, filters, [a.model_dump() for a in all_artifacts])],
                "sql": final_message.get("sql", ""),
                "error": "",
            }
            conversation_api.append_message(conversation_id, "assistant", final_message.get("response", ""), metadata=metadata)

            new_memory = memory_api.build_memory_update(
                working_memory, message,
                final_message.get("actions", []),
                final_message.get("response", ""),
            )
            conversation_api.update_working_memory(conversation_id, new_memory)

            if is_first_message:
                try:
                    conversation_api.update_title(conversation_id, memory_api.generate_title(message))
                except Exception:
                    pass

            # Yield final complete event with full message structure
            intent = final_message.get("intent", "analytics")
            is_report = intent == "report"
            raw_response = final_message.get("response", "")

            # For reports: report_html is the same as response (the HTML content).
            # Pass it in BOTH fields so the frontend can find it regardless.
            report_html_content = (final_message.get("report_html", "") or raw_response) if is_report else ""

            yield {
                "type": "complete",
                "conversation_id": conversation_id,
                "message": {
                    "markdown": "" if is_report else raw_response,
                    "response": "" if is_report else raw_response,
                    "content": "" if is_report else raw_response,
                    "artifacts": [a.model_dump() for a in all_artifacts],
                    "datasets": [d.model_dump(by_alias=True) for d in all_datasets],
                    "suggested_actions": [a.model_dump() for a in _suggested_actions(message, filters, [a.model_dump() for a in all_artifacts])],
                    "actions": final_message.get("actions", []),
                    "intent": intent,
                    "sql": final_message.get("sql", ""),
                    "error": "",
                    "report_html": report_html_content,
                },
                "response": "" if is_report else raw_response,
                "actions": final_message.get("actions", []),
            }
        elif event.get("type") == "clarification_needed":
            # Store agent state for resumption and emit clarification event
            clarify_q = event.get("question", "Could you clarify?")
            clarify_state = event.get("agent_state")
            conversation_api.update_agent_state(conversation_id, clarify_state)
            conversation_api.append_message(conversation_id, "assistant", clarify_q)
            yield {
                "type": "clarification_needed",
                "conversation_id": conversation_id,
                "question": clarify_q,
            }
            return  # Stop streaming — wait for user reply
        elif event.get("type") == "error":
            yield event
        else:
            # Pass through phase, plan, step_complete, iteration, report_plan, report_step events
            yield event


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
