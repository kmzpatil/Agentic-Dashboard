import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List

from agentic_analytics import run_nl_query
from json_to_xml import json_to_xml_payload
from sql_query import execute_sql_query_for_posts


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
REQUIRED_ANALYTICS_TABLES = [
    "video_list_data",
    "channel_metrics",
    "monthly_counts",
    "input_type_data",
    "language_data",
    "output_type_data",
]


def ask_ollama(prompt: str, model: str) -> str:
    """Send a prompt to Ollama and return generated text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            return parsed.get("response", "").strip()
    except urllib.error.HTTPError as exc:
        return f"Ollama HTTP error: {exc}"
    except urllib.error.URLError as exc:
        return f"Ollama connection error: {exc}"
    except json.JSONDecodeError:
        return "Ollama returned invalid JSON response."


def should_use_analytics(user_text: str) -> bool:
    """Route to analytics only for explicit data/metric questions."""
    text = user_text.lower().strip()
    if text.startswith("/analytics "):
        return True

    keywords = {
        "kpi",
        "dashboard",
        "metric",
        "analytics",
        "count",
        "duration",
        "published",
        "processed",
        "created",
        "channel",
        "language",
        "output type",
        "input type",
        "publish conversion",
        "data quality",
        "funnel",
        "top 10 videos",
    }
    return any(word in text for word in keywords)


def build_general_prompt(user_text: str, chat_history: List[Dict[str, str]]) -> str:
    """Build prompt for normal conversational mode."""
    history_lines: List[str] = []
    for turn in chat_history[-6:]:
        history_lines.append(f"User: {turn['user']}")
        history_lines.append(f"Assistant: {turn['assistant']}")

    history_block = "\n".join(history_lines)

    return (
        "You are a helpful, concise chatbot. Respond naturally and clearly. "
        "If user asks analytics about media operations, you can answer conceptually unless asked for data run.\n\n"
        f"Conversation history:\n{history_block}\n\n"
        f"User: {user_text}\n"
        "Assistant:"
    )


def build_unavailable_chart_xml(user_question: str) -> str:
    """Return a safe fallback XML payload when analytics backend is unavailable."""
    payload = {
        "config": {
            "success": False,
            "status": "analytics_unavailable",
            "reason": "data_source_unreachable_or_missing",
            "requested_query": user_question,
        },
        "data": [],
    }
    return json_to_xml_payload(json.dumps(payload), root_tag="analytics_response")


def get_db_health_status() -> Dict[str, Any]:
    """Check DB connectivity and required table availability."""
    status: Dict[str, Any] = {
        "connected": False,
        "missing_tables": [],
        "available_tables": [],
        "errors": [],
    }

    ping_raw = execute_sql_query_for_posts("SELECT 1 AS ok")
    try:
        ping = json.loads(ping_raw)
    except json.JSONDecodeError:
        status["errors"].append("Health ping returned invalid JSON")
        return status

    ping_config = ping.get("config", {}) if isinstance(ping, dict) else {}
    if not ping_config.get("success", False):
        status["errors"].append("Database connection failed")
        return status

    status["connected"] = True

    for table_name in REQUIRED_ANALYTICS_TABLES:
        raw = execute_sql_query_for_posts(f"SELECT 1 AS ok FROM {table_name} LIMIT 1")
        try:
            parsed = json.loads(raw)
            config = parsed.get("config", {}) if isinstance(parsed, dict) else {}
            if config.get("success", False):
                status["available_tables"].append(table_name)
            else:
                status["missing_tables"].append(table_name)
        except json.JSONDecodeError:
            status["missing_tables"].append(table_name)

    return status


def print_db_health_status() -> None:
    """Print DB health summary in user-friendly format."""
    health = get_db_health_status()
    print("\nDB Health Check:")

    if not health.get("connected"):
        print("  Status: NOT CONNECTED")
        print("  Hint: Check DATABASE_URL and database credentials.")
        return

    missing = health.get("missing_tables", [])
    available = health.get("available_tables", [])

    if missing:
        print("  Status: PARTIAL")
        print(f"  Available tables: {len(available)}")
        print(f"  Missing tables: {', '.join(missing)}")
    else:
        print("  Status: READY")
        print("  All required analytics tables are available.")


from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """Tracks the state of the agent across conversation turns."""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    current_model: str = Field(default_factory=lambda: DEFAULT_OLLAMA_MODEL)
    last_chart_xml: str = ""
    last_intent: str = ""

def run_chat_turn(
    user_question: str,
    state: AgentState
) -> Dict[str, str]:
    """
    Process a chat turn using the persistent AgentState.
    Return the required shape:
    {
      "message": "chat answer from llm",
      "chart": "xml"
    }
    """
    normalized = user_question.strip()
    if normalized.startswith("/analytics "):
        normalized = normalized.replace("/analytics ", "", 1).strip()

    if should_use_analytics(user_question):
        output = run_nl_query(question=normalized, model=state.current_model, filters=state.filters)
        result = output.get("result", {})
        config = result.get("config", {}) if isinstance(result, dict) else {}
        data_raw = result.get("data", []) if isinstance(result, dict) else []
        data_list = data_raw if isinstance(data_raw, list) else []
        
        state.last_intent = config.get("intent", "unknown")

        # If DB query fails, degrade gracefully with a user-safe message and fallback chart XML.
        if not config.get("success", False):
            err_msg = config.get("error", "Unknown database error.")
            generated_sql = config.get("query", "No SQL generated.")
            fallback_xml = build_unavailable_chart_xml(normalized)
            state.last_chart_xml = fallback_xml
            return {
                "message": (
                    f"The analytics engine failed to execute the dynamically generated SQL.\n\n"
                    f"**Generated SQL:**\n```sql\n{generated_sql}\n```\n\n"
                    f"**Execution Error:** `{err_msg}`\n\n"
                    "Please try rephrasing your question or simplifying the query."
                ),
                "chart": fallback_xml,
            }

        xml_output = json_to_xml_payload(json.dumps(result), root_tag="analytics_response")
        state.last_chart_xml = xml_output
        summary_prompt = (
            "You are an analytics assistant. Give a direct natural-language answer based on the result below. "
            "No markdown table required. Keep it concise and useful.\n\n"
            f"Question: {normalized}\n"
            f"Applied filters: {config.get('applied_filters')}\n"
            f"Result config: {json.dumps(config)}\n"
            f"Result data sample: {json.dumps(data_list[:10])}\n"
            "Assistant:"
        )

        response_msg = ask_ollama(summary_prompt, model=state.current_model)
        state.messages.append({"user": user_question, "assistant": response_msg})
        return {
            "message": response_msg,
            "chart": xml_output,
        }

    general_prompt = build_general_prompt(normalized, state.messages)
    response_msg = ask_ollama(general_prompt, model=state.current_model)
    state.messages.append({"user": user_question, "assistant": response_msg})
    
    # Keep only last 6 messages
    if len(state.messages) > 6:
        state.messages = state.messages[-6:]
        
    state.last_chart_xml = ""
    return {
        "message": response_msg,
        "chart": "",
    }


def _print_help() -> None:
    print("Commands:")
    print("  /quit                Exit chat")
    print("  /model <name>        Switch Ollama model (example: /model llama3:latest)")
    print("  /filters <json>      Set analytics filters (example: /filters {\"team_name\":\"sports\"})")
    print("  /clearfilters        Clear analytics filters")
    print("  /analytics <query>   Force analytics mode for this query")
    print("  /dbcheck             Run DB/table health check")
    print("  /last                Print last response object")
    print("  /help                Show commands")


def chat_cli() -> None:
    """Interactive chatbot CLI with optional analytics mode."""
    state = AgentState()

    print("=== Frammer Chatbot (Ollama) ===")
    print(f"Model: {state.current_model}")
    print("Type /help for commands.")
    print_db_health_status()

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue

        if user_input == "/quit":
            print("Bye.")
            break

        if user_input == "/help":
            _print_help()
            continue

        if user_input.startswith("/model "):
            model_name = user_input.replace("/model ", "", 1).strip()
            if model_name:
                state.current_model = model_name
                print(f"Switched model to: {state.current_model}")
            continue

        if user_input.startswith("/filters "):
            raw = user_input.replace("/filters ", "", 1).strip()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    state.filters = parsed
                    print(f"Filters set: {state.filters}")
                else:
                    print("Filters must be a JSON object.")
            except json.JSONDecodeError:
                print("Invalid JSON for filters.")
            continue

        if user_input == "/clearfilters":
            state.filters = {}
            print("Filters cleared.")
            continue

        if user_input == "/last":
            if state.last_chart_xml:
                print(state.last_chart_xml)
            else:
                print("No result yet.")
            continue

        if user_input == "/dbcheck":
            print_db_health_status()
            continue

        result = run_chat_turn(
            user_question=user_input,
            state=state
        )

        assistant_text = result.get("message", "")
        print("\nAssistant:")
        print(assistant_text)

        if result.get("chart"):
            print("\n(Chart XML generated. Use /last to view full object.)")


if __name__ == "__main__":
    chat_cli()
