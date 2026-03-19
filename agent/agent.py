"""
agent.py
-------------
Frammer Analytics Agent — Plan-Execute-Synthesize Architecture.

Architecture:
  1. Planner:     Single LLM call produces a structured execution plan (SQL queries, charts).
  2. Executor:    Runs plan steps in parallel (no LLM calls needed).
  3. Synthesizer: Single LLM call summarizes results into a concise response.
  4. Repair:      Optional — fixes failed SQL steps (max 2 retries).

Token budget: ~20-30k total (down from 150-200k with the old ReAct loop).
"""

import asyncio
import json
import logging
import re
import sys
import time
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, TypedDict

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
    valid_types: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    intent: str = "analytics" # "analytics", "conversational", or "report"
    response: str = ""
    actions: List[str] = field(default_factory=list)
    charts: List[ChartResult] = field(default_factory=list)
    sql: str = ""
    error: str = ""
    plan: str = ""
    report_xml: str = ""  # New field for deep research reports
    # Legacy compat
    chart_xml: str = ""
    chart_data: Dict = field(default_factory=dict)


# ── Plan Step Types ──────────────────────────────────────────────────────────

class PlanStep(TypedDict, total=False):
    id: str           # "s1", "s2", ...
    action: str       # "run_sql" | "build_chart" | "get_column_values" | "get_time" | "explore"
    params: Dict      # action-specific parameters
    depends_on: List[str]  # step IDs this depends on
    description: str  # human-readable description


# ── Schema cache ─────────────────────────────────────────────────────────────
_schema_cache: Optional[str] = None

# ── LLM client ───────────────────────────────────────────────────────────────
_llm_client = LLMClient()

# ── System Prompts (split for token efficiency) ──────────────────────────────

PLANNER_PROMPT = """\
You are Frammer AI, an analytics planner for a media production platform.
Your job is to analyze the user's question and produce an EXECUTION PLAN — a list of steps (SQL queries, charts) that will answer the question.

## How to Plan

1. First, understand what the user is asking:
   - If it's conversational (greeting, thanks, small talk) → respond with `"conversational": true` and a brief reply. No plan needed.
   - If it's a data question → create a plan with SQL queries and optional charts.

2. For data questions, plan ALL needed queries upfront:
   - Each query should be independent where possible (so they can run in parallel)
   - Use the schema and metrics below to write correct SQL
   - Plan charts for results that benefit from visualization

3. Mark dependencies: if a chart needs data from a specific query, set `depends_on` to that query's step ID.

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
- NEVER guess filter values. The schema above has sample values — check them. If uncertain, add a `get_column_values` step.
- If >100 rows expected, use GROUP BY / aggregations in SQL
{auth_block}
{memory_block}

## Custom KPIs
The following specialized business KPIs are available for analytics. If you need the exact formula or business significance of any KPI, add a `get_kpi_info` step to your plan.
Available IDs: uploaded_count, processed_count, created_count, published_count, publish_conversion, month_by_month_use_rate, processing_efficiency, creation_rate, waste_index, upload_failure_rate, roi, cdas, interaction_lift, cross_dimension_entropy, publish_dependency_index, point_biserial, multidimensional_waste, ctas, rei

## System Environment
Current System Time: {now_str}

## Output Format

You MUST call the `create_plan` tool with your execution plan. The plan is a JSON object with:
- `conversational`: boolean — true if this is just a greeting/chat (no data needed)
- `reply`: string — only if conversational, the response text
- `reasoning`: string — brief explanation of your approach
- `steps`: array of step objects, each with:
  - `id`: string like "s1", "s2", ...
  - `action`: "run_sql" | "build_chart" | "get_column_values" | "get_time" | "explore" | "get_kpi_info"
  - `params`: object with action-specific params
  - `depends_on`: array of step IDs this depends on (empty if independent)
  - `description`: brief human-readable description

### Action params:
- `run_sql`: {{ "sql": "SELECT ...", "description": "what this query computes" }}
- `build_chart`: see Chart Type Selection Guide below
- `get_column_values`: {{ "table_name": "table", "column_name": "column" }}
- `get_time`: {{}}  (returns current datetime)
- `explore`: {{ "queries": ["SELECT DISTINCT ...", "SELECT MIN(...) ..."] }}  (lightweight exploration)
- `get_kpi_info`: {{ "kpi_id": "uploaded_count" }} (returns definition/formula for a specific KPI)

### Chart Type Selection Guide

Pick the chart type that best matches the DATA SHAPE and ANALYTICAL INTENT:

#### Comparison Charts
- `bar` — Compare values across categories (e.g. uploads by channel). Best for ≤15 categories, 1-2 metrics.
- `stacked-bar` — Show composition AND total across categories (e.g. uploads by channel, broken down by language). Use when you have 2+ metrics that sum to a meaningful total.
- `horizontal-bar` — Rank items or compare categories with long labels (e.g. "Top 10 users by upload count").

#### Trend Charts
- `line` — Show change over time for 1-2 metrics (e.g. monthly upload trend). X-axis MUST be a date/time column.
- `area` — Show composition over time with stacked filled regions (e.g. monthly uploads by language stacked). Use when 2+ metrics should show both individual trends AND their cumulative total.

#### Proportion Charts
- `pie` — Show parts of a whole (e.g. share of uploads by language). ONLY when ≤6 categories and 1 metric.
- `doughnut` — Same as pie but cleaner. Prefer over pie for a modern look.
- `polar-area` — Compare magnitudes across categories on a radial layout. Good for 4-8 categories.

#### Distribution Charts
- `box` — Show statistical distribution (min, Q1, median, Q3, max). SQL MUST return columns: category, min_val, q1, median, q3, max_val.
  SQL pattern: `SELECT category, MIN(val) AS min_val, PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY val) AS q1, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY val) AS median, PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY val) AS q3, MAX(val) AS max_val FROM ... GROUP BY category`
- `violin` — Same as box but shows distribution shape. Same SQL pattern.

#### Correlation Charts
- `scatter` — Show relationship between two numeric variables. X and Y must both be numeric. Use `group_column` to color-code by category.
- `bubble` — Like scatter but adds a third dimension via bubble size. Use `size_column` param.

#### Multi-dimensional
- `radar` — Compare entities across multiple metrics on a spider web (e.g. compare 3 channels across uploads, assets, publish rate). Best for 4-8 metrics, ≤5 entities. SQL should return one row per entity with metrics as columns.
- `heatmap` — Show intensity across two categorical dimensions (e.g. output_type × channel). SQL must return x_dim, y_dim, value columns. For correlation heatmaps, use PostgreSQL CORR(x, y) to compute Pearson correlation values between numeric columns.

#### Hierarchical
- `treemap` — Show hierarchical proportions (e.g. uploads by client > channel). SQL should return label, value, and optionally group columns.

### build_chart params:
{{
  "chart_type": "bar"|"stacked-bar"|"horizontal-bar"|"line"|"area"|"pie"|"doughnut"|"polar-area"|"scatter"|"bubble"|"radar"|"heatmap"|"box"|"violin"|"treemap",
  "valid_types": ["type1", "type2"],   // List of alternative chart types valid for this data
  "x_column": "column for X axis or category axis",
  "y_columns": "col1,col2",
  "size_column": "col3",              // ONLY for bubble charts
  "group_column": "col4",             // for scatter color groups or radar entities
  "title": "Short descriptive title",
  "source_step": "s1"
}}

### Chart Compatibility Guiding Rules:
- **Time Series (X is date)**: `line`, `area`, `bar` (if few points). NEVER `pie`/`doughnut`.
- **Categorical (X is labels)**: `bar`, `horizontal-bar`, `pie` (if metrics are summable and ≤6 categories).
- **Parts of a Whole**: `pie`, `doughnut`, `treemap`. Valid if values represent a complete set.
- **Correlations**: `scatter`, `bubble`. Valid if X and Y are both continuous numeric metrics.
- **Multiple Metrics**: `radar`, `stacked-bar` (if units match).
- **Distributions**: `box`, `violin`. Valid only if SQL returns the statistical columns (min, q1, etc).
"""

