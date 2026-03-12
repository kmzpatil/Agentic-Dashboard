"""
orchestrate.py
--------------
Multi-chart analytics agent with parallel SQL execution and JSON dashboard output.
Uses MCP (Model Context Protocol) to execute domain tools.

Pipeline:
    retrieve_context -> get_schema -> decompose_question
                                             |
                                     generate_all_charts   <- each chart spec runs in parallel
                                     (SQL + chart per spec, with retry & backoff)
                                             |
                                      generate_insights --> format_json_output --> END
                                             |
                                       handle_error --> END
"""

import asyncio
import json
import logging
import sys
import os
import time
from typing import Any, Dict, List, Optional, TypedDict

# Configure orchestrator logging (writes to console & file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("orchestrator.log")
    ]
)
logger = logging.getLogger("orchestrator")

# Clear SSL_CERT_FILE if it points to a non-existent file (common conda env leftover)
_ssl_cert = os.environ.get("SSL_CERT_FILE", "")
if _ssl_cert and not os.path.isfile(_ssl_cert):
    os.environ.pop("SSL_CERT_FILE")

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

# Local tools
from tools.metric_definitions import retrieve_metric_definitions

# MCP Client
from mcp_client import MCPClient

# --- Environment & LLMs -----------------------------------------------------

load_dotenv()

# Strict model: SQL generation, JSON decisions, chart attr selection
llm_orchestrator = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# Creative model: business insights synthesis
llm_analyst = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)


# --- Agent State ------------------------------------------------------------

class ChartSpec(TypedDict, total=False):
    sub_question:      str
    chart_type_hint:   str
    sql_query:         str
    records:           List[Dict]
    chart_attrs:       Dict
    chart_xml:         str
    sql_error:         str

class AgentState(TypedDict, total=False):
    question:          str
    semantic_context:  str           
    schema:            str           
    chart_specs:       List[ChartSpec]    
    chart_json:        str           
    insights:          str           
    error:             str           


# --- Helpers ----------------------------------------------------------------

import re

