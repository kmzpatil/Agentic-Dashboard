"""
agent.py
-------------
Frammer Analytics Agent — Unified ReAct Loop Architecture.

Architecture:
  The agent uses a tool-calling ReAct loop with six tools:
    1. execute_queries — Run SQL queries in parallel, results summarized and fed back.
    2. answer — Provide the final response (with optional chart specs).
    3. clarify — Ask the user a clarifying question mid-loop (pauses and resumes).
    4. get_column_values — Look up distinct values for a table column.
    5. get_kpi_info — Get KPI definition, formula, and SQL pattern.
    6. explore — Run lightweight exploration queries (max 5 rows each).

  Two modes:
    - normal: Standard analytics Q&A. Returns text + charts.
    - report: Data gathering + Gemini-powered report formatting → HTML report.

  The loop iterates until the agent calls answer/clarify, with a safety cap
  of MAX_ITERATIONS. SQL errors are implicitly repaired via the feedback loop.

  All database access routes through the MCP DatabaseClient (via execute_sql_query)
  which provides query validation, auth-scoped CTE injection, and connection management.
"""

import asyncio
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv

# -- Load env: agent dir first, then project root --
_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.append(str(_AGENT_DIR))

load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

try:
    from client import LLMClient
except ImportError:
    from agent.client import LLMClient

try:
    from prompts.report_prompt import (
        build_report_planning_prompt,
        build_report_synthesis_prompt,
    )
    from gemini_client import get_gemini_llm
except ImportError:
    from agent.prompts.report_prompt import (
        build_report_planning_prompt,
        build_report_synthesis_prompt,
    )
    from agent.gemini_client import get_gemini_llm

# -- Core MCP and Tools --
try:
    from mcp_server.config import ServerSettings
    from mcp_server.database import DatabaseClient, QueryValidationError
    from tools.metric_definitions import retrieve_metric_definitions, METRIC_DICTIONARY
    from tools.chart import generate_plotly_chart
    from tools import get_frammer_schema, execute_sql_query, get_db, get_custom_kpi_info
except ImportError:
    from agent.mcp_server.config import ServerSettings
    from agent.mcp_server.database import DatabaseClient, QueryValidationError
    from agent.tools.metric_definitions import retrieve_metric_definitions, METRIC_DICTIONARY
    from agent.tools.chart import generate_plotly_chart
    from agent.tools import get_frammer_schema, execute_sql_query, get_db, get_custom_kpi_info

logger = logging.getLogger("frammer.agent")

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_OPEN_RE = re.compile(r"<think>.*", re.DOTALL)
_THINK_CLOSE = "</think>"


def _clean(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text).strip()


def _extract_response(text: str) -> str:
    if _THINK_CLOSE in text:
        after = text.split(_THINK_CLOSE, 1)[-1].strip()
        if after:
            return after
        match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return _THINK_OPEN_RE.sub("", text).strip() or text.strip()


# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class ChartResult:
    chart_xml: str = ""
    data_records: List[Dict] = field(default_factory=list)
    sql: str = ""
    title: str = ""
    chart_type: str = ""
    size_column: str = ""
    group_column: str = ""


@dataclass
class AgentResult:
    intent: str = "analytics"
    response: str = ""
    actions: List[str] = field(default_factory=list)
    charts: List[ChartResult] = field(default_factory=list)
    sql: str = ""
    error: str = ""
    plan: str = ""
    # Legacy compat
    chart_xml: str = ""
    chart_data: Dict = field(default_factory=dict)
    # Report mode
    mode: str = "normal"
    report: Optional[Dict] = None
    # Clarification
    clarification: Optional[str] = None
    agent_state: Optional[Dict] = None


# ── Constants ────────────────────────────────────────────────────────────────

MAX_ITERATIONS = 10  # Safety cap — agent finishes naturally via answer/clarify

# ── Schema cache ─────────────────────────────────────────────────────────────
_schema_cache: Optional[str] = None

# ── LLM client ───────────────────────────────────────────────────────────────
_llm_client = LLMClient()


# ── Report Planning ──────────────────────────────────────────────────────────

