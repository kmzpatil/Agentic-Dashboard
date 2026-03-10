"""
orchestrate.py
--------------
Multi-chart analytics agent with parallel SQL execution and XML dashboard merging.
Connects to the MCP server via stdio using the MCPClient.

Pipeline:
    retrieve_context -> get_schema -> decompose_question
                                             |
                                     generate_all_charts   <- each chart spec runs in parallel
                                     (MCP tool call + chart per spec, with SQL fallback & retry)
                                             |
                                         merge_xml --> generate_insights --> END
                                             |
                                       handle_error --> END

    decompose_question splits the user question into 1-4 focused chart specs.
    generate_all_charts processes ALL specs concurrently using asyncio.gather.
    merge_xml combines all individual dashboard XMLs into one consistent <dashboard>.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import date
from typing import Any, Dict, List, Optional, TypedDict
import xml.etree.ElementTree as ET

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

# Local tools that don't need the MCP server
from tools.metric_definitions import retrieve_metric_definitions
from tools.chart import generate_plotly_chart

# MCP client for communicating with mcp_server via stdio
import sys
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


# --- XML Merge Helper -------------------------------------------------------

def _merge_dashboard_xmls(xml_strings: List[str], title: str = "Dashboard") -> str:
    """
    Merge multiple single-chart dashboard XML strings into one <dashboard>
    that contains all <row> elements under a single <layout>.
    Row IDs are renumbered sequentially so they are globally unique.
    """
    root = ET.Element("dashboard", {"version": "1.0", "theme": "light", "cols": "12"})

    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "title").text = title
    ET.SubElement(meta, "description").text = "Auto-generated multi-chart analytics dashboard"
    ET.SubElement(meta, "created").text = date.today().isoformat()

    layout = ET.SubElement(root, "layout")
    row_counter = 1

    for xml_str in xml_strings:
        if not xml_str or not xml_str.strip().startswith("<?xml"):
            continue
        try:
            # Strip the XML declaration so ET.fromstring can parse the element
            clean = xml_str.split("?>", 1)[-1].strip()
            chart_root = ET.fromstring(clean)
            chart_layout = chart_root.find("layout")
            if chart_layout is not None:
                for row in list(chart_layout):
                    row.set("id", f"r{row_counter}")
                    row_counter += 1
                    layout.append(row)
        except ET.ParseError:
            continue  # Skip malformed XML chunks silently

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


# --- MCP Tool Helpers -------------------------------------------------------

# Tool names as registered on the MCP server (from GCDataToolModule + DatabaseToolModule)
MCP_DOMAIN_TOOLS = {
    "get_channel_metrics",
    "get_top_channels_by_platform",
    "get_monthly_trend",
    "get_language_breakdown",
    "get_input_type_breakdown",
    "get_output_type_breakdown",
    "search_videos",
    "get_video_stats_by_team",
    "get_video_stats_by_platform",
}

MCP_DB_TOOLS = {
    "list_tables",
    "describe_table",
    "execute_sql_query",
    "get_database_overview",
    "preview_table",
}


def _normalise_tool_result(raw: str) -> list:
    """Parse whatever JSON a tool returns into a flat list of row dicts."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        # try common wrapper keys
        for key in ("rows", "top_channels", "data", "items"):
            if key in obj and isinstance(obj[key], list):
                return obj[key]
        # single-dict result → wrap in list
        return [obj]
    return []


# --- Per-Spec Processing Helpers --------------------------------------------

def _generate_sql_for_spec(sub_question: str, schema: str, context: str, error: str = "") -> str:
    """Generate a PostgreSQL SELECT query for a single chart spec (synchronous)."""
    prompt = PromptTemplate.from_template(
        "Database Schema:\n{schema}\n\n"
        "Business Metric Definitions: {context}\n\n"
        "Previous Error (fix this if present): {error}\n\n"
        "Question: {question}\n\n"
        "Write a valid PostgreSQL SELECT query to answer the question.\n"
        "CRITICAL RULES:\n"
        "1. ONLY use EXACT table and column names from the Database Schema above.\n"
        "2. DO NOT guess table names. Do not drop plurals "
        "(e.g. use 'channel_metrics', NOT 'channel_metric').\n"
        "3. Return ONLY the raw SQL query string — no markdown fences, no formatting, no explanation."
    )
    raw = llm_orchestrator.invoke(
        prompt.format(schema=schema, context=context, error=error, question=sub_question)
    ).content
    return raw.strip().strip("```sql").strip("```").strip()