def _extract_json_array(text: str) -> Optional[List[Dict]]:
    """Robustly extract a JSON array from LLM text using regex."""
    match = re.search(r"(\[.*\])", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


async def _generate_chart_attrs(sql: str, sub_question: str, records: List[Dict]) -> Dict:
    """Decide chart type and axes for a single spec using the real column names (async)."""
    sample_rows = records[:3]
    col_names = list(sample_rows[0].keys()) if sample_rows else []

    col_hint = (
        f"Available columns in the result: {col_names}\n"
        f"Sample rows: {json.dumps(sample_rows, default=str)}\n\n"
        if col_names else ""
    )

    prompt = PromptTemplate.from_template(
        "You are a data visualisation expert.\n\n"
        "SQL query that produced the data:\n{sql}\n\n"
        "{col_hint}"
        "User question: {question}\n\n"
        "Choose the best chart type and identify the right columns.\n"
        "Respond with a single valid JSON object (no markdown, no extra text) "
        "with EXACTLY these keys:\n"
        "  type    -- one of: bar, line, pie\n"
        "            Use 'line' for time-series or trend data (x-axis is a date/month/period).\n"
        "            Use 'pie' when showing proportions or share of a total (few categories).\n"
        "            Use 'bar' for comparisons across categories (default).\n"
        "  x_axis  -- EXACT column name for the X axis (must be one of the available columns)\n"
        "  y_axis  -- EXACT column name(s) for the Y axis, comma-separated if multiple\n"
        "             (must be numeric columns from the available columns)\n"
        "  title   -- a short, descriptive chart title (max 8 words)\n\n"
        "Return ONLY the JSON object."
    )
    raw_resp = await llm_orchestrator.ainvoke(
        prompt.format(sql=sql, question=sub_question, col_hint=col_hint)
    )
    
    # Use robust extraction
    match = re.search(r"(\{.*\})", raw_resp.content, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


async def _process_single_spec(
    mcp: MCPClient,
    spec: Dict,
    schema: str,
    context: str,
) -> Dict:
    """
    Generate and execute SQL for a single chart spec using MCP tools.
    Retries up to 3 times with exponential backoff.
    """
    sub_question = spec.get("sub_question", "")

    # Define a fake tool schema so the LLM thinks in tool-call mode
    sql_tool_schema = [{
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": "Execute a read-only PostgreSQL SELECT query.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL SELECT query"}},
                "required": ["query"],
            },
        },
    }]
    llm_with_sql = llm_orchestrator.bind_tools(sql_tool_schema)

    prompt = (
        f"Database schema:\n{schema}\n\n"
        f"Business context:\n{context}\n\n"
        f"Question: {sub_question}\n\n"
        "You MUST generate a PostgreSQL query to answer this question.\n"
        "RULES:\n"
        "1. ONLY use EXACT table and column names from the Database Schema above.\n"
        "2. DO NOT guess table names.\n"
        "3. Use execute_sql_query to run your query."
    )

    spec_error = ""
    last_sql = ""

    for _attempt in range(3):
        try:
            current_prompt = prompt + (f"\n\nPrevious Error to fix: {spec_error}" if spec_error else "")
            response = await llm_with_sql.ainvoke([HumanMessage(content=current_prompt)])

            sql = ""
            if response.tool_calls:
                sql = response.tool_calls[0].get("args", {}).get("query", "")
            else:
                # Fallback to robust extraction
                match = re.search(r"(SELECT\s+.*)", response.content, re.IGNORECASE | re.DOTALL)
                if match:
                    sql = match.group(1).strip().strip("```sql").strip("```").strip()

            if not sql:
                spec_error = "LLM failed to generate a valid SQL query."
                if _attempt < 2: await asyncio.sleep(2 ** _attempt)
                continue

            last_sql = sql
            logger.info("  -> [MCP] SQL attempt %d: %s...", _attempt + 1, sql[:80])

            # Execute via MCP tool
            result_raw = await mcp.call_tool("execute_sql_query", {"query": sql})
            result = json.loads(result_raw)

            if "error" in result_raw.lower() and "rows" not in result:
                spec_error = result_raw
                logger.error(f"   [SQL ERROR] {spec_error}")
                if _attempt < 2: await asyncio.sleep(2 ** _attempt)
                continue

            records = result.get("rows", [])
            attrs = await _generate_chart_attrs(sql, sub_question, records)
            
            if not attrs.get("type") and spec.get("chart_type_hint"):
                attrs["type"] = spec["chart_type_hint"]

            # Generate chart config via MCP tool
            chart_config_raw = await mcp.call_tool("generate_chart_config", {
                "records": records,
                "type_hint": attrs.get("type", "bar"),
                "x_axis": attrs.get("x_axis"),
                "y_axis": attrs.get("y_axis"),
                "title": attrs.get("title")
            })
            chart_config = json.loads(chart_config_raw)

            logger.info("   [SQL OK]  ->  %d rows", len(records))
            return {
                **spec,
                "sql_query": sql,
                "records": records,
                "chart_attrs": attrs,
                "chart_config": chart_config,
            }
        except Exception as e:
            spec_error = str(e)
            logger.error(f"   [SQL SYSTEM ERROR] {spec_error}")
            if _attempt < 2: await asyncio.sleep(2 ** _attempt)
            continue

    logger.warning("   [SQL] FAILED after 3 retries")
    return {
        **spec,
        "sql_query": last_sql,
        "records": [],
        "chart_attrs": {},
        "chart_config": {},
        "sql_error": spec_error,
    }


# --- LangGraph Pipeline -----------------------------------------------------

# --- Global Schema Cache ---
_SCHEMA_CACHE: tuple[str, float] | None = None  # (schema_text, timestamp)
_SCHEMA_TTL = 300  # 5-minute TTL

