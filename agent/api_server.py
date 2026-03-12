"""
api_server.py
─────────────
FastAPI server that exposes the GCData analytics agent as a web API and
serves an HTML dashboard that visualises live query results.

Uses direct DatabaseClient access — no MCP subprocess needed.

Endpoints:
  GET  /                → serve the dashboard HTML
  POST /api/query       → run the NLQ → SQL → JSON pipeline; return results
  GET  /api/tables      → return live schema (table + column list)
  POST /api/data        → execute raw SQL query, return records

Usage:
  pip install -r requirements.txt
  python api_server.py
"""

import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrate import build_and_run_pipeline
from db import get_db, db_list_tables, db_describe_table, db_execute_query


app = FastAPI(title="GCData Analytics API", version="2.0.0")

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class DataRequest(BaseModel):
    sql: str


class QueryResponse(BaseModel):
    question:   str
    insights:   str
    error:      str
    charts:     list         # List of structured chart objects (title, sql, config)


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
    Run the full NLQ -> SQL -> JSON pipeline for a given question.
    Returns the structured JSON with insights and charts.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    db = get_db()
    result = await build_and_run_pipeline(req.question, db=db)

    try:
        output = json.loads(result.get("chart_json", "{}"))

        return QueryResponse(
            question=output.get("question", req.question),
            insights=output.get("insights", ""),
            error=output.get("error", ""),
            charts=output.get("charts", []),
        )
    except json.JSONDecodeError:
        return QueryResponse(
            question=req.question,
            insights=result.get("insights", ""),
            error="Failed to parse agent output.",
            charts=[],
        )


@app.get("/api/tables")
async def get_schema():
    """Return the live database schema (table + column list) as JSON."""
    table_list = db_list_tables()

    tables = {}
    for t in table_list:
        t_name = t["name"]
        try:
            details = db_describe_table(t_name)
            tables[t_name] = [c["name"] for c in details.get("columns", [])]
        except Exception:
            tables[t_name] = []

    return {"tables": tables}


@app.post("/api/data")
async def get_data(req: DataRequest):
    """
    Run a raw SQL query and return data records as JSON.
    Used by the frontend Chart.js renderer to obtain live query results.
    """
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL cannot be empty.")

    result = db_execute_query(req.sql)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"records": result.get("rows", [])}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)