def _generate_chart_attrs(sql: str, sub_question: str, records: List[Dict]) -> Dict:
    """Decide chart type and axes for a single spec using the real column names (synchronous)."""
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
    raw = llm_orchestrator.invoke(
        prompt.format(sql=sql, question=sub_question, col_hint=col_hint)
    ).content.strip().strip("```json").strip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def _fetch_data_via_mcp(
    client: MCPClient,
    sub_question: str,
    schema: str,
    context: str,
    available_tools: list[dict],
) -> tuple[list | None, str | None]:
    """
    Ask the LLM (with all MCP tool schemas) to pick the best tool for the question.
    Executes the chosen tool via the MCP client and returns (records, tool_ref).
    Falls back to raw SQL if no tool call is made or the tool returns nothing.
    """
    # Build LangChain-compatible tool schemas for bind_tools dynamically
    from langchain_core.tools import StructuredTool

    # Filter to domain tools only (not generic DB tools) for LLM selection
    domain_tool_schemas = [t for t in available_tools if t["name"] in MCP_DOMAIN_TOOLS]
    # Also include execute_sql_query as a last-resort option
    sql_tool_schema = [t for t in available_tools if t["name"] == "execute_sql_query"]
    tool_schemas = domain_tool_schemas + sql_tool_schema

    tool_names = [t["name"] for t in tool_schemas]

    prompt = (
        f"Database schema:\n{schema}\n\n"
        f"Business context:\n{context}\n\n"
        f"Question: {sub_question}\n\n"
        "You MUST call ONE of the available tools to fetch data for this question.\n"
        f"Available tools: {', '.join(tool_names)}\n\n"
        "RULES:\n"
        "1. ALWAYS prefer domain tools (e.g. get_top_channels_by_platform, get_monthly_trend).\n"
        "2. Only use execute_sql_query as an absolute last resort if NO other tool works."
    )

    # Bind MCP tool schemas to the LLM for tool calling
    llm_with_tools = llm_orchestrator.bind_tools(tool_schemas)
    response = llm_with_tools.invoke([HumanMessage(content=prompt)])

    if response.tool_calls:
        call = response.tool_calls[0]
        tool_name = call["name"]
        tool_args = call.get("args", {})

        if tool_name in tool_names:
            logger.info(f"  -> [MCP Client] Calling tool: {tool_name}({tool_args})")
            raw = await client.call_tool(tool_name, tool_args)
            records = _normalise_tool_result(raw)
            if records:
                return records, f"tool:{tool_name}"

    # Fallback: generate and execute raw SQL
    return None, None


async def _process_single_spec(
    client: MCPClient,
    spec: Dict,
    schema: str,
    context: str,
    available_tools: list[dict],
) -> Dict:
    """
    Run the MCP-tool-first pipeline for a single chart spec:
      1. Try the most appropriate MCP tool via LLM tool-calling.
      2. Fall back to SQL generation + execution via MCP (with up to 3 retries).
      3. Generate chart attributes and chart XML from the result data.
    Returns the spec dict enriched with records, chart_attrs, and chart_xml.
    """
    sub_question = spec.get("sub_question", "")

    # ── Step 1: Try MCP tool calling ──────────────────────────────────────────
    records, ref = await _fetch_data_via_mcp(client, sub_question, schema, context, available_tools)

    if records:
        attrs = _generate_chart_attrs(ref, sub_question, records)
        if not attrs.get("type") and spec.get("chart_type_hint"):
            attrs["type"] = spec["chart_type_hint"]
        chart_xml = generate_plotly_chart(data_records=records, chart_attributes=attrs) if records else ""
        logger.info("   [MCP TOOL] %s  ->  %d rows", ref, len(records))
        return {**spec, "sql_query": ref, "records": records, "chart_attrs": attrs, "chart_xml": chart_xml}

    # ── Step 2: SQL fallback via MCP execute_sql_query tool ───────────────────
    spec_error = ""
    for _attempt in range(3):
        sql = _generate_sql_for_spec(sub_question, schema, context, error=spec_error)
        logger.info("  -> [MCP Client] SQL fallback attempt %d: %s...", _attempt + 1, sql[:80])
        raw_result = await client.call_tool("execute_sql_query", {"query": sql})

        # MCP server's execute_sql_query returns JSON with "rows" key on success
        # or a string starting with "Error:" on failure
        if raw_result.startswith("Error"):
            spec_error = raw_result
            continue

        parsed = json.loads(raw_result)

        if "error" in parsed:
            spec_error = parsed["error"]
            continue

        records = parsed.get("rows", parsed.get("data", []))
        attrs = _generate_chart_attrs(sql, sub_question, records)
        if not attrs.get("type") and spec.get("chart_type_hint"):
            attrs["type"] = spec["chart_type_hint"]
        chart_xml = generate_plotly_chart(data_records=records, chart_attributes=attrs) if records else ""
        logger.info("   [MCP SQL FALLBACK]  ->  %d rows", len(records))
        return {**spec, "sql_query": sql, "records": records, "chart_attrs": attrs, "chart_xml": chart_xml}

    # All retries exhausted
    logger.warning("   [MCP SQL FALLBACK] FAILED after 3 retries")
    return {**spec, "sql_query": "", "records": [], "chart_attrs": {}, "chart_xml": "", "sql_error": spec_error}


