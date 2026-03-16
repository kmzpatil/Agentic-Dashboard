"""
agent_groq.py
-------------
Frammer Analytics Agent (Groq / MCP edition).

Architecture:
  1. Client: Groq via client2.py with random key rotation.
  2. Tools:  Loaded from the local MCP server (AgentToolModule).
  3. Loop:   LangGraph ReAct StateGraph.
  4. Planning: A fast LLM pass generates a numbered plan before the ReAct loop.
"""

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Dict, List, Optional, TypedDict
import re

from dotenv import load_dotenv

# -- Load env: agent dir first, then project root --
_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

from logger_setup import setup_logging
setup_logging()

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import uuid as _uuid

# -- Use client2.py for key rotation --
from client2 import LLMClient

# -- MCP-backed tool implementations (still usable as LangChain tools) --
from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient, QueryValidationError
from tools.metric_definitions import retrieve_metric_definitions
from tools.chart import generate_plotly_chart
from tools import get_frammer_schema, execute_sql_query, get_db

logger = logging.getLogger("frammer.agent.groq")

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_OPEN_RE  = re.compile(r"<think>.*", re.DOTALL)   # unclosed think tag
_THINK_CLOSE    = "</think>"

def _clean(text: str) -> str:
    """Strip all <think>...</think> blocks and return the remainder."""
    return _THINK_BLOCK_RE.sub("", text).strip()

def _extract_response(text: str) -> str:
    """
    Qwen3 outputs reasoning inside <think> tags and the real answer AFTER them.
    This function extracts the post-think answer.
    Falls back to the full text (stripped) if no think tags are present.
    """
    if _THINK_CLOSE in text:
        # Everything after the last </think> is the real answer
        after = text.split(_THINK_CLOSE, 1)[-1].strip()
        if after:
            return after
        # Edge case: content was only inside think (shouldn't happen with final answers)
        # Extract and return the think content as fallback
        match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    # No think tags — return as-is, but clean any stray unclosed tags
    return _THINK_OPEN_RE.sub("", text).strip() or text.strip()

# ── Per-request context ──────────────────────────────────────────────────────
from contextvars import ContextVar
_ctx: ContextVar[dict] = ContextVar("agent_ctx")

def _new_ctx() -> dict:
    return {
        "sql": "", "records": [], "query_results": {}, "latest_result_id": "",
        "chart_xml": "", "chart_data": {}, "actions": [], "plan": "",
    }

def _get_ctx() -> dict:
    try:
        return _ctx.get()
    except LookupError:
        ctx = _new_ctx()
        _ctx.set(ctx)
        return ctx

# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    intent: str = "analytics"
    response: str = ""
    actions: List[str] = field(default_factory=list)
    chart_xml: str = ""
    chart_data: Dict = field(default_factory=dict)
    sql: str = ""
    error: str = ""
    plan: str = ""

# ── Schema cache ─────────────────────────────────────────────────────────────
_schema_cache: Optional[str] = None

# ── Tool definitions (LangChain-compatible, backed by MCP module logic) ───────

@tool
def get_schema() -> str:
    """Retrieve the full database schema — table names, column names and types.
    ALWAYS call this FIRST before writing any SQL."""
    global _schema_cache
    ctx = _get_ctx()
    if not _schema_cache:
        _schema_cache = get_frammer_schema()
    ctx["actions"].append("Retrieved database schema")
    logger.info("[tool] get_schema → %d chars", len(_schema_cache))
    return _schema_cache

@tool
def get_metric_definitions(query: str) -> str:
    """Look up business metric definitions, formulas, table names, join paths, and example SQL.
    Args:
        query: Keyword describing the metric (e.g. 'conversion', 'publish', 'duration').
    """
    ctx = _get_ctx()
    result = retrieve_metric_definitions(query)
    ctx["actions"].append("Looked up metric definitions")
    logger.info("[tool] get_metric_definitions(%r) → %d chars", query[:40], len(result))
    return result

@tool
def search_relevant_schemas(query: str) -> str:
    """Semantic CHESS-RAG search for relevant tables and columns.
    Args:
        query: Natural language description of the data you need.
    """
    ctx = _get_ctx()
    try:
        db = get_db()
        results = db.search_table_schemas(query, limit=5)
        ctx["actions"].append(f"Schema search — {len(results)} match(es)")
        logger.info("[tool] search_relevant_schemas(%r) → %d results", query[:40], len(results))
        return json.dumps(results, indent=2, default=str)
    except Exception as exc:
        ctx["actions"].append("Schema search failed")
        return f"Schema search error: {exc}. Use get_schema instead."