async def _plan_report_sub_questions(
    question: str,
    schema: str,
    metrics: str,
    auth: Any = None,
) -> List[Dict]:
    """
    Decompose a report query into typed sub-questions using a fast LLM call.
    Uses the structured report planning prompt from prompts/report_prompt.py.
    """
    auth_block = _build_auth_block(auth) if auth else ""

    prompt = build_report_planning_prompt(
        question=question,
        schema_context=schema or "",
        metrics_context=metrics or "",
        auth_block=auth_block,
    )

    fast_client = LLMClient.fast()
    resp = await asyncio.to_thread(fast_client.call, prompt)

    # Parse JSON from response
    raw = resp.content.strip()
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\n?```\s*$', '', raw).strip()

    try:
        parsed = json.loads(raw)
        # Handle both formats: list of sub-questions or dict with sub_questions key
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "sub_questions" in parsed:
            return parsed["sub_questions"]
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse report sub-questions: %s", raw[:200])

    # Fallback: generic sub-questions
    return [
        {"id": "q1", "type": "trend", "question": f"What are the time trends for: {question}"},
        {"id": "q2", "type": "breakdown", "question": f"What is the breakdown by category for: {question}"},
        {"id": "q3", "type": "comparison", "question": f"How do different segments compare for: {question}"},
    ]


# ── Tool definitions (for LangChain bind_tools) ─────────────────────────────

from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@tool
def execute_queries(
    queries: Optional[List[Dict[str, str]]] = None,
    reasoning: str = "",
) -> str:
    """Execute SQL queries to gather data for answering the user's question.
    Args:
        queries: List of {"sql": "SELECT ...", "description": "what this computes"}.
                 All queries run in parallel. Use valid PostgreSQL SELECT statements.
        reasoning: Brief explanation of why you need this data.
    """
    return json.dumps({"status": "ok", "queries": queries or []})


@tool
def answer(
    response: str = "",
    needs_chart: bool = False,
    chart_intent: str = "",
    charts: Optional[List[Dict]] = None,
) -> str:
    """Provide the final answer to the user's question.
    Args:
        response: Markdown response (2-3 sentences, business language, bold key numbers).
                  Never expose SQL, table names, column names, or internal IDs.
        needs_chart: Whether the answer benefits from a chart visualization.
        chart_intent: If needs_chart, the broad intent: "comparison", "trend", "distribution", "proportion", "correlation".
        charts: If needs_chart, list of chart specs. Each: {
            "chart_type": "bar"|"line"|"pie"|"doughnut"|"scatter"|"horizontal-bar"|"stacked-bar"|"area"|"heatmap"|"treemap"|"box"|"violin"|"radar"|"bubble"|"polar-area",
            "source_query_index": 0,
            "x_column": "column_name",
            "y_columns": "col1,col2",
            "title": "Chart Title",
            "size_column": "",
            "group_column": ""
        }
    """
    return json.dumps({"status": "ok"})


@tool
def clarify(question: str = "") -> str:
    """Ask the user a clarifying question when the request is ambiguous.
    Args:
        question: The specific clarification question to ask the user.
                  Use this when the query is genuinely ambiguous between two+
                  interpretations, or when a filter value or time range is unclear.
    """
    return json.dumps({"status": "clarification_requested", "question": question})


@tool
def get_column_values_tool(
    table_name: str = "",
    column_name: str = "",
) -> str:
    """Look up distinct values for a column in the database schema profile.
    Args:
        table_name: The database table name (e.g. "raw_videos", "created_assets").
        column_name: The column to get distinct values for (e.g. "Language", "Input_Type").
    Use this BEFORE writing SQL when you need to know valid filter values.
    """
    return json.dumps({"status": "ok", "table_name": table_name, "column_name": column_name})


@tool
def get_kpi_info_tool(
    kpi_id: str = "",
) -> str:
    """Get the definition, formula, and SQL pattern for a specific business KPI.
    Args:
        kpi_id: The KPI identifier. Available: uploaded_count, processed_count,
                created_count, published_count, publish_conversion,
                month_by_month_use_rate, processing_efficiency, creation_rate,
                waste_index, upload_failure_rate, roi, cdas, interaction_lift,
                cross_dimension_entropy, publish_dependency_index, point_biserial,
                multidimensional_waste, ctas, rei.
    """
    return json.dumps({"status": "ok", "kpi_id": kpi_id})


@tool
def explore_tool(
    queries: Optional[List[str]] = None,
    reasoning: str = "",
) -> str:
    """Run lightweight exploration queries (e.g. DISTINCT values, MIN/MAX, sample rows).
    Args:
        queries: List of simple SQL strings for exploration. Each returns max 5 rows.
        reasoning: Why you need this exploration.
    Use this for quick schema/data discovery before writing full analytical queries.
    """
    return json.dumps({"status": "ok", "queries": queries or []})


# ── Unified System Prompt ────────────────────────────────────────────────────

AGENT_PROMPT = """\
You are Frammer AI, an analytics agent for a media production platform.
You answer questions by querying a PostgreSQL database and synthesizing results.

## How to Work

You have six tools:
1. `execute_queries` — Run SQL queries to gather data. All queries execute in parallel.
2. `answer` — Provide your final response when you have enough information.
3. `clarify` — Ask the user a clarifying question when the request is genuinely ambiguous.
4. `get_column_values_tool` — Look up distinct values for a column. Use before writing SQL when unsure about filter values.
5. `get_kpi_info_tool` — Get the definition, formula, and SQL pattern for a business KPI.
6. `explore_tool` — Run lightweight exploration queries (DISTINCT values, MIN/MAX, sample rows). Max 5 rows each.

**Process:**
- First, decide if this is conversational (greeting, thanks, small talk) → call `answer` directly with a brief reply.
- For data questions: call `execute_queries` with the SQL you need. Pack as many queries as you can into each call — they run in parallel.
- You'll receive a summary of results (columns, row counts, sample rows, numeric stats).
- If the data is sufficient to answer the question, call `answer`.
- If you need more data (e.g. a follow-up query based on initial results, or a query failed and needs fixing), call `execute_queries` again.
- You may iterate up to {max_iterations} times. Make each iteration count.

**Efficiency rules:**
- Check "Previous Query Results" before every iteration. If data is already there, use it — do NOT re-fetch.
- Never repeat a query whose results already appear in Previous Query Results.
- For broad questions, gather all the data you need in one or two batches, then call `answer`.

**When to use `get_column_values_tool`:**
- You need to filter by a specific value but aren't sure what values exist.
- Example: before filtering by language, check what languages are in the data.

**When to use `get_kpi_info_tool`:**
- The user asks about a specific KPI (e.g. "waste index", "publish conversion").
- You need the exact formula or SQL pattern for a KPI calculation.

**When to use `explore_tool`:**
- Quick data discovery (e.g. "SELECT DISTINCT ..." or "SELECT MIN/MAX ...").
- Checking if a join path works before writing a complex query.

**When to use `clarify`:**
- The question could refer to multiple different metrics, entities, or time periods.
- A filter value is ambiguous (e.g. "recent" without a clear timeframe).
- The user's intent is genuinely unclear between two+ interpretations.
- Do NOT use clarify for simple questions. Most queries (99%+) should proceed without clarification.

## Database Schema
{schema_block}

## Business Metrics & Join Rules
{metrics_block}

## Dataset Overview
The dataset tracks a media content pipeline:
1. **Upload Phase** (`raw_videos`): Raw footage is uploaded. Each record has a `Language`, `Input_Type`, and `Uploaded_Duration`.
2. **Processing Phase** (`created_assets`): AI-generated assets (clips, summaries, chapters). One video → multiple assets of different `Output_Type`.
3. **Publication Phase** (`published_posts`): Assets distributed to platforms. An asset is 'published' only if it appears here.
4. **Distribution** (`post_distribution`): Where a post was published (`Published_Platform`).
5. **Ownership** (`raw_video_channel`, `users`, `channels`, `clients`): Videos mapped to channels and users.

## Dataset Statistics
- **raw_videos**: ~10.7k rows  |  **created_assets**: ~53.7k rows  |  **published_posts**: ~1.3k rows

## Critical SQL Rules
- ALWAYS double-quote mixed-case column names: pp."Post_ID", rv."Input_Type"
- Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')
- Monthly grouping: date_trunc('month', to_date("Upload_Date",'YYYY-MM-DD'))::date AS month
- Join chain: raw_videos (rv) -> created_assets (ca) -> published_posts (pp) -> post_distribution (pd)
- For conversion rates: group by channel/user through rv/rvc, NOT through post_distribution
- Count published volume with COUNT(DISTINCT pp."Asset_ID"), not Post_ID
- NEVER guess filter values. If uncertain, use `get_column_values_tool` or `explore_tool` first.
- If >100 rows expected, use GROUP BY / aggregations in SQL

## Custom KPIs
The following specialized business KPIs are available. Use `get_kpi_info_tool` to get the exact formula and SQL pattern.
Available IDs: uploaded_count, processed_count, created_count, published_count, publish_conversion, month_by_month_use_rate, processing_efficiency, creation_rate, waste_index, upload_failure_rate, roi, cdas, interaction_lift, cross_dimension_entropy, publish_dependency_index, point_biserial, multidimensional_waste, ctas, rei

## Chart Type Selection Guide

Pick the chart type that best matches the DATA SHAPE and ANALYTICAL INTENT:

**Comparison**: `bar` (≤15 categories), `stacked-bar` (composition + total), `horizontal-bar` (ranking/long labels)
**Trend**: `line` (change over time, x-axis must be date), `area` (stacked composition over time)
**Proportion**: `pie`/`doughnut` (≤6 categories, 1 metric), `polar-area` (4-8 categories)
**Distribution**: `box`/`violin` (SQL must return category, min_val, q1, median, q3, max_val)
**Correlation**: `scatter` (two numeric vars, use group_column for color), `bubble` (add size_column)
**Multi-dimensional**: `radar` (4-8 metrics, ≤5 entities), `heatmap` (x_dim, y_dim, value columns)
**Hierarchical**: `treemap` (label, value, optional group)

When specifying charts in `answer`, reference queries by their 0-based index in the order they were executed across ALL iterations.
{auth_block}
{memory_block}

## Previous Query Results
{results_context}

## Rules for Answering
- **Extreme brevity**: 2-3 sentences max for simple questions. For broad questions, up to a short paragraph with key findings.
- **Data integrity**: ONLY use numbers from the results. Never estimate or hallucinate.
- **Business language**: uploads (not raw_videos), generated content/assets (not created_assets), published content (not published_posts), content format (not Input_Type), asset type (not Output_Type).
- **Never expose**: SQL, table names, column names, internal IDs, or schema details.
- **Bold** key numbers and terms. Use markdown.
- If results show trends or comparisons, highlight the most important finding.
- **NEVER generate HTML**. Your response must be plain text with markdown formatting only. No `<div>`, `<style>`, `<html>`, or any HTML tags.
- If the user asks for a "report", still answer in concise markdown. Full formatted reports are generated separately via report mode.

Current System Time: {now_str}
"""

SYNTHESIZER_PROMPT = """\
You are Frammer AI. Summarize the analysis results below into a clear, concise response.

## Rules
- **Extreme Brevity**: 2-3 sentences max. No fluff.
- **Data Integrity**: ONLY use numbers from the results. Never estimate or hallucinate.
- **Formatting**: **Bold** key numbers and terms. Use markdown.
- **Privacy**: Never expose SQL, internal IDs, database table names, column names, or any technical schema details.
- **Business Language**: Always translate technical terms to business language — uploads (not raw_videos), generated content/assets (not created_assets), published content (not published_posts), content format (not Input_Type), asset type (not Output_Type).
- **No Images**: Do NOT generate markdown image tags.

## User Question
{question}

## Analysis Results
{results_block}
"""


# ── Auth block builder ───────────────────────────────────────────────────────

def _build_auth_block(auth: Any = None) -> str:
    if not auth:
        return ""
    role = getattr(auth, "role", "user")
    username = getattr(auth, "username", "Unknown")
    client_name = getattr(auth, "client_name", None)
    user_id = getattr(auth, "user_id", None)

    block = f"\n## USER PROFILE\n- User: **{username}** | Role: **{role}**"
    if role != "website_admin":
        if client_name:
            block += f"\n- RESTRICTION: Only client **{client_name}** data. Use: `COALESCE(ch.\"Client_Name\", u.\"Client_Name\") = '{client_name}'`"
        elif role == "user" and user_id:
            block += f"\n- RESTRICTION: Only data for user ID **{user_id}**. Use: `rv.\"User_ID\" = {user_id}`"
    return block


# ── SQL Step Executor ────────────────────────────────────────────────────────

async def _execute_sql_step(params: Dict, auth: Any = None) -> Dict:
    """Execute a SQL query step via MCP DatabaseClient."""
    sql = params.get("sql", "")
    raw = await asyncio.to_thread(execute_sql_query, sql, limit=200, auth=auth)
    parsed = json.loads(raw)

    if "error" in parsed:
        return {"status": "error", "error": parsed["error"], "sql": sql}

    records = parsed.get("data", [])
    cols = list(records[0].keys()) if records else []

    return {
        "status": "success",
        "row_count": len(records),
        "columns": cols,
        "data": records,
        "sql": sql,
        "sample": records[:30],
    }


# ── Result Summarizer ────────────────────────────────────────────────────────

def _summarize_query_results(query_results: List[Dict]) -> str:
    """Build a compact summary of query results for the LLM context."""
    if not query_results:
        return "No queries executed yet."

    parts = []
    for i, qr in enumerate(query_results):
        desc = qr.get("description", f"Query {i}")
        if qr.get("status") == "success":
            cols = qr.get("columns", [])
            row_count = qr.get("row_count", 0)
            sample = qr.get("data", [])[:5]  # First 5 rows only

            # Compute basic numeric stats for richer context
            stats = {}
            for col in cols:
                values = [r.get(col) for r in qr.get("data", []) if isinstance(r.get(col), (int, float))]
                if values:
                    stats[col] = {"min": min(values), "max": max(values), "sum": round(sum(values), 2)}

            part = (
                f"### Query {i} — {desc}\n"
                f"Status: SUCCESS | Rows: {row_count} | Columns: {cols}\n"
                f"Sample (first 5 rows):\n```json\n{json.dumps(sample, default=str, indent=1)}\n```"
            )
            if stats:
                part += f"\nNumeric summaries: {json.dumps(stats, default=str)}"
            parts.append(part)
        else:
            error = qr.get("error", "Unknown error")
            sql = qr.get("sql", "")
            parts.append(
                f"### Query {i} — {desc}\n"
                f"Status: ERROR\n"
                f"Error: {error}\n"
                f"SQL attempted: {sql}"
            )

    return "\n\n".join(parts)


# ── Force Synthesize (fallback when max iterations reached) ──────────────────

async def _force_synthesize(question: str, query_results: List[Dict]) -> str:
    """Emergency synthesis when the agent hits max iterations without answering."""
    results_block = _summarize_query_results(query_results)
    prompt = SYNTHESIZER_PROMPT.format(question=question, results_block=results_block)
    resp = await asyncio.to_thread(_llm_client.llm.invoke, prompt)
    return _extract_response(resp.content)


# ── Chart Generation Helper ─────────────────────────────────────────────────

async def _generate_charts_from_specs(
    chart_specs: List[Dict],
    all_full_data: List[Dict],
) -> List[ChartResult]:
    """Generate ChartResult objects from answer tool chart specs."""
    charts = []
    for spec in chart_specs:
        source_idx = spec.get("source_query_index", 0)
        if source_idx < len(all_full_data) and all_full_data[source_idx].get("status") == "success":
            source_data = all_full_data[source_idx]
            records = source_data.get("data", [])
            attrs = {
                "type": spec.get("chart_type", "bar"),
                "x_axis": spec.get("x_column", ""),
                "y_axis": spec.get("y_columns", ""),
                "title": spec.get("title", "Chart"),
            }
            if spec.get("size_column"):
                attrs["size_field"] = spec["size_column"]
            if spec.get("group_column"):
                attrs["group_field"] = spec["group_column"]

            xml = await asyncio.to_thread(
                generate_plotly_chart, data_records=records, chart_attributes=attrs
            )
            if xml and xml.startswith("<?xml"):
                charts.append(ChartResult(
                    chart_xml=xml,
                    data_records=records,
                    sql=source_data.get("sql", ""),
                    title=spec.get("title", "Chart"),
                    chart_type=spec.get("chart_type", "bar"),
                    size_column=spec.get("size_column", ""),
                    group_column=spec.get("group_column", ""),
                ))
    return charts


# ── Core ReAct Loop Logic ────────────────────────────────────────────────────

ALL_TOOLS = [execute_queries, answer, clarify, get_column_values_tool, get_kpi_info_tool, explore_tool]


def _build_system_prompt(
    schema: str,
    metrics: str,
    auth: Any,
    working_memory: str,
    query_results: List[Dict],
) -> str:
    """Build the full system prompt with current state."""
    return AGENT_PROMPT.format(
        schema_block=schema or "",
        metrics_block=metrics or "",
        auth_block=_build_auth_block(auth),
        memory_block=f"\n## Conversation Memory\n{working_memory}" if working_memory else "",
        results_context=_summarize_query_results(query_results),
        now_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        max_iterations=MAX_ITERATIONS,
    )


def _build_messages(
    system: str,
    question: str,
    history: Optional[List[Dict]] = None,
) -> List:
    """Build the message list for the LLM call."""
    messages = [SystemMessage(content=system)]
    for msg in (history or [])[-4:]:
        role = msg.get("role", "")
        content = msg.get("content", "") or ""
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=question))
    return messages


