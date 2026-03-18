"""
agent.py
-------------
Frammer Analytics Agent.

Architecture:
  1. Client: Anthropic Claude 3 Haiku via client.py.
  2. Tools:  Loaded from the local MCP server (AgentToolModule).
  3. Loop:   LangGraph ReAct StateGraph.
"""

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict
import re

from dotenv import load_dotenv

# -- Load env: agent dir first, then project root --
_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.append(str(_AGENT_DIR))

load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

try:
    from logger_setup import setup_logging
except ImportError:
    from agent.logger_setup import setup_logging
setup_logging()

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import uuid as _uuid

try:
    from client import LLMClient
except ImportError:
    from agent.client import LLMClient

# -- Core MCP and Tools --
try:
    from mcp_server.config import ServerSettings
    from mcp_server.database import DatabaseClient, QueryValidationError
    from tools.metric_definitions import retrieve_metric_definitions
    from tools.chart import generate_plotly_chart
    from tools import get_frammer_schema, execute_sql_query, get_db
    from tools.sql_query import execute_exploration_queries
except ImportError:
    from agent.mcp_server.config import ServerSettings
    from agent.mcp_server.database import DatabaseClient, QueryValidationError
    from agent.tools.metric_definitions import retrieve_metric_definitions
    from agent.tools.chart import generate_plotly_chart
    from agent.tools import get_frammer_schema, execute_sql_query, get_db
    from agent.tools.sql_query import execute_exploration_queries

logger = logging.getLogger("frammer.agent")

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_OPEN_RE  = re.compile(r"<think>.*", re.DOTALL)   # unclosed think tag
_THINK_CLOSE    = "</think>"

def _clean(text: str) -> str:
    """Strip all <think>...</think> blocks and return the remainder."""
    return _THINK_BLOCK_RE.sub("", text).strip()

def _extract_response(text: str) -> str:
    """
    Extracts the final answer. Claude Haiku rarely uses <think> tags, but kept for compatibility.
    """
    if _THINK_CLOSE in text:
        after = text.split(_THINK_CLOSE, 1)[-1].strip()
        if after:
            return after
        match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return _THINK_OPEN_RE.sub("", text).strip() or text.strip()

# ── Per-request context ──────────────────────────────────────────────────────
from contextvars import ContextVar
_ctx: ContextVar[dict] = ContextVar("agent_ctx")

def _new_ctx(auth: Optional[Any] = None) -> dict:
    return {
        "sql": "", "records": [], "query_results": {}, "latest_result_id": "",
        "chart_xml": "", "chart_data": {}, "actions": [], "plan": "", "auth": auth
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
    raw = execute_sql_query(sql, limit=limit, auth=ctx.get("auth"))
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

@tool
def execute_exploration_queries_tool(json_queries: str) -> str:
    """Run multiple simple SELECTs in batch (e.g. check distinct values or min/max dates).
    Args:
        json_queries: A JSON array of string SQL queries.
    """
    import json as json_lib
    ctx = _get_ctx()
    try:
        queries = json_lib.loads(json_queries)
        if not isinstance(queries, list):
            return "Expected a JSON list of strings."
        results = []
        for q in queries:
            try:
                res = json_lib.loads(execute_sql_query(q, 5))
                if "error" in res:
                    results.append({"query": q, "error": res["error"]})
                else:
                    results.append({"query": q, "data": res.get("data", [])})
            except Exception as ex:
                results.append({"query": q, "error": str(ex)})
        ctx["actions"].append(f"Ran {len(queries)} exploration queries")
        return json.dumps(results, default=str)
    except Exception as e:
        return f"failed to parse json_queries: {e}"

@tool
def get_data_profile(result_id: str = "") -> str:
    """Returns descriptive statistics for a previously run query result.
    Use this to understand the distribution of large datasets (e.g. 10,000+ rows) without retrieving all rows.
    Includes: Count, Mean, Median, StdDev, Min/Max, and Top 5 unique values per column.
    Args:
        result_id: Optional result_id from a prior run_sql_query. Uses latest if empty.
    """
    import pandas as pd
    ctx = _get_ctx()
    records = (
        ctx["query_results"].get(result_id)
        if result_id
        else ctx.get("records", [])
    )
    if not records:
        return "No data available. Run a SQL query first."

    df = pd.DataFrame(records)
    
    # Basic numeric stats
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    profile = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "numeric_stats": df.describe().to_dict(),
        "top_values": {
            col: df[col].value_counts().head(5).to_dict()
            for col in df.columns
        }
    }
    
    ctx["actions"].append(f"Profiled data — {len(df)} rows")
    return json.dumps(profile, default=str, indent=2)

# ── LLM clients ──────────────────────────────────────────────────────────────
TOOLS = [get_schema, get_metric_definitions, search_relevant_schemas, execute_exploration_queries_tool, run_sql_query, build_chart, get_current_time, get_data_profile]

