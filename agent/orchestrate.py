"""
orchestrate.py
--------------
Multi-chart analytics agent with parallel SQL execution and XML dashboard merging.

Pipeline:
    retrieve_context -> get_schema -> decompose_question
                                             |
                                     generate_all_charts   <- each chart spec runs in parallel
                                     (SQL gen + execute + chart per spec, with retry)
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
import os
from datetime import date
from typing import Any, Dict, List, Optional, TypedDict
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

# Import all tool functions directly from the tools package
from tools import (
    execute_sql_query,
    generate_plotly_chart,
    generate_chartjs_json,
    get_frammer_schema,
    retrieve_metric_definitions,
)

# --- Environment & LLMs -----------------------------------------------------

load_dotenv()

# Strict model: SQL generation, JSON decisions, chart attr selection
llm_orchestrator = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# Creative model: business insights synthesis
llm_analyst = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)


# --- Agent State ------------------------------------------------------------

class AgentState(TypedDict):
    question:          str
    semantic_context:  str           # Output of retrieve_metric_definitions
    schema:            str           # Output of get_frammer_schema
    chart_specs:       List[Dict]    # Decomposed chart specs; each gets enriched in-place
    chart_json:        str           # Final merged XML dashboard
    insights:          str           # LLM-generated business insights
    error:             str           # Pipeline-level error message


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


def _generate_chart_attrs(sql: str, sub_question: str, records: List[Dict], chart_type_hint: Optional[str] = None) -> Dict:
    """Decide chart type and axes for a single spec using the real column names (synchronous)."""
    sample_rows = records[:3]
    col_names = list(sample_rows[0].keys()) if sample_rows else []

    col_hint = (
        f"Available columns in the result: {col_names}\n"
        f"Sample rows: {json.dumps(sample_rows, default=str)}\n\n"
        if col_names else ""
    )

    hint_str = f"The orchestrator suggests '{chart_type_hint}' for this chart. Strongly prefer this unless the data format makes it impossible.\n" if chart_type_hint else ""

    prompt = PromptTemplate.from_template(
        "You are a data visualisation expert.\n\n"
        "SQL query that produced the data:\n{sql}\n\n"
        "{col_hint}"
        "User question: {question}\n\n"
        "{hint_str}"
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
        prompt.format(sql=sql, question=sub_question, col_hint=col_hint, hint_str=hint_str)
    ).content.strip().strip("```json").strip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _process_single_spec(spec: Dict, schema: str, context: str) -> Dict:
    """
    Run the full SQL -> execute -> chart-attrs -> chart-xml pipeline for one spec.
    Retries SQL generation up to 3 times on execution error.
    Returns the input spec dict enriched with 'sql_query', 'records', and 'chart_xml'.
    """
    sub_question = spec.get("sub_question", "")
    spec_error = ""

    for _attempt in range(3):
        sql = _generate_sql_for_spec(sub_question, schema, context, error=spec_error)
        raw_result = execute_sql_query(sql, chart_attributes={})
        parsed = json.loads(raw_result)

        if "error" in parsed:
            spec_error = parsed["error"]
            continue  # Retry with the error in context

        # SQL succeeded
        records = parsed.get("data", [])
        attrs = _generate_chart_attrs(sql, sub_question, records, chart_type_hint=spec.get("chart_type_hint"))

        # Override type with LLM's initial hint if the formatter left it blank
        if not attrs.get("type") and spec.get("chart_type_hint"):
            attrs["type"] = spec["chart_type_hint"]

        chart_xml = generate_plotly_chart(data_records=records, chart_attributes=attrs) if records else ""
        chart_js  = generate_chartjs_json(data_records=records, chart_attributes=attrs) if records else "{}"

        return {**spec, "sql_query": sql, "records": records, "chart_attrs": attrs, "chart_xml": chart_xml, "chart_js": chart_js}

    # All 3 retries exhausted
    return {**spec, "sql_query": "", "records": [], "chart_attrs": {}, "chart_xml": "", "chart_js": "{}", "sql_error": spec_error}


# --- LangGraph Pipeline -----------------------------------------------------

async def build_and_run_pipeline(question: str) -> AgentState:
    """
    Compile and run the LangGraph pipeline for a single user question.
    Generates one or more charts in parallel, then merges their XMLs.
    """

    # Node 1 — Retrieve semantic/business context
    def retrieve_context(state: AgentState):
        result = retrieve_metric_definitions(state["question"])
        return {"semantic_context": result}

    # Node 2 — Fetch live DB schema
    def get_schema(state: AgentState):
        result = get_frammer_schema()
        return {"schema": result}

    # Node 3 — LLM decomposes the question into 1-4 chart specs
    def decompose_question(state: AgentState):
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
            specs = [{"sub_question": state["question"], "chart_type_hint": "bar"}]

        return {"chart_specs": specs}

    # Node 4 — Process all chart specs concurrently
    async def generate_all_charts(state: AgentState):
        specs  = state.get("chart_specs", [])
        schema  = state.get("schema", "")
        context = state.get("semantic_context", "")

        if not specs:
            return {"chart_specs": [], "error": "No chart specs were produced."}

        # asyncio.gather + run_in_executor lets synchronous SQL + LLM calls
        # for each spec run concurrently without blocking the event loop.
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, _process_single_spec, spec, schema, context)
            for spec in specs
        ]
        completed = await asyncio.gather(*tasks)
        return {"chart_specs": list(completed)}

    # Node 5 — Merge all XML outputs into one consistent dashboard
    def merge_xml(state: AgentState):
        specs = state.get("chart_specs", [])
        xml_strings = [s.get("chart_xml", "") for s in specs]
        valid_xmls  = [x for x in xml_strings if x and x.strip().startswith("<?xml")]

        if not valid_xmls:
            return {"chart_json": "{}"}

        merged = _merge_dashboard_xmls(valid_xmls, title=state.get("question", "Dashboard"))
        return {"chart_json": merged}

    # Node 6 — Generate holistic insights across ALL chart data (uses Analyst LLM)
    def generate_insights(state: AgentState):
        specs = state.get("chart_specs", [])

        # Assemble a combined payload: {chart_title, first 20 rows}
        all_data = [
            {"chart": s.get("sub_question", ""), "data": s.get("records", [])[:20]}
            for s in specs
            if s.get("records")
        ]

        if not all_data:
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
    print("--- Orchestrated Multi-Chart Analytics Agent --------------------------")
    print("Tools loaded from: tools/")
    print("Type 'quit' to exit.\n")

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

        print("\n Processing (Multi-Chart Parallel)...\n")
        try:
            result = await build_and_run_pipeline(user_query)

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

            # Print SQL and Chart.js Config for each chart
            for i, s in enumerate(specs, 1):
                print(f"\n--- Chart {i}: {s.get('sub_question', '')} ---")
                print("📜 SQL Query:")
                print(s.get("sql_query", "N/A"))
                print("\n📊 Chart.js Config (JSON):")
                print(s.get("chart_js", "{}"))

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
