# ATLAS — Complete Technical Documentation

> **Version**: 1.0 | **Architecture**: Unified ReAct Loop | **LLM Backend**: Google Gemini (native SDK) | **Framework**: Zero-framework (no LangChain)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Directory Structure](#3-directory-structure)
4. [Core Components](#4-core-components)
   - [4.1 ReAct Loop Engine (agent.py)](#41-react-loop-engine-agentpy)
   - [4.2 API Server (api_server.py)](#42-api-server-api_serverpy)
   - [4.3 LLM Client (client.py)](#43-llm-client-clientpy)
   - [4.4 Conversation Persistence (conversations.py)](#44-conversation-persistence-conversationspy)
   - [4.5 Working Memory Manager (memory.py)](#45-working-memory-manager-memorypy)
   - [4.6 Report Formatter (report_formatter.py)](#46-report-formatter-report_formatterpy)
   - [4.7 Analytics Routes (analytics_routes.py)](#47-analytics-routes-analytics_routespy)
   - [4.8 Logger (logger_setup.py)](#48-logger-logger_setuppy)
5. [MCP Server (Model Context Protocol)](#5-mcp-server-model-context-protocol)
   - [5.1 DatabaseClient (database.py)](#51-databaseclient-databasepy)
   - [5.2 Configuration (config.py)](#52-configuration-configpy)
   - [5.3 Tool Registry (registry.py)](#53-tool-registry-registrypy)
   - [5.4 Tool Modules](#54-tool-modules)
6. [Agent Tools](#6-agent-tools)
   - [6.1 Schema Inspector (schema.py)](#61-schema-inspector-schemapy)
   - [6.2 SQL Query Executor (sql_query.py)](#62-sql-query-executor-sql_querypy)
   - [6.3 Chart Generator (chart.py)](#63-chart-generator-chartpy)
   - [6.4 Custom KPIs (custom_kpis.py)](#64-custom-kpis-custom_kpispy)
   - [6.5 Metric Definitions (metric_definitions.py)](#65-metric-definitions-metric_definitionspy)
7. [The Six-Tool System](#7-the-six-tool-system)
8. [Data Flow — End to End](#8-data-flow--end-to-end)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Report Generation Pipeline](#10-report-generation-pipeline)
11. [Conversation & Memory Management](#11-conversation--memory-management)
12. [Chart & Visualization System](#12-chart--visualization-system)
13. [Design Patterns](#13-design-patterns)
14. [Error Handling & Resilience](#14-error-handling--resilience)
15. [Scalability Architecture](#15-scalability-architecture)
16. [Feedback Loops](#16-feedback-loops)
17. [Data Models](#17-data-models)
18. [Security Model](#18-security-model)
19. [Observability & Diagnostics](#19-observability--diagnostics)
20. [Configuration Reference](#20-configuration-reference)

---

## 1. Architecture Overview

ATLAS is a production-grade, LLM-powered data analysis system built on a **unified ReAct (Reason + Act) loop** architecture. It enables natural-language querying of a PostgreSQL database tracking a media content pipeline — from raw video upload through AI-powered asset creation to multi-platform publication.

### Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Zero-framework** | Uses Google's `google-genai` SDK directly — no LangChain, no LangGraph, no abstraction layers. Full control over tool calling, prompt engineering, and loop behavior. |
| **Tool-calling-first** | The LLM never produces raw text answers. Every response is a structured tool call (`execute_queries`, `answer`, `clarify`, etc.), ensuring predictable, parseable output. |
| **Security by default** | All SQL is validated at ingress (forbidden keyword detection, single-statement enforcement). Auth-scoped CTE injection ensures row-level security even if the LLM generates unrestricted queries. |
| **Parallel by design** | SQL queries execute via `asyncio.gather()` — 10 queries complete in the time of 1. The agent plans broad, executes fast. |
| **Feedback-driven** | Query results (with numeric stats and sample rows) feed back into the LLM context. Failed queries are seen by the model, which self-corrects in the next iteration. |
| **Deterministic rendering** | Charts and reports are rendered by pure Python code (no LLM in the render path). The LLM decides *what* to show; deterministic code decides *how* it looks. |

### What It Does

- Answers natural-language analytics questions with SQL-backed data
- Generates interactive charts (14 chart types via XML dashboard format)
- Produces board-level HTML reports (A4-paginated, print-to-PDF ready)
- Manages multi-turn conversations with persistent memory
- Enforces role-based data access (website_admin, client_admin, user)
- Provides 18 specialized business KPIs with formulas and SQL patterns

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     FRONTEND SPA (index.html)                    │
│          Chat UI  ·  Conversation List  ·  Chart Rendering       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP (REST + SSE)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   API SERVER (FastAPI)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌────────────┐  │
│  │/api/chat  │  │/api/query│  │/api/convo/*  │  │/analytics/*│  │
│  │(full loop)│  │(one-shot)│  │(CRUD)        │  │(static KPI)│  │
│  └─────┬─────┘  └─────┬────┘  └──────┬───────┘  └──────┬─────┘  │
│        │              │              │                  │         │
│        └──────────────┼──────────────┘                  │         │
│                       ▼                                 ▼         │
│              ┌─────────────────┐             ┌─────────────────┐ │
│              │  AGENT (ReAct)  │             │ ANALYTICS ROUTES│ │
│              │  10-iter loop   │             │ (deterministic) │ │
│              └────────┬────────┘             └────────┬────────┘ │
└───────────────────────┼──────────────────────────────┼───────────┘
                        │                              │
         ┌──────────────┼──────────────┐               │
         ▼              ▼              ▼               │
   ┌──────────┐  ┌──────────┐  ┌────────────┐         │
   │MEMORY.PY │  │CLIENT.PY │  │REPORT      │         │
   │(compact) │  │(Gemini)  │  │FORMATTER   │         │
   └──────────┘  └─────┬────┘  └────────────┘         │
                       │                               │
                       ▼                               │
              ┌─────────────────┐                      │
              │  GOOGLE GEMINI  │                      │
              │  API            │                      │
              └─────────────────┘                      │
                       ▲                               │
                       │ Tool dispatch                 │
         ┌─────────────┼─────────────┐                 │
         ▼             ▼             ▼                 │
   ┌──────────┐  ┌──────────┐  ┌──────────┐           │
   │Schema   │  │ SQL      │  │ Chart    │           │
   │ Inspector│  │ Executor │  │ Generator│           │
   └─────┬────┘  └─────┬────┘  └──────────┘           │
         │             │                               │
         └──────┬──────┘                               │
                ▼                                      │
   ┌────────────────────────────┐                      │
   │  MCP DATABASE CLIENT       │                      │
   │  • Query validation        │                      │
   │  • CTE auth injection      │                      │
   │  • Schema profiling        │                      │
   │  • RAG via embeddings      │                      │
   └────────────┬───────────────┘                      │
                │                                      │
                ▼                                      ▼
   ┌───────────────────────────────────────────────────────────┐
   │                   POSTGRESQL DATABASE                      │
   │  raw_videos · created_assets · published_posts ·           │
   │  post_distribution · channels · users · clients ·          │
   │  raw_video_channel · conversations · conversation_messages │
   └───────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
agent/
├── agent.py                  # Core: ReAct loop, tool dispatch, system prompt
├── api_server.py             # Core: FastAPI HTTP server, endpoints
├── client.py                 # Core: LLM client wrapper (Gemini)
├── conversations.py          # Core: SQLAlchemy ORM, conversation persistence
├── memory.py                 # Core: Working memory management + compaction
├── report_formatter.py       # Core: Deterministic HTML report rendering
├── analytics_routes.py       # Core: Static KPI routes for fast UI
├── logger_setup.py           # Core: Colored logging infrastructure
├── __init__.py               # Package init + lazy imports
│
├── mcp_server/               # Model Context Protocol server
│   ├── server.py             #   FastMCP initialization
│   ├── config.py             #   Settings + DB URL resolution
│   ├── database.py           #   DatabaseClient (validation, auth, profiling)
│   ├── registry.py           #   Tool module registration
│   └── modules/              #   MCP tool definitions
│       ├── database_tools.py #     SQL/schema operations
│       ├── analytics_tools.py#     Analytics-specific tools
│       ├── agent_tools.py    #     Agent coordination tools
│       └── system_tools.py   #     System health/config tools
│
├── tools/                    # Agent tool implementations
│   ├── __init__.py           #   Tool exports
│   ├── _db.py                #   Shared DatabaseClient singleton
│   ├── schema.py             #   get_frammer_schema (DB inspection)
│   ├── sql_query.py          #   execute_sql_query (validated execution)
│   ├── chart.py              #   generate_plotly_chart (XML dashboard)
│   ├── custom_kpis.py        #   18 specialized business KPIs
│   └── metric_definitions.py #   Metric dictionary + formulas
│
├── prompts/                  # LLM prompt templates
│   ├── __init__.py
│   └── report_prompt.py      #   Planning + synthesis prompt builders
│
├── templates/
│   └── index.html            #   Frontend SPA
│
├── tests/                    # Test suite
│   ├── test_auth_enforcement.py
│   ├── test_improvements.py
│   └── README.md
│
├── outputs/                  #   Generated reports
├── frammer_data.sql          #   Seed data
├── frammer_database.dump     #   Database backup
├── .env                      #   Local environment config
└── README.md                 #   Architecture overview
```

---

## 4. Core Components

### 4.1 ReAct Loop Engine (`agent.py`)

**The brain of the system.** Implements a unified Reason + Act loop where the LLM decides which tool to call, receives results, and iterates until it has enough data to answer.

#### Entry Point

```python
async def run_agent(
    question: str,
    auth: Optional[Any] = None,
    working_memory: str = "",
    history: Optional[List[Dict]] = None,
    mode: str = "normal",          # "normal" | "report"
    agent_state: Optional[Dict] = None,
    report_mode: bool = False,
) -> AgentResult
```

#### Loop Mechanics

1. **Schema & Metrics Loading** — Cached schema inspection + metric dictionary loaded once per process
2. **System Prompt Construction** — Dynamic prompt with schema, metrics, auth context, working memory, and mode-specific instructions
3. **Gemini Config** — Tool declarations, temperature, max tokens, system instruction
4. **Content Accumulation** — Message history + tool results accumulate as `types.Content` objects
5. **Iteration Loop** (max 10 iterations):
   - LLM receives all accumulated content
   - LLM responds with exactly one tool call
   - Tool is dispatched and executed
   - Result is appended as `function_response` content
   - Loop continues or exits based on tool type

#### Two Modes

| Mode | Behavior | Output |
|------|----------|--------|
| **normal** | Standard analytics Q&A. Agent queries, analyzes, generates charts. | `AgentResult` with text + charts |
| **report** | Comprehensive data gathering. Plans sub-questions, executes all in parallel, synthesizes via Gemini, renders as HTML. | `AgentResult` with HTML report |

#### Conversational Fast-Path

Greetings and small talk (`hi`, `hello`, `thanks`, `who are you`) bypass the full ReAct loop entirely. A simple regex match routes these to a lightweight LLM call without schema loading or tool configuration.

```python
_CONVERSATIONAL_RE = re.compile(
    r"^(hi|hello|hey|thanks|thank you|bye|goodbye|...)$", re.IGNORECASE
)
```

#### Force Synthesis Fallback

If the agent hits `MAX_ITERATIONS` (10) without calling `answer`, a fallback `_force_synthesize()` call sends all accumulated query results to Gemini for an emergency summary. This ensures the user always gets a response.

---

### 4.2 API Server (`api_server.py`)

FastAPI application providing the HTTP transport layer.

#### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Full conversational agent — creates/resumes conversations, manages memory |
| `/api/query` | POST | One-shot query — no conversation persistence |
| `/api/conversations` | GET | List all conversations for a user |
| `/api/conversations/{id}` | GET | Retrieve a specific conversation with messages |
| `/api/conversations/{id}` | DELETE | Delete a conversation (cascading) |
| `/api/data` | POST | Raw SQL execution (admin) |
| `/healthz` | GET | Health check — DB connection, table count, dialect |
| `/analytics/*` | Various | Static KPI routes (via `analytics_routes.py`) |

#### Lifecycle Management

- **Startup**: Initializes DatabaseClient, builds schema profile + schema index (embedding-based RAG)
- **CORS**: Configured for cross-origin requests
- **Error handling**: All exceptions caught at the endpoint level, returned as `ChatResponse` with error field

#### Request Flow (`/api/chat`)

```
ChatRequest → create_conversation() if new
            → append_message(user)
            → build working_memory from history
            → run_agent(question, working_memory, auth, mode)
            → append_message(assistant)
            → update_working_memory()
            → ChatResponse
```

---

### 4.3 LLM Client (`client.py`)

Thin wrapper around the `google-genai` SDK providing:

- **Factory constructors**: `LLMClient.fast()`, `.thinking()`, `.creative()` — preconfigured temperature modes
- **Exponential backoff**: 5 retries with `5 * 2^attempt` second waits on 429/rate-limit errors
- **Free-tier detection**: Identifies free-tier quota errors and surfaces actionable guidance
- **Dual invoke methods**:
  - `ainvoke(prompt, label)` — Simple text generation
  - `ainvoke_with_tools(contents, config)` — Tool-calling with `GenerateContentConfig`

#### Retry Logic

```python
async def _invoke_with_retry(invoke_fn, *, label: str = "llm"):
    for attempt in range(5):
        try:
            return await invoke_fn()
        except Exception as exc:
            if is_rate_limit and attempt < 4:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s, 40s, 80s
                await asyncio.sleep(wait)
                continue
            raise
```

---

### 4.4 Conversation Persistence (`conversations.py`)

SQLAlchemy-based persistence layer for multi-turn conversations.

#### ORM Models

```python
class Conversation:
    id: str              # UUID primary key
    user_id: str         # Optional, indexed
    title: str           # LLM-generated from first message
    working_memory: str  # Rolling compacted context
    agent_state_json: str# Serialized state for clarification resumption
    created_at: DateTime
    updated_at: DateTime

class ConversationMessage:
    id: int              # Auto-increment primary key
    conversation_id: str # FK → conversations.id (CASCADE delete)
    role: str            # 'user' | 'assistant'
    content: str         # Message text
    metadata_json: str   # {intent, actions, charts...}
    created_at: DateTime
```

#### Key Operations

- **Append-only messages**: `INSERT` only — no full JSON reserialize on every chat
- **Session scoping**: `@contextmanager _session_scope()` with automatic rollback on failure
- **Cascading deletes**: Deleting a conversation removes all its messages
- **Working memory**: Stored on the conversation row, updated after each turn

---

### 4.5 Working Memory Manager (`memory.py`)

Manages the rolling context window that the agent uses across conversation turns.

#### Memory Update Cycle

```
existing_memory + "[User]: question\n[Agent actions]: ...\n[Agent response]: ..."
    ↓
if len(updated) > MAX_MEMORY_CHARS (8000):
    _compact_memory(updated) via LLM
    ↓
returns compacted memory (~6000 chars)
```

#### Compaction Strategy

- **Trigger**: Memory exceeds 8000 characters
- **Method**: LLM call (fast model) summarizes the full memory into <6000 chars
- **Preserves**: Key facts, user preferences, data findings, follow-up context
- **Drops**: Redundant details, repeated queries, verbose explanations
- **Fallback**: If LLM compaction fails, truncates to last 8000 characters

#### Title Generation

```python
def generate_title(user_query: str) -> str:
    # LLM generates 3-6 word title from first user message
    # Fallback: first 50 chars of query
```

---

### 4.6 Report Formatter (`report_formatter.py`)

**Pure rendering module** — no LLM calls, no agent logic. Takes structured JSON + query results and produces self-contained A4-ready HTML.

#### Design Philosophy

The report generation pipeline has a strict separation:
1. **LLM Phase**: Gemini generates structured JSON (what to show — narrative, chart specs, table specs)
2. **Render Phase**: `render_report_html()` produces deterministic HTML (how it looks)

Charts and tables bind to **actual query data** via `source_query_index`, so visualizations show real database values — not LLM approximations.

#### Output Characteristics

- Self-contained HTML (inline CSS + Chart.js)
- A4-paginated with `@media print` CSS
- Page breaks at section boundaries
- Fixed header repeats on printed pages
- Chart.js for interactive charts
- Responsive tables with numeric alignment
- Executive summary + analytical sections + recommendations

---

### 4.7 Analytics Routes (`analytics_routes.py`)

Secondary FastAPI router providing deterministic, pre-computed KPI endpoints for the frontend dashboard.

#### Why It Exists

The main agent takes 2-5 seconds per query (LLM + DB). The dashboard needs instant (<100ms) responses for static KPIs. These routes execute hardcoded SQL queries directly against the database — no LLM involved.

---

### 4.8 Logger (`logger_setup.py`)

Custom logging infrastructure with ANSI color-coded output.

#### Color Scheme

| Level | Color | Use Case |
|-------|-------|----------|
| DEBUG | Cyan | Internal tracing |
| INFO | Green | Normal operations |
| WARNING | Yellow | Retries, fallbacks |
| ERROR | Red | Failures |
| CRITICAL | Bold Red | System-level failures |

#### Features

- Logger name highlighting (e.g., `frammer.agent`, `frammer.database`)
- Keyword highlighting (`RATE LIMIT`, `LLM CALL FAILED`, `SQL Execution COMPLETE`)
- Noisy library suppression (httpx, urllib3, etc.)

---

## 5. MCP Server (Model Context Protocol)

### 5.1 DatabaseClient (`database.py`)

The security and data access backbone of the entire system.

#### Query Validation Pipeline

```
Input SQL
  ↓
_strip_comments()          → Remove -- and /* */ to prevent bypass
  ↓
_clean_query()
  ├── Empty check           → QueryValidationError
  ├── Multi-statement check → QueryValidationError (no semicolons)
  ├── Prefix check          → Must start with SELECT or WITH
  └── Forbidden keyword scan → INSERT, UPDATE, DELETE, DROP, ALTER,
                                CREATE, TRUNCATE, GRANT, REVOKE,
                                MERGE, CALL, EXECUTE, VACUUM,
                                ANALYZE, COPY, app_users
  ↓
Validated query
```

#### Auth-Scoped CTE Injection

The most critical security feature. When a non-admin user executes a query, the DatabaseClient **proactively injects CTEs** that shadow the physical table names with pre-filtered versions:

```sql
-- User's query:
SELECT COUNT(*) FROM raw_videos

-- After CTE injection (for client_admin of "Acme Corp"):
WITH
  scoped_videos AS (
    SELECT rv.* FROM raw_videos rv
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
    WHERE COALESCE(ch."Client_Name", u."Client_Name") = 'Acme Corp'
  ),
  scoped_channels AS (SELECT * FROM channels WHERE "Client_Name" = 'Acme Corp'),
  scoped_users AS (SELECT * FROM users WHERE "Client_Name" = 'Acme Corp'),
  raw_videos AS (SELECT * FROM scoped_videos),
  created_assets AS (SELECT ca.* FROM created_assets ca JOIN scoped_videos sv ON ...),
  published_posts AS (SELECT pp.* FROM published_posts pp JOIN created_assets ca ON ...),
  post_distribution AS (SELECT pd.* FROM post_distribution pd JOIN published_posts pp ON ...),
  raw_video_channel AS (SELECT rvc.* FROM raw_video_channel rvc JOIN scoped_videos sv ON ...),
  channels AS (SELECT * FROM scoped_channels),
  users AS (SELECT * FROM scoped_users)
SELECT COUNT(*) FROM raw_videos
```

The key insight: by using CTEs that **shadow the physical table names**, even a completely unrestricted `SELECT * FROM raw_videos` only returns rows the user is authorized to see. The LLM never needs to know about auth — the database layer enforces it transparently.

#### Schema Profiling

Thread-safe, one-time cached profiling of the database schema:

1. **`build_schema_profile()`** — Scans all tables, identifies low-cardinality text columns (<50 distinct values), caches their values. Protected by `threading.Lock`, runs exactly once per process.

2. **`build_schema_index()`** — Builds an embedding-based index of table schemas using `sentence-transformers` (all-MiniLM-L6-v2). Enables RAG-style schema search.

3. **`search_table_schemas(query)`** — Cosine similarity search over schema embeddings. Returns the most relevant tables for a natural-language query.

#### LIMIT Enforcement

```python
def normalise_limit(self, requested, default, maximum):
    return max(1, min(int(requested), maximum))
```

Every query is wrapped in a CTE with a LIMIT clause, preventing row explosions regardless of what the LLM generates.

---

### 5.2 Configuration (`config.py`)

Dataclass-based settings management:

```python
@dataclass
class ServerSettings:
    database_url: str     # PostgreSQL/SQLite connection string
    default_schema: str   # Schema name (default: "public")
    default_limit: int    # Default row limit (200)
    max_limit: int        # Maximum row limit (1000)
```

Resolves `DATABASE_URL` from environment with fallback chain: `.env` (agent dir) → `.env` (project root) → environment variables.

---

### 5.3 Tool Registry (`registry.py`)

Registers four tool modules with the FastMCP server:
- `database_tools` — Schema inspection, SQL execution, table preview
- `analytics_tools` — KPI calculations, metric lookups
- `agent_tools` — Agent coordination, conversation management
- `system_tools` — Health checks, configuration

---

### 5.4 Tool Modules

Each module in `mcp_server/modules/` defines MCP-compatible tool functions that are registered with the FastMCP server. These provide a standardized protocol interface for external tool consumers.

---

## 6. Agent Tools

### 6.1 Schema Inspector (`schema.py`)

```python
def get_frammer_schema() -> str
```

Returns a human-readable schema description including:
- Table names and column definitions with types
- Cardinality rules (join relationships)
- Sample values for low-cardinality text columns
- Falls back to standard SQLAlchemy inspection if no data rows exist

The schema is cached per-process via `_schema_cache_lock` — loaded once, reused across all agent runs.

---

### 6.2 SQL Query Executor (`sql_query.py`)

```python
def execute_sql_query(query: str, limit: int = 200, auth: Any = None) -> str
```

Pipeline:
1. Get shared `DatabaseClient` singleton via `get_db()`
2. Call `db.run_read_only_query(query, limit, auth)`
3. Convert DataFrame → records → JSON
4. Return `{"data": [...], "chart_attributes": {...}}` or `{"error": "..."}`

Uses pandas as an intermediate layer for type handling and null normalization.

---

### 6.3 Chart Generator (`chart.py`)

```python
def generate_plotly_chart(data_records: List[Dict], chart_attributes: Dict) -> str
```

Transforms query results into the Frammer XML dashboard format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dashboard>
  <meta>
    <title>Chart Title</title>
    <generated>2024-01-15</generated>
  </meta>
  <layout>
    <row>
      <widget type="bar-chart">
        <title>Revenue by Channel</title>
        <data>
          <labels>["Channel A", "Channel B"]</labels>
          <datasets>
            <dataset label="Revenue">[1000, 2000]</dataset>
          </datasets>
        </data>
      </widget>
    </row>
  </layout>
</dashboard>
```

#### Supported Chart Types (14)

| Type | XML Widget | Best For |
|------|------------|----------|
| `bar` | `bar-chart` | Category comparison (≤15 categories) |
| `stacked-bar` | `stacked-bar-chart` | Composition + total comparison |
| `horizontal-bar` | `horizontal-bar` | Rankings, long labels |
| `line` | `line-chart` | Time-series trends |
| `area` | `area-chart` | Stacked composition over time |
| `pie` / `doughnut` | `pie-chart` | Proportions (≤6 categories) |
| `polar-area` | `polar-area-chart` | Multi-category proportions (4-8) |
| `scatter` | `scatter-chart` | Correlation between two variables |
| `bubble` | `bubble-chart` | Scatter + size dimension |
| `heatmap` | `heatmap` | Cross-tabular intensity |
| `treemap` | `treemap` | Hierarchical proportions |
| `box` | `box-chart` | Distribution statistics |
| `violin` | `violin-chart` | Distribution shape |
| `radar` | `radar-chart` | Multi-dimensional comparison |

#### KPI Card Auto-Detection

When the query returns a single row, the chart generator automatically creates KPI cards instead of a chart — each column becomes a KPI widget with the value prominently displayed.

---

### 6.4 Custom KPIs (`custom_kpis.py`)

18 specialized business KPIs with definitions, formulas, significance, and ready-to-use SQL:

| KPI ID | Title | What It Measures |
|--------|-------|-----------------|
| `uploaded_count` | Total Uploaded | Intake volume — fundamental growth metric |
| `processed_count` | Total Processed | Processing engine throughput capacity |
| `created_count` | Total Created | Output volume of the creation stage |
| `published_count` | Total Published | Final content reach — ultimate success metric |
| `publish_conversion` | Publish Conversion Rate | % of created clips that get published |
| `month_by_month_use_rate` | Month-by-Month Use Rate | Relative growth/decline vs previous month |
| `processing_efficiency` | Processing Efficiency | % of uploaded videos successfully processed |
| `creation_rate` | Creation Rate | Average clips created per processed video |
| `waste_index` | Waste Index | % of created clips never published — measures inefficiency |
| `upload_failure_rate` | Upload Failure Rate | % of uploads that fail processing |
| `roi` | ROI | Return on investment per video (published value / upload cost) |
| `dfs` | Distribution Frequency Score | Average platforms per published post |
| `interaction_lift` | Interaction Lift | Engagement improvement from multi-platform distribution |
| `cross_dimension_entropy` | Cross-Dimension Entropy | Content diversity across languages/formats |
| `publish_dependency_index` | Publish Dependency Index | How dependent publishing is on specific channels |
| `point_biserial` | Point-Biserial Correlation | Statistical relationship between features and publish likelihood |
| `multidimensional_waste` | Multidimensional Waste | Waste broken down by language × format × channel |
| `ctas` | Content-to-Asset Score | Efficiency of content-to-asset conversion pipeline |
| `rei` | Re-Engagement Index | How often published content drives return visits |

Each KPI provides:
- `definition` — Business-level explanation
- `formula` — Mathematical formula
- `significance` — Why it matters
- `sql` — Ready-to-execute PostgreSQL query

---

### 6.5 Metric Definitions (`metric_definitions.py`)

A broader metric dictionary providing SQL patterns for common analysis types:

- **Trend analysis**: Monthly/weekly aggregation patterns
- **Correlation**: Cross-table join patterns
- **Heatmap**: Pivot query templates
- **Join rules**: Canonical join paths between tables

Used to inject domain knowledge into the system prompt so the LLM knows how to construct correct queries.

---

## 7. The Six-Tool System

The agent has exactly six tools, each with a specific role in the analysis workflow:

### Tool 1: `execute_queries`

```python
def execute_queries(
    queries: List[Dict[str, str]],  # [{"sql": "SELECT ...", "description": "..."}]
    reasoning: str = "",
) -> str
```

**Purpose**: Run SQL queries to gather data. All queries execute in parallel via `asyncio.gather()`.

**When the LLM uses it**: Every time it needs data from the database. The LLM is instructed to batch multiple queries into a single call — trends, breakdowns, and comparisons all execute simultaneously.

**What happens**: Queries are dispatched to `_execute_query_batch()`, which runs them in parallel. Results (with sample rows and numeric stats) are formatted and fed back to the LLM as a `function_response`.

---

### Tool 2: `answer`

```python
def answer(
    response: str = "",             # Markdown analysis text
    needs_chart: bool = False,
    chart_intent: str = "",         # "comparison" | "trend" | "distribution" | ...
    charts: List[Dict] = None,      # Chart specs with source_query_index
) -> str
```

**Purpose**: Provide the final answer to the user. Exits the ReAct loop.

**When the LLM uses it**: After gathering enough data through `execute_queries`. The response contains the full analytical text, and chart specs reference specific query results by index.

**What happens**: Charts are generated via `_generate_charts_from_specs()` which maps each spec to its source query data and produces XML dashboards. The loop exits.

---

### Tool 3: `clarify`

```python
def clarify(question: str = "") -> str
```

**Purpose**: Ask the user a clarifying question when the request is ambiguous.

**When the LLM uses it**: When the query could mean multiple things, a filter value is unclear, or the time range is ambiguous.

**What happens**: The ReAct loop **pauses**. The entire agent state (query results, message history, iteration count) is serialized to `agent_state_json` in the database. When the user responds, `run_agent()` is called with the stored state, and the loop resumes from where it left off.

---

### Tool 4: `get_column_values_tool`

```python
def get_column_values_tool(
    table_name: str = "",
    column_name: str = "",
) -> str
```

**Purpose**: Look up distinct values for a column from the cached schema profile.

**When the LLM uses it**: Before writing a SQL filter — e.g., "What languages are in the data?" before filtering by language.

**What happens**: Reads from the in-memory schema profile (built once at startup). Returns the list of distinct values without hitting the database.

---

### Tool 5: `get_kpi_info_tool`

```python
def get_kpi_info_tool(kpi_id: str = "") -> str
```

**Purpose**: Get the definition, formula, and SQL pattern for a business KPI.

**When the LLM uses it**: When the user asks about a specific KPI (e.g., "What's our waste index?"). The LLM gets the exact formula and can use the provided SQL pattern.

---

### Tool 6: `explore_tool`

```python
def explore_tool(
    queries: List[str] = None,  # Simple SQL strings
    reasoning: str = "",
) -> str
```

**Purpose**: Run lightweight exploration queries (max 5 rows each). For quick data discovery before committing to full analytical queries.

**When the LLM uses it**: To check join paths, discover distinct values, find min/max ranges — anything that helps plan better analytical queries.

---

## 8. Data Flow — End to End

### Example: "How are uploads trending by language?"

```
Step 1: User sends POST /api/chat
        → ChatRequest { message: "How are uploads trending by language?" }

Step 2: api_server.py
        → create_conversation() → UUID generated, title created via LLM
        → append_message(role="user", content="How are uploads trending...")
        → Build working_memory from last 10 messages
        → run_agent(question, auth, working_memory)

Step 3: agent.py — run_agent()
        → _load_schema_and_metrics() [cached]
        → _build_system_prompt(schema, metrics, auth, memory, mode="normal")
        → _build_gemini_config(system_prompt)
        → contents = [_user_content("How are uploads trending...")]

Step 4: ITERATION 1
        → LLM receives: system prompt + user question
        → LLM returns: execute_queries({
            queries: [
              {sql: "SELECT date_trunc('month', ...) AS month, COUNT(*) ...", desc: "Monthly trend"},
              {sql: "SELECT \"Language\", COUNT(*) ... GROUP BY 1", desc: "By language"},
              {sql: "SELECT date_trunc('month', ...), \"Language\", COUNT(*) ...", desc: "Trend × language"},
              {sql: "WITH monthly AS (...) SELECT month, count, LAG...", desc: "MoM growth"}
            ],
            reasoning: "Need trend, language breakdown, cross-tab, and growth rate"
          })

Step 5: _execute_query_batch()
        → asyncio.gather(*[_run_one(q) for q in 4 queries])  # PARALLEL
        → Each query: execute_sql_query → DatabaseClient.run_read_only_query
          → _clean_query (validation)
          → CTE injection (if non-admin)
          → text(f"WITH mcp_cte AS ({query}) SELECT * FROM mcp_cte LIMIT :limit")
          → pd.read_sql_query → DataFrame → records
        → All 4 complete in ~2-3 seconds

Step 6: Results fed back
        → _summarize_query_results(batch_results)
          → Sample rows (first 5) + numeric stats (min/max/sum) per query
        → contents.append(_tool_response_content("execute_queries", summary))

Step 7: ITERATION 2
        → LLM receives: system prompt + user question + execute_queries call + results
        → LLM analyzes results, decides it has enough data
        → LLM returns: answer({
            response: "**Upload volume has grown 23% over the past 12 months**...",
            needs_chart: true,
            chart_intent: "trend",
            charts: [{
              chart_type: "line",
              source_query_index: 0,
              x_column: "month",
              y_columns: "count",
              title: "Monthly Upload Trend"
            }, {
              chart_type: "bar",
              source_query_index: 1,
              x_column: "Language",
              y_columns: "count",
              title: "Uploads by Language"
            }]
          })

Step 8: _generate_charts_from_specs()
        → Maps chart_specs to actual query data via source_query_index
        → generate_plotly_chart(records, attrs) → XML dashboard string
        → Returns [ChartResult, ChartResult]

Step 9: AgentResult returned
        → response: "**Upload volume has grown 23%...**"
        → charts: [ChartResult(xml=..., data=...), ...]
        → actions: ["Thinking...", "Executing 4 queries", "SQL OK — 12 rows", ...]
        → sql: last executed SQL

Step 10: api_server.py
         → append_message(role="assistant", content=response, metadata={intent, actions, charts})
         → update_working_memory(conversation, build_memory_update(...))
         → Return ChatResponse to frontend

Step 11: Frontend
         → Renders markdown response
         → Parses chart XML → Chart.js visualizations
         → Updates conversation sidebar
```

---

## 9. Authentication & Authorization

### Three-Tier Role Model

| Role | Scope | What They See |
|------|-------|---------------|
| `website_admin` | Full access | All data across all clients, users, channels |
| `client_admin` | Client-scoped | Only data belonging to their client organization |
| `user` | User-scoped | Only their own uploaded data |

### Dual-Layer Enforcement

Authorization is enforced at **two independent layers**, creating defense-in-depth:

#### Layer 1: Prompt-Level (Soft)

The system prompt includes auth context that instructs the LLM to include appropriate WHERE clauses:

```
## USER PROFILE
- User: **john** | Role: **client_admin**
- RESTRICTION: Only client **Acme Corp** data. Use: COALESCE(ch."Client_Name", u."Client_Name") = 'Acme Corp'
```

#### Layer 2: CTE Injection (Hard)

Even if the LLM ignores the prompt instruction (or is prompt-injected), the `DatabaseClient.run_read_only_query()` method **proactively injects scoping CTEs** that shadow physical table names. This is enforced at the database query layer — the LLM cannot bypass it.

The CTE injection handles the full table chain:
- `raw_videos` → scoped by client/user
- `created_assets` → scoped via join to scoped videos
- `published_posts` → scoped via join chain (pp → ca → scoped videos)
- `post_distribution` → scoped via join to scoped posts
- `raw_video_channel` → scoped via join to scoped videos
- `channels` → scoped by client
- `users` → scoped by client/user

### WITH-Merge Logic

If the LLM generates a query that already starts with `WITH`, the injector merges the CTE blocks:

```python
if cleaned_query.upper().startswith("WITH"):
    user_query_no_with = cleaned_query[4:].strip()
    query = f"{full_cte_block},\n{user_query_no_with}"
else:
    query = f"{full_cte_block}\n{cleaned_query}"
```

---

## 10. Report Generation Pipeline

### Four-Phase Architecture

```
Phase 1: PLANNING
  User question → _plan_report_sub_questions()
  → LLM decomposes into 8-15 typed sub-questions
  → Types: trend, breakdown, comparison, anomaly, forecast, correlation

Phase 2: DATA GATHERING (ReAct loop in report mode)
  → System prompt appends report-mode instructions
  → Agent executes ALL sub-questions in first batch (parallel)
  → Reviews results, fills gaps with follow-up queries
  → 2-3 iterations to build comprehensive data foundation
  → Only calls `answer` when 8+ successful results across dimensions

Phase 3: SYNTHESIS
  → _synthesize_report(question, all_query_results)
  → Gemini receives 20-row samples from each query
  → Generates structured JSON:
    {
      title, executive_summary,
      sections: [{title, content, charts: [{...}], tables: [{...}], findings}],
      recommendations: [{title, description, priority}],
      metadata: {generated_at, data_sources, caveats}
    }

Phase 4: RENDERING
  → render_report_html(report_dict, query_results)
  → Deterministic HTML generation (NO LLM)
  → Charts bind to actual query data via source_query_index
  → Self-contained HTML with inline CSS + Chart.js
  → A4-paginated, print-to-PDF ready
```

### Why Two-Phase (Synthesis + Rendering)?

The separation ensures:
1. **LLM controls narrative** — The LLM decides what's important, what charts to show, what recommendations to make
2. **Code controls formatting** — No LLM hallucination in the visual output. Charts show real data. Tables are properly formatted. CSS is correct.
3. **Data integrity** — Chart data comes from actual query results (`source_query_index`), not from the LLM's memory of the results

---

## 11. Conversation & Memory Management

### Conversation Lifecycle

```
New conversation:
  POST /api/chat (no conversation_id)
  → UUID generated
  → Title generated via LLM (3-6 words)
  → First user message stored
  → Agent runs → response stored
  → Working memory initialized

Continued conversation:
  POST /api/chat (with conversation_id)
  → Load conversation + last N messages
  → Build working memory from history
  → Inject memory into system prompt
  → Agent runs with context
  → Memory updated with new turn

Clarification:
  Agent calls `clarify` tool
  → Agent state serialized (query results, messages, iteration)
  → Stored in conversation.agent_state_json
  → Response sent to user as question
  → User replies → run_agent(answer, agent_state=stored_state)
  → Loop resumes from saved iteration
```

### Working Memory vs Message History

| Aspect | Working Memory | Message History |
|--------|---------------|-----------------|
| **Storage** | Single string on conversation row | Append-only message table |
| **Size** | Bounded (8000 chars, compacted) | Unbounded (all messages) |
| **Content** | Summarized key facts | Full message text + metadata |
| **Purpose** | LLM context injection | UI display, debugging |
| **Update** | After each turn (with compaction) | Append-only (never modified) |

### Message Serialization

For clarification state persistence, google-genai `Content` objects are serialized to/from JSON:

```python
Content(role="user", parts=[Part(text="...")])
    ↔
{"role": "user", "parts": [{"type": "text", "text": "..."}]}

Part.from_function_call(name="execute_queries", args={...})
    ↔
{"type": "function_call", "name": "execute_queries", "args": {...}}
```

This allows the full ReAct loop state (including all prior tool calls and results) to be stored in PostgreSQL and restored when the user responds to a clarification.

---

## 12. Chart & Visualization System

### XML Dashboard Format

The agent uses a custom XML schema for chart transport between backend and frontend:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dashboard>
  <meta>
    <title>Dashboard Title</title>
    <generated>2024-01-15</generated>
  </meta>
  <layout>
    <row>
      <widget type="kpi">
        <title>Total Uploads</title>
        <value>10,742</value>
      </widget>
      <widget type="kpi">
        <title>Published</title>
        <value>1,312</value>
      </widget>
    </row>
    <row>
      <widget type="line-chart" span="12">
        <title>Monthly Upload Trend</title>
        <data>
          <labels>["Jan", "Feb", "Mar", ...]</labels>
          <datasets>
            <dataset label="Uploads">[100, 120, 95, ...]</dataset>
          </datasets>
        </data>
        <options>
          <x-axis-label>Month</x-axis-label>
          <y-axis-label>Count</y-axis-label>
        </options>
      </widget>
    </row>
  </layout>
</dashboard>
```

### Chart Selection Logic

The LLM is given explicit guidance on when to use each chart type:

| Intent | Recommended Types | Criteria |
|--------|------------------|----------|
| Comparison | `bar`, `stacked-bar`, `horizontal-bar` | ≤15 categories |
| Trend | `line`, `area` | X-axis must be date/time |
| Proportion | `pie`, `doughnut`, `polar-area` | ≤6 categories, 1 metric |
| Distribution | `box`, `violin` | SQL must return stats columns |
| Correlation | `scatter`, `bubble` | Two numeric variables |
| Multi-dimensional | `radar`, `heatmap` | 4-8 metrics, ≤5 entities |
| Hierarchical | `treemap` | Label + value + optional group |

### Source Query Binding

Charts reference their data source by `source_query_index` — a 0-based index into the ordered list of all queries executed across all iterations. This ensures:

1. Chart data comes from real query results (not LLM memory)
2. Charts can reference any query from any iteration
3. Multiple charts can reference the same query data
4. Failed queries produce no chart (graceful degradation)

---

## 13. Design Patterns

### Architectural Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **ReAct Loop** | `agent.py` run_agent() | Enables multi-step reasoning with iterative data gathering. The LLM reasons about what data it needs, acts by calling tools, and reasons again about results. |
| **Singleton** | `tools/_db.py` `@lru_cache(maxsize=1) get_db()` | Single DatabaseClient instance shared across all tool invocations. Avoids connection pool proliferation. |
| **Factory** | `client.py` `LLMClient.fast()`, `.thinking()`, `.creative()` | Pre-configured LLM clients for different use cases without exposing temperature details. |
| **Strategy** | `agent.py` `_build_system_prompt()` | Same loop code, different behavior. Mode-specific instructions injected into the system prompt. |
| **Repository** | `conversations.py` | Clean CRUD abstraction over SQLAlchemy. Context-managed sessions with automatic rollback. |
| **Builder** | `report_formatter.py` | Programmatic HTML construction from structured data. |
| **Chain of Responsibility** | `agent.py` tool dispatch | Each tool handler is tried in sequence based on tool_name. Extensible — new tools are just new elif branches. |
| **State Machine** | `agent.py` ReAct loop | The agent transitions between states: querying → reviewing → querying → answering (or clarifying). |

### Concurrency Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Parallel Execution** | `agent.py` `_execute_query_batch()` | `asyncio.gather()` runs all queries simultaneously. 10 queries in ~2-3s instead of serial ~20-30s. |
| **Lock-Protected Init** | `database.py` `_schema_lock`, `_profile_lock` | Schema profiling runs exactly once per process, even with concurrent requests. |
| **Thread-Safe Caching** | `database.py` `_shared_schema_index` | Built once, read by all threads. Lock released after initialization. |
| **Async/Thread Bridge** | `agent.py` `asyncio.to_thread()` | Synchronous database operations (SQLAlchemy) wrapped for async context. |

### Data Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Append-Only Log** | `conversations.py` messages | O(1) append, no deserialization cost. Scales to large conversations. |
| **Rolling Window** | `memory.py` working memory | Bounded context window with LLM-powered compaction. Old turns compressed, not lost. |
| **CTE Shadow** | `database.py` auth injection | Physical tables shadowed by filtered CTEs. Transparent to all downstream code. |
| **Source Binding** | `agent.py` `source_query_index` | Charts reference actual data by index, not by copying. Single source of truth. |

---

## 14. Error Handling & Resilience

### Error Recovery Matrix

| Error Type | Detection | Recovery | Fallback |
|------------|-----------|----------|----------|
| **Rate Limit (429)** | Keyword scan in error message | Exponential backoff: 5s, 10s, 20s, 40s, 80s | Raise after 5 attempts |
| **Free-Tier Quota** | `free_tier` / `freetier` in message | Immediate raise with actionable URL | N/A (billing required) |
| **SQL Validation** | `_clean_query()` checks | `QueryValidationError` → returned to LLM | LLM reformulates query |
| **SQL Execution** | Try/except around DB call | Error message → returned to LLM | LLM sees error, tries different SQL |
| **Max Iterations** | Loop counter ≥ 10 | `_force_synthesize()` — emergency LLM call | Summarize whatever data exists |
| **No Tool Call** | Empty `tool_calls` list | Check if text is analytical → treat as answer | Return as conversational response |
| **LLM Parse Error** | JSON decode failures | Regex extraction, fallback patterns | Graceful degradation |
| **Memory Compaction** | LLM call exception | Truncate to last 8000 chars | Lossy but functional |
| **Report JSON Parse** | Malformed LLM output | Regex extraction → minimal report structure | "Report structure could not be parsed" |
| **Chart Generation** | Exception in XML building | Return empty charts list | Text-only response |

### Error Flow Architecture

```
External Error (DB, LLM, Network)
    ↓
Component-Level Catch (try/except in handler)
    ↓
Structured Error Response ({"status": "error", "error": "..."})
    ↓
Fed back to LLM as tool result (LLM sees the error)
    ↓
LLM Self-Corrects (fixes SQL, changes approach)
    ↓
If still failing → Max Iterations → Force Synthesize
    ↓
If catastrophic → Top-Level Catch in run_agent() → AgentResult with error
    ↓
API Layer → ChatResponse with error field
    ↓
Frontend → Displays error message to user
```

### Self-Healing SQL

When the LLM generates invalid SQL:
1. Query validation catches syntax issues → error returned as tool result
2. LLM sees the error message in the next iteration
3. LLM reformulates the query (fixes quoting, corrects table names, adjusts joins)
4. New query executes successfully

This feedback loop means the agent recovers from most SQL errors without user intervention.

---

## 15. Scalability Architecture

### Horizontal Scaling

```
                    Load Balancer
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ API Inst │ │ API Inst │ │ API Inst │
     │    1     │ │    2     │ │    N     │
     └─────┬────┘ └─────┬────┘ └─────┬────┘
           │            │            │
           └────────────┼────────────┘
                        ▼
                   PostgreSQL
                (single / replicated)
```

**Why this works:**
- **Stateless servers**: All state lives in PostgreSQL (conversations, messages, memory). No session affinity required.
- **Per-process caching**: Schema index rebuilt per instance (small overhead; worth the simplicity vs shared cache).
- **No coordination needed**: Instances share nothing except the database.

### Scaling Dimensions

| Dimension | Current Capacity | Bottleneck | Scaling Path |
|-----------|-----------------|------------|--------------|
| **Concurrent Users** | ~50-100 per instance | LLM API rate limits | More instances + API key rotation |
| **Database Size** | Millions of rows | Query complexity | Read replicas, materialized views |
| **Conversation Volume** | Unlimited (append-only) | Storage | Archive old conversations |
| **Context Window** | 8000 char memory limit | LLM context | Already bounded by compaction |
| **Query Parallelism** | 10 queries per batch | DB connection pool | Increase pool_size |

### Performance Characteristics

| Operation | Latency | Why |
|-----------|---------|-----|
| Static KPI (analytics_routes) | <100ms | Hardcoded SQL, no LLM |
| Conversational fast-path | ~1s | Single lightweight LLM call |
| Simple factual query | ~3-5s | 1 LLM round + 1-2 SQL queries |
| Analytical query | ~5-10s | 2 LLM rounds + 4-8 SQL queries (parallel) |
| Full report | ~15-30s | Planning + 2-3 data rounds + synthesis + render |

### Memory Efficiency

| Resource | Strategy | Bound |
|----------|----------|-------|
| Working memory | LLM compaction at 8000 chars | O(1) per conversation |
| Schema cache | One-time build, process lifetime | O(tables × columns) |
| Embedding index | Shared global, lock-protected | O(tables) vectors |
| Query results | Per-request, GC'd after response | O(queries × rows) |
| Message history | DB-stored, loaded on demand | O(1) memory per request |

---

## 16. Feedback Loops

### 1. Tool Result Feedback (Core Loop)

```
LLM decides → execute_queries([...])
    ↓
Queries execute in parallel
    ↓
Results summarized (first 5 rows + numeric stats)
    ↓
Summary fed back as function_response Content
    ↓
LLM sees results → decides next action
    ├── More queries needed → execute_queries again
    ├── Enough data → answer
    ├── Ambiguous → clarify
    └── Need exploration → explore_tool
```

**Key property**: The LLM sees not just the data but also the **errors**. A failed query with its error message is visible in the next iteration, enabling self-correction.

### 2. SQL Error Self-Correction

```
Iteration 1: LLM generates SQL with wrong column name
    → "ERROR: column 'upload_date' does not exist"
    → Appended to contents as function_response
Iteration 2: LLM sees error, fixes to "Upload_Date" (quoted)
    → "SUCCESS: 42 rows"
```

### 3. User Feedback via Clarification

```
LLM uncertain → clarify("Did you mean X or Y?")
    → Agent state serialized to DB
    → User sees question in chat
    → User responds ("I meant X")
    → run_agent(answer, agent_state=stored_state)
    → Loop resumes with full context + user's clarification
```

### 4. Memory Feedback (Cross-Turn)

```
Turn 1: User asks about uploads → Agent analyzes
    → Memory: "[User]: upload trends\n[Agent]: 10.7k total, growing 23% MoM"
Turn 2: User asks "break that down by language"
    → System prompt includes memory → Agent knows "that" = uploads
    → Agent queries with correct context
```

### 5. Actions Audit Trail (User-Facing)

Every significant action is logged to `actions_log`:
```json
[
  "Thinking (round 1)...",
  "Executing 4 queries — Need trend, breakdown, growth rate",
  "SQL OK — 12 rows (Monthly upload trend)",
  "SQL OK — 8 rows (By language)",
  "SQL Error — column 'Language' does not exist",
  "SQL OK — 8 rows (By Language, fixed quoting)",
  "Thinking (round 2)...",
  "Answering",
  "Generated 2 chart(s)"
]
```

Users see what the agent did, building trust and enabling debugging.

---

## 17. Data Models

### AgentResult (Return Type)

```python
@dataclass
class AgentResult:
    intent: str = "analytics"           # analytics | conversational | clarification | report
    response: str = ""                  # Final text (markdown) or HTML (report mode)
    actions: List[str] = []             # Audit trail
    charts: List[ChartResult] = []      # Generated chart objects
    sql: str = ""                       # Last executed SQL (for debugging)
    error: str = ""                     # Error message if failed
    plan: str = ""                      # Report plan (if applicable)
    chart_xml: str = ""                 # Legacy: first chart XML
    chart_data: Dict = {}               # Legacy: first chart data
    mode: str = "normal"                # normal | report
    report: Optional[Dict] = None       # Parsed report structure
    clarification: Optional[str] = None  # Clarification question text
    agent_state: Optional[Dict] = None   # Serialized state for resumption
```

### ChartResult

```python
@dataclass
class ChartResult:
    chart_xml: str = ""                 # XML dashboard string
    data_records: List[Dict] = []       # Source query data
    sql: str = ""                       # SQL that produced the data
    title: str = ""                     # Chart title
    chart_type: str = ""                # bar, line, pie, etc.
    size_column: str = ""               # For bubble charts
    group_column: str = ""              # For grouped/colored charts
```

### API Request/Response Models

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    filters: Dict = {}
    report_mode: bool = False

class ChatResponse(BaseModel):
    response: str
    chart_xml: str = ""
    error: str = ""
    actions: List[str] = []
    chart_data: Dict = {}
    conversation_id: str = ""
    intent: str = "analytics"
    report_html: str = ""
```

### Database Schema (Content Pipeline)

```
raw_videos                          # Upload phase
├── Video_ID (PK)
├── User_ID (FK → users)
├── Upload_Date, Language, Input_Type
├── Uploaded_Duration
└── ...

created_assets                      # Processing phase
├── Asset_ID (PK)
├── Video_ID (FK → raw_videos)
├── Output_Type, Asset_Duration
└── ...

published_posts                     # Publication phase
├── Post_ID (PK)
├── Asset_ID (FK → created_assets)
├── Published_Date
└── ...

post_distribution                   # Distribution phase
├── Post_ID (FK → published_posts)
├── Published_Platform
├── Post_Views, Post_Likes, ...
└── ...

raw_video_channel                   # Ownership bridge
├── Video_ID (FK → raw_videos)
├── Channel_Name (FK → channels)
└── ...

channels                            # Channel ownership
├── Channel_Name (PK)
├── Client_Name (FK → clients)
└── ...

users                               # User accounts
├── User_ID (PK)
├── Client_Name
└── ...
```

---

## 18. Security Model

### Defense-in-Depth Layers

```
Layer 1: INPUT VALIDATION
├── SQL comment stripping (bypass prevention)
├── Forbidden keyword detection (INSERT, DROP, etc.)
├── Single-statement enforcement (no ; allowed)
├── SELECT/WITH prefix requirement
└── app_users table blocked (credential protection)

Layer 2: AUTH SCOPING (CTE Injection)
├── Non-admin queries auto-scoped via CTEs
├── Physical table names shadowed by filtered CTEs
├── Full table chain scoped (videos → assets → posts → distribution)
├── LLM-transparent (agent code doesn't know about auth)
└── Even prompt injection cannot bypass

Layer 3: OUTPUT SAFETY
├── LIMIT enforcement on all queries (max 1000 rows)
├── Column name quoting enforced (SQL injection prevention)
├── SQL never exposed to users
├── Table/column names translated to business language
└── No HTML in normal mode responses

Layer 4: PROMPT ENGINEERING
├── Explicit "never expose SQL" instructions
├── Business language translation rules
├── auth block in system prompt (soft guidance)
└── Tool-calling-only protocol (no raw text responses)
```

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| SQL Injection | `_clean_query()` validation + CTE wrapping |
| Prompt Injection | CTE injection is code-level (bypasses prompt manipulation) |
| Data Exfiltration | Role-based CTE scoping, LIMIT enforcement |
| Schema Exposure | "Never expose SQL/table names" in system prompt |
| Credential Access | `app_users` table in FORBIDDEN_SQL_PATTERN |
| Mutation | Only SELECT/WITH allowed, all DML keywords blocked |
| Multi-Statement | Semicolon detection, single-statement enforcement |
| Comment Bypass | `_strip_comments()` removes `--` and `/* */` before validation |

---

## 19. Observability & Diagnostics

### Logging Architecture

```python
# logger_setup.py — FrammerColorFormatter
# Color-coded ANSI output with keyword highlighting

logger = logging.getLogger("frammer.agent")      # Agent loop events
logger = logging.getLogger("frammer.database")    # Query execution
logger = logging.getLogger("frammer.memory")      # Memory compaction
logger = logging.getLogger("frammer.report")      # Report generation
```

### Key Log Events

| Event | Logger | Level | Content |
|-------|--------|-------|---------|
| Agent start | frammer.agent | INFO | Mode, timestamp |
| Iteration start | frammer.agent | INFO | Iteration number, content count |
| Iteration complete | frammer.agent | INFO | Duration, input/output tokens |
| Query execution | frammer.database | INFO | Duration, row count |
| Rate limit hit | frammer.agent | WARNING | Retry count, wait time |
| Free-tier quota | frammer.agent | ERROR | Actionable URL |
| SQL error | frammer.agent | INFO | Error message, attempted SQL |
| Memory compaction | frammer.memory | INFO | Before/after character counts |
| Report synthesis | frammer.agent | INFO | Duration, token usage |
| Agent complete | frammer.agent | INFO | Total duration, mode |

### Token Usage Tracking

```python
# Extracted from Gemini response metadata
usage = {
    "input_tokens": resp.usage_metadata.prompt_token_count,
    "output_tokens": resp.usage_metadata.candidates_token_count,
}
logger.info("Iteration %d — %d input, %d output tokens", ...)
```

### Health Check Endpoint

```
GET /healthz → {
    "status": "healthy",
    "database": "connected",
    "dialect": "postgresql",
    "tables": 8,
    "schema": "public"
}
```

### Actions Audit Trail

Every agent run produces an ordered list of actions visible to the user:

```python
actions_log = [
    "Thinking (round 1)...",
    "Executing 4 queries — Need trend and breakdown data",
    "SQL OK — 12 rows (Monthly upload trend)",
    "SQL OK — 8 rows (Uploads by language)",
    "SQL OK — 96 rows (Monthly trend by language)",
    "SQL OK — 12 rows (Month-over-month growth)",
    "Thinking (round 2)...",
    "Answering",
    "Generated 2 chart(s)"
]
```

---

## 20. Configuration Reference

### Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `GOOGLE_API_KEY` | Yes | — | Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Model name |
| `LLM_TEMPERATURE` | No | `0.1` | Default temperature |

### Constants

| Constant | File | Value | Purpose |
|----------|------|-------|---------|
| `MAX_ITERATIONS` | agent.py | 10 | ReAct loop safety cap |
| `_RETRY_MAX_ATTEMPTS` | agent.py | 5 | LLM retry limit |
| `MAX_MEMORY_CHARS` | memory.py | 8000 | Memory compaction threshold |
| `DEFAULT_QUERY_LIMIT` | tools/_db.py | 200 | Default SQL row limit |
| `MAX_QUERY_LIMIT` | tools/_db.py | 1000 | Maximum SQL row limit |

### LLM Client Modes

| Mode | Temperature | Use Case |
|------|-------------|----------|
| Default | 0.1 | Standard analytics (precise) |
| `fast()` | 0.0 | Report planning, memory compaction (deterministic) |
| `thinking()` | 0.2 | Complex reasoning tasks |
| `creative()` | 0.7 | Title generation, narrative writing |

---

## Summary

ATLAS is an end-to-end, production-grade AI analytics system that combines:

- **Intelligent reasoning** via a 10-iteration ReAct loop with 6 specialized tools
- **Parallel execution** via asyncio.gather for zero-latency-cost multi-query analysis
- **Ironclad security** via dual-layer auth enforcement (prompt + CTE injection)
- **Rich visualization** with 14 chart types rendered via XML dashboard format
- **Board-level reporting** with LLM synthesis + deterministic HTML rendering
- **Persistent conversations** with append-only messages + LLM-compacted working memory
- **Self-healing queries** where SQL errors feed back into the loop for automatic correction
- **Horizontal scalability** via stateless servers sharing a single PostgreSQL database
- **Full observability** with colored logs, token tracking, and user-facing action trails

The architecture prioritizes **simplicity** (no framework dependencies, no DAGs, just async/await + SQLAlchemy), **security** (validation-first, read-only, defense-in-depth), and **correctness** (deterministic rendering, source-bound charts, real data only).
