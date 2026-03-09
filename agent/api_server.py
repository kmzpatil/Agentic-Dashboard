"""
api_server.py
─────────────
FastAPI server that exposes the Frammer analytics agent as a web API and
serves an HTML dashboard that visualises live query results.

Endpoints:
  GET  /                → serve the dashboard HTML
  POST /api/query       → run the NLQ → SQL → XML pipeline; return results
  GET  /api/tables      → return live schema (table + column list)

Usage:
  pip install -r requirements.txt
  uvicorn api_server:app --reload --port 8000
"""

import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from orchestrate import build_and_run_pipeline
from tools.schema import get_frammer_schema
from tools.sql_query import execute_sql_query

app = FastAPI(title="Frammer Analytics API", version="1.0.0")

# ── Request / response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class DataRequest(BaseModel):
    sql: str


class QueryResponse(BaseModel):
    question:   str
    sql:        str          # First chart's SQL (for display in the UI)
    xml:        str          # Merged dashboard XML
    insights:   str
    error:      str
    chart_data: dict         # Map of widget title -> list of data records


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML page."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/query", response_model=QueryResponse)
async def run_query(req: QueryRequest):
    """
    Run the full NLQ -> SQL -> XML pipeline for a given question.
    Returns the merged XML, per-chart data records, LLM insights, and SQLs.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = await build_and_run_pipeline(req.question)

    specs = result.get("chart_specs", [])

    # Build a chart_title -> records map.
    # The key MUST match the XML <row label=...> which chart.py sets to
    # chart_attributes['title']. We also add sub_question as a fallback key.
    chart_data: dict = {}
    first_sql = ""
    for i, spec in enumerate(specs):
        chart_title  = spec.get("chart_attrs", {}).get("title", "")
        sub_question = spec.get("sub_question", f"Chart {i+1}")
        records      = spec.get("records", [])
        # Register under both keys so the frontend JS can find it either way
        if chart_title:
            chart_data[chart_title] = records
        chart_data[sub_question] = records
        if i == 0:
            first_sql = spec.get("sql_query", "")

    return QueryResponse(
        question=req.question,
        sql=first_sql,
        xml=result.get("chart_json", ""),
        insights=result.get("insights", ""),
        error=result.get("error", ""),
        chart_data=jsonable_encoder(chart_data),
    )


@app.get("/api/tables")
async def get_schema():
    """Return the live database schema (table + column list) as JSON."""
    schema_str = get_frammer_schema()
    tables = {}
    current_table = None
    for line in schema_str.splitlines():
        if line.startswith("Table:"):
            current_table = line.replace("Table:", "").strip()
            tables[current_table] = []
        elif line.startswith("Columns:") and current_table:
            col_part = line.replace("Columns:", "").strip()
            tables[current_table] = [
                c.split("(")[0].strip() for c in col_part.split(",")
            ]
    return {"tables": tables}


@app.post("/api/data")
async def get_data(req: DataRequest):
    """
    Run a raw SQL query and return data records as JSON.
    Used by the frontend Chart.js renderer to obtain live query results.
    """
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL cannot be empty.")

    raw = execute_sql_query(req.sql)
    parsed = json.loads(raw)

    if "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed["error"])

    return {"records": parsed.get("data", [])}

