"""
kpi_generator.py
----------------
Specialized KPI SQL generator using the exact same LLMClient, content helpers,
and tool-calling patterns as agent.py.

Runs a synchronous ReAct loop to translate natural language → PostgreSQL.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.genai import types

# Ensure agent directory is in sys.path
_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.append(str(_AGENT_DIR))

# ── Reuse exact same infrastructure as agent.py ──────────────────────────────
from client import LLMClient
from tools import get_frammer_schema, execute_sql_query
from tools.metric_definitions import METRIC_DICTIONARY, retrieve_metric_definitions

logger = logging.getLogger("frammer.kpi_generator")

# ── Content helpers — identical to agent.py ───────────────────────────────────

def _user_content(text: str) -> types.Content:
    """Build a user message Content object."""
    return types.Content(role="user", parts=[types.Part(text=text)])


def _tool_response_content(tool_name: str, result_text: str) -> types.Content:
    """Build a function response Content object."""
    return types.Content(role="user", parts=[
        types.Part.from_function_response(name=tool_name, response={"result": result_text})
    ])


def _parse_genai_response(resp):
    """Parse a google-genai GenerateContentResponse — identical to agent.py."""
    text = ""
    tool_calls = []

    if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
        for part in resp.candidates[0].content.parts:
            if part.function_call:
                tool_calls.append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args) if part.function_call.args else {},
                    "id": f"call_{len(tool_calls)}",
                })
            elif part.text:
                text += part.text

    return text, tool_calls


# ── Tool stubs (for Gemini schema generation) ────────────────────────────────

def explore_tool(queries: Optional[List[str]] = None, reasoning: str = "") -> str:
    """Run lightweight exploration queries to verify SQL before finalizing.
    Args:
        queries: List of simple SQL strings for exploration. Each returns max 5 rows.
        reasoning: Why you need this exploration.
    """
    return json.dumps({"status": "ok", "queries": queries or []})


def yield_sql(sql: str = "", formula: str = "", reasoning: str = "") -> str:
    """Provide the final, validated PostgreSQL query for the Custom KPI.
    Args:
        sql: The final SELECT query returning columns: period, value.
        formula: A short human-readable mathematical formula describing the calculation using attribute names. Example: '(Created Assets - Published Assets) / Created Assets'.
        reasoning: Brief explanation of the query logic.
    """
    return json.dumps({"status": "ok", "sql": sql, "formula": formula})


KPI_TOOLS = [explore_tool, yield_sql]


# ── System Prompt ─────────────────────────────────────────────────────────────

KPI_AGENT_PROMPT = """\
You are the Frammer AI Custom KPI Generator.
Your ONLY goal is to produce a valid PostgreSQL SELECT query.

## Database Schema
{schema_block}

## Metric Definitions & Business Context
{metrics_block}

## Output Requirements
The query MUST return exactly two columns:
1. `period` — date truncated to {time_granularity}: `date_trunc('{time_granularity}', to_date("Date_Column", 'YYYY-MM-DD'))::date AS period`
2. `value` — the numeric KPI result

## Critical SQL Rules
- ALWAYS double-quote mixed-case column names: rv."Video_ID", ca."Asset_ID"
- Cast text dates: to_date("Upload_Date", 'YYYY-MM-DD')
- Join chain: raw_videos (rv) -> created_assets (ca) -> published_posts (pp)
- Use COUNT(DISTINCT ...) where appropriate
- Guard division with NULLIF(..., 0)
- End with GROUP BY 1 ORDER BY 1
- PREFER flat SELECT queries without CTEs. Your SQL will be automatically wrapped with scoping CTEs by the compiler.
- If you MUST use WITH clauses (CTEs), that is fine — the compiler will merge them. But flat queries are simpler and less error-prone.
- Reference tables as: raw_videos, created_assets, published_posts (the compiler rewrites these to scoped versions).
- For published volume, count Asset_ID not Post_ID: COUNT(DISTINCT pp."Asset_ID")

## Tools
1. `explore_tool` — test queries (max 5 rows each). ONLY use if you are genuinely unsure about column names or data shape.
2. `yield_sql` — return the final validated SQL AND a human-readable formula. You MUST call this when done.
   - `sql`: the PostgreSQL query
   - `formula`: a short mathematical expression using attribute names (NOT SQL). Examples:
     - "COUNT(Distinct Videos)" for a simple count
     - "(Created Assets - Published Assets) / Created Assets" for a ratio
     - "SUM(Uploaded Duration) / COUNT(Distinct Videos)" for an average
   Keep it concise and readable — this is shown to users in the UI.

