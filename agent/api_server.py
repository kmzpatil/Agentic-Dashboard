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
from mcp_client import MCPClient


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

    async with MCPClient() as client:
        result = await build_and_run_pipeline(req.question, client=client)

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
    async with MCPClient() as client:
        tables_json = await client.call_tool("list_tables", {})
        table_list = json.loads(tables_json)
        
        tables = {}
        for table_entry in table_list:
            table_name = table_entry["name"]
            try:
                details_json = await client.call_tool("describe_table", {"table_name": table_name})
                details = json.loads(details_json)
                tables[table_name] = [c["name"] for c in details.get("columns", [])]
            except Exception:
                tables[table_name] = []
                
    return {"tables": tables}


@app.post("/api/data")
async def get_data(req: DataRequest):
    """
    Run a raw SQL query and return data records as JSON.
    Used by the frontend Chart.js renderer to obtain live query results.
    """
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL cannot be empty.")

    async with MCPClient() as client:
        raw = await client.call_tool("execute_sql_query", {"query": req.sql})
        
    if raw.startswith("Error"):
        raise HTTPException(status_code=400, detail=raw)

    try:
        parsed = json.loads(raw)
        if "error" in parsed:
            raise HTTPException(status_code=400, detail=parsed["error"])
            
        records = parsed.get("rows", parsed.get("data", []))
        return {"records": records}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse remote data.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)