SYNTHESIZER_PROMPT = """\
You are Frammer AI. Summarize the analysis results below into a clear, concise response.

## Rules
- **Extreme Brevity**: 2-3 sentences max. No fluff.
- **Data Integrity**: ONLY use numbers from the results. Never estimate or hallucinate.
- **Formatting**: **Bold** key numbers and terms. Use markdown.
- **Privacy**: Never expose SQL, internal IDs, database table names (e.g. raw_videos, created_assets, published_posts, post_distribution, raw_video_channel), column names (e.g. Video_ID, Asset_ID, Input_Type, Output_Type, User_ID), or any technical schema details.
- **Business Language**: Always translate technical terms to business language — uploads (not raw_videos), generated content/assets (not created_assets), published content (not published_posts), content format (not Input_Type), asset type (not Output_Type), channel (not Channel_Name), user (not User_ID).
- **No Images**: Do NOT generate markdown image tags.
- If results show trends or comparisons, highlight the most important finding.
- If multiple datasets were queried, synthesize the overall story.

## User Question
{question}

## Analysis Results
{results_block}
"""

REPAIR_PROMPT = """\
The following SQL query failed. Fix the SQL and return ONLY the corrected query.

## Error
{error}

## Failed SQL
```sql
{sql}
```

## Schema Context
{schema_block}

## Rules
- Double-quote mixed-case columns: "Upload_Date", "Video_ID"
- Check table/column names against the schema
- Return ONLY the corrected SQL, nothing else.
"""