async def build_and_run_pipeline(question: str) -> AgentState:
    """
    Compile and run the LangGraph pipeline for a single user question.
    Uses MCPClient to connect to the domain server.
    """
    global _SCHEMA_CACHE

    async with MCPClient() as mcp:

        # Node 1 — Retrieve semantic/business context
        def retrieve_context(state: AgentState):
            logger.info("\n[Node: retrieve_context] Fetching business metric definitions...")
            result = retrieve_metric_definitions(state["question"])
            logger.info(f"  -> Retrieved {len(result)} chars of business context.")
            return {"semantic_context": result}

        # Node 2 — Fetch live DB schema
        async def get_schema(state: AgentState):
            global _SCHEMA_CACHE
            now = time.time()
            if _SCHEMA_CACHE and (now - _SCHEMA_CACHE[1]) < _SCHEMA_TTL:
                logger.info("[Node: get_schema] Using cached database schema.")
                return {"schema": _SCHEMA_CACHE[0]}

            logger.info("[Node: get_schema] Fetching live database schema via MCP...")
            try:
                # Call list_tables tool
                tables_raw = await mcp.call_tool("list_tables")
                tables = json.loads(tables_raw)
                
                schema_info = "GCData Analytics Database Schema (PostgreSQL / Supabase):\n"

                for t in tables:
                    table_name = t["name"]
                    try:
                        details_raw = await mcp.call_tool("describe_table", {"table_name": table_name})
                        details = json.loads(details_raw)
                        cols = ", ".join(f"{c['name']} ({c['type']})" for c in details.get("columns", []))
                        schema_info += f"\nTable: {table_name}\nColumns: {cols}\n"
                    except Exception:
                        schema_info += f"\nTable: {table_name}\nColumns: (could not be retrieved)\n"

                logger.info(f"  -> Retrieved {len(schema_info)} chars of schema data.")
                _SCHEMA_CACHE = (schema_info, now)
                return {"schema": schema_info}
            except Exception as exc:
                error_msg = f"Error retrieving schema: {exc}"
                logger.error(f"  -> {error_msg}")
                return {"schema": error_msg}

        # Node 3 — LLM decomposes the question
        def decompose_question(state: AgentState):
            logger.info(f"[Node: decompose_question] Asking LLM to break down question: '{state['question']}'")
            prompt = PromptTemplate.from_template(
                "You are a data analytics orchestrator for a media analytics platform.\n\n"
                "Database Schema (overview):\n{schema}\n\n"
                "Business Metric Definitions:\n{context}\n\n"
                "User question: {question}\n\n"
                "Decide how many charts are needed to answer this question.\n"
                "IMPORTANT RULES:\n"
                "- DEFAULT to 1 chart. Only return more than 1 if the question EXPLICITLY asks for "
                "  multiple unrelated views (e.g. 'show me X AND ALSO Y by Z').\n"
                "- Questions like 'show me X vs Y' or 'compare A and B' are STILL 1 chart "
                "  (multi-series on the same chart).\n"
                "- Never return more than 3 charts.\n"
                "- Do NOT generate overlapping or redundant charts.\n\n"
                "Respond with a JSON array of objects. Each object must have exactly:\n"
                "  sub_question    -- the specific data question for this chart (full sentence)\n"
                "  chart_type_hint -- one of: bar, line, pie\n\n"
                "Return ONLY the JSON array, no markdown, no extra text.\n\n"
                'Example (single chart): [{{"sub_question": "Total sessions by channel?", "chart_type_hint": "bar"}}]\n'
                'Example (two charts only when both EXPLICITLY requested): '
                '[{{"sub_question": "Revenue by region?", "chart_type_hint": "bar"}}, '
                '{{"sub_question": "Revenue trend over time?", "chart_type_hint": "line"}}]'
            )
            response = llm_orchestrator.invoke(
                prompt.format(
                    schema=state.get("schema", ""),
                    context=state.get("semantic_context", ""),
                    question=state["question"],
                )
            )
            
            specs = _extract_json_array(response.content)

            if not specs:
                logger.warning("  -> LLM failed to return valid JSON array, falling back to 1 spec.")
                specs = [{"sub_question": state["question"], "chart_type_hint": "bar"}]
            else:
                # Hard cap at 3 regardless of what the LLM returns
                specs = specs[:3]

            logger.info(f"  -> Generated {len(specs)} chart spec(s): {[s.get('sub_question', '') for s in specs]}")
            return {"chart_specs": specs}

        # Node 4 — Process all chart specs concurrently
        async def generate_all_charts(state: AgentState):
            specs  = state.get("chart_specs", [])
            schema  = state.get("schema", "")
            context = state.get("semantic_context", "")

            logger.info(f"\n[Node: generate_all_charts] Processing {len(specs)} chart(s) in parallel via MCP...")

            if not specs:
                logger.error("  -> ERROR: No specs to process.")
                return {"chart_specs": [], "error": "No chart specs were produced."}

            tasks = [_process_single_spec(mcp, spec, schema, context) for spec in specs]
            completed = await asyncio.gather(*tasks)

            logger.info("  -> All parallel chart tasks completed.")
            return {"chart_specs": completed}

        # Node 5 — Format all chart results
        def format_json_output(state: AgentState):
            specs = state.get("chart_specs", [])
            logger.info(f"\n[Node: format_json_output] Formatting {len(specs)} chart(s) into JSON...")
            
            charts_output = []
            for spec in specs:
                config = spec.get("chart_config", {}).copy()
                
                if "data" in config:
                    config["data"] = config["data"].copy()
                    config["data"]["labels"] = []
                    if "datasets" in config["data"]:
                        new_datasets = []
                        for ds in config["data"]["datasets"]:
                            ds_copy = ds.copy()
                            ds_copy["data"] = []
                            new_datasets.append(ds_copy)
                        config["data"]["datasets"] = new_datasets

                charts_output.append({
                    "title": spec.get("chart_attrs", {}).get("title", "Chart") or spec.get("sub_question"),
                    "sql": spec.get("sql_query", ""),
                    "config": config,
                    "error": spec.get("sql_error", "")
                })
            
            output_data = {
                "question": state.get("question", ""),
                "insights": state.get("insights", ""),
                "error": state.get("error", ""),
                "charts": charts_output
            }
            
            return {"chart_json": json.dumps(output_data, indent=2)}

        # Node 6 — Generate holistic insights
        def generate_insights(state: AgentState):
            specs = state.get("chart_specs", [])
            logger.info("\n[Node: generate_insights] Synthesising holistic business insights from chart data...")

            # Increased row limit from 20 to 100 for better insights
            all_data = [
                {"chart": s.get("sub_question", ""), "data": s.get("records", [])[:100]}
                for s in specs
                if s.get("records")
            ]

            if not all_data:
                print("  -> ERROR: No records found to generate insights.")
                return {"insights": "No data was returned — cannot generate insights."}

            data_str = json.dumps(all_data, indent=2, default=str)

            prompt = PromptTemplate.from_template(
                "You are a business analyst for a media analytics platform.\n"
                "The user's overall question was: {question}\n\n"
                "Data retrieved across {n} chart(s):\n{data}\n\n"
                "Provide 3-5 concise, actionable bullet-point insights that directly answer the user's "
                "question. Synthesise across all charts where relevant. "
                "Focus on key trends, comparisons, or anomalies. "
                "Use business language only — no code, no SQL."
            )
            insights = llm_analyst.invoke(
                prompt.format(
                    question=state.get("question", ""),
                    n=len(all_data),
                    data=data_str,
                )
            ).content
            logger.info("  -> Insights generated successfully.")
            return {"insights": insights}

        # Node 7 — Surface errors gracefully
        def handle_error(state: AgentState):
            return {
                "insights": f"Pipeline error: {state.get('error', 'Unknown error')}",
                "chart_json": "{}",
            }

        # -- Routing --------------------------------------------------------------

        def route_after_decompose(state: AgentState) -> str:
            return "handle_error" if not state.get("chart_specs") else "generate_all_charts"

        # -- Build graph ----------------------------------------------------------

        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve_context",    retrieve_context)
        workflow.add_node("get_schema",          get_schema)
        workflow.add_node("decompose_question",  decompose_question)
        workflow.add_node("generate_all_charts", generate_all_charts)
        workflow.add_node("format_json_output",  format_json_output)
        workflow.add_node("generate_insights",   generate_insights)
        workflow.add_node("handle_error",        handle_error)

        workflow.set_entry_point("retrieve_context")
        workflow.add_edge("retrieve_context",   "get_schema")
        workflow.add_edge("get_schema",         "decompose_question")
        workflow.add_conditional_edges(
            "decompose_question",
            route_after_decompose,
            {"generate_all_charts": "generate_all_charts", "handle_error": "handle_error"},
        )
        workflow.add_edge("generate_all_charts", "generate_insights")
        workflow.add_edge("generate_insights",   "format_json_output")
        workflow.add_edge("format_json_output",  END)
        workflow.add_edge("handle_error",        END)

        # Build and compile the graph
        app = workflow.compile()

        # Run the pipeline and capture the state
        final_output = await app.ainvoke(
            {
                "question":         question,
                "semantic_context": "",
                "schema":           "",
                "chart_specs":      [],
                "chart_json":       "{}",
                "insights":         "",
                "error":            "",
            }
        )
        return final_output


