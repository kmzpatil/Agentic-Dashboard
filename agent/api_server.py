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
import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from orchestrate import build_and_run_pipeline
from mcp_client import MCPClient


from contextlib import asynccontextmanager

# --- Shared MCP Client ---
shared_mcp_client = MCPClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the shared MCP connection
    await shared_mcp_client.__aenter__()
    yield
    # Shutdown: Cleanly close the connection
    await shared_mcp_client.__aexit__(None, None, None)

app = FastAPI(title="Frammer Analytics API", version="1.0.0", lifespan=lifespan)

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

    # Use the shared client
    result = await build_and_run_pipeline(req.question, client=shared_mcp_client)

    try:
        # result['chart_json'] is a JSON string containing {question, insights, error, charts}
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
            charts=[]
        )


@app.get("/api/tables")
async def get_schema():
    """Return the live database schema (table + column list) as JSON."""
    tables_json = await shared_mcp_client.call_tool("list_tables", {})
    table_list = json.loads(tables_json)
    
    tables = {}
    
    async def fetch_table_columns(table_name):
        try:
            details_json = await shared_mcp_client.call_tool("describe_table", {"table_name": table_name})
            details = json.loads(details_json)
            return table_name, [c["name"] for c in details.get("columns", [])]
        except Exception:
            return table_name, []

    # Fetch all table columns in parallel
    tasks = [fetch_table_columns(t["name"]) for t in table_list]
    results = await asyncio.gather(*tasks)
    
    for item in results:
        t_name, cols = item
        tables[t_name] = cols
                
    return {"tables": tables}


@app.post("/api/data")
async def get_data(req: DataRequest):
    """
    Run a raw SQL query and return data records as JSON.
    Used by the frontend Chart.js renderer to obtain live query results.
    """
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL cannot be empty.")

    raw = await shared_mcp_client.call_tool("execute_sql_query", {"query": req.sql})
        
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