REPORT_PLANNER_PROMPT = """\
You are Frammer AI, specialized in Deep Research Report Generation.
Your goal is to create a COMPREHENSIVE EXHAUSTIVE plan for a 1-2 page business report.

## How to Plan for Research
1. Start by exploring the data landscape if the question is broad.
2. Plan multiple SQL queries to cover different dimensions (Time, Language, Platform, User).
3. Always include steps to 'get_column_values' if you need to filter by a specific category.
4. Plan at least 3-5 distinct charts to visualize the data.
5. Use Custom KPIs (uploaded_count, waste_index, etc.) to add depth.

## Output Format
You MUST call the `create_report_plan` tool.
Plan for a multi-step investigation that can be refined.
"""

REPORT_REFINER_PROMPT = """\
You are the Frammer Research Critic. Review the current investigation results.
Determine if the research is complete or if we need more 'Deep Dive' steps.

## Current Results
{results_summary}

## Goal
A 1-2 page detailed report answering: {question}

## Your Job
If the data is insufficient or hints at a deeper trend (e.g. a specific month has high failure), add NEW steps to investigate that.
If the research is sufficient, return an empty list of steps.

## Response Format
Call `create_report_plan` with ONLY the additional steps needed. Set `research_complete` to true if no more steps are needed.
"""

REPORT_GENERATOR_PROMPT = """\
You are a Professional Business Report Designer.
Convert the following research results into a structured, 1-2 page XML report.

## Research Results
{results_block}

## XML Schema
The report must follow this structure:
<report>
  <meta>
    <title>Business Title</title>
    <description>Brief summary</description>
  </meta>
  <section title="Section Title">
    <text>Detailed analytical explanation (2-3 paragraphs).</text>
    <chart_ref id="step_id" /> <!-- Reference a chart created in the plan -->
  </section>
</report>

## Rules
- Focus on business impact and trends.
- Use 3-5 sections.
- Ensure the tone is professional and insightful.
"""


# ── Tool: create_plan (for structured LLM output) ───────────────────────────

from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@tool
def create_plan(
    conversational: bool = False,
    reply: str = "",
    reasoning: str = "",
    steps: Optional[List[Dict]] = None,
) -> str:
    """Create an execution plan for answering the user's data question.
    Args:
        conversational: True if this is just a greeting/chat (no data queries needed).
        reply: If conversational, the response text.
        reasoning: Brief explanation of your analytical approach.
        steps: List of execution steps. Each step has: id, action, params, depends_on, description.
    """
    return json.dumps({
        "conversational": conversational,
        "reply": reply,
        "reasoning": reasoning,
        "steps": steps or [],
    })


@tool
def create_report_plan(
    reasoning: str = "",
    steps: Optional[List[Dict]] = None,
    research_complete: bool = False,
) -> str:
    """Create or refine a deep research plan.
    Args:
        reasoning: Explanation of the research strategy.
        steps: List of research steps (SQL, explore, KPI info, etc).
        research_complete: Set to True if no more investigation is needed.
    """
    return json.dumps({
        "reasoning": reasoning,
        "steps": steps or [],
        "research_complete": research_complete,
    })


# ── LLM with plan tool ──────────────────────────────────────────────────────
_planner_llm = _llm_client.llm.bind_tools([create_plan])
_report_planner_llm = _llm_client.llm.bind_tools([create_report_plan])
_synthesizer_llm = _llm_client.llm
_repair_llm = _llm_client.llm
_report_generator_llm = _llm_client.creative # Use creative model for report generation


# ── Step Executors ───────────────────────────────────────────────────────────

async def _execute_sql_step(params: Dict, auth: Any = None) -> Dict:
    """Execute a SQL query step."""
    sql = params.get("sql", "")
    raw = await asyncio.to_thread(execute_sql_query, sql, limit=200, auth=auth)
    parsed = json.loads(raw)

    if "error" in parsed:
        return {"status": "error", "error": parsed["error"], "sql": sql}

    records = parsed.get("data", [])
    result_id = str(_uuid.uuid4())[:8]
    cols = list(records[0].keys()) if records else []

    return {
        "status": "success",
        "result_id": result_id,
        "row_count": len(records),
        "columns": cols,
        "data": records,
        "sql": sql,
        "sample": records[:30],
    }


async def _execute_chart_step(params: Dict, results: Dict) -> Dict:
    """Execute a chart-building step."""
    source_step = params.get("source_step", "")
    source_data = results.get(source_step, {})
    records = source_data.get("data", [])

    if not records:
        return {"status": "error", "error": f"No data from step {source_step}"}

    attrs = {
        "type": params.get("chart_type", "bar"),
        "x_axis": params.get("x_column", ""),
        "y_axis": params.get("y_columns", ""),
        "title": params.get("title", "Chart"),
    }
    if params.get("size_column"):
        attrs["size_field"] = params["size_column"]
    if params.get("group_column"):
        attrs["group_field"] = params["group_column"]

    xml = await asyncio.to_thread(generate_plotly_chart, data_records=records, chart_attributes=attrs)

    if xml and xml.startswith("<?xml"):
        return {
            "status": "success",
            "chart_xml": xml,
            "chart_type": params.get("chart_type", "bar"),
            "valid_types": params.get("valid_types", []),
            "data_records": records,
            "sql": source_data.get("sql", ""),
            "title": params.get("title", "Chart"),
            "size_column": params.get("size_column", ""),
            "group_column": params.get("group_column", ""),
        }

    return {"status": "error", "error": f"Chart generation failed: {xml}"}