def _load_schema_and_metrics() -> tuple:
    """Load and cache schema + metrics."""
    global _schema_cache
    if not _schema_cache:
        _schema_cache = get_frammer_schema()
    all_metrics = "\n".join(f"- **{k}**: {v}" for k, v in METRIC_DICTIONARY.items())
    all_metrics += "\n\n" + retrieve_metric_definitions("XYZ_FAIL")
    return _schema_cache, all_metrics


async def _execute_query_batch(
    queries: List[Dict[str, str]],
    auth: Any = None,
) -> List[Dict]:
    """Execute a batch of SQL queries in parallel via MCP DatabaseClient."""
    async def _run_one(q: Dict) -> Dict:
        sql = q.get("sql", "")
        desc = q.get("description", "")
        result = await _execute_sql_step({"sql": sql}, auth=auth)
        result["description"] = desc
        return result

    raw_results = await asyncio.gather(
        *[_run_one(q) for q in queries],
        return_exceptions=True,
    )

    results = []
    for i, result in enumerate(raw_results):
        if isinstance(result, Exception):
            result = {
                "status": "error",
                "error": str(result),
                "sql": queries[i].get("sql", ""),
                "description": queries[i].get("description", ""),
            }
        results.append(result)
    return results


# ── Tool Handlers ────────────────────────────────────────────────────────────

