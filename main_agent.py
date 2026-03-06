"""
main_agent.py
─────────────
Standalone analytics agent that follows the same LangGraph pipeline as
agent_client.py, but calls the tool functions in tools/ directly instead of
routing through the MCP server. No MCP server needs to be running.

Pipeline:
    retrieve_context → get_schema → generate_sql → execute_sql
         ↑__(on error, up to 3 retries)__|
                                         ↓ (on success)
                                   generate_chart → generate_insights → END
"""

import asyncio
import os
from dotenv import load_dotenv
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# Import all tool functions directly from the tools package
from tools import (
    retrieve_metric_definitions,
    get_frammer_schema,
    execute_sql_query,
    generate_plotly_chart,
)

# ─── Environment & LLM ───────────────────────────────────────────────────────

load_dotenv()
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# ─── Agent State ─────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:         str
    semantic_context: str   # Output of retrieve_metric_definitions
    schema:           str   # Output of get_frammer_schema
    sql_query:        str   # LLM-generated SQL
    data:             str   # JSON string from execute_sql_query
    chart_json:       str   # Serialised Plotly figure from generate_plotly_chart
    insights:         str   # LLM-generated business insights
    error:            str   # Last SQL error (used for self-correction)
    retry_count:      int   # Guards against infinite retry loops

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

    # Node 3 — LLM generates SQL (with self-correction when error is present)
    def generate_sql(state: AgentState):
        prompt = PromptTemplate.from_template(
            "Database Schema:\n{schema}\n\n"
            "Business Metric Definitions: {context}\n\n"
            "Previous Error (fix this if present): {error}\n\n"
            "Question: {question}\n\n"
            "Write a valid SQLite SELECT query to answer the question. "
            "Return ONLY the SQL, no explanation, no markdown."
        )
        raw = llm.invoke(prompt.format(
            schema=state.get("schema", ""),
            context=state.get("semantic_context", ""),
            error=state.get("error", ""),
            question=state["question"],
        )).content
        # Strip markdown code fences if the LLM wraps the query
        query = raw.strip().strip("```sql").strip("```").strip()
        return {"sql_query": query, "error": ""}

    # Node 4 — Execute SQL; flag errors for the self-correction loop
    def execute_sql(state: AgentState):
        result = execute_sql_query(state["sql_query"])
        if result.startswith("Error") or result.startswith("SQL Execution Error"):
            return {
                "error": result,
                "data": "[]",
                "retry_count": state.get("retry_count", 0) + 1,
            }
        return {"data": result, "error": ""}

    # Node 5 — Generate a Plotly chart from the same SQL
    def generate_chart(state: AgentState):
        result = generate_plotly_chart(state["sql_query"])
        return {"chart_json": result}

    # Node 6 — LLM derives business insights from the raw data
    def generate_insights(state: AgentState):
        prompt = PromptTemplate.from_template(
            "You are a business analyst. Analyze the following dataset and provide "
            "2-3 concise, actionable bullet-point insights:\n\n{data}"
        )
        insights = llm.invoke(
            prompt.format(data=state.get("data", "[]"))
        ).content
        return {"insights": insights}

    # Conditional edge — retry SQL generation on error (max 3x)
    def route_after_sql(state: AgentState):
        if state.get("error") and state.get("retry_count", 0) < 3:
            return "generate_sql"
        return "generate_chart"

    # Build the graph
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("get_schema",        get_schema)
    workflow.add_node("generate_sql",      generate_sql)
    workflow.add_node("execute_sql",       execute_sql)
    workflow.add_node("generate_chart",    generate_chart)
    workflow.add_node("generate_insights", generate_insights)

    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "get_schema")
    workflow.add_edge("get_schema",       "generate_sql")
    workflow.add_edge("generate_sql",     "execute_sql")
    workflow.add_conditional_edges(
        "execute_sql",
        route_after_sql,
        {
            "generate_sql":  "generate_sql",    # Loop back on SQL error
            "generate_chart": "generate_chart", # Proceed on success
        },
    )
    workflow.add_edge("generate_chart",    "generate_insights")
    workflow.add_edge("generate_insights", END)

    app = workflow.compile()

    return await app.ainvoke({
        "question":         question,
        "semantic_context": "",
        "schema":           "",
        "sql_query":        "",
        "data":             "[]",
        "chart_json":       "{}",
        "insights":         "",
        "error":            "",
        "retry_count":      0,
    })

# ─── Interactive Loop ─────────────────────────────────────────────────────────

async def run_agent():
    print("--- Frammer Analytics Agent ---")
    print("Tools loaded from: tools/")
    print("Type 'quit' to exit.\n")

    while True:
        loop = asyncio.get_event_loop()
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

            print(" Insights:")
            print(result["insights"])

            chart = result.get("chart_json", "{}")
            if chart and chart not in ("{}", ""):
                chart_path = "chart_output.json"
                with open(chart_path, "w") as f:
                    f.write(chart)
                print(f"\n Chart saved to {chart_path}")

        except Exception as exc:
            print(f"\n Agent error: {exc}")

        print()


if __name__ == "__main__":
    asyncio.run(run_agent())