## Workflow
You already have the full schema and metric definitions above. In MOST cases you have enough information to write the query immediately.
- **Default**: Call `yield_sql` directly with your query on the FIRST turn. Do NOT explore unless you truly need to.
- **Only explore if**: you are uncertain about a specific column name, data type, or join that is not covered in the schema above.
- **Maximum 1 exploration** before calling `yield_sql`. Do not loop.

You MUST respond with a tool call on every turn. NEVER produce plain text.
"""


def generate_kpi_sql(expression: str, time_granularity: str = "month") -> dict:
    """
    Synchronous ReAct loop using LLMClient (same as agent.py).
    Returns dict with 'sql' and 'formula' keys.
    """
    llm = LLMClient.fast()
    schema = get_frammer_schema()

    # Build metrics block — same pattern as main agent (agent.py:822-823)
    all_metrics = "\n".join(f"- **{k}**: {v}" for k, v in METRIC_DICTIONARY.items())
    all_metrics += "\n\n" + retrieve_metric_definitions("XYZ_FAIL")

    system_prompt = KPI_AGENT_PROMPT.format(
        schema_block=schema or "",
        time_granularity=time_granularity,
        metrics_block=all_metrics,
    )

    gemini_config = types.GenerateContentConfig(
        tools=KPI_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=llm.temperature,
        max_output_tokens=4096,
        system_instruction=system_prompt,
    )

    contents = [_user_content(f"Generate a Custom KPI SQL query for: {expression}")]

    MAX_ITERATIONS = 5

    for iteration in range(MAX_ITERATIONS):
        logger.info("=== KPI GEN ITERATION %d ===", iteration + 1)

        # Nudge the LLM to yield when iterations are running low
        if iteration == MAX_ITERATIONS - 1:
            contents.append(_user_content(
                "FINAL TURN — you MUST call yield_sql NOW with your best query. Do NOT explore."
            ))

        try:
            # Use the sync client directly — same as LLMClient._client
            resp = llm._client.models.generate_content(
                model=llm.model,
                contents=contents,
                config=gemini_config,
            )
        except Exception as e:
            logger.error("KPI generator LLM call failed: %s", e)
            raise ValueError(f"LLM call failed: {e}") from e

        text, tool_calls = _parse_genai_response(resp)

        # Append model response to contents (exactly like agent.py line 1294)
        if resp.candidates and resp.candidates[0].content:
            contents.append(resp.candidates[0].content)

        if not tool_calls:
            # Try to extract SQL from plain text as fallback (WITH or SELECT)
            match = re.search(r"```(?:sql)?\s*((?:WITH|SELECT).*?)```", text, re.DOTALL | re.IGNORECASE)
            if match:
                return {"sql": match.group(1).strip(), "formula": expression}
            raise ValueError("Agent stopped returning tool calls without yielding SQL.")

        tc = tool_calls[0]
        tool_name = tc["name"]
        args = tc["args"]

        # ── YIELD_SQL ──
        if tool_name == "yield_sql":
            sql = args.get("sql", "")
            if not sql:
                raise ValueError("Agent called yield_sql with empty SQL.")
            formula = args.get("formula", "") or expression
            logger.info("=== KPI GEN COMPLETE: SQL generated ===")
            return {"sql": sql, "formula": formula}

        # ── EXPLORE_TOOL ──
        elif tool_name == "explore_tool":
            queries = args.get("queries", [])
            reasoning = args.get("reasoning", "")
            logger.info("=== KPI GEN EXPLORE (%d queries): %s ===", len(queries), reasoning[:80])

            explorations = []
            for q in queries:
                try:
                    raw = execute_sql_query(q, limit=5)
                    parsed = json.loads(raw)
                    if "error" in parsed:
                        explorations.append({"query": q, "error": parsed["error"]})
                    else:
                        explorations.append({"query": q, "data": parsed.get("data", [])})
                except Exception as e:
                    explorations.append({"query": q, "error": str(e)})

            result_text = json.dumps({"status": "ok", "explorations": explorations}, default=str)
            # After exploration, nudge to yield on next turn
            result_text += '\n\nYou have explored the data. Now call yield_sql with your final query.'
            contents.append(_tool_response_content(tool_name, result_text))
            continue

        else:
            logger.warning("KPI generator called unknown tool: %s", tool_name)
            contents.append(_tool_response_content(tool_name, json.dumps({"error": f"Unknown tool: {tool_name}"})))
            continue

    raise ValueError("KPI SQL generation failed: max iterations reached without yielding SQL.")
