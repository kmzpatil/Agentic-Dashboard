# Orchestration Agent API

A FastAPI-powered REST interface for the **LangGraph Orchestrator pipeline**.  
The pipeline translates a user's natural-language intent into SQL, executes it, and returns both a natural-language analysis and a structured XML response.

---

## Pipeline Architecture

```
User JSON Request
       │
       ▼
┌─────────────────┐
│  Orchestrator   │  ← Generates SQL (uses MCP tool for schema lookup)
└────────┬────────┘
         │ sql_query
         ▼
┌─────────────────┐
│    SQL  DB      │  ← Executes the query, returns raw data + metadata
└────────┬────────┘
         │ db_result_mixed
         ▼
┌─────────────────┐
│ Data Processor  │  ← Strips metadata, returns clean row data
└────────┬────────┘
         │ processed_data
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌──────┐
│ Haiku │  │ FRT  │  ← Run in parallel
│ Agent │  │ Agent│
└───┬───┘  └──┬───┘
    │          │
    ▼          ▼
 analysis    XML
```

| Node | Role |
|---|---|
| **Orchestrator** | Converts user intent → SQL query; may call `mcp_lookup_table_schema` |
| **SQL DB** | Executes the SQL query and returns `raw_data + metadata_json` |
| **Data Processor** | Strips metadata; passes clean rows downstream |
| **Haiku Agent** | Produces a concise natural-language summary of the data |
| **FRT Agent** | Formats the data as well-formed XML for delivery |

---

## LLM Modes

| Mode | Trigger | Behaviour |
|---|---|---|
| **Mock** | No `HUGGINGFACEHUB_API_TOKEN` / `HF_TOKEN` in `.env` | Deterministic, rule-based outputs — no API calls |
| **Live** | API key present | Uses `Qwen/Qwen3.5-35B-A3B` via HuggingFace Inference Endpoints |

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Add your HuggingFace key to .env
echo "HUGGINGFACEHUB_API_TOKEN=hf_..." >> .env