_fast_client  = LLMClient.fast()
_creat_client = LLMClient.creative()
_loop_client  = LLMClient()
_llm_with_tools = _loop_client.llm.bind_tools(TOOLS)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are Frammer AI, an analytics assistant for a media production platform.

## Database Schema
{schema_block}

## Business Metrics & Join Rules
{metrics_block}

## Dataset Overview
The dataset tracks a media content pipeline:
1. **Upload Phase** (`raw_videos`): Raw footage is uploaded. Each record has a `Language`, `Input_Type` (e.g., 'speech', 'interview'), and `Uploaded_Duration`.
2. **Processing Phase** (`created_assets`): AI-generated assets (clips, summaries, chapters) are created from raw videos. One video can produce multiple assets of different `Output_Type` values.
3. **Publication Phase** (`published_posts`): Assets are distributed to platforms. An asset is 'published' only if it appears in this table.
4. **Distribution context** (`post_distribution`): Tracks where a post was published (`Published_Platform`).
5. **Ownership context** (`raw_video_channel`, `users`, `channels`, `clients`): Videos are mapped to specific channels and users.

## Dataset Statistics
- **raw_videos**: ~10.7k rows. Track uploads by language and type.
- **created_assets**: ~53.7k rows. Track generation of clips/summaries.
- **published_posts**: ~1.3k rows. Track distribution to platforms.
- **Join Rule**: rv (Video) -> ca (Asset) -> pp (Post) -> pd (Platform).

## Tools
1. **execute_exploration_queries_tool** — Evaluate distinct categories or data availability early.
2. **run_sql_query** — Execute a PostgreSQL SELECT (retry on error).
3. **build_chart** — Visualise query results.

## Execution Plan
{plan_block}

## Workflow
1. Read the provided Schema and Metrics exactly as written.
2. run_sql_query → retrieve data (fix and retry on error).
3. build_chart → visualise.
4. Write a VERY CONCISE business markdown summary (MAX 2-3 SENTENCES). Do not over-explain.

## Shift-Left: Server-Side Aggregation
The most efficient way to handle large data is to ensure you never retrieve raw rows for large datasets.
- **Aggregation is Mandatory**: If a query is likely to return >100 rows, you MUST use `GROUP BY`, `SUM`, `AVG`, or `COUNT` in SQL.
- **Statistical Profiling**: For understanding the "shape" and distribution of a large result set without seeing all rows, ALWAYS call `get_data_profile`.

## Metric Recipes
Use these SQL patterns for complex calculations:
- **WoW Growth**: `(count_this_week::float - count_last_week) / NULLIF(count_last_week, 0)` using CTEs for each period.
- **Rolling 7-Day Average**: `AVG(count) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)`
- **Conversion Rate**: `COUNT(DISTINCT pp."Asset_ID")::float / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0)`
- **Retention**: Join `raw_videos` with itself on `User_ID` and `Upload_Date` intervals.

## Response Rules
- **Extreme Brevity**: Your final answer MUST be 2-3 sentences maximum. Get straight to the point. No fluff.
- **Data Integrity**: ONLY use numbers and facts present in the tool output. Never estimate or hallucinate values.
- **Sample Handling**: If `total_row_count` > provided `data` rows, explicitly state you are summarizing a sample.
- **Data Profiling**: Mention key statistics (mean, median, top values) from `get_data_profile` if you used it.
- **Chart Tool**: When calling `build_chart`, you MUST provide BOTH `x_column` and `y_columns` arguments. Never omit `y_columns`.
- **Formatting**: **Bold** key numbers and terms.
- **Privacy**: Never expose SQL or internal technical IDs to the user.
- **No Images**: Do NOT generate markdown image tags.
- **No Thinking**: Do NOT wrap final responses in <think> tags.

## Critical SQL Rules
- ALWAYS double-quote mixed-case column names: pp."Post_ID", rv."Input_Type", pd."Channel_Name"
- ALWAYS double-quote mixed-case table aliases too when referencing columns
- Keep SQL concise — avoid unnecessary subqueries
- Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')

## Common SQL Pitfalls (AVOID)
- **Join Error**: Joining `published_posts.Asset_ID` directly to `raw_videos.Video_ID`. Use `created_assets` (ca) as the bridge.
- **Cartesian Product**: Adding tables without an explicit `ON` join condition.
- **Case Error**: Querying `Input_Type = 'Interview'`. Use `lower("Input_Type") = 'interview'`.