# --- LangGraph Pipeline -----------------------------------------------------

async def build_and_run_pipeline(question: str, client: MCPClient) -> AgentState:
    """
    Compile and run the LangGraph pipeline for a single user question.
    Generates one or more charts in parallel, then merges their XMLs.
    All data is fetched through the MCP server via the client.
    """
    # Fetch the tool list from the MCP server once for this pipeline run
    available_tools = await client.list_tools()
    print(f"  -> [MCP Client] {len(available_tools)} tools available from MCP server")

    # Node 1 — Retrieve semantic/business context (in-memory, no MCP needed)
    def retrieve_context(state: AgentState):
        logger.info("\n[Node: retrieve_context] Fetching business metric definitions...")
        result = retrieve_metric_definitions(state["question"])
        logger.info(f"  -> Retrieved {len(result)} chars of business context.")
        return {"semantic_context": result}

    # Node 2 — Fetch live DB schema via MCP tools
    async def get_schema(state: AgentState):
        logger.info("[Node: get_schema] Fetching live database schema via MCP server...")
        try:
            tables_json = await client.call_tool("list_tables", {})
            tables = json.loads(tables_json)

            schema_info = "GCData Analytics Database Schema (PostgreSQL / Supabase):\n"
            for table_entry in tables:
                table_name = table_entry["name"]
                try:
                    details_json = await client.call_tool("describe_table", {"table_name": table_name})
                    details = json.loads(details_json)
                    cols = ", ".join(
                        f"{c['name']} ({c['type']})"
                        for c in details.get("columns", [])
                    )
                    schema_info += f"\nTable: {table_name}\nColumns: {cols}\n"
                except Exception:
                    schema_info += f"\nTable: {table_name}\nColumns: (could not be retrieved)\n"

            logger.info(f"  -> Retrieved {len(schema_info)} chars of schema data.")
            return {"schema": schema_info}
        except Exception as exc:
            error_msg = f"Error retrieving schema: {exc}"
            logger.error(f"  -> {error_msg}")
            return {"schema": error_msg}

    # Node 3 — LLM decomposes the question into 1-4 chart specs
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
        raw = llm_orchestrator.invoke(
            prompt.format(
                schema=state.get("schema", ""),
                context=state.get("semantic_context", ""),
                question=state["question"],
            )
        ).content.strip().strip("```json").strip("```").strip()

        try:
            specs = json.loads(raw)
            if not isinstance(specs, list) or not specs:
                raise ValueError("Empty or non-list response")
            # Hard cap at 3 regardless of what the LLM returns
            specs = specs[:3]
        except (json.JSONDecodeError, ValueError):
            # Fallback: treat the whole question as one spec
            logger.warning("  -> LLM failed to return valid JSON array, falling back to 1 spec.")
            specs = [{"sub_question": state["question"], "chart_type_hint": "bar"}]

        logger.info(f"  -> Generated {len(specs)} chart spec(s): {[s.get('sub_question', '') for s in specs]}")
        return {"chart_specs": specs}

    # Node 4 — Process all chart specs concurrently via MCP
    async def generate_all_charts(state: AgentState):
        specs  = state.get("chart_specs", [])
        schema  = state.get("schema", "")
        context = state.get("semantic_context", "")
        
        logger.info(f"\n[Node: generate_all_charts] Processing {len(specs)} chart(s) via MCP server...")

        if not specs:
            logger.error("  -> ERROR: No specs to process.")
            return {"chart_specs": [], "error": "No chart specs were produced."}

        # Process specs sequentially since they share a single MCP client session
        completed = []
        for spec in specs:
            result = await _process_single_spec(client, spec, schema, context, available_tools)
            completed.append(result)

        logger.info("  -> All chart tasks completed.")
        return {"chart_specs": completed}

    # Node 5 — Merge all XML outputs into one consistent dashboard
    def merge_xml(state: AgentState):
        specs = state.get("chart_specs", [])
        logger.info(f"\n[Node: merge_xml] Merging {len(specs)} chart XMLs into single dashboard...")
        xml_strings = [s.get("chart_xml", "") for s in specs]
        valid_xmls  = [x for x in xml_strings if x and x.strip().startswith("<?xml")]

        if not valid_xmls:
            logger.error("  -> ERROR: No valid XML charts generated.")
            return {"chart_json": "{}"}

        merged = _merge_dashboard_xmls(valid_xmls, title=state.get("question", "Dashboard"))
        logger.info(f"  -> Successfully merged {len(valid_xmls)} XMLs.")
        return {"chart_json": merged}

    # Node 6 — Generate holistic insights across ALL chart data (uses Analyst LLM)
    def generate_insights(state: AgentState):
        specs = state.get("chart_specs", [])
        logger.info("\n[Node: generate_insights] Synthesising holistic business insights from chart data...")

        # Assemble a combined payload: {chart_title, first 20 rows}
        all_data = [
            {"chart": s.get("sub_question", ""), "data": s.get("records", [])[:20]}
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

    # Node 7 — Surface pipeline-level errors gracefully
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
    workflow.add_node("merge_xml",           merge_xml)
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
    workflow.add_edge("generate_all_charts", "merge_xml")
    workflow.add_edge("merge_xml",           "generate_insights")
    workflow.add_edge("generate_insights",   END)
    workflow.add_edge("handle_error",        END)

    app = workflow.compile()

    return await app.ainvoke(
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


# --- Interactive Loop -------------------------------------------------------

async def run_agent():
    print("--- Orchestrated Multi-Chart Analytics Agent (MCP Client) ---------------")
    print("Connecting to MCP server via stdio...\n")

    async with MCPClient() as client:
        tools = await client.list_tools()
        print(f"✓ Connected! {len(tools)} tools available:")
        for t in tools:
            print(f"  • {t['name']}")
        print("\nType 'quit' to exit.\n")

        loop = asyncio.get_event_loop()

        while True:
            user_query = (
                await loop.run_in_executor(None, input, "Ask about the Frammer data: ")
            ).strip()

            if user_query.lower() == "quit":
                print("Goodbye!")
                break

            if not user_query:
                continue

            print("\n Processing (Multi-Chart via MCP)...\n")
            try:
                result = await build_and_run_pipeline(user_query, client)

                # Show chart generation summary
                specs = result.get("chart_specs", [])
                print(f"Charts generated: {len(specs)}")
                for i, s in enumerate(specs, 1):
                    ok = s.get("chart_xml", "").startswith("<?xml")
                    status = "OK" if ok else "FAILED"
                    print(f"  [{status}] Chart {i}: {s.get('sub_question', '')}")
                    if not ok and s.get("sql_error"):
                        print(f"           Error: {s['sql_error']}")

                print("\nInsights:")
                print(result["insights"])

                chart = result.get("chart_json", "")
                if chart and chart.strip().startswith("<?xml"):
                    chart_path = "chart_output.xml"
                    with open(chart_path, "w", encoding="utf-8") as f:
                        f.write(chart)
                    print(f"\nDashboard XML saved to {chart_path}")
                elif chart and chart not in ("{}", ""):
                    try:
                        chart_obj = json.loads(chart)
                        if "error" in chart_obj:
                            print(f"\nChart warning: {chart_obj['error']}")
                    except json.JSONDecodeError:
                        pass

            except Exception as exc:
                print(f"\nAgent error: {exc}")

            print()


if __name__ == "__main__":
    asyncio.run(run_agent())