@tool
def run_sql_query(sql: str, limit: int = 200) -> str:
    """Execute a read-only PostgreSQL SELECT. Returns JSON with row_count, columns, result_id, sample_rows.
    On failure returns an error — fix the SQL and retry.

    SQL RULES:
    - Double-quote mixed-case columns: "Upload_Date", "User_Name"
    - Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')
    - Monthly grouping: date_trunc('month', to_date("Upload_Date",'YYYY-MM-DD'))::date AS month
    Args:
        sql: Valid PostgreSQL SELECT statement.
        limit: Max rows to return.
    """
    ctx = _get_ctx()
    logger.info("[tool] run_sql_query: %s…", sql[:120])
    raw = execute_sql_query(sql, limit=limit)
    parsed = json.loads(raw)

    if "error" in parsed:
        ctx["actions"].append(f"SQL failed — {parsed['error'][:60]}")
        logger.warning("[tool] SQL error: %s", parsed["error"][:200])
        return f"SQL Error: {parsed['error']}\n\nFix the query and retry."

    records = parsed.get("data", [])
    result_id = str(_uuid.uuid4())[:8]
    ctx["sql"] = sql
    ctx["records"] = records
    ctx["query_results"][result_id] = records
    ctx["latest_result_id"] = result_id
    ctx["chart_data"]["query_result"] = records

    cols = list(records[0].keys()) if records else []
    ctx["actions"].append(f"SQL OK — {len(records)} rows, {len(cols)} cols")
    logger.info("[tool] SQL OK: %d rows, cols=%s", len(records), cols)

    sample_size = 50
    return json.dumps({
        "status": "success",
        "result_id": result_id,
        "total_row_count": len(records),
        "columns": cols,
        "data": records[:sample_size],
        "note": f"Showing first {sample_size} rows only." if len(records) > sample_size else "Showing all rows."
    }, default=str)

@tool
def build_chart(chart_type: str, x_column: str, y_columns: str, title: str, result_id: str = "") -> str:
    """Build a chart from SQL query results. Call AFTER run_sql_query.
    Args:
        chart_type: 'bar', 'line', or 'pie'.
        x_column: Exact column name for X axis.
        y_columns: Column name(s) for Y axis (comma-separated for multi-series).
        title: Short chart title, max 8 words.
        result_id: Optional result_id from a prior run_sql_query. Uses latest if empty.
    """
    ctx = _get_ctx()
    records = (
        ctx["query_results"].get(result_id)
        if result_id
        else ctx.get("records", [])
    )
    if not records:
        ctx["actions"].append("Chart skipped — no data")
        return "No data available. Run a SQL query first."

    attrs = {"type": chart_type, "x_axis": x_column, "y_axis": y_columns, "title": title}
    xml = generate_plotly_chart(data_records=records, chart_attributes=attrs)

    if xml and xml.startswith("<?xml"):
        ctx["chart_xml"] = xml
        ctx["actions"].append(f"Chart: {chart_type} — {title}")
        logger.info("[tool] build_chart OK (%d chars)", len(xml))
        return f"Chart created: {title} ({chart_type}, {len(records)} points)"

    ctx["actions"].append("Chart generation failed")
    logger.warning("[tool] build_chart failed: %s", str(xml)[:100])
    return f"Chart failed: {xml or 'Unknown error'}"

@tool
def get_current_time() -> str:
    """Return the current local date and time.
    ALWAYS call this if the user uses relative time terms like 'today', 'yesterday', 'last week', or 'last month'
    to calculate the exact date range for SQL."""
    from datetime import datetime
    now = datetime.now()
    ctx = _get_ctx()
    ctx["actions"].append("Checked current time")
    return now.strftime("%Y-%m-%d %H:%M:%S")


# ── LLM clients ──────────────────────────────────────────────────────────────
TOOLS = [get_schema, get_metric_definitions, search_relevant_schemas, run_sql_query, build_chart, get_current_time]

# Fast and creative clients used for classify/plan/chat — these also rotate on each .invoke() call
_fast_client  = LLMClient.fast(provider="groq")
_creat_client = LLMClient.creative(provider="groq")

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are Frammer AI, an analytics assistant for a media production platform.