async def _handle_get_column_values(args: Dict) -> Dict:
    """Handle get_column_values_tool call — look up distinct values from schema profile."""
    table = args.get("table_name", "")
    column = args.get("column_name", "")
    try:
        db = get_db()
        profile = db.get_schema_profile()
        col_info = profile.get(table, {}).get(column, {})
        values = col_info.get("values")
        if values is None:
            return {
                "status": "success",
                "description": f"Distinct values for {table}.{column}",
                "data": [{"note": "Column not in profile (high-cardinality or non-text). Try a SELECT DISTINCT query instead."}],
                "row_count": 0,
                "columns": ["note"],
            }
        return {
            "status": "success",
            "description": f"Distinct values for {table}.{column}",
            "data": [{"table": table, "column": column, "values": values}],
            "row_count": len(values) if isinstance(values, list) else 1,
            "columns": ["table", "column", "values"],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": f"Distinct values for {table}.{column}",
        }


async def _handle_get_kpi_info(args: Dict) -> Dict:
    """Handle get_kpi_info_tool call — look up KPI definition and formula."""
    kpi_id = args.get("kpi_id", "")
    try:
        kpi_raw = get_custom_kpi_info(kpi_id)
        kpi_data = json.loads(kpi_raw)
        return {
            "status": "success",
            "description": f"KPI info: {kpi_id}",
            "data": [kpi_data] if isinstance(kpi_data, dict) else kpi_data,
            "row_count": 1,
            "columns": list(kpi_data.keys()) if isinstance(kpi_data, dict) else ["id", "title"],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "description": f"KPI info: {kpi_id}",
        }