async def _execute_column_values_step(params: Dict) -> Dict:
    """Execute a column values lookup step."""
    table = params.get("table_name", "")
    column = params.get("column_name", "")
    try:
        db = get_db()
        profile = db.get_schema_profile()
        col_info = profile.get(table, {}).get(column, {})
        values = col_info.get("values")
        if values is None:
            return {"status": "success", "note": "Column not in profile (high-cardinality or non-text)"}
        return {"status": "success", "table": table, "column": column, "values": values}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _execute_time_step() -> Dict:
    """Return current time."""
    return {"status": "success", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


async def _execute_explore_step(params: Dict, auth: Any = None) -> Dict:
    """Execute lightweight exploration queries."""
    queries = params.get("queries", [])
    results = []
    for q in queries:
        try:
            raw = await asyncio.to_thread(execute_sql_query, q, limit=5, auth=auth)
            parsed = json.loads(raw)
            if "error" in parsed:
                results.append({"query": q, "error": parsed["error"]})
            else:
                results.append({"query": q, "data": parsed.get("data", [])})
        except Exception as e:
            results.append({"query": q, "error": str(e)})
    return {"status": "success", "explorations": results}


async def _execute_step(step: PlanStep, results: Dict, auth: Any = None) -> Dict:
    """Dispatch a plan step to the appropriate executor."""
    action = step.get("action", "")
    params = step.get("params", {})
    step_id = step.get("id", "?")

    logger.info("--- STEP %s: %s (%s) ---", step_id, action, step.get("description", "")[:60])
    start = time.time()

    try:
        if action == "run_sql":
            result = await _execute_sql_step(params, auth=auth)
        elif action == "build_chart":
            result = await _execute_chart_step(params, results)
        elif action == "get_column_values":
            result = await _execute_column_values_step(params)
        elif action == "get_time":
            result = await _execute_time_step()
        elif action == "explore":
            result = await _execute_explore_step(params, auth=auth)
        elif action == "get_kpi_info":
            kpi_id = params.get("kpi_id")
            result_raw = await asyncio.to_thread(get_custom_kpi_info, kpi_id)
            result = {"status": "success", "data": json.loads(result_raw)}
        else:
            result = {"status": "error", "error": f"Unknown action: {action}"}

        duration = time.time() - start
        status = result.get("status", "unknown")
        logger.info("--- STEP %s DONE (%.2fs) → %s ---", step_id, duration, status)
        return result

    except Exception as e:
        logger.error("--- STEP %s FAILED: %s ---", step_id, e)
        return {"status": "error", "error": str(e)}


# ── Parallel Executor ────────────────────────────────────────────────────────

async def _execute_plan(
    steps: List[PlanStep],
    auth: Any = None,
) -> Dict[str, Any]:
    """
    Execute plan steps with topological ordering and parallelism.
    Steps with no unresolved dependencies run concurrently.
    """
    results: Dict[str, Any] = {}
    remaining = list(steps)
    actions_log: List[str] = []

    while remaining:
        # Find steps whose dependencies are all satisfied
        ready = [s for s in remaining if all(d in results for d in s.get("depends_on", []))]
        if not ready:
            # All remaining steps have unresolved deps — break to avoid infinite loop
            for s in remaining:
                results[s["id"]] = {"status": "error", "error": "Unresolved dependencies"}
                actions_log.append(f"Step {s['id']} skipped — unresolved deps")
            break

        # Execute ready steps in parallel
        logger.info("=== EXECUTING BATCH: %s ===", [s["id"] for s in ready])
        tasks = [_execute_step(s, results, auth=auth) for s in ready]
        step_results = await asyncio.gather(*tasks, return_exceptions=True)

        for step, result in zip(ready, step_results):
            if isinstance(result, Exception):
                result = {"status": "error", "error": str(result)}

            results[step["id"]] = result
            remaining.remove(step)

            # Build action log
            action = step.get("action", "")
            desc = step.get("description", action)
            status = result.get("status", "unknown")
            if action == "run_sql" and status == "success":
                actions_log.append(f"SQL OK — {result.get('row_count', 0)} rows ({desc})")
            elif action == "build_chart" and status == "success":
                actions_log.append(f"Chart: {result.get('title', 'chart')}")
            elif status == "error":
                actions_log.append(f"Failed: {desc} — {result.get('error', '')[:60]}")
            else:
                actions_log.append(f"{desc}")

    return {"results": results, "actions": actions_log}


# ── SQL Repair ───────────────────────────────────────────────────────────────

async def _repair_sql(failed_steps: List[tuple], schema: str) -> List[tuple]:
    """
    Attempt to fix failed SQL steps. Returns list of (step, fixed_sql) tuples.
    """
    repaired = []
    for step, error_result in failed_steps:
        sql = step.get("params", {}).get("sql", "")
        error_msg = error_result.get("error", "")

        prompt = REPAIR_PROMPT.format(
            error=error_msg,
            sql=sql,
            schema_block=schema[:3000],  # Condensed schema for repair
        )

        logger.info("--- REPAIR: Fixing SQL for step %s ---", step["id"])
        try:
            resp = await asyncio.to_thread(_repair_llm.invoke, prompt)
            fixed_sql = _extract_response(resp.content).strip()
            # Strip markdown fences
            fixed_sql = re.sub(r"^```(?:sql)?\s*\n?", "", fixed_sql, flags=re.IGNORECASE)
            fixed_sql = re.sub(r"\n?```\s*$", "", fixed_sql).strip()

            if fixed_sql and fixed_sql.upper().startswith("SELECT"):
                repaired.append((step, fixed_sql))
            else:
                logger.warning("--- REPAIR: Invalid fix for step %s ---", step["id"])
        except Exception as e:
            logger.error("--- REPAIR FAILED for step %s: %s ---", step["id"], e)

    return repaired


# ── Report Generation Functions ──────────────────────────────────────────────

async def _run_report_planner(
    question: str,
    schema: str,
    metrics: str,
    auth: Any = None,
    history: Optional[List[Dict]] = None,
) -> Dict:
    """Initial research plan for reports."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system = REPORT_PLANNER_PROMPT.format(
        schema_block=schema,
        metrics_block=metrics,
        now_str=now_str,
    )
    messages = [SystemMessage(content=system), HumanMessage(content=question)]
    
    resp = await asyncio.to_thread(_report_planner_llm.invoke, messages)
    tool_calls = getattr(resp, "tool_calls", [])
    if tool_calls:
        return tool_calls[0].get("args", {})
    return json.loads(_extract_response(resp.content))

async def _run_report_refiner(
    question: str,
    results_summary: str,
) -> Dict:
    """Analyze results and decide if more deep-dive steps are needed."""
    system = REPORT_REFINER_PROMPT.format(
        results_summary=results_summary,
        question=question,
    )
    messages = [SystemMessage(content=system), HumanMessage(content="Refine the research plan.")]
    
    resp = await asyncio.to_thread(_report_planner_llm.invoke, messages)
    tool_calls = getattr(resp, "tool_calls", [])
    if tool_calls:
        return tool_calls[0].get("args", {})
    return json.loads(_extract_response(resp.content))

async def _run_report_generator(
    results_block: str,
) -> str:
    """Generate the final report XML."""
    system = REPORT_GENERATOR_PROMPT.format(results_block=results_block)
    messages = [SystemMessage(content=system), HumanMessage(content="Generate the report XML.")]
    
    resp = await asyncio.to_thread(_report_generator_llm.invoke, messages)
    xml = _extract_response(resp.content)
    # Strip markdown fences
    xml = re.sub(r"^```(?:xml)?\s*\n?", "", xml, flags=re.IGNORECASE)
    xml = re.sub(r"\n?```\s*$", "", xml).strip()
    return xml


# ── Planner ──────────────────────────────────────────────────────────────────

async def _run_planner(
    question: str,
    schema: str,
    metrics: str,
    auth: Any = None,
    history: Optional[List[Dict]] = None,
    working_memory: str = "",
) -> Dict:
    """Run the planner LLM to produce an execution plan."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    auth_block = ""
    if auth:
        role = getattr(auth, "role", "user")
        username = getattr(auth, "username", "Unknown")
        client_name = getattr(auth, "client_name", None)
        user_id = getattr(auth, "user_id", None)

        auth_block = f"\n## USER PROFILE\n- User: **{username}** | Role: **{role}**"
        if role != "website_admin":
            if client_name:
                auth_block += f"\n- RESTRICTION: Only client **{client_name}** data. Use: `COALESCE(ch.\"Client_Name\", u.\"Client_Name\") = '{client_name}'`"
            elif role == "user" and user_id:
                auth_block += f"\n- RESTRICTION: Only data for user ID **{user_id}**. Use: `rv.\"User_ID\" = {user_id}`"

    memory_block = f"\n## Conversation Memory\n{working_memory}" if working_memory else ""

    system = PLANNER_PROMPT.format(
        schema_block=schema or "",
        metrics_block=metrics or "",
        auth_block=auth_block,
        memory_block=memory_block,
        now_str=now_str,
    )

    # Build message history (limited to last 4 for planner)
    history_messages = []
    for msg in (history or [])[-4:]:
        role = msg.get("role", "")
        content = msg.get("content", "") or ""
        if role == "user":
            history_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            history_messages.append(AIMessage(content=content))

    messages = [SystemMessage(content=system)] + history_messages + [HumanMessage(content=question)]

    logger.info("=== PLANNER: Calling LLM (%d messages) ===", len(messages))
    start = time.time()
    resp = await asyncio.to_thread(_planner_llm.invoke, messages)
    duration = time.time() - start

    usage = getattr(resp, "usage_metadata", {})
    logger.info(
        "=== PLANNER DONE (%.2fs) — %d input, %d output tokens ===",
        duration,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )

    # Extract plan from tool call
    tool_calls = getattr(resp, "tool_calls", [])
    if tool_calls:
        tc = tool_calls[0]
        args = tc.get("args", {})
        return {
            "conversational": args.get("conversational", False),
            "reply": args.get("reply", ""),
            "reasoning": args.get("reasoning", ""),
            "steps": args.get("steps", []),
        }

    # Fallback: try to parse from text content
    content = _extract_response(resp.content)
    try:
        parsed = json.loads(content)
        return parsed
    except json.JSONDecodeError:
        # If the LLM just responded conversationally without using the tool
        return {
            "conversational": True,
            "reply": content,
            "reasoning": "",
            "steps": [],
        }


# ── Synthesizer ──────────────────────────────────────────────────────────────

async def _run_synthesizer(question: str, results: Dict[str, Any], plan_steps: List[PlanStep]) -> str:
    """Run the synthesizer LLM to produce the final response."""
    # Build results block — only include data summaries, not full datasets
    results_parts = []
    for step in plan_steps:
        step_id = step.get("id", "")
        desc = step.get("description", step.get("action", ""))
        result = results.get(step_id, {})
        action = step.get("action", "")

        if action == "run_sql" and result.get("status") == "success":
            sample = result.get("sample", result.get("data", []))[:20]
            display_cols = [c.replace('_', ' ').title() for c in result.get('columns', [])]
            results_parts.append(
                f"### {desc}\n"
                f"Rows: {result.get('row_count', 0)} | Columns: {display_cols}\n"
                f"Sample data:\n```json\n{json.dumps(sample, default=str, indent=1)}\n```"
            )
        elif action == "build_chart" and result.get("status") == "success":
            results_parts.append(f"### Chart: {result.get('title', 'Chart')} — created successfully")
        elif action == "get_column_values" and result.get("status") == "success":
            results_parts.append(f"### Available values for {desc}: {result.get('values', [])}")
        elif action == "explore" and result.get("status") == "success":
            results_parts.append(f"### Exploration:\n{json.dumps(result.get('explorations', []), default=str, indent=1)}")
        elif action == "get_kpi_info" and result.get("status") == "success":
            kpi_data = result.get("data", {})
            sql_block = f"\nSQL Pattern: {kpi_data.get('sql')}" if kpi_data.get('sql') else ""
            results_parts.append(f"### KPI Info: {kpi_data.get('title')}\nDefinition: {kpi_data.get('definition')}\nFormula: {kpi_data.get('formula')}{sql_block}")
        elif result.get("status") == "error":
            results_parts.append(f"### {desc} — FAILED: {result.get('error', '')[:100]}")

    results_block = "\n\n".join(results_parts) if results_parts else "No data was retrieved."

    prompt = SYNTHESIZER_PROMPT.format(
        question=question,
        results_block=results_block,
    )

    logger.info("=== SYNTHESIZER: Calling LLM ===")
    start = time.time()
    resp = await asyncio.to_thread(_synthesizer_llm.invoke, prompt)
    duration = time.time() - start

    usage = getattr(resp, "usage_metadata", {})
    logger.info(
        "=== SYNTHESIZER DONE (%.2fs) — %d input, %d output tokens ===",
        duration,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )

    return _extract_response(resp.content)


# ── Main Entry Point ─────────────────────────────────────────────────────────

async def run_agent(
    question: str,
    auth: Optional[Any] = None,
    working_memory: str = "",
    history: Optional[List[Dict]] = None,
    mode: str = "analytics",
) -> AgentResult:
    """
    Main agent entry point. Runs either the standard analytic pipeline 
    or the Deep Research Report pipeline.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=== AGENT START (%s) === @ %s", mode, now_str)
    overall_start = time.time()

    actions_log: List[str] = []

    try:
        # 1. Load schema + metrics
        global _schema_cache
        if not _schema_cache:
            _schema_cache = get_frammer_schema()

        all_metrics = "\n".join(f"- **{k}**: {v}" for k, v in METRIC_DICTIONARY.items())
        all_metrics += "\n\n" + retrieve_metric_definitions("XYZ_FAIL")

        # Automatically switch to report mode if keywords are present
        if any(w in question.lower() for w in ["report", "deep research", "thorough analysis"]):
            mode = "report"

        # 2. Run Planner
        actions_log.append(f"Planning {mode}...")
        if mode == "report":
            plan = await _run_report_planner(question, _schema_cache, all_metrics, auth, history)
        else:
            plan = await _run_planner(question, _schema_cache, all_metrics, auth, history, working_memory)

        # Handle conversational responses
        if plan.get("conversational"):
            return AgentResult(
                intent="conversational",
                response=plan.get("reply", ""),
                actions=["Conversational response"],
            )

        steps = plan.get("steps", [])
        reasoning = plan.get("reasoning", "")
        actions_log.append(f"Initial Plan: {len(steps)} steps")
        
        if not steps:
            return AgentResult(
                response="I couldn't determine what data to look up. Could you rephrase your question?",
                actions=actions_log,
            )

        # 3. Execution & Refinement Loop (for reports)
        results: Dict[str, Any] = {}
        
        async def execute_and_repair(current_steps):
            exec_res = await _execute_plan(current_steps, auth=auth)
            results.update(exec_res["results"])
            actions_log.extend(exec_res["actions"])
            
            # Repair loop (only for new steps)
            for _ in range(2):
                failed = [(s, results[s["id"]]) for s in current_steps if results.get(s["id"], {}).get("status") == "error" and s.get("action") == "run_sql"]
                if not failed: break
                repaired = await _repair_sql(failed, _schema_cache)
                if not repaired: break
                for s, sql in repaired:
                    s["params"]["sql"] = sql
                    results[s["id"]] = await _execute_step(s, results, auth=auth)
                    actions_log.append(f"SQL Repaired — {s.get('id')}")

        await execute_and_repair(steps)

        if mode == "report":
            for loop_i in range(1): # One refinement loop for now to avoid token explosion
                summary = ""
                for sid, res in results.items():
                    if res.get("status") == "success":
                        summary += f"- {sid}: {res.get('row_count', 0)} rows found.\n"
                
                refinement = await _run_report_refiner(question, summary)
                if refinement.get("research_complete") or not refinement.get("steps"):
                    actions_log.append("Research complete — no further deep-dive needed.")
                    break
                
                new_steps = refinement.get("steps", [])
                actions_log.append(f"Deep-dive: Adding {len(new_steps)} research steps.")
                steps.extend(new_steps)
                await execute_and_repair(new_steps)

        # 4. Final Aggregation
        charts = []
        for step in steps:
            if step.get("action") == "build_chart":
                res = results.get(step["id"], {})
                if res.get("status") == "success":
                    charts.append(ChartResult(
                        chart_xml=res.get("chart_xml", ""),
                        data_records=res.get("data_records", []),
                        sql=res.get("sql", ""),
                        title=res.get("title", ""),
                        chart_type=res.get("chart_type", ""),
                        valid_types=res.get("valid_types", []),
                    ))

        # Synthesize final message
        final_response = await _run_synthesizer(question, results, steps)
        
        report_xml = ""
        if mode == "report":
            # Build results block for generator
            results_block = ""
            for step in steps:
                res = results.get(step["id"], {})
                if res.get("status") == "success":
                    results_block += f"Step {step['id']} ({step.get('description')}):\n{json.dumps(res.get('sample', []), default=str)}\n\n"
            
            report_xml = await _run_report_generator(results_block)
            actions_log.append("Detailed XML report generated")

        last_sql = ""
        last_records = []
        for step in reversed(steps):
            if step.get("action") == "run_sql":
                res = results.get(step["id"], {})
                if res.get("status") == "success":
                    last_sql = res.get("sql", "")
                    last_records = res.get("data", [])
                    break

        total_time = time.time() - overall_start
        logger.info("=== AGENT COMPLETE (%s, %.2fs) ===", mode, total_time)

        return AgentResult(
            intent=mode,
            response=final_response,
            actions=actions_log,
            charts=charts,
            sql=last_sql,
            plan=reasoning,
            report_xml=report_xml,
            chart_xml=charts[0].chart_xml if charts else "",
            chart_data={"query_result": last_records} if last_records else {},
        )

    except Exception as exc:
        logger.error("!!! Agent Runtime Error: %s !!!", exc, exc_info=True)
        return AgentResult(
            response=f"I encountered an error generating the report: {exc}. Please try a more specific question.",
            error=str(exc),
            actions=actions_log,
        )


# ── Streaming Entry Point ───────────────────────────────────────────────────

async def run_agent_stream(
    question: str,
    auth: Optional[Any] = None,
    working_memory: str = "",
    history: Optional[List[Dict]] = None,
    mode: str = "analytics",
) -> AsyncGenerator[Dict, None]:
    """
    Streaming version of run_agent. Yields SSE events as the agent progresses.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=== AGENT STREAM START (%s) === @ %s", mode, now_str)
    overall_start = time.time()

    try:
        # 1. Load schema + metrics
        global _schema_cache
        if not _schema_cache:
            _schema_cache = get_frammer_schema()

        all_metrics = "\n".join(f"- **{k}**: {v}" for k, v in METRIC_DICTIONARY.items())
        all_metrics += "\n\n" + retrieve_metric_definitions("XYZ_FAIL")

        # Automatically switch to report mode
        if any(w in question.lower() for w in ["report", "deep research", "thorough analysis"]):
            mode = "report"

        # 2. Plan
        yield {"type": "phase", "phase": "planning"}

        if mode == "report":
            plan = await _run_report_planner(question, _schema_cache, all_metrics, auth, history)
        else:
            plan = await _run_planner(question, _schema_cache, all_metrics, auth, history, working_memory)

        if plan.get("conversational"):
            yield {"type": "complete", "message": {
                "response": plan.get("reply", ""),
                "intent": "conversational",
                "actions": ["Conversational response"],
                "charts": [],
                "sql": "",
            }}
            return

        steps = plan.get("steps", [])
        yield {"type": "plan", "steps": [
            {"id": s.get("id"), "action": s.get("action"), "description": s.get("description", "")}
            for s in steps
        ], "reasoning": plan.get("reasoning", "")}

        if not steps:
            yield {"type": "complete", "message": {
                "response": "I couldn't determine what data to look up. Could you rephrase your question?",
                "intent": "analytics",
                "actions": [],
                "charts": [],
                "sql": "",
            }}
            return

        # 3. Execute
        yield {"type": "phase", "phase": "executing"}

        results: Dict[str, Any] = {}
        remaining = list(steps)
        actions_log = [f"Plan: {len(steps)} steps"]

        while remaining:
            ready = [s for s in remaining if all(d in results for d in s.get("depends_on", []))]
            if not ready:
                for s in remaining:
                    results[s["id"]] = {"status": "error", "error": "Unresolved dependencies"}
                break

            tasks = [_execute_step(s, results, auth=auth) for s in ready]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(ready, step_results):
                if isinstance(result, Exception):
                    result = {"status": "error", "error": str(result)}

                results[step["id"]] = result
                remaining.remove(step)

                # Yield step completion event
                event = {
                    "type": "step_complete",
                    "step_id": step.get("id"),
                    "action": step.get("action"),
                    "description": step.get("description", ""),
                    "status": result.get("status", "unknown"),
                }
                if result.get("status") == "success" and step.get("action") == "run_sql":
                    event["row_count"] = result.get("row_count", 0)
                    event["columns"] = result.get("columns", [])
                if result.get("status") == "success" and step.get("action") == "build_chart":
                    event["title"] = result.get("title", "")
                yield event

                # Build action log
                action = step.get("action", "")
                desc = step.get("description", action)
                if action == "run_sql" and result.get("status") == "success":
                    actions_log.append(f"SQL OK — {result.get('row_count', 0)} rows ({desc})")
                elif action == "build_chart" and result.get("status") == "success":
                    actions_log.append(f"Chart: {result.get('title', 'chart')}")
                elif result.get("status") == "error":
                    actions_log.append(f"Failed: {desc}")
                else:
                    actions_log.append(desc)

        # 4. Repair (simplified for streaming — one round)
        failed_sql = [
            (s, results[s["id"]])
            for s in steps
            if s.get("action") == "run_sql" and results.get(s["id"], {}).get("status") == "error"
        ]
        if failed_sql:
            yield {"type": "phase", "phase": "repairing"}
            repaired = await _repair_sql(failed_sql, _schema_cache)
            for step, fixed_sql in repaired:
                step["params"]["sql"] = fixed_sql
                result = await _execute_step(step, results, auth=auth)
                results[step["id"]] = result
                yield {
                    "type": "step_complete",
                    "step_id": step.get("id"),
                    "action": "run_sql",
                    "description": f"Repaired: {step.get('description', '')}",
                    "status": result.get("status", "unknown"),
                }

        # 5. Synthesize
        yield {"type": "phase", "phase": "synthesizing"}

        charts = []
        for step in steps:
            if step.get("action") == "build_chart":
                result = results.get(step["id"], {})
                if result.get("status") == "success":
                    charts.append({
                        "chart_xml": result.get("chart_xml", ""),
                        "chart_type": result.get("chart_type", ""),
                        "data_records": result.get("data_records", []),
                        "sql": result.get("sql", ""),
                        "title": result.get("title", ""),
                        "size_column": result.get("size_column", ""),
                        "group_column": result.get("group_column", ""),
                        "valid_types": result.get("valid_types", []),
                    })

        # 5. Synthesize & Generate Report
        yield {"type": "phase", "phase": "synthesizing"}

        report_xml = ""
        if mode == "report":
            results_block = ""
            for step in steps:
                res = results.get(step["id"], {})
                if res.get("status") == "success":
                    results_block += f"Step {step['id']} ({step.get('description')}):\n{json.dumps(res.get('sample', []), default=str)}\n\n"
            report_xml = await _run_report_generator(results_block)

        response = await _run_synthesizer(question, results, steps)

        last_sql = ""
        for step in reversed(steps):
            if step.get("action") == "run_sql" and results.get(step["id"], {}).get("status") == "success":
                last_sql = results[step["id"]].get("sql", "")
                break

        yield {"type": "complete", "message": {
            "response": response,
            "intent": mode,
            "actions": actions_log,
            "charts": charts,
            "sql": last_sql,
            "report_xml": report_xml,
        }}

        logger.info("=== AGENT STREAM COMPLETE (%s, %.2fs) ===", mode, time.time() - overall_start)

    except Exception as exc:
        logger.error("!!! Agent Stream Error: %s !!!", exc, exc_info=True)
        yield {"type": "error", "error": str(exc)}


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def _cli():
        print("-- Frammer AI (Plan-Execute-Synthesize) --\n")
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