## Tools
1. **get_schema** — Full DB schema. Call FIRST.
2. **get_metric_definitions** — Business metric formulas & join paths.
3. **search_relevant_schemas** — Semantic RAG search for relevant tables.
4. **run_sql_query** — Execute a PostgreSQL SELECT (retry on error).
5. **build_chart** — Visualise query results.
6. **get_current_time** — Get current date/time to resolve 'last month', 'today', etc.

## Execution Plan
{plan_block}

## Workflow
1. get_schema → understand tables
2. get_metric_definitions → understand the metric
3. search_relevant_schemas → find precise tables
4. run_sql_query → retrieve data (fix and retry on error)
5. build_chart → visualise
6. Write a clear business-language markdown summary

## Response Rules
- **Data Integrity**: ONLY use numbers and facts present in the tool output. Never estimate or hallucinate values.
- **Sample Handling**: If `total_row_count` > provided `data` rows, explicitly state you are summarizing a sample.
- **Formatting**: **Bold** key numbers and terms.
- **Insight Style**: Use bullet points for multiple insights.
- **Privacy**: Never expose SQL or internal technical IDs to the user.
- **No Images**: Do NOT generate markdown image tags.
- **No Thinking**: Do NOT wrap final responses in <think> tags.

## Critical SQL Rules
- ALWAYS double-quote mixed-case column names: pp."Post_ID", rv."Input_Type", pd."Channel_Name"
- ALWAYS double-quote mixed-case table aliases too when referencing columns
- Keep SQL concise — avoid unnecessary subqueries
- Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')

## Common SQL Pitfalls (AVOID)
- **Join Error**: Joining `published_posts.Asset_ID` directly to `raw_videos.Video_ID` (results in empty or wrong data). Use `created_assets` (ca) as the bridge.
- **Case Error**: Querying `Input_Type = 'Interview'` (case-sensitive). Use `lower("Input_Type") = 'interview'`.
- **Date Error**: Comparing strings directly (`'2025-10'`). Use `BETWEEN` with full YYYY-MM-DD strings or `to_date`.
{memory_block}"""

# ── LangGraph StateGraph ─────────────────────────────────────────────────────

class _AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def _call_model(state: _AgentState):
    msg_count = len(state["messages"])
    logger.info("--- LOOP ITER: Calling LLM (Context: %d messages) ---", msg_count)
    start = time.time()

    # Re-instantiate with a fresh random key on every iteration
    _loop_client = LLMClient(provider="groq")
    llm_with_tools = _loop_client.llm.bind_tools(TOOLS)

    try:
        resp = llm_with_tools.invoke(state["messages"])
        duration = time.time() - start
        tool_count = len(getattr(resp, "tool_calls", []))
        if tool_count:
            for tc in resp.tool_calls:
                args_preview = json.dumps(tc.get("args", {}))[:200]
                logger.info(
                    "--- TOOL CALL: [%s]\n  Args: %s",
                    tc.get("name", "?"), args_preview,
                )
            logger.info("--- LOOP: %d tool call(s) in %.2fs ---", tool_count, duration)
        else:
            final_text = _clean(resp.content)[:400]
            logger.info(
                "--- LOOP FINAL ANSWER (%.2fs)\n%s\n--- END ---",
                duration, final_text,
            )
        return {"messages": [resp]}
    except Exception as e:
        logger.error("--- LOOP ERROR: %s ---", e)
        raise

def _should_continue(state: _AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

_tool_node = ToolNode(TOOLS)
_builder = StateGraph(_AgentState)
_builder.add_node("agent", _call_model)
_builder.add_node("tools", _tool_node)
_builder.set_entry_point("agent")
_builder.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
_builder.add_edge("tools", "agent")
_graph = _builder.compile()

# ── Planner ───────────────────────────────────────────────────────────────────

def _generate_plan(question: str) -> str:
    """Fast LLM pass to generate a numbered execution plan before the ReAct loop."""
    logger.info("Planner: Generating plan for: %r", question[:80])
    start = time.time()

    prompt = (
        "You are a data analytics planner. Given the user's question, write a short numbered plan "
        "(max 5 steps) describing exactly which database tables to query, which joins to use, "
        "and what type of chart to generate. Be concise and precise — no explanation, just steps.\n\n"
        f"Question: {question}\n\nPlan:"
    )
    try:
        resp = _fast_client.invoke(prompt, label="planner")
        plan = _clean(resp.content).strip()
        duration = time.time() - start
        steps = [l for l in plan.splitlines() if l.strip()]
        logger.info("Planner: Done in %.2fs. Plan (%d steps):\n%s",
                    duration, len(steps), plan)
        return plan
    except Exception as exc:
        logger.warning("Planner: Failed (%s). Proceeding without plan.", exc)
        return ""

# ── Intent classifier ─────────────────────────────────────────────────────────

def _classify(question: str) -> str:
    logger.info("Classify: %r", question[:80])
    prompt = (
        "Reply with ONLY 'analytics' or 'conversational'.\n\n"
        "'analytics' = data, metrics, trends, counts, charts, uploads, channels, time, date, SQL needed.\n"
        "'conversational' = greetings, thanks, how-to, small talk.\n\n"
        f"Message: {question}\n\nOne word:"
    )
    raw = _fast_client.invoke(prompt, label="classify").content.lower().strip()
    intent = "analytics" if raw.startswith("analytics") else "conversational"
    logger.info("Intent → %s", intent.upper())
    return intent

def _conversational_reply(question: str, memory: str = "", current_time: str = "") -> AgentResult:
    mem = f"\nConversation context:\n{memory}\n" if memory else ""
    time_ctx = f"\nCurrent System Time: {current_time}\n" if current_time else ""
    prompt = (
        "You are Frammer AI, an analytics assistant.\n"
        f"{time_ctx}{mem}\nUser: {question}\n\nRespond in markdown. No <think> tags."
    )
    resp = _creat_client.invoke(prompt, label="chat")
    return AgentResult(
        intent="conversational",
        response=_extract_response(resp.content),
        actions=["Conversational reply"],
    )

# ── Main entry point ──────────────────────────────────────────────────────────

async def run_agent(question: str, working_memory: str = "") -> AgentResult:
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    intent = _classify(question)
    if intent == "conversational":
        return _conversational_reply(question, working_memory, current_time=now_str)

    ctx = _new_ctx()
    _ctx.set(ctx)

    # ── Planning phase ────────────────────────────────────────────────────────
    plan = _generate_plan(question)
    ctx["plan"] = plan
    plan_block = f"Your execution plan for this question:\n{plan}" if plan else "(No plan generated)"
    memory_block = f"\n## Conversation Memory\n{working_memory}" if working_memory else ""

    system = SYSTEM_PROMPT.format(plan_block=plan_block, memory_block=memory_block)
    # Inject current time directly into the first message for immediate context
    system += f"\n\n## System Environment\nCurrent System Time: {now_str}\n"
    
    messages = [SystemMessage(content=system), HumanMessage(content=question)]

    try:
        logger.info("=== ReAct loop start ===")
        state = await _graph.ainvoke({"messages": messages}, config={"recursion_limit": 30})

        response = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                response = _extract_response(msg.content)
                break

        if not response:
            response = "I analyzed your query but couldn't produce a summary. Try rephrasing."

        logger.info(
            "=== AGENT DONE ===\n"
            "  Actions  : %s\n"
            "  Has chart: %s\n"
            "  SQL len  : %d chars\n"
            "  Response :\n%s",
            ctx["actions"],
            bool(ctx["chart_xml"]),
            len(ctx["sql"]),
            response[:600],
        )

        return AgentResult(
            intent="analytics",
            response=response,
            actions=ctx["actions"],
            chart_xml=ctx["chart_xml"],
            chart_data=ctx["chart_data"],
            sql=ctx["sql"],
            plan=plan,
        )

    except Exception as exc:
        err = str(exc)
        logger.error("=== Agent error: %s ===", err, exc_info=True)
        return AgentResult(intent="analytics", response=f"Error: {err}", actions=ctx["actions"], error=err, plan=plan)

# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def _cli():
        print("-- Frammer AI (Groq + MCP + Planning) --\nType 'quit' to exit.\n")
        loop = asyncio.get_event_loop()
        while True:
            q = (await loop.run_in_executor(None, input, "You: ")).strip()
            if q.lower() == "quit":
                break
            if not q:
                continue
            r = await run_agent(q)
            print(f"\n[{r.intent}]")
            if r.plan:
                print(f"PLAN:\n{r.plan}\n")
            print(f"RESPONSE:\n{r.response}")
            if r.actions:
                print(f"ACTIONS: {r.actions}")
            print()

    asyncio.run(_cli())