# 3. Start the API server
python Orchestration.py
# or directly with uvicorn:
uvicorn Orchestration:api --reload --port 8000
```

Interactive docs are available at **http://127.0.0.1:8000/docs** once the server is running.

---

## API Endpoints

### Utility

#### `GET /health`
Returns current health and LLM mode.

**Response**
```json
{
  "status": "ok",
  "llm_mode": "mock",
  "version": "1.0.0"
}
```

---

#### `GET /schema/{table_name}`
Calls the MCP `mcp_lookup_table_schema` tool and returns schema information for the given table name.

**Path parameter:** `table_name` — e.g. `sales`

**Response**
```json
{
  "table_name": "sales",
  "schema_info": "Schema for sales: id INT, name VARCHAR, value FLOAT"
}
```

---

### Pipeline Stages

#### `POST /sql`
Runs **only the Orchestrator node** — translates intent into a SQL query without touching the database.

**Request body**
```json
{
  "intent": "Get total sales figures",
  "parameters": { "region": "US", "quarter": "Q3" }
}
```

**Response**
```json
{
  "sql_query": "SELECT SUM(value) AS total_sales FROM sales WHERE region = 'US' AND quarter = 'Q3';"
}
```

---

#### `POST /process`
Runs the pipeline through **Orchestrator → SQL DB → Data Processor**.  
Returns the generated SQL and the cleaned row data — useful for inspecting what the LLM queried before analysis.

**Request body** — same as `/sql`

**Response**
```json
{
  "sql_query": "SELECT SUM(value) AS total_sales FROM sales WHERE region = 'US' AND quarter = 'Q3';",
  "raw_data": [
    { "id": 1, "name": "Item A", "value": 100 },
    { "id": 2, "name": "Item B", "value": 200 }
  ]
}
```

---

#### `POST /analyze`
Runs the full pipeline and returns **only the Haiku Agent's natural-language analysis**.

**Request body** — same as `/sql`

**Response**
```json
{
  "sql_query": "SELECT SUM(value) AS total_sales FROM sales WHERE region = 'US' AND quarter = 'Q3';",
  "haiku_analysis": "Returned 2 records. Total value is 300.00. No anomalies detected in this small sample."
}
```

---

#### `POST /format`
Runs the full pipeline and returns **only the FRT Agent's XML output**.

**Request body** — same as `/sql`

**Response**
```json
{
  "sql_query": "SELECT SUM(value) AS total_sales FROM sales WHERE region = 'US' AND quarter = 'Q3';",
  "frt_xml": "<response>\n  <item>\n    <id>1</id>\n    <name>Item A</name>\n    <value>100</value>\n  </item>\n  ...\n</response>"
}
```

---

### Orchestration

#### `POST /run`
Executes the **complete LangGraph pipeline** end-to-end via `graph.invoke()`.  
Returns all outputs: generated SQL, raw data rows, Haiku analysis, and FRT XML.

**Request body** — same as `/sql`

**Response**
```json
{
  "sql_query": "SELECT SUM(value) AS total_sales FROM sales WHERE region = 'US' AND quarter = 'Q3';",
  "raw_data": [
    { "id": 1, "name": "Item A", "value": 100 },
    { "id": 2, "name": "Item B", "value": 200 }
  ],
  "haiku_analysis": "Returned 2 records. Total value is 300.00. No anomalies detected in this small sample.",
  "frt_xml": "<response>\n  <item>\n    <id>1</id>\n    <name>Item A</name>\n    <value>100</value>\n  </item>\n  <item>\n    <id>2</id>\n    <name>Item B</name>\n    <value>200</value>\n  </item>\n</response>"
}
```

---

#### `POST /run/stream`
Streams each **node's output** as it completes.  
Returns a list of `{ node, output }` objects — one per executed node in pipeline order.  
Useful for frontend progress bars or real-time status updates.

**Request body** — same as `/sql`

**Response**
```json
{
  "steps": [
    { "node": "Orchestrator",    "output": { "sql_query": "..." } },
    { "node": "SQL_DB",          "output": { "db_result_mixed": { ... } } },
    { "node": "Data_Processor",  "output": { "processed_data": "[...]" } },
    { "node": "Haiku_Agent",     "output": { "haiku_analysis": "..." } },
    { "node": "FRT_Agent",       "output": { "frt_xml": "<response>...</response>" } }
  ],
  "total_nodes": 5
}
```

---

## Endpoint Summary

| Method | Path | Tag | Description |
|--------|------|-----|-------------|
| `GET` | `/health` | Utility | API health + LLM mode status |
| `GET` | `/schema/{table_name}` | Utility | MCP table schema lookup |
| `POST` | `/sql` | Pipeline Stages | Generate SQL only (no DB call) |
| `POST` | `/process` | Pipeline Stages | SQL generation + DB execution + data extraction |
| `POST` | `/analyze` | Pipeline Stages | Full pipeline → Haiku natural-language analysis |
| `POST` | `/format` | Pipeline Stages | Full pipeline → FRT XML output |
| `POST` | `/run` | Orchestration | Full pipeline → all outputs combined |
| `POST` | `/run/stream` | Orchestration | Full pipeline → streaming node-by-node output |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HUGGINGFACEHUB_API_TOKEN` | Optional | HuggingFace API key — enables live LLM calls |
| `HF_TOKEN` | Optional | Alias for `HUGGINGFACEHUB_API_TOKEN` |
| `DATABASE_URL` | Optional | SQLAlchemy DB URL (defaults to mock data) |

---

## Project Structure

```
agent2/
├── Orchestration.py   # LangGraph pipeline + FastAPI app
├── logger_setup.py    # Logging configuration
├── requirements.txt   # Python dependencies
└── README.md          # This file
```
