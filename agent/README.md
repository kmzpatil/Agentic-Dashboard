# ATLAS — The Guide to Your Data

AI-powered analytics engine using a unified ReAct (Reason + Act) loop architecture. Built directly on Google's `google-genai` SDK with zero framework dependencies (no LangChain, no LangGraph).

## Architecture

The agent answers natural-language analytics questions by iteratively reasoning and executing tools against a PostgreSQL database tracking a media content pipeline (upload → create → publish).

### Core Design

| Principle | Detail |
|-----------|--------|
| **Zero-framework** | Uses `google-genai` SDK directly — full control over tool calling and loop behavior |
| **Tool-calling-first** | Every LLM response is a structured tool call (`execute_queries`, `answer`, `clarify`, etc.) |
| **Security by default** | SQL validation + auth-scoped CTE injection for row-level security |
| **Parallel execution** | SQL queries run via `asyncio.gather()` — multiple queries in the time of one |
| **Feedback-driven** | Query results feed back into LLM context; failed queries trigger self-correction |

### Capabilities

- Natural-language SQL-backed analytics queries
- Interactive chart generation (14+ chart types via XML dashboard format)
- Board-level HTML report generation (A4-paginated, print-to-PDF ready)
- Custom KPI creation from natural language or formulas
- Multi-turn conversation persistence with memory compaction
- Role-based data scoping (website_admin, client_admin, user)

## Directory Structure

```
agent/
├── agent.py              # Core ReAct loop engine (orchestrator)
├── api_server.py          # FastAPI server exposing /api/chat, /api/query endpoints
├── client.py              # Google Gemini LLM client wrapper
├── conversations.py       # SQLAlchemy conversation persistence
├── memory.py              # Working memory manager with auto-compaction
├── report_formatter.py    # HTML report renderer
├── kpi_generator.py       # KPI creation assistant
├── analytics_routes.py    # Deterministic analytics endpoints (static KPIs)
├── logger_setup.py        # Colorized logging setup
├── mcp_server/            # MCP tool registry, database client, RAG schema indexing
├── tools/                 # Tool modules (SQL query, schema, chart, KPI, metrics)
├── prompts/               # LLM prompt templates
├── templates/             # Report HTML templates
└── tests/                 # pytest suite (SQL scoping, auth boundaries, query sanitization)
```

## Core Modules

### `agent.py` — The Orchestrator
Core ReAct loop with up to 10 iterations per request. Injects database schemas, metric definitions, and auth-scoped filtering into the system prompt. Classifies intent (analytics vs. conversational) and coordinates tool execution.

### `api_server.py` — API Server
FastAPI instance with CORS middleware. Exposes `/api/chat` (streaming SSE), `/api/query` (one-shot), and conversation CRUD endpoints.

### `client.py` — LLM Client
Google Gemini SDK wrapper with retry logic and exponential backoff for rate limits.

### `conversations.py` — Persistence
SQLAlchemy-backed conversation and message storage in PostgreSQL. Append-only message inserts for efficient multi-turn state.

### `memory.py` — Context Manager
Monitors token usage and auto-compacts conversation history when context exceeds safety thresholds via an LLM summarization pass.

### `report_formatter.py` — Report Renderer
Converts agent-generated data into styled HTML reports with charts, tables, and KPI cards. Deterministic rendering (no LLM in the render path).

### `mcp_server/` — Database & Tools
- `database.py` — DatabaseClient with query validation (forbidden keywords, single-statement enforcement) and proactive CTE injection for row-level security
- Tool registry exposing schema inspection, SQL execution, chart generation, and metric definition tools

### `tools/` — Tool Modules
Executable tool logic for SQL queries, schema retrieval, chart XML generation, custom KPI operations, and metric formula definitions.

## Running Standalone

```bash
uvicorn agent.api_server:app --host 0.0.0.0 --port 4001
```

## Detailed Documentation

See [AGENT_DOCUMENTATION.md](AGENT_DOCUMENTATION.md) for comprehensive technical documentation covering all modules, data flows, security model, and configuration reference.
