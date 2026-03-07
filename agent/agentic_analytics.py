import json
import re
from typing import Any, Dict, List, Tuple
import urllib.request
import urllib.error
import os

from sql_query import execute_sql_query_for_posts

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

SCHEMA_PROMPT_TEMPLATE = """
You are an expert Data Analyst and SQL Developer. Your task is to generate valid, highly-optimized SQLite queries based on the user's natural language question, and recommend the best chart type to visualize the results.

# Database Schema
The database contains the following tables and definitions. This is the ACTUAL live schema of the database:

{schema}

# Rules & Constraints
1. **JSON Only**: You must respond with a STRICTLY VALID JSON object. Do NOT wrap the JSON in markdown code blocks (no ```json ... ```). Do NOT include any conversational filler (like "Here is the query").
2. **Required Keys**: The JSON MUST have exactly two keys: "sql" and "chart_type".
3. **"sql" Key Requirements**:
   - The query must be standard SQLite syntax.
   - ALL numeric aggregations must use `CAST(column_name AS REAL)` if the data is stored as TEXT. Example: `SUM(CAST(total_published AS REAL))`.
   - Never query a column that does not exist in the schema. Check the schema provided above carefully!
   - Ensure you select labels for visualization (like `month` or `channel`) alongside your calculated metrics.
4. **"chart_type" Key Requirements**:
   - Recommend the best visualization. Must be one of: "bar", "line", "pie", "doughnut".
   - Use "line" for time-series data.
   - Use "bar" for categorical comparisons. Stacked bars are automatically handled for multi-category data.
   - Use "pie" or "doughnut" for simple percentage/distribution breakdowns.

# User Question
Question: {question}
"""

def get_dynamic_schema() -> str:
    try:
        from sql_query import engine
        from sqlalchemy import text
        schemas = []
        with engine.connect() as conn:
            res = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
            for row in res:
                if row[0]:
                    schemas.append(row[0])
        return "\\n".join(schemas)
    except Exception as e:
        print(f"Failed to fetch dynamic schema: {e}")
        return "Schema unavailable"


ANALYTICS_KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {
        "id": "kpi_upload_processed_published",
        "title": "Core KPI Funnel",
        "text": "Uploaded, processed, and published counts and duration are core funnel KPIs. Processed vs published gap and publish conversion are key operational metrics.",
        "sql_hint": "Use monthly_counts totals and conversion formulas.",
    },
    {
        "id": "channel_performance",
        "title": "Channel Performance",
        "text": "Channel-wise breakdown should include count and duration views, plus conversion rates where available.",
        "sql_hint": "Use channel_metrics for per-channel activity fields.",
    },
    {
        "id": "output_mix",
        "title": "Output Type Mix",
        "text": "Output type mix includes reels, shorts, chapters, summaries and other output categories with count and duration.",
        "sql_hint": "Use output_type_data table.",
    },
    {
        "id": "input_mix",
        "title": "Input Type Mix",
        "text": "Input type mix includes speech, interview, special report and similar source categories.",
        "sql_hint": "Use input_type_data table.",
    },
    {
        "id": "language_usage",
        "title": "Language Usage",
        "text": "Language-level usage helps identify demand and underperforming combinations.",
        "sql_hint": "Use language_data table.",
    },
    {
        "id": "video_explorer",
        "title": "Video Explorer",
        "text": "Video-level details should include headline, source, team_name, type, uploader, platform and URL for troubleshooting and export.",
        "sql_hint": "Use video_list_data table.",
    },
    {
        "id": "data_quality",
        "title": "Data Quality Monitoring",
        "text": "Monitor Unknown and missing values in team/platform/url fields and include trends over time where possible.",
        "sql_hint": "Aggregate null and unknown counts in video_list_data.",
    },
]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def semantic_retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Lightweight semantic retrieval using token-overlap scoring.

    This provides an explainable retrieval layer for NL analytics prompts
    without requiring extra embedding dependencies.
    """
    query_tokens = set(_tokenize(query))
    ranked: List[Tuple[float, Dict[str, str]]] = []

    for item in ANALYTICS_KNOWLEDGE_BASE:
        haystack = f"{item['title']} {item['text']} {item['sql_hint']}"
        item_tokens = set(_tokenize(haystack))
        if not item_tokens:
            continue
        overlap = len(query_tokens.intersection(item_tokens))
        score = overlap / max(len(query_tokens), 1)
        if score > 0:
            ranked.append((score, item))

    ranked.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, item in ranked[: max(1, top_k)]:
        results.append(
            {
                "id": item["id"],
                "title": item["title"],
                "score": round(score, 4),
                "sql_hint": item["sql_hint"],
                "text": item["text"],
            }
        )
    return results


def generate_sql_with_llm(question: str, model: str) -> str:
    schema_str = get_dynamic_schema()
    prompt = SCHEMA_PROMPT_TEMPLATE.format(schema=schema_str, question=question)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            # Strip markdown if llm ignored the rule
            sql_response = re.sub(r'```json\s*', '', parsed.get("response", "").strip(), flags=re.IGNORECASE)
            sql_response = re.sub(r'```', '', sql_response)
            
            try:
                llm_data = json.loads(sql_response)
                sql = llm_data.get("sql", "")
                chart_type = llm_data.get("chart_type", "bar")
            except json.JSONDecodeError:
                # Fallback if the LLM didn't return valid JSON
                sql = sql_response
                chart_type = "bar"
                match = re.search(r'(?i)\b(SELECT|WITH)\b[\s\S]*?(?:;|$)', sql)
                if match:
                    sql = match.group(0).strip()
                else:
                    sql = sql.strip()
                
            return sql, chart_type
    except Exception as e:
        print(f"Error calling Ollama for SQL: {e}")
        return "SELECT 'Failed to generate SQL' AS error_msg", "bar"


def plan_nl_query(question: str, model: str, filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    sql, chart_type = generate_sql_with_llm(question, model)

    return {
        "question": question,
        "intent": "dynamic_llm_sql",
        "chart_type": chart_type,
        "metric_family": "dynamic",
        "primary_table": "dynamic",
        "dimensions": [],
        "applied_filters": filters or {},
        "sql": sql,
        "retrieved_context": semantic_retrieve(question, top_k=4),
        "assumptions": [
            "SQL is generated dynamically by LLM based on user intent.",
            "Filters currently not applied to dynamic SQL automatically.",
        ],
    }


def run_nl_query(question: str, model: str = "llama3:latest", filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    plan = plan_nl_query(question=question, model=model, filters=filters)
    raw_json = execute_sql_query_for_posts(plan["sql"])

    try:
        result = json.loads(raw_json)
    except json.JSONDecodeError:
        result = {
            "config": {
                "success": False,
                "error": "SQL executor did not return valid JSON"
            },
            "data": []
        }

    # Make applied planning explicit in config for explainable NLQ.
    config = result.get("config", {}) if isinstance(result, dict) else {}
    config["nlq_question"] = question
    config["intent"] = plan["intent"]
    config["metric_family"] = plan["metric_family"]
    config["primary_table"] = plan["primary_table"]
    config["dimensions"] = plan["dimensions"]
    config["applied_filters"] = plan["applied_filters"]
    config["generated_sql"] = plan["sql"]
    config["chart_type"] = plan.get("chart_type", "bar")
    result["config"] = config

    return {
        "plan": plan,
        "result": result,
    }