async def _handle_explore(args: Dict, auth: Any = None) -> Dict:
    """Handle explore_tool call — run lightweight exploration queries."""
    queries = args.get("queries", [])
    reasoning = args.get("reasoning", "")
    explorations = []
    for q in queries:
        try:
            raw = await asyncio.to_thread(execute_sql_query, q, limit=5, auth=auth)
            parsed = json.loads(raw)
            if "error" in parsed:
                explorations.append({"query": q, "error": parsed["error"]})
            else:
                explorations.append({"query": q, "data": parsed.get("data", [])})
        except Exception as e:
            explorations.append({"query": q, "error": str(e)})
    return {
        "status": "success",
        "description": f"Exploration: {reasoning[:60]}",
        "data": explorations,
        "row_count": len(explorations),
        "columns": ["query", "data"],
    }


# ── Report Synthesis (Gemini) ────────────────────────────────────────────────

async def _synthesize_report(question: str, all_query_results: List[Dict]) -> str:
    """
    Format accumulated query results into an HTML report via Gemini.
    Falls back to Anthropic if Gemini is unavailable.
    Returns the HTML string directly.
    """
    results_parts = []
    for i, qr in enumerate(all_query_results):
        desc = qr.get("description", f"Query {i}")
        sq_type = qr.get("type", "breakdown")

        if qr.get("status") == "success":
            sample = qr.get("sample", qr.get("data", []))[:30]
            cols = qr.get("columns", [])
            results_parts.append(
                f"### Query {i} ({sq_type}): {desc}\n"
                f"Status: SUCCESS | Rows: {qr.get('row_count', 0)} | Columns: {cols}\n"
                f"Data:\n```json\n{json.dumps(sample, default=str, indent=1)}\n```"
            )
        else:
            results_parts.append(
                f"### Query {i} ({sq_type}): {desc}\n"
                f"Status: FAILED — {qr.get('error', 'Unknown error')[:200]}"
            )

    results_block = "\n\n".join(results_parts) if results_parts else "No data was retrieved."

    prompt = build_report_synthesis_prompt(
        question=question,
        results_block=results_block,
    )

    # Use Gemini for report synthesis, fall back to Anthropic
    gemini = get_gemini_llm()
    llm_label = "Gemini" if gemini else "Anthropic (fallback)"
    llm_to_use = gemini or _llm_client.llm

    logger.info("=== REPORT SYNTHESIZER: Calling %s ===", llm_label)
    start = time.time()
    resp = await asyncio.to_thread(llm_to_use.invoke, prompt)
    duration = time.time() - start

    usage = getattr(resp, "usage_metadata", {})
    logger.info(
        "=== REPORT SYNTHESIZER DONE (%s, %.2fs) — %d input, %d output tokens ===",
        llm_label, duration,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )

    content = _extract_response(resp.content)

    # Strip markdown code fences if the LLM wrapped the HTML
    content = re.sub(r"^```(?:html)?\s*\n?", "", content.strip(), flags=re.IGNORECASE)
    content = re.sub(r"\n?```\s*$", "", content).strip()

    # Ensure we have the report div
    if '<div class="report">' not in content:
        match = re.search(r'(<div class="report">.*</div>)\s*$', content, re.DOTALL)
        if match:
            content = match.group(1)

    return content


# ── Main Entry Point ─────────────────────────────────────────────────────────

