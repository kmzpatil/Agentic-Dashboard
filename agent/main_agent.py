"""
main_agent.py
─────────────
Standalone analytics agent that follows a LangGraph pipeline, calling tool
functions in tools/ directly (no MCP server required).

Pipeline:
    retrieve_context → get_schema → generate_sql → decide_chart_attrs
                                                          ↓
                                                    execute_sql
                                         ┌──────────────┤
                            (error, retry_count < 3)     (success)
                                         ↓               ↓
                                    generate_sql   generate_chart
                                                         ↓
                                                  generate_insights → END

    If 3 SQL retries are exhausted the graph routes to handle_sql_error → END.
"""

import asyncio
import json
import os
from typing import Any, Dict, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

# Import all tool functions directly from the tools package
from tools import (
    execute_sql_query,
    generate_plotly_chart,
    get_frammer_schema,
    retrieve_metric_definitions,
)

# ─── Environment & LLM ───────────────────────────────────────────────────────

load_dotenv()
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# ─── Agent State ─────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:          str
    semantic_context:  str              # Output of retrieve_metric_definitions
    schema:            str              # Output of get_frammer_schema
    sql_query:         str              # LLM-generated SQL
    chart_attributes:  Dict[str, Any]  # LLM-decided chart config
    data:              str              # JSON string from execute_sql_query
    chart_json:        str              # Serialised Plotly figure
    insights:          str              # LLM-generated business insights
    error:             str              # Last SQL error (used for self-correction)
    retry_count:       int              # Guards against infinite retry loops

# ─── Pipeline ────────────────────────────────────────────────────────────────