# --- Interactive Loop -------------------------------------------------------

async def run_agent():
    print("--- Orchestrated Multi-Chart Analytics Agent (MCP) ----------------")
    print("Connecting to MCP server...\n")

    async with MCPClient() as mcp:
        tables_raw = await mcp.call_tool("list_tables")
        tables = json.loads(tables_raw)
        print(f"✓ Connected! {len(tables)} tables available:")
        for t in tables:
            print(f"  • {t['name']}")
        print("\nType 'quit' to exit.\n")

        loop = asyncio.get_event_loop()

        while True:
            user_query = (
                await loop.run_in_executor(None, input, "Ask about the GCData: ")
            ).strip()

            if user_query.lower() == "quit":
                print("Goodbye!")
                break

            if not user_query:
                continue

            print("\n Processing...\n")
            try:
                # build_and_run_pipeline now manages its own internall MCP session
                result = await build_and_run_pipeline(user_query)

                specs = result.get("chart_specs", [])
                print(f"Charts generated: {len(specs)}")
                for i, s in enumerate(specs, 1):
                    has_data = bool(s.get("records"))
                    status = "OK" if has_data else "FAILED"
                    print(f"  [{status}] Chart {i}: {s.get('sub_question', '')}")
                    if not has_data and s.get("sql_error"):
                        print(f"           Error: {s['sql_error']}")

                print("\nInsights:")
                print(result["insights"])

                chart_json_str = result.get("chart_json", "")
                if chart_json_str:
                    print("\nFinal Output (JSON):")
                    print(chart_json_str)

                    with open("agent_output.json", "w", encoding="utf-8") as f:
                        f.write(chart_json_str)
                    print(f"\nOutput saved to agent_output.json")

            except Exception as exc:
                print(f"\nAgent error: {exc}")

            print()


if __name__ == "__main__":
    asyncio.run(run_agent())