async def run_agent(
    question: str,
    auth: Optional[Any] = None,
    working_memory: str = "",
    history: Optional[List[Dict]] = None,
    mode: str = "normal",
    agent_state: Optional[Dict] = None,
    report_mode: bool = False,
) -> AgentResult:
    """
    Main agent entry point. Runs the ReAct loop:
      LLM(decide) → execute_queries | answer | clarify | explore | ... → repeat or exit.

    Modes:
      - "normal": Standard analytics Q&A → text + charts.
      - "report": Data gathering → Gemini report formatting → HTML report.

    If agent_state is provided, resumes from a prior clarification pause.
    report_mode is a legacy param — use mode="report" instead.
    """
    if report_mode:
        mode = "report"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=== AGENT START (mode=%s) === @ %s", mode, now_str)
    overall_start = time.time()

    # Initialize actions_log before try block for safe access in except
    actions_log: List[str] = []

    # Restore state if resuming from clarification
    if agent_state:
        all_query_results = agent_state.get("query_results", [])
        all_full_data = agent_state.get("full_data", [])
        actions_log = agent_state.get("actions_log", [])
        last_sql = agent_state.get("last_sql", "")
        start_iter = agent_state.get("iteration", 0) + 1
        logger.info("=== RESUMING from iteration %d with %d prior results ===", start_iter, len(all_query_results))
    else:
        all_query_results: List[Dict] = []
        all_full_data: List[Dict] = []
        last_sql = ""
        start_iter = 0

    try:
        # 1. Load schema + metrics
        schema, metrics = _load_schema_and_metrics()

        # 2. Build LLM with tools
        agent_llm = _llm_client.llm.bind_tools(ALL_TOOLS)

        # 2b. Report planning phase
        report_sub_questions: List[Dict] = []
        if mode == "report" and not agent_state:
            try:
                report_sub_questions = await _plan_report_sub_questions(
                    question, schema, metrics, auth
                )
                actions_log.append(f"Planned {len(report_sub_questions)} sub-questions")
            except Exception as plan_err:
                logger.warning("Report planning failed: %s", plan_err)

        # 3. ReAct loop
        answer_text = ""
        answer_charts: List[ChartResult] = []

        for iteration in range(start_iter, MAX_ITERATIONS):
            system = _build_system_prompt(schema, metrics, auth, working_memory, all_query_results)
            if mode == "report":
                sq_text = "\n".join(
                    f"  {sq['id']}. [{sq['type'].upper()}] {sq['question']}"
                    for sq in report_sub_questions
                ) if report_sub_questions else ""
                system += "\n\n## Mode: REPORT"
                system += "\nYou are gathering data for a comprehensive analytical report. A separate system will format the final report — you do NOT need to format anything."
                system += "\nGather data by executing queries for the sub-questions below. Query multiple angles, breakdowns, and comparisons to ensure thorough coverage."
                system += "\nOnce you have data covering the sub-questions, call `answer` with a brief text summary of what you found. Do NOT generate HTML."
                system += "\nIf a query fails, fix it and retry. If you need a follow-up query based on results, go ahead."
                system += "\nCheck Previous Query Results — do not re-run queries whose data is already there."
                if sq_text:
                    system += f"\n\n## Report Sub-Questions to Investigate\n{sq_text}\nAddress these systematically with your queries."
            messages = _build_messages(system, question, history)

            logger.info("=== ITERATION %d: Calling LLM (%d messages) ===", iteration + 1, len(messages))
            actions_log.append(f"Thinking (round {iteration + 1})...")
            start = time.time()
            resp = await asyncio.to_thread(agent_llm.invoke, messages)
            duration = time.time() - start

            usage = getattr(resp, "usage_metadata", {})
            logger.info(
                "=== ITERATION %d DONE (%.2fs) — %d input, %d output tokens ===",
                iteration + 1, duration,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )

            # Extract tool call
            tool_calls = getattr(resp, "tool_calls", [])
            if not tool_calls:
                if mode == "report":
                    logger.info("=== REPORT MODE: No tool call, treating as answer ===")
                    answer_text = _extract_response(resp.content)
                    actions_log.append("Answering (from context)")
                    break
                else:
                    # No tool call = conversational response
                    logger.info("=== AGENT COMPLETE (conversational, %.2fs) ===", time.time() - overall_start)
                    return AgentResult(
                        intent="conversational",
                        response=_extract_response(resp.content),
                        actions=actions_log,
                    )

            tc = tool_calls[0]
            tool_name = tc.get("name", "")
            args = tc.get("args", {})

            # ── EXECUTE QUERIES ──
            if tool_name == "execute_queries":
                queries = args.get("queries", [])
                reasoning = args.get("reasoning", "")
                actions_log.append(f"Executing {len(queries)} queries — {reasoning[:80]}")
                logger.info("=== EXECUTING %d QUERIES — %s ===", len(queries), reasoning[:80])

                batch_results = await _execute_query_batch(queries, auth=auth)

                for result in batch_results:
                    all_query_results.append(result)
                    all_full_data.append(result)

                    if result.get("status") == "success":
                        last_sql = result.get("sql", "")
                        actions_log.append(
                            f"SQL OK — {result.get('row_count', 0)} rows ({result.get('description', '')})"
                        )
                    else:
                        actions_log.append(
                            f"SQL Error — {result.get('error', '')[:60]}"
                        )

                continue  # Next iteration

            # ── CLARIFY ──
            elif tool_name == "clarify":
                clarify_q = args.get("question", "Could you clarify your question?")
                actions_log.append(f"Clarification: {clarify_q}")
                logger.info("=== AGENT PAUSED FOR CLARIFICATION ===")

                return AgentResult(
                    intent="clarification",
                    response=clarify_q,
                    actions=actions_log,
                    sql=last_sql,
                    mode=mode,
                    clarification=clarify_q,
                    agent_state={
                        "query_results": all_query_results,
                        "full_data": all_full_data,
                        "actions_log": actions_log,
                        "last_sql": last_sql,
                        "iteration": iteration,
                    },
                )

            # ── ANSWER ──
            elif tool_name == "answer":
                answer_text = args.get("response", "")
                needs_chart = args.get("needs_chart", False)
                chart_specs = args.get("charts", []) or []
                actions_log.append("Answering")

                # Generate charts if requested (normal mode only — report mode uses Gemini)
                if needs_chart and chart_specs and mode == "normal":
                    answer_charts = await _generate_charts_from_specs(chart_specs, all_full_data)
                    if answer_charts:
                        actions_log.append(f"Generated {len(answer_charts)} chart(s)")

                break  # Exit loop — answer or report formatting follows

            # ── GET COLUMN VALUES ──
            elif tool_name == "get_column_values_tool":
                table = args.get("table_name", "")
                column = args.get("column_name", "")
                actions_log.append(f"Looking up values for {table}.{column}")
                result = await _handle_get_column_values(args)
                all_query_results.append(result)
                all_full_data.append(result)
                continue

            # ── GET KPI INFO ──
            elif tool_name == "get_kpi_info_tool":
                kpi_id = args.get("kpi_id", "")
                actions_log.append(f"Looking up KPI: {kpi_id}")
                result = await _handle_get_kpi_info(args)
                all_query_results.append(result)
                all_full_data.append(result)
                continue

            # ── EXPLORE ──
            elif tool_name == "explore_tool":
                reasoning = args.get("reasoning", "")
                queries = args.get("queries", [])
                actions_log.append(f"Exploring ({len(queries)} queries) — {reasoning[:60]}")
                result = await _handle_explore(args, auth=auth)
                all_query_results.append(result)
                all_full_data.append(result)
                continue

        else:
            # Max iterations reached — force synthesis
            logger.warning("=== MAX ITERATIONS REACHED — forcing synthesis ===")
            actions_log.append("Max iterations reached — synthesizing from available data")
            answer_text = await _force_synthesize(question, all_query_results)

        # ── POST-LOOP: mode branching ──
        total_time = time.time() - overall_start

        if mode == "report":
            # Format as report via Gemini — returns HTML directly
            actions_log.append("Formatting report with Gemini...")
            report_html = await _synthesize_report(question, all_query_results)
            logger.info("=== AGENT COMPLETE (report, %.2fs) ===", total_time)

            return AgentResult(
                intent="report",
                mode="report",
                response=report_html,
                actions=actions_log,
                sql=last_sql,
            )
        else:
            # Normal mode — return text + charts
            logger.info("=== AGENT COMPLETE (%.2fs) ===", total_time)

            return AgentResult(
                response=answer_text,
                actions=actions_log,
                charts=answer_charts,
                sql=last_sql,
                chart_xml=answer_charts[0].chart_xml if answer_charts else "",
                chart_data={"query_result": all_full_data[-1].get("data", [])} if all_full_data else {},
            )

    except Exception as exc:
        logger.error("!!! Agent Runtime Error: %s !!!", exc, exc_info=True)
        return AgentResult(
            response=f"I'm sorry, an internal error occurred: {exc}",
            error=str(exc),
            actions=actions_log,
        )


