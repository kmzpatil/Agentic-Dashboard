"""
agent.py
--------
True ReAct Agent using LangGraph StateGraph with native tool-calling.

The agent autonomously decides which tools to call, observes results,
self-corrects on errors, and loops until it has enough to answer.
No fixed pipeline — the LLM drives the entire flow.

Entry point:
    result = await run_agent(question)
"""

import json
import logging
import os
import re
import uuid as _uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from client import LLMClient
from tools import (
    execute_sql_query,
    generate_plotly_chart,
    get_db,
    get_frammer_schema,
    retrieve_metric_definitions,
)

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env")
load_dotenv()
logger = logging.getLogger("frammer.agent")

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _clean(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


# ── Per-request context (thread-safe via contextvars) ────────────────────────

_ctx: ContextVar[dict] = ContextVar("agent_ctx")


def _new_ctx() -> dict:
    return {"sql": "", "records": [], "query_results": {}, "latest_result_id": "",
            "chart_xml": "", "chart_data": {}, "actions": []}


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


# ── Schema cache ─────────────────────────────────────────────────────────────

_schema_cache: Optional[str] = None


# ── Tool definitions ─────────────────────────────────────────────────────────
# Each tool is a @tool-decorated function that the LLM invokes via bind_tools.
# Tools write side-effects into the per-request context (_ctx) so we can
# extract chart_xml, chart_data, actions, etc. after the loop completes.

@tool
def get_schema() -> str:
    """Retrieve the full database schema — all table names, column names,
    and column types. ALWAYS call this FIRST before writing any SQL query
    so you use exact, correct table and column names."""
    global _schema_cache
    ctx = _get_ctx()
    if not _schema_cache:
        _schema_cache = get_frammer_schema()
    ctx["actions"].append("Retrieved database schema")
    logger.info("[tool] get_schema -> %d chars", len(_schema_cache))
    return _schema_cache


@tool
def get_metric_definitions(query: str) -> str:
    """Look up business metric definitions, formulas, table names, join paths,
    and example SQL for metrics like uploads, conversions, durations, channels,
    clients, etc. Call this to understand how to correctly calculate a metric
    before writing SQL.

    Args:
        query: The user's question or a keyword describing the metric.
    """
    ctx = _get_ctx()
    result = retrieve_metric_definitions(query)
    ctx["actions"].append("Looked up metric definitions")
    logger.info("[tool] get_metric_definitions(%r) -> %d chars", query[:50], len(result))
    return result


@tool
def search_relevant_schemas(query: str) -> str:
    """Semantic search for database tables and columns relevant to a question.
    Uses CHESS-style RAG with embedding vectors to find the most relevant
    schema elements. Returns table names, column details, and similarity scores.
    Call this when you need to discover which tables are relevant for a query.

    Args:
        query: Natural language description of the data you need (e.g. 'interview uploads by channel').
    """
    ctx = _get_ctx()
    try:
        db = get_db()
        results = db.search_table_schemas(query, limit=5)
        ctx["actions"].append(f"Searched schemas — {len(results)} matches")
        logger.info("[tool] search_relevant_schemas(%r) -> %d results", query[:50], len(results))
        return json.dumps(results, indent=2, default=str)
    except Exception as exc:
        ctx["actions"].append("Schema search failed")
        logger.warning("[tool] search_relevant_schemas error: %s", exc)
        return f"Schema search error: {exc}. Use get_schema instead."


@tool
def run_sql_query(sql: str, limit: int = 200) -> str:
    """Execute a read-only PostgreSQL SELECT query and return results.
    Returns JSON with row_count, columns, result_id, and sample_rows on success.
    Returns an error message on failure — read the error, fix the SQL, and retry.

    SQL RULES:
    - Use ONLY exact table/column names from get_schema()
    - Double-quote mixed-case columns: "Upload_Date", "User_Name"
    - Alias aggregations: COUNT(*) AS upload_count
    - Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')
    - Monthly grouping: date_trunc('month', to_date("Upload_Date",'YYYY-MM-DD'))::date AS month

    Args:
        sql: A valid PostgreSQL SELECT statement.
        limit: Maximum rows to return (default 200, capped by server config).
    """
    ctx = _get_ctx()
    logger.info("[tool] run_sql_query: %s", sql[:200])

    raw = execute_sql_query(sql, limit=limit)
    parsed = json.loads(raw)

    if "error" in parsed:
        error_msg = parsed["error"]
        ctx["actions"].append(f"SQL failed — {error_msg[:60]}")
        logger.warning("[tool] SQL error: %s", error_msg[:200])
        return f"SQL Error: {error_msg}\n\nFix the query and call run_sql_query again."

    records = parsed.get("data", [])
    result_id = str(_uuid.uuid4())[:8]

    ctx["sql"] = sql
    ctx["records"] = records
    ctx["query_results"][result_id] = records
    ctx["latest_result_id"] = result_id
    ctx["chart_data"]["query_result"] = records

    cols = list(records[0].keys()) if records else []
    sample = records[:5]

    ctx["actions"].append(f"Queried database — {len(records)} rows, {len(cols)} columns")
    logger.info("[tool] SQL OK: %d rows, cols=%s", len(records), cols)

    return json.dumps({
        "status": "success",
        "result_id": result_id,
        "row_count": len(records),
        "columns": cols,
        "sample_rows": sample,
    }, default=str)


@tool
def build_chart(chart_type: str, x_column: str, y_columns: str, title: str, result_id: str = "") -> str:
    """Build a chart from SQL query results.
    Call this AFTER run_sql_query returns data successfully.

    Args:
        chart_type: 'bar', 'line', or 'pie'.
                    line = time-series, pie = proportions (<=6 cats), bar = comparisons.
        x_column: Exact column name for the X axis (from query results).
        y_columns: Column name(s) for the Y axis, comma-separated for multi-series.
        title: Short chart title, max 8 words.
        result_id: Optional result_id from a prior run_sql_query call to chart
                   a specific dataset. If empty, charts the most recent query.
    """
    ctx = _get_ctx()

    # Resolve which dataset to chart
    if result_id and result_id in ctx.get("query_results", {}):
        records = ctx["query_results"][result_id]
    else:
        records = ctx.get("records", [])

    if not records:
        ctx["actions"].append("Chart skipped — no data")
        return "No data available. Run a SQL query first."

    attrs = {"type": chart_type, "x_axis": x_column, "y_axis": y_columns, "title": title}
    xml = generate_plotly_chart(data_records=records, chart_attributes=attrs)

    if xml and xml.startswith("<?xml"):
        ctx["chart_xml"] = xml
        ctx["actions"].append(f"Generated {chart_type} chart: {title}")
        logger.info("[tool] build_chart -> OK (%d chars)", len(xml))
        return f"Chart created: {title} ({chart_type}, {len(records)} data points)"

    error = xml if xml else "Unknown error"
    ctx["actions"].append("Chart generation failed")
    logger.warning("[tool] build_chart failed: %s", str(error)[:120])
    return f"Chart failed: {error}. Try different columns or chart_type."


# ── LangGraph ReAct graph ────────────────────────────────────────────────────

TOOLS = [get_schema, get_metric_definitions, search_relevant_schemas, run_sql_query, build_chart]

SYSTEM_PROMPT = """\
You are Frammer AI, an analytics assistant for the Frammer media production platform.

## Tools
1. **get_schema** — Full database schema (tables + columns). Call FIRST.
2. **get_metric_definitions** — How business metrics are calculated.
3. **search_relevant_schemas** — Semantic search for relevant tables/columns using CHESS RAG.
4. **run_sql_query** — Execute a PostgreSQL SELECT query.
5. **build_chart** — Visualize query results as a chart.

## Workflow for data questions
1. get_schema → see available tables
2. get_metric_definitions → understand the metric
3. search_relevant_schemas → find the most relevant tables for your question
4. run_sql_query → get data (retry on error — fix SQL based on the error message)
5. build_chart → visualize results
6. Write a clear, concise markdown summary

## Response rules
- **Bold** key numbers and terms
- Bullet points for multiple insights
- Business language only — never show SQL or technical details to the user
- Focus on trends, comparisons, top/bottom performers, actionable findings
- Do NOT generate markdown images tags. NEVER try to embed the chart image using markdown text. A separate interactive chart widget is already built into the UI.
- Do NOT wrap your response in <think> tags
{memory_block}"""


_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT", "o4-mini")
_O_SERIES = any(_DEPLOYMENT.lower().startswith(p) for p in ("o1", "o3", "o4"))

_llm_kwargs: dict = dict(
    azure_deployment=_DEPLOYMENT,
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
    max_retries=3,
)
if not _O_SERIES:
    _llm_kwargs["temperature"] = 0

_llm = AzureChatOpenAI(**_llm_kwargs)
_llm_with_tools = _llm.bind_tools(TOOLS)


class _AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _call_model(state: _AgentState):
    resp = _llm_with_tools.invoke(state["messages"])
    return {"messages": [resp]}


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


# ── Intent classification (fast, single LLM call) ───────────────────────────

_fast = LLMClient.fast()
_creative = LLMClient.creative()


def _classify(question: str) -> str:
    logger.info("=== [classify] %r", question[:100])
    prompt = (
        "Reply with ONLY 'analytics' or 'conversational'.\n\n"
        "'analytics' if the message asks about data, metrics, trends, counts, "
        "comparisons, uploads, channels, clients, users, or anything needing "
        "a database query.\n\n"
        "'conversational' for greetings, small talk, how-to, thanks, or "
        "non-data questions.\n\n"
        f"Message: {question}\n\nOne word:"
    )
    raw = _fast.invoke(prompt, label="classify").content.lower()
    intent = "analytics" if raw.strip().startswith("analytics") else "conversational"
    logger.info("  -> %s", intent.upper())
    return intent


def _conversational_reply(question: str, memory: str = "") -> AgentResult:
    mem = f"\nConversation context:\n{memory}\n" if memory else ""
    prompt = (
        "You are Frammer AI, an analytics assistant for a media production platform.\n"
        f"{mem}\nUser: {question}\n\n"
        "Respond helpfully in markdown. Do NOT use <think> tags."
    )
    resp = _creative.invoke(prompt, label="chat")
    return AgentResult(
        intent="conversational",
        response=_clean(resp.content),
        actions=["Conversational response"],
    )


# ── Entry point ──────────────────────────────────────────────────────────────

async def run_agent(question: str, working_memory: str = "") -> AgentResult:
    """
    Run the ReAct agent.

    1. Classify intent (conversational → direct reply, analytics → tool loop).
    2. For analytics: build a LangGraph message list with system prompt and
       user question, then run the StateGraph loop until the LLM stops
       calling tools and produces a final answer.
    3. Extract chart_xml, chart_data, actions from per-request context.
    """

    intent = _classify(question)
    if intent == "conversational":
        return _conversational_reply(question, working_memory)

    ctx = _new_ctx()
    _ctx.set(ctx)

    memory_block = f"\n## Conversation Memory\n{working_memory}" if working_memory else ""
    system = SYSTEM_PROMPT.format(memory_block=memory_block)

    messages = [SystemMessage(content=system), HumanMessage(content=question)]

    try:
        logger.info("=== [react] Starting for: %r", question[:100])

        state = await _graph.ainvoke(
            {"messages": messages},
            config={"recursion_limit": 30},
        )

        response = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                response = _clean(msg.content)
                break

        if not response:
            response = "I analyzed your query but couldn't produce a summary. Try rephrasing."

        logger.info("=== Done. actions=%d chart=%s sql=%d chars",
                     len(ctx["actions"]), bool(ctx["chart_xml"]), len(ctx["sql"]))

        return AgentResult(
            intent="analytics",
            response=response,
            actions=ctx["actions"],
            chart_xml=ctx["chart_xml"],
            chart_data=ctx["chart_data"],
            sql=ctx["sql"],
        )

    except Exception as exc:
        err = str(exc)
        logger.error("=== Agent error: %s", err, exc_info=True)

        if "recursion" in err.lower() or "limit" in err.lower():
            return AgentResult(
                intent="analytics",
                response="I reached the maximum analysis steps. Here's what I found so far.",
                actions=ctx["actions"] + ["Reached step limit"],
                chart_xml=ctx["chart_xml"],
                chart_data=ctx["chart_data"],
                sql=ctx["sql"],
                error="Max iterations reached",
            )

        return AgentResult(
            intent="analytics",
            response=f"Sorry, an error occurred: {err}",
            actions=ctx["actions"],
            error=err,
        )


# ── CLI for testing ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def _cli():
        print("-- Frammer AI Agent CLI --\nType 'quit' to exit.\n")
        loop = asyncio.get_event_loop()
        while True:
            q = (await loop.run_in_executor(None, input, "You: ")).strip()
            if q.lower() == "quit":
                break
            if not q:
                continue
            r = await run_agent(q)
            print(f"\n[{r.intent}] {r.response}")
            if r.actions:
                print(f"  Actions: {r.actions}")
            print()

    asyncio.run(_cli())