async def build_and_run_pipeline(question: str) -> AgentState:
    """
    Compile and run the LangGraph pipeline for a single user question.
    All heavy lifting is done by the pure Python functions in tools/.
    """

    # Node 1 — Retrieve semantic/business context
    def retrieve_context(state: AgentState):
        result = retrieve_metric_definitions(state["question"])
        return {"semantic_context": result}

    # Node 2 — Fetch live DB schema
    def get_schema(state: AgentState):
        result = get_frammer_schema()
        return {"schema": result}

    # Node 3 — LLM generates SQL (also used during self-correction retries)
    def generate_sql(state: AgentState):
        prompt = PromptTemplate.from_template(
            "Database Schema:\n{schema}\n\n"
            "Business Metric Definitions: {context}\n\n"
            "Previous Error (fix this if present): {error}\n\n"
            "Question: {question}\n\n"
            "Write a valid PostgreSQL SELECT query to answer the question.\n"
            "CRITICAL RULES:\n"
            "1. ONLY use EXACT table and column names from the Database Schema above.\n"
            "2. DO NOT guess table names. Do not drop plurals (e.g. use 'channel_metrics', NOT 'channel_metric').\n"
            "3. Return ONLY the raw SQL query string — no markdown fences, no formatting, no explanation."
        )
        raw = llm.invoke(
            prompt.format(
                schema=state.get("schema", ""),
                context=state.get("semantic_context", ""),
                error=state.get("error", ""),
                question=state["question"],
            )
        ).content
        # Strip markdown code fences if the LLM wraps the query
        query = raw.strip().strip("```sql").strip("```").strip()
        return {"sql_query": query, "error": ""}

    # Node 3.5 — LLM decides chart configuration from the SQL + question
    def decide_chart_attributes(state: AgentState):
        prompt = PromptTemplate.from_template(
            "You are a data visualisation expert.\n\n"
            "SQL query:\n{sql}\n\n"
            "User question: {question}\n\n"
            "Respond with a single valid JSON object (no markdown) with these keys:\n"
            "  type    — one of: bar, line, scatter, pie\n"
            "  x_axis  — exact column name for the X axis\n"
            "  y_axis  — exact column name for the Y axis\n"
            "  title   — a short, descriptive chart title\n\n"
            "Return ONLY the JSON object."
        )
        raw = llm.invoke(
            prompt.format(sql=state.get("sql_query", ""), question=state["question"])
        ).content.strip()

        # Strip fences if the LLM wraps the JSON
        raw = raw.strip("```json").strip("```").strip()
        try:
            attrs = json.loads(raw)
        except json.JSONDecodeError:
            # Safe fallback — chart.py will auto-guess from column position
            attrs = {}

        return {"chart_attributes": attrs}

    # Node 4 — Execute SQL; flag errors for the self-correction loop
    def execute_sql(state: AgentState):
        result = execute_sql_query(
            state["sql_query"],
            chart_attributes=state.get("chart_attributes", {}),
        )
        parsed = json.loads(result)
        if "error" in parsed:
            return {
                "error": parsed["error"],
                "data": "[]",
                "retry_count": state.get("retry_count", 0) + 1,
            }
        return {"data": result, "error": ""}

    # Node 5 — Build Plotly chart from the already-fetched data (no second DB hit)
    def generate_chart(state: AgentState):
        raw_data = state.get("data", "{}")
        try:
            payload = json.loads(raw_data)
            records = payload.get("data", [])
            attrs   = payload.get("chart_attributes", state.get("chart_attributes", {}))
        except (json.JSONDecodeError, AttributeError):
            records = []
            attrs   = state.get("chart_attributes", {})

        if not records:
            return {"chart_json": "{}"}

        result = generate_plotly_chart(data_records=records, chart_attributes=attrs)
        # If charting failed, result is an error JSON — store it as-is so the
        # caller can inspect it; insights generation will handle the empty case.
        return {"chart_json": result}

    # Node 6 — LLM derives business insights from the data rows only
    def generate_insights(state: AgentState):
        raw_data = state.get("data", "{}")
        try:
            payload    = json.loads(raw_data)
            data_rows  = payload.get("data", [])
            data_str   = json.dumps(data_rows, indent=2)
        except (json.JSONDecodeError, AttributeError):
            data_str = raw_data  # fall back to whatever is in state

        if not data_str or data_str in ("[]", "{}"):
            return {"insights": "No data was returned by the query — cannot generate insights."}

        prompt = PromptTemplate.from_template(
            "You are a business analyst. Analyse the following dataset and provide "
            "2-3 concise, actionable bullet-point insights:\n\n{data}"
        )
        insights = llm.invoke(prompt.format(data=data_str)).content
        return {"insights": insights}

    # Node 7 — Surface a clear error message when all SQL retries are exhausted
    def handle_sql_error(state: AgentState):
        return {
            "insights": (
                f"Could not generate a valid SQL query after "
                f"{state.get('retry_count', 3)} attempts.\n"
                f"Last error: {state.get('error', 'Unknown error')}"
            ),
            "chart_json": "{}",
        }

    # ── Routing ───────────────────────────────────────────────────────────────

    def route_after_sql(state: AgentState) -> str:
        if state.get("error"):
            return "generate_sql" if state.get("retry_count", 0) < 3 else "handle_sql_error"
        return "generate_chart"

    # ── Build the graph ───────────────────────────────────────────────────────

    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve_context",       retrieve_context)
    workflow.add_node("get_schema",             get_schema)
    workflow.add_node("generate_sql",           generate_sql)
    workflow.add_node("decide_chart_attributes", decide_chart_attributes)
    workflow.add_node("execute_sql",            execute_sql)
    workflow.add_node("generate_chart",         generate_chart)
    workflow.add_node("generate_insights",      generate_insights)
    workflow.add_node("handle_sql_error",       handle_sql_error)

    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context",        "get_schema")
    workflow.add_edge("get_schema",              "generate_sql")
    workflow.add_edge("generate_sql",            "decide_chart_attributes")
    workflow.add_edge("decide_chart_attributes", "execute_sql")
    workflow.add_conditional_edges(
        "execute_sql",
        route_after_sql,
        {
            "generate_sql":     "generate_sql",      # Retry on SQL error
            "handle_sql_error": "handle_sql_error",  # Abort after max retries
            "generate_chart":   "generate_chart",    # Happy path
        },
    )
    workflow.add_edge("generate_chart",    "generate_insights")
    workflow.add_edge("generate_insights", END)
    workflow.add_edge("handle_sql_error",  END)

    app = workflow.compile()

    return await app.ainvoke(
        {
            "question":         question,
            "semantic_context": "",
            "schema":           "",
            "sql_query":        "",
            "chart_attributes": {},
            "data":             "{}",
            "chart_json":       "{}",
            "insights":         "",
            "error":            "",
            "retry_count":      0,
        }
    )

# ─── Interactive Loop ─────────────────────────────────────────────────────────

async def run_agent():
    print("─── Frammer Analytics Agent ───────────────────────────────────")
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

        print("\n Processing...\n")
        try:
            result = await build_and_run_pipeline(user_query)

            print("💡 Insights:")
            print(result["insights"])

            chart = result.get("chart_json", "")
            if chart and chart.strip().startswith("<?xml"):
                chart_path = "chart_output.xml"
                with open(chart_path, "w", encoding="utf-8") as f:
                    f.write(chart)
                print(f"\n Dashboard XML saved to {chart_path}")
            elif chart and chart not in ("{}", ""):
                # May be an error JSON from chart.py
                try:
                    chart_obj = json.loads(chart)
                    if "error" in chart_obj:
                        print(f"\n Chart warning: {chart_obj['error']}")
                except json.JSONDecodeError:
                    pass  # Unknown format, silently skip

        except Exception as exc:
            print(f"\n Agent error: {exc}")

        print()


if __name__ == "__main__":
    asyncio.run(run_agent())
