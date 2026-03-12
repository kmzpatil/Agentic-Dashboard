from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
import json
import logging

from orchestrate import build_and_run_pipeline
# Optional direct db imports for other endpoints
from db import db_list_tables, db_describe_table, db_execute_query

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

class ChartData(BaseModel):
    title: str
    sql: str
    config: dict
    error: Optional[str] = None

class QueryResponse(BaseModel):
    question: str
    insights: str
    error: Optional[str] = None
    charts: List[ChartData]

@app.post("/api/query", response_model=QueryResponse)
async def run_query(req: QueryRequest):
    """
    Run the full pipeline. Orchestrate now manages its own 
    MCPClient connection internally to execute domain tools.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # build_and_run_pipeline returns the final state of the LangGraph
        final_state = await build_and_run_pipeline(req.question)
        
        # The 'chart_json' field contains the serialized dashboard JSON
        chart_json_str = final_state.get("chart_json", "{}")
        output_data = json.loads(chart_json_str)
        
        return output_data
    except Exception as e:
        logging.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/api/tables")
def get_tables():
    """Returns a list of all tables."""
    return db_list_tables()

@app.get("/api/tables/{table_name}")
def get_table_details(table_name: str):
    """Returns detailed schema for a specific table."""
    return db_describe_table(table_name)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)