## Join Integrity Safety Check
- Correct Chain: `raw_videos` (rv) -> `created_assets` (ca) -> `published_posts` (pp) -> `post_distribution` (pd)
{memory_block}"""

# ── LangGraph StateGraph ─────────────────────────────────────────────────────

class _AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def _call_model(state: _AgentState):
    msg_count = len(state["messages"])
    logger.info("--- LOOP ITER: Calling LLM (Context: %d messages) ---", msg_count)
    start = time.time()

    try:
        resp = _llm_with_tools.invoke(state["messages"])
        duration = time.time() - start
        
        usage = getattr(resp, "usage_metadata", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        logger.info(
            "--- LLM STEP DONE ---\n"
            "  Duration     : %.2fs\n"
            "  Input Tokens : %d\n"
            "  Output Tokens: %d\n"
            "  Total Tokens : %d\n"
            "  Response Raw : %s",
            duration, input_tokens, output_tokens, total_tokens, resp.content[:1000]
        )

        tool_count = len(getattr(resp, "tool_calls", []))
        if tool_count:
            for tc in resp.tool_calls:
                args_preview = json.dumps(tc.get("args", {}))
                logger.info("--- TOOL CALL: %s(%s) ---", tc.get("name", "?"), args_preview)
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

def _generate_plan(question: str, schema_text: str, metrics_text: str, intent_info: dict) -> str:
    """Fast LLM pass to generate a numbered execution plan before the ReAct loop."""
    logger.info("Planner: Building plan for %s", intent_info.get("sub_intent"))
    start = time.time()

    prompt = (
        "You are a data analytics planner. Given the user's question, database schema, and metric definitions, write a short numbered plan "
        "(max 5 steps) describing exactly which database tables to query, which joins to use, "
        "and what type of chart to generate. Be concise and precise — no explanation, just steps.\n\n"
        "## Perceived User Intent:\n"
        f"- Intent: {intent_info.get('intent')}\n"
        f"- Sub-Intent: {intent_info.get('sub_intent')}\n"
        f"- Reasoning: {intent_info.get('reasoning')}\n\n"
        f"Schema:\n{schema_text[:3000]}\n\n"
        f"Metric Rules:\n{metrics_text[:2000]}\n\n"
        f"Question: {question}\n\nPlan:"
    )
    try:
        resp = _fast_client.invoke(prompt, label="planner")
        plan = _clean(resp.content).strip()
        duration = time.time() - start
        logger.info("Planner: OK in %.2fs", duration)
        return plan
    except Exception as exc:
        logger.warning("Planner: Fail (%s)", exc)
        return ""

# ── Intent classifier ─────────────────────────────────────────────────────────

def _classify(message: str, memory: str = "") -> dict:
    """
    Enhanced intent classifier for Frammer AI.
    Returns a structured dictionary with intent, sub_intent, reasoning, and requirements.
    """
    logger.info("Classifying: %r", message[:80])
    mem_ctx = f"\nConversation History Summary:\n{memory}" if memory else "This is a new conversation."
    
    prompt = f"""\
You are the Intent Classification engine for Frammer AI. Analyze the user message and return a JSON object.

### Intent Categories:
1. **analytics**: Calculating metrics, identifying trends, performing joins.
2. **discovery**: Asking about system capabilities, definitions, or table structures.
3. **visualisation**: Explicit request for charts or graphs.
4. **conversational**: Greetings, thanks, small talk.
5. **assistance**: Troubleshooting or asking for help with queries.

### JSON Fields:
- `intent`: [analytics, discovery, visualisation, conversational, assistance]
- `sub_intent`: technical tag
- `confidence`: 0.0 to 1.0
- `reasoning`: one-sentence explanation
- `requires_sql`: boolean
- `requires_chart`: boolean

### Context:
{mem_ctx}
User Question: "{message}"

Return ONLY valid JSON.
"""
    try:
        resp = _fast_client.invoke(prompt, label="intent-classifier")
        content = resp.content
        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[-1].split("```")[0]
        data = json.loads(content.strip())
        
        valid_intents = ["analytics", "discovery", "visualisation", "conversational", "assistance"]
        if data.get("intent") not in valid_intents:
            data["intent"] = "analytics"
        data["flow"] = "conversational" if data["intent"] in ("conversational", "assistance") else "analytics"
        
        logger.info("Intent: %s | Flow: %s", data["intent"].upper(), data["flow"])
        return data
    except Exception as e:
        logger.error("Classification fail: %s. Fallback used.", e)
        is_chat = any(w in message.lower() for w in ["hi", "hello", "thanks", "hey", "bye", "how are you"])
        return {
            "intent": "conversational" if is_chat else "analytics",
            "flow": "conversational" if is_chat else "analytics",
            "sub_intent": "fallback",
            "confidence": 0.5,
            "reasoning": "Fallback used due to error",
            "requires_sql": not is_chat,
            "requires_chart": "chart" in message.lower()
        }

def _conversational_reply(question: str, memory: str = "", current_time: str = "") -> AgentResult:
    mem = f"\nConversation context:\n{memory}\n" if memory else ""
    time_ctx = f"\nCurrent System Time: {current_time}\n" if current_time else ""
    prompt = (
        "You are Frammer AI, a helpful analytics assistant.\n"
        f"{time_ctx}{mem}\nUser: {question}\n\nRespond in markdown. Be concise."
    )
    resp = _creat_client.invoke(prompt, label="chat")
    return AgentResult(intent="conversational", response=_extract_response(resp.content), actions=["Conversational reply"])

# ── Main entry point ──────────────────────────────────────────────────────────

async def run_agent(question: str, auth: Optional[Any] = None, working_memory: str = "") -> AgentResult:
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("--- AGENT START --- @ %s", now_str)

    ctx = _new_ctx(auth=auth)
    _ctx.set(ctx)

    try:
        # 1. Classification
        classification = _classify(question, working_memory)
        if classification["flow"] == "conversational":
            return _conversational_reply(question, working_memory, current_time=now_str)

        # 2. Context
        global _schema_cache
        if not _schema_cache:
            _schema_cache = get_frammer_schema()
            
        from tools.metric_definitions import METRIC_DICTIONARY, retrieve_metric_definitions
        all_metrics = "\n".join(f"- **{k}**: {v}" for k, v in METRIC_DICTIONARY.items())
        all_metrics += "\n\n" + retrieve_metric_definitions("XYZ_FAIL")

        # 3. Planning
        plan = _generate_plan(question, _schema_cache, all_metrics, intent_info=classification)
        ctx["plan"] = plan
        plan_block = f"## Recommended Execution Plan:\n{plan}" if plan else ""
        memory_block = f"\n## Conversation Memory\n{working_memory}" if working_memory else ""

        # 4. Prompt Assembly
        system = SYSTEM_PROMPT.replace("{schema_block}", _schema_cache or "")
        system = system.replace("{metrics_block}", all_metrics or "")
        system = system.replace("{plan_block}", plan_block or "")
        system = system.replace("{memory_block}", memory_block or "")
        
        system += f"\n\n## ASSISTANT GOAL\n- **Detected Intent**: {classification['intent']} ({classification['sub_intent']})"
        system += f"\n- **Reasoning**: {classification['reasoning']}"
        if classification.get("requires_chart"):
            system += "\n- **Note**: User requested a visual. Ensure `build_chart` is used."
        
        # 5. Client Scoping
        if auth:
            role = getattr(auth, "role", "user")
            username = getattr(auth, "username", "Unknown")
            client_name = getattr(auth, "client_name", None)
            user_id = getattr(auth, "user_id", None)
            
            scoping = f"\n\n## USER PROFILE\n- User: **{username}** | Role: **{role}**"
            if role != "website_admin":
                if client_name:
                    scoping += f"\n- RESTRICTION: Only client **{client_name}** data. Use: `COALESCE(ch.\"Client_Name\", u.\"Client_Name\") = '{client_name}'`"
                elif role == "user" and user_id:
                    scoping += f"\n- RESTRICTION: Only data for user ID **{user_id}**. Use: `rv.\"User_ID\" = {user_id}`"
            system += scoping

        system += f"\n\n## System Environment\nCurrent System Time: {now_str}\n"
        messages = [SystemMessage(content=system), HumanMessage(content=question)]

        # 6. ReAct Loop
        logger.info("=== ReAct Loop: START ===")
        start_react = time.time()
        state = await _graph.ainvoke({"messages": messages}, config={"recursion_limit": 30})

        response = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                response = _extract_response(msg.content)
                break
        if not response:
            response = "Agent loop finished without final answer."

        logger.info("=== AGENT COMPLETE (%.2fs) ===", time.time() - start_react)

        return AgentResult(
            intent=classification["intent"],
            response=response,
            actions=ctx["actions"],
            chart_xml=ctx["chart_xml"],
            chart_data=ctx["chart_data"],
            sql=ctx["sql"],
            plan=plan,
        )

    except Exception as exc:
        logger.error("!!! Agent Runtime Error: %s !!!", exc, exc_info=True)
        return AgentResult(
            intent="analytics",
            response=f"I'm sorry, an internal error occurred: {exc}",
            error=str(exc),
            actions=ctx.get("actions", []),
            plan=ctx.get("plan", "")
        )

if __name__ == "__main__":
    import asyncio
    async def _cli():
        print("-- Frammer AI --\n")
        while True:
            q = input("You: ").strip()
            if q.lower() in ("quit", "exit"): break
            if not q: continue
            r = await run_agent(q)
            print(f"\nPLAN:\n{r.plan}\n" if r.plan else "")
            print(f"RESPONSE:\n{r.response}\n")
            print(f"ACTIONS: {r.actions}\n")
    asyncio.run(_cli())