# ── Streaming Entry Point ───────────────────────────────────────────────────

async def run_agent_stream(
    question: str,
    auth: Optional[Any] = None,
    working_memory: str = "",
    history: Optional[List[Dict]] = None,
    mode: str = "normal",
    agent_state: Optional[Dict] = None,
    report_mode: bool = False,
) -> AsyncGenerator[Dict, None]:
    """
    Streaming version of run_agent. Yields SSE events as the agent progresses.
    Supports mode="report" and agent_state for clarification resumption.
    report_mode is a legacy param — use mode="report" instead.
    """
    if report_mode:
        mode = "report"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=== AGENT STREAM START (mode=%s) === @ %s", mode, now_str)
    overall_start = time.time()

    try:
        # 1. Load schema + metrics
        schema, metrics = _load_schema_and_metrics()

        # 2. Build LLM with tools
        agent_llm = _llm_client.llm.bind_tools(ALL_TOOLS)

        # 3. State — restore if resuming from clarification
        if agent_state:
            all_query_results = agent_state.get("query_results", [])
            all_full_data = agent_state.get("full_data", [])
            actions_log = agent_state.get("actions_log", [])
            last_sql = agent_state.get("last_sql", "")
            start_iter = agent_state.get("iteration", 0) + 1
            logger.info("=== RESUMING from iteration %d ===", start_iter)
        else:
            all_query_results: List[Dict] = []
            all_full_data: List[Dict] = []
            actions_log: List[str] = []
            last_sql = ""
            start_iter = 0

        answer_text = ""
        answer_charts_data = []
        report_sub_questions: List[Dict] = []

        # 3b. Report planning phase — decompose into typed sub-questions
        if mode == "report" and not agent_state:
            yield {"type": "phase", "phase": "planning report"}
            try:
                report_sub_questions = await _plan_report_sub_questions(
                    question, schema, metrics, auth
                )
                actions_log.append(f"Planned {len(report_sub_questions)} sub-questions")
                yield {
                    "type": "report_plan",
                    "sub_questions": report_sub_questions,
                }
            except Exception as plan_err:
                logger.warning("Report planning failed, continuing without plan: %s", plan_err)

        # 4. ReAct loop
        report_step_idx = 0  # Track which sub-question we're on
        for iteration in range(start_iter, MAX_ITERATIONS):
            # Yield thinking phase
            phase_label = "thinking" if iteration == 0 else f"thinking (round {iteration + 1})"
            if agent_state and iteration == start_iter:
                phase_label = "thinking (continued)"
            yield {"type": "phase", "phase": phase_label}

            system = _build_system_prompt(schema, metrics, auth, working_memory, all_query_results)
            if mode == "report":
                sq_text = "\n".join(
                    f"  {sq['id']}. [{sq['type'].upper()}] {sq['question']}"
                    for sq in report_sub_questions
                ) if report_sub_questions else ""
                system += "\n\n## Mode: REPORT"
                system += "\nYou are gathering data for a comprehensive analytical report. A separate system will format the final report — you do NOT need to format anything."
                system += "\nGather data by executing queries for the sub-questions below. Query multiple angles, breakdowns, and comparisons to ensure thorough coverage."
                system += "\nOnce you have data covering the sub-questions, call `answer` with a brief text summary of what you found. Do NOT generate HTML."
                system += "\nIf a query fails, fix it and retry. If you need a follow-up query based on results, go ahead."
                system += "\nCheck Previous Query Results — do not re-run queries whose data is already there."
                if sq_text:
                    system += f"\n\n## Report Sub-Questions to Investigate\n{sq_text}\nAddress these systematically with your queries."
            messages = _build_messages(system, question, history)

            logger.info("=== STREAM ITERATION %d: Calling LLM ===", iteration + 1)
            actions_log.append(f"Thinking (round {iteration + 1})...")
            resp = await asyncio.to_thread(agent_llm.invoke, messages)

            # Extract tool call
            tool_calls = getattr(resp, "tool_calls", [])
            if not tool_calls:
                if mode == "report":
                    logger.info("=== REPORT MODE: No tool call, treating as answer ===")
                    answer_text = _extract_response(resp.content)
                    actions_log.append("Answering (from context)")
                    break
                else:
                    # Conversational response
                    yield {"type": "complete", "message": {
                        "response": _extract_response(resp.content),
                        "intent": "conversational",
                        "actions": ["Conversational response"],
                        "charts": [],
                        "sql": "",
                    }}
                    return

            tc = tool_calls[0]
            tool_name = tc.get("name", "")
            args = tc.get("args", {})

            # ── EXECUTE QUERIES ──
            if tool_name == "execute_queries":
                queries = args.get("queries", [])
                reasoning = args.get("reasoning", "")
                actions_log.append(f"Executing {len(queries)} queries — {reasoning[:80]}")

                yield {"type": "phase", "phase": "executing"}
                yield {
                    "type": "iteration",
                    "round": iteration + 1,
                    "action": "execute_queries",
                    "query_count": len(queries),
                    "reasoning": reasoning,
                }

                yield {"type": "plan", "steps": [
                    {"id": f"q{len(all_query_results) + i}", "action": "run_sql", "description": q.get("description", f"Query {i + 1}")}
                    for i, q in enumerate(queries)
                ], "reasoning": reasoning}

                batch_results = await _execute_query_batch(queries, auth=auth)

                for i, result in enumerate(batch_results):
                    all_query_results.append(result)
                    all_full_data.append(result)

                    step_id = f"q{len(all_query_results) - 1}"
                    event = {
                        "type": "step_complete",
                        "step_id": step_id,
                        "action": "run_sql",
                        "description": result.get("description", f"Query {i + 1}"),
                        "status": result.get("status", "unknown"),
                    }
                    if result.get("status") == "success":
                        event["row_count"] = result.get("row_count", 0)
                        event["columns"] = result.get("columns", [])
                        last_sql = result.get("sql", "")
                        actions_log.append(
                            f"SQL OK — {result.get('row_count', 0)} rows ({result.get('description', '')})"
                        )
                    else:
                        actions_log.append(f"SQL Error — {result.get('error', '')[:60]}")

                    yield event

                    # Emit report_step progress for report mode
                    if mode == "report" and report_sub_questions and report_step_idx < len(report_sub_questions):
                        sq = report_sub_questions[report_step_idx]
                        yield {
                            "type": "report_step",
                            "step_id": sq["id"],
                            "step_type": sq.get("type", ""),
                            "question": sq.get("question", ""),
                            "status": "complete" if result.get("status") == "success" else "error",
                            "row_count": result.get("row_count", 0),
                        }
                        report_step_idx += 1

                continue  # Next iteration

            # ── CLARIFY ──
            elif tool_name == "clarify":
                clarify_q = args.get("question", "Could you clarify your question?")
                actions_log.append(f"Clarification: {clarify_q}")
                logger.info("=== AGENT PAUSED FOR CLARIFICATION ===")

                yield {
                    "type": "clarification_needed",
                    "question": clarify_q,
                    "agent_state": {
                        "query_results": all_query_results,
                        "full_data": all_full_data,
                        "actions_log": actions_log,
                        "last_sql": last_sql,
                        "iteration": iteration,
                    },
                }
                return  # Stop streaming — wait for user reply

            # ── ANSWER ──
            elif tool_name == "answer":
                answer_text = args.get("response", "")
                needs_chart = args.get("needs_chart", False)
                chart_specs = args.get("charts", []) or []
                actions_log.append("Answering")

                # Generate charts (normal mode only — report mode uses Gemini)
                if needs_chart and chart_specs and mode == "normal":
                    yield {"type": "phase", "phase": "generating charts"}
                    chart_results = await _generate_charts_from_specs(chart_specs, all_full_data)
                    for cr in chart_results:
                        answer_charts_data.append({
                            "chart_xml": cr.chart_xml,
                            "chart_type": cr.chart_type,
                            "data_records": cr.data_records,
                            "sql": cr.sql,
                            "title": cr.title,
                            "size_column": cr.size_column,
                            "group_column": cr.group_column,
                        })
                    if chart_results:
                        actions_log.append(f"Generated {len(chart_results)} chart(s)")

                break  # Exit loop — answer or report formatting follows

            # ── GET COLUMN VALUES ──
            elif tool_name == "get_column_values_tool":
                table = args.get("table_name", "")
                column = args.get("column_name", "")
                actions_log.append(f"Looking up values for {table}.{column}")

                yield {"type": "phase", "phase": f"looking up {table}.{column}"}
                result = await _handle_get_column_values(args)
                all_query_results.append(result)
                all_full_data.append(result)

                yield {
                    "type": "step_complete",
                    "step_id": f"cv_{table}_{column}",
                    "action": "get_column_values",
                    "description": f"Distinct values for {table}.{column}",
                    "status": result.get("status", "unknown"),
                }
                continue

            # ── GET KPI INFO ──
            elif tool_name == "get_kpi_info_tool":
                kpi_id = args.get("kpi_id", "")
                actions_log.append(f"Looking up KPI: {kpi_id}")

                yield {"type": "phase", "phase": f"looking up KPI: {kpi_id}"}
                result = await _handle_get_kpi_info(args)
                all_query_results.append(result)
                all_full_data.append(result)

                yield {
                    "type": "step_complete",
                    "step_id": f"kpi_{kpi_id}",
                    "action": "get_kpi_info",
                    "description": f"KPI info: {kpi_id}",
                    "status": result.get("status", "unknown"),
                }
                continue

            # ── EXPLORE ──
            elif tool_name == "explore_tool":
                reasoning = args.get("reasoning", "")
                queries = args.get("queries", [])
                actions_log.append(f"Exploring ({len(queries)} queries) — {reasoning[:60]}")

                yield {"type": "phase", "phase": "exploring"}
                result = await _handle_explore(args, auth=auth)
                all_query_results.append(result)
                all_full_data.append(result)

                yield {
                    "type": "step_complete",
                    "step_id": f"explore_{iteration}",
                    "action": "explore",
                    "description": f"Exploration: {reasoning[:60]}",
                    "status": result.get("status", "unknown"),
                }
                continue

        else:
            # Max iterations reached — force synthesis
            yield {"type": "phase", "phase": "synthesizing"}
            actions_log.append("Max iterations reached — synthesizing from available data")
            answer_text = await _force_synthesize(question, all_query_results)

        # ── POST-LOOP: mode branching ──
        if mode == "report":
            yield {"type": "phase", "phase": "formatting report"}
            actions_log.append("Formatting report with Gemini...")
            report_html = await _synthesize_report(question, all_query_results)

            yield {"type": "complete", "message": {
                "response": report_html,
                "intent": "report",
                "actions": actions_log,
                "charts": [],
                "sql": last_sql,
                "report_html": report_html,
            }}
        else:
            yield {"type": "complete", "message": {
                "response": answer_text,
                "intent": "analytics",
                "actions": actions_log,
                "charts": answer_charts_data,
                "sql": last_sql,
            }}

        logger.info("=== AGENT STREAM COMPLETE (%.2fs) ===", time.time() - overall_start)

    except Exception as exc:
        logger.error("!!! Agent Stream Error: %s !!!", exc, exc_info=True)
        yield {"type": "error", "error": str(exc)}


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def _cli():
        print("-- Frammer AI (ReAct Loop) --\n")
        while True:
            q = input("You: ").strip()
            if q.lower() in ("quit", "exit"):
                break
            if not q:
                continue
            r = await run_agent(q)
            print(f"RESPONSE:\n{r.response}\n")
            if r.actions:
                print(f"ACTIONS: {r.actions}\n")
            if r.charts:
                print(f"CHARTS: {len(r.charts)} generated\n")

    asyncio.run(_cli())
