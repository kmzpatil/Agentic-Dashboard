# Frammer AI — Agent System Documentation

> A complete technical reference for the `agent/` backend and the **Copilot** tab that drives it.

---

## Table of Contents

1. [What Is This System?](#1-what-is-this-system)
2. [Folder Structure](#2-folder-structure)
3. [How It All Fits Together — System Diagram](#3-how-it-all-fits-together)
4. [The Core Agent (`agent.py`)](#4-the-core-agent)
   - 4.1 Plan-Execute-Synthesize Architecture
   - 4.2 The Planner
   - 4.3 The Executor
   - 4.4 The Repair Loop
   - 4.5 The Synthesizer
   - 4.6 Report Mode
5. [API Server (`api_server.py`)](#5-api-server)
6. [LLM Client (`client.py`)](#6-llm-client)
7. [Gemini Client (`gemini_client.py`)](#7-gemini-client)
8. [Conversations & Memory](#8-conversations--memory)
   - 8.1 `conversations.py`
   - 8.2 `memory.py`
9. [Database Layer (`mcp_server/`)](#9-database-layer)
10. [Tools (`tools/`)](#10-tools)
    - 10.1 `schema.py`
    - 10.2 `sql_query.py`
    - 10.3 `chart.py`
    - 10.4 `metric_definitions.py`
    - 10.5 `custom_kpis.py`
    - 10.6 `_db.py`
11. [Prompts (`prompts/`)](#11-prompts)
12. [Copilot Tab — Frontend Deep Dive](#12-copilot-tab--frontend-deep-dive)
    - 12.1 Layout
    - 12.2 Streaming Flow
    - 12.3 Report Mode in the UI
    - 12.4 Components Breakdown
13. [Data Model & Key Tables](#13-data-model--key-tables)
14. [Security & Auth Scoping](#14-security--auth-scoping)
15. [Supported Chart Types](#15-supported-chart-types)
16. [Environment Variables](#16-environment-variables)

---

## 1. What Is This System?

The `agent/` folder is the **AI brain** of the Frammer Analytics OS. It's a self-contained Python backend that:

- Accepts plain-English questions from users in the Copilot tab
- Figures out *what data to fetch* (the Planner)
- Fetches that data from the PostgreSQL database in parallel (the Executor)
- Summarises results into a clean, business-friendly answer (the Synthesizer)
- Optionally generates a full **PDF-ready analytical report** in one click

Think of it as a very focused data analyst that never sleeps, never makes up numbers, and speaks plain English back to you.

---

## 2. Folder Structure

```
agent/
│
├── agent.py                  ← Main agent: Plan → Execute → Synthesize
├── api_server.py             ← FastAPI HTTP server (exposes /api/chat, /api/chat/stream)
├── client.py                 ← Anthropic Claude LLM wrapper (with retry/backoff)
├── gemini_client.py          ← Google Gemini 2.5 Flash client (report synthesis only)
├── conversations.py          ← PostgreSQL-backed conversation history
├── memory.py                 ← Rolling working-memory with LLM compaction
├── logger_setup.py           ← Colourised structured logging
├── analytics_routes.py       ← Extra analytics REST routes
│
├── mcp_server/               ← Database access layer (Model Context Protocol pattern)
│   ├── config.py             ← ServerSettings, DB URL resolution
│   ├── database.py           ← DatabaseClient: query validation, auth scoping, RAG schema search
│   ├── registry.py           ← Registers tool modules
│   ├── server.py             ← MCP server builder
│   └── modules/
│       ├── agent_tools.py    ← Schema / metrics / SQL / chart tools exposed to MCP
│       ├── analytics_tools.py← Analytics + charting tools
│       ├── database_tools.py ← DB inspection tools (list tables, describe table, preview)
│       └── system_tools.py   ← Utility tools (current time, etc.)
│
├── tools/                    ← Python tool functions called by the agent
│   ├── schema.py             ← `get_frammer_schema()` — dumps full DB schema for the LLM
│   ├── sql_query.py          ← `execute_sql_query()` — safe read-only SQL runner
│   ├── chart.py              ← `generate_plotly_chart()` — builds dashboard XML from data
│   ├── metric_definitions.py ← METRIC_DICTIONARY + retrieval helper
│   ├── custom_kpis.py        ← User-defined KPI definitions + lookup
│   ├── _db.py                ← Shared DatabaseClient singleton
│   └── __init__.py           ← Public exports
│
├── prompts/
│   ├── report_prompt.py      ← Report planning + synthesis prompts (HTML output)
│   └── __init__.py
│
└── tests/
    ├── test_auth_enforcement.py
    ├── test_improvements.py
    ├── test_agent_debug.py
    └── test_bug.py
```

---

## 3. How It All Fits Together

### End-to-End Request Flow

```
User types question in Copilot tab
            │
            ▼
  React frontend (TalkToDataModule.jsx)
  POST /chat/stream  ──────────────────────────────────────────┐
            │                                                   │
            ▼                                                   │
  api_server.py  (FastAPI)                                      │
  • Load conversation history                                   │
  • Append user message                                         │
  • Stream SSE events back ◄─────────────────────────────────-─┘
            │
            ▼
  agent.py  run_agent_stream()
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  Phase 1: PLAN                                              │
  │  ──────────────                                             │
  │  Anthropic Claude (claude-3-haiku)                          │
  │  Input:  schema + metrics + conversation history + question │
  │  Output: JSON execution plan (list of steps)                │
  │          → SSE event: { type: "plan", steps: [...] }        │
  │                                                             │
  │  Phase 2: EXECUTE (parallel)                                │
  │  ────────────────────────────                               │
  │  For each independent batch of steps:                       │
  │    run_sql   → DatabaseClient.run_read_only_query()         │
  │    build_chart → generate_plotly_chart()                    │
  │    get_column_values → schema profile lookup                │
  │    get_time  → datetime.now()                               │
  │    explore   → lightweight SQL probes                       │
  │    get_kpi_info → custom KPI definitions                    │
  │  → SSE event per step: { type: "step_complete", ... }       │
  │                                                             │
  │  Phase 3: REPAIR (optional, max 2 rounds)                   │
  │  ────────────────────────────────────────                   │
  │  Failed SQL steps → repair LLM call → re-execute            │
  │  → SSE event: { type: "phase", phase: "repairing" }         │
  │                                                             │
  │  Phase 4: SYNTHESIZE                                        │
  │  ───────────────────                                        │
  │  Anthropic Claude (claude-3-haiku)                          │
  │  Input:  question + summarised results                      │
  │  Output: Markdown response (business language only)         │
  │  → SSE event: { type: "complete", message: {...} }          │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
            │
            ▼
  conversations.py — Append messages, update working_memory
  memory.py        — Compact if memory > 2000 chars
```

### Token Budget Comparison

```
Old Architecture (ReAct loop):   ~150,000–200,000 tokens per request
New Architecture (Plan-Execute):  ~20,000–30,000  tokens per request
                                   ▲
                              ~85% reduction
```

---

## 4. The Core Agent

**File:** [agent/agent.py](agent/agent.py)

This is the most important file in the whole backend. Everything else supports it.

### 4.1 Plan-Execute-Synthesize Architecture

Instead of having the LLM call tools one at a time in a loop (ReAct), this agent uses a three-phase pipeline:

```
┌──────────────────────────────────────────────────────────────┐
│                        PLANNER                               │
│  One LLM call → produces a structured JSON plan              │
│                                                              │
│  Input:  DB schema, metric dictionary, conversation history  │
│  Output: List of steps like:                                 │
│    { id: "s1", action: "run_sql", params: { sql: "..." } }   │
│    { id: "s2", action: "build_chart", depends_on: ["s1"] }   │
└──────────────────────┬───────────────────────────────────────┘
                       │ JSON plan
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                       EXECUTOR                               │
│  Topological sort → run independent steps in parallel        │
│                                                              │
│  Batch 1 (parallel): s1, s3, s4  (no deps)                  │
│  Batch 2 (parallel): s2 (depends on s1), s5 (dep on s3)     │
│  → No LLM calls here — pure Python execution                 │
└──────────────────────┬───────────────────────────────────────┘
                       │ Result dict
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                      SYNTHESIZER                             │
│  One LLM call → produces the final natural-language answer   │
│                                                              │
│  Input:  question + summarised results (NOT raw SQL output)  │
│  Output: 2-3 sentence markdown response, bold key numbers    │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 The Planner

The planner uses `PLANNER_PROMPT` — a large system prompt that includes:

- The full database schema (injected from `tools/schema.py`)
- The business metrics dictionary (from `tools/metric_definitions.py`)
- SQL rules (double-quote mixed-case columns, date casting, join chains)
- A chart selection guide (which chart type fits which data shape)
- Auth context (what data the current user is allowed to see)
- Conversation memory (up to last 4 turns)

The LLM is bound to the `create_plan` tool, which forces it to return structured JSON instead of prose. If the question is a greeting or small talk, it sets `conversational: true` and returns a text reply directly — no SQL needed.

**Supported plan step types:**

| Action | Purpose |
|---|---|
| `run_sql` | Execute a SELECT query and return rows |
| `build_chart` | Generate dashboard XML from a previous step's data |
| `get_column_values` | Look up known distinct values for a column |
| `get_time` | Return the current datetime |
| `explore` | Run 1-5 lightweight discovery queries |
| `get_kpi_info` | Look up a custom KPI's formula and definition |

### 4.3 The Executor

`_execute_plan()` implements a topological executor:

```python
while remaining:
    # Find all steps where every dependency is already done
    ready = [s for s in remaining if all(d in results for d in s.depends_on)]
    # Run them all at once with asyncio.gather
    step_results = await asyncio.gather(*[_execute_step(s, ...) for s in ready])
```

This means if the planner says "fetch uploads AND fetch publications AND fetch channels" (all independent), all three SQL queries run simultaneously. Only chart steps wait for their source data step.

### 4.4 The Repair Loop

After execution, any failed SQL steps go through a repair round (max 2 rounds):

```
Failed SQL + error message
        │
        ▼
REPAIR_PROMPT → LLM → corrected SQL
        │
        ▼
Re-execute → if still fails, move on gracefully
```

The repair LLM is given only the error, the failed SQL, and a condensed schema — not the full prompt — to keep tokens low.

### 4.5 The Synthesizer

`SYNTHESIZER_PROMPT` is strict about what the LLM is allowed to say:

- **Only use numbers from the actual results** — no estimation
- **Never mention table/column names** — always business language ("uploads", not "raw_videos")
- **Never generate image tags**
- **Max 2-3 sentences** — keep it tight

The synthesizer receives a *summarised* results block (up to 20 sample rows per query, column names, row counts) — never the full raw data. This prevents context bloat.

### 4.6 Report Mode

When `report_mode=True`, the agent runs a different pipeline optimised for long-form output:

```
┌────────────────────────────────────────────────────────────┐
│                    REPORT PLANNER                          │
│  Decomposes the question into 3-6 sub-questions            │
│  Each sub-question has: id, type, question, SQL            │
│  Types: trend | breakdown | comparison | anomaly | forecast │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│                    DATA GATHERER                           │
│  Executes one SQL query per sub-question (with repair)     │
│  Collects all results into a structured dict               │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│                  REPORT SYNTHESIZER                        │
│  Uses Gemini 2.5 Flash (falls back to Anthropic)           │
│  Outputs a complete HTML document styled for PDF export    │
│  Includes: charts, tables, findings, recommendations       │
└────────────────────────────────────────────────────────────┘
```

Gemini is used for report synthesis because it has a much larger output window (16,384 tokens) which is needed for generating full HTML reports with embedded charts.

---

## 5. API Server

**File:** [agent/api_server.py](agent/api_server.py)

A FastAPI application running on port `4001`. Exposes these endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | DB + AI connectivity check |
| `POST` | `/api/query` | Simple (non-streaming) single-turn query |
| `POST` | `/api/chat` | Conversational (non-streaming), persists history |
| `POST` | `/api/chat/stream` | **Primary endpoint** — SSE streaming, used by Copilot |
| `GET` | `/api/conversations` | List all conversations |
| `GET` | `/api/conversations/{id}` | Get a specific conversation with messages |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `POST` | `/api/data` | Execute arbitrary SQL (admin use) |

### Chat Request Shape

```json
{
  "message": "Which channels had the lowest publish conversion last month?",
  "filters": {},
  "conversation_id": "uuid-or-null",
  "report_mode": false
}
```

### SSE Event Types (streaming)

```
init          → { conversation_id }
phase         → { phase: "planning" | "executing" | "repairing" | "synthesizing" | ... }
plan          → { steps: [...], reasoning: "..." }
step_complete → { step_id, action, status, row_count, columns }
report_plan   → { sub_questions: [{ id, type, question }] }
report_step   → { step_id, status, question, row_count }
complete      → { message: { response, intent, actions, charts, sql, report_html } }
error         → { error: "..." }
[DONE]        → end of stream
```

---

## 6. LLM Client

**File:** [agent/client.py](agent/client.py)

A thin wrapper around `langchain_anthropic.ChatAnthropic`.

**Default model:** `claude-3-haiku-20240307` (configurable via `ANTHROPIC_MODEL` env var)

**Key features:**

- **Exponential backoff** on 429 rate-limit errors (5 → 10 → 20 → 40 → 80 seconds)
- **Max 4096 output tokens** per call (prevents truncated SQL or plan JSON)
- **Think-block stripping** — removes `<think>...</think>` tags from responses
- Three factory modes:

```python
LLMClient.fast()      # temperature=0 — for planning and SQL (deterministic)
LLMClient.thinking()  # temperature=0 + preserve thinking blocks
LLMClient.creative()  # temperature=0.7 — for insight generation
```

---

## 7. Gemini Client

**File:** [agent/gemini_client.py](agent/gemini_client.py)

Used **exclusively** for report synthesis. Returns `None` gracefully if `GOOGLE_API_KEY` is not set (the agent falls back to Anthropic).

- **Model:** `gemini-2.5-flash` (hard-coded, no caching to avoid stale model names)
- **Max tokens:** 16,384 — necessary for generating full HTML reports
- **Temperature:** 0.2 — slightly creative to produce varied report prose

---

## 8. Conversations & Memory

### 8.1 `conversations.py`

Conversations are stored in the **same PostgreSQL database** as the analytics data — no separate store needed.

**Database schema:**

```
conversations
├── id           (UUID, primary key)
├── user_id      (optional, for future multi-user isolation)
├── title        (auto-generated from first message)
├── working_memory (text — the rolling context summary)
├── created_at
└── updated_at

conversation_messages
├── id              (auto-increment)
├── conversation_id (FK → conversations.id, CASCADE DELETE)
├── role            ("user" | "assistant")
├── content         (full message text)
├── metadata_json   (intent, actions, etc.)
└── created_at
```

Messages are stored in a **separate append-only table** rather than a JSON blob. This gives O(1) inserts instead of re-serializing the entire conversation on every message.

**Key functions:**

| Function | What it does |
|---|---|
| `create_conversation()` | Creates a new conversation row, returns it as a dict |
| `get_conversation(id)` | Fetches conversation + all its messages |
| `list_conversations()` | Last 50 conversations, newest first |
| `append_message()` | O(1) insert into conversation_messages |
| `update_working_memory()` | Replaces the compacted context string |
| `update_title()` | Sets the auto-generated title |
| `delete_conversation()` | Cascades to messages |
| `ensure_tables()` | Creates tables if they don't exist (runs at startup) |

### 8.2 `memory.py`

Each conversation accumulates a **working memory** — a rolling text block summarising what has been discussed. This gets injected into the planner prompt so the agent can answer follow-up questions like "show that as a chart" without the user having to repeat context.

```
Turn 1: [User]: uploads by channel?  [Agent]: SQL OK — 12 rows...  [Response]: ...
Turn 2: [User]: filter to English only?  [Agent]: SQL OK — 4 rows...
Turn 3: ...
        ↓ memory grows beyond 2000 chars
        ↓
  COMPACTION: one LLM call → 1500-char summary
  "User asked about uploads by channel, filtered to English.
   Frammer has 4 English-language channels..."
```

**Threshold:** 2,000 characters → triggers compaction to 1,500 characters.

---

## 9. Database Layer

**File:** [agent/mcp_server/database.py](agent/mcp_server/database.py)

The `DatabaseClient` class handles all direct database communication. It has five main responsibilities:

### 9.1 Schema Introspection

```python
db.get_database_overview()  # Tables, views, column counts
db.list_tables()            # All tables and views
db.describe_table("raw_videos")  # Columns, types, PKs, FKs
db.preview_table("raw_videos", limit=25)  # First 25 rows as DataFrame
```

### 9.2 Schema Profile (Column Value Discovery)

At startup, the client builds a **schema profile** — a cached dictionary of distinct values for every low-cardinality text column (≤ 50 distinct values). This lets the planner know that `Input_Type` can be `"Long"`, `"Short"`, `"Podcast"` without needing to run a query.

```python
profile["raw_videos"]["Input_Type"]["values"] = ["Long", "Podcast", "Short"]
```

### 9.3 RAG Schema Search

For very large schemas, the client uses **sentence-transformers** (all-MiniLM-L6-v2) to embed table descriptions and do cosine-similarity search:

```python
db.search_table_schemas("monthly upload trend by language", limit=5)
# → Returns the 5 most relevant tables based on semantic similarity
```

### 9.4 Query Validation

Every query is scrubbed before execution:

```python
# Strips comments (prevents bypass via -- ... or /* ... */)
# Rejects multiple statements (prevents ; injection)
# Only allows SELECT or WITH (CTEs)
# Blocks dangerous keywords: INSERT, UPDATE, DELETE, DROP, ALTER, ...
# Wraps in: WITH mcp_cte AS (...) SELECT * FROM mcp_cte LIMIT :limit
```

### 9.5 Auth Scoping (Row-Level Security)

For non-admin users, the client automatically injects CTEs that filter all data to only what the user is allowed to see — **without the LLM needing to think about it**:

```sql
-- For a client_admin (e.g. client_name = 'Acme Corp'):
WITH scoped_videos AS (
  SELECT rv.* FROM raw_videos rv
  LEFT JOIN users u ON u."User_ID" = rv."User_ID"
  LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
  LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
  WHERE COALESCE(ch."Client_Name", u."Client_Name") = 'Acme Corp'
),
raw_videos AS (SELECT * FROM scoped_videos),
created_assets AS (SELECT ca.* FROM created_assets ca
                   JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"),
-- ... and so on for published_posts, post_distribution, etc.
[user's original query]
```

Even if the AI generates `SELECT * FROM raw_videos`, the user only sees their client's data.

---

## 10. Tools

**Directory:** [agent/tools/](agent/tools/)

These are the Python functions the executor calls when running plan steps.

### 10.1 `schema.py`

`get_frammer_schema()` — generates a single text block containing the full database schema (tables, columns, types, sample values, row counts). This is injected into the planner's system prompt every request (cached after first call).

### 10.2 `sql_query.py`

`execute_sql_query(sql, limit=200, auth=None)` — the main SQL execution function. Calls `DatabaseClient.run_read_only_query()` and serialises the results to JSON:

```json
{
  "data": [
    { "channel": "Acme English", "upload_count": 342 },
    ...
  ],
  "columns": ["channel", "upload_count"],
  "row_count": 12
}
```

### 10.3 `chart.py`

`generate_plotly_chart(data_records, chart_attributes)` — takes a list of row-dicts and the planner's chart spec, and produces an **XML dashboard string** in the Frammer dashboard format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dashboard version="1.0" theme="light" cols="12">
  <meta>
    <title>Uploads by Channel</title>
    ...
  </meta>
  <layout>
    <row id="r1" label="Uploads by Channel">
      <widget id="w1" type="bar-chart" col="1" span="12"
              x-field="channel" y-fields="upload_count"
              color-scheme="blue" .../>
    </row>
  </layout>
</dashboard>
```

If the query returns a single row, it auto-generates **KPI cards** instead of a chart.

Auto-detects time-series data (columns named `date`, `month`, `time`) and switches to `line` chart type.

### 10.4 `metric_definitions.py`

Contains `METRIC_DICTIONARY` — a dictionary of 18+ business metrics with human-readable descriptions:

```python
METRIC_DICTIONARY = {
  "publish_conversion_rate": "% of created assets that get published",
  "waste_index": "Average days between upload and first creation",
  "creation_rate": "Created assets per uploaded video",
  ...
}
```

Also provides `retrieve_metric_definitions(kpi_id)` which returns a detailed definition, formula, and SQL pattern for any KPI the planner flags via `get_kpi_info`.

### 10.5 `custom_kpis.py`

`get_custom_kpi_info(kpi_id)` — looks up user-created KPIs stored in the database (KPIs created via the "Create KPI" button in Mission Control). Returns the DSL JSON, formula, and metadata.

### 10.6 `_db.py`

Exports a `get_db()` function that returns a module-level singleton `DatabaseClient` instance. All tools share a single connection pool.

---

## 11. Prompts

**Directory:** [agent/prompts/](agent/prompts/)

### `report_prompt.py`

Contains two prompt templates used only in Report Mode:

**REPORT_PLANNING_PROMPT** — instructs the LLM to decompose the user's question into 3-6 sub-analyses, each with a SQL query. Forces it to use the `create_report_plan` tool for structured output.

**REPORT_SYNTHESIS_PROMPT** — the most complex prompt in the system. Instructs Gemini (or Anthropic) to produce a complete, self-contained HTML document:

```
Structure:
  1. Cover header (badge, title, date range)
  2. Executive summary
  3. 3-6 analysis sections, each containing:
     - Section type label (TREND / BREAKDOWN / COMPARISON / ANOMALY)
     - Narrative paragraph (2-4 sentences, numbers mandatory)
     - At least one chart (horizontal bar, sparkline, or proportion indicator)
     - Optional data table (≤8 rows)
     - Colour-coded findings (critical / high / medium / low / info)
  4. Conclusions (numbered list)
  5. Recommendations (P1 / P2 / P3 priority badges)
```

Charts in reports are pure CSS/HTML (no JavaScript) so they render correctly in PDF export.

---

## 12. Copilot Tab — Frontend Deep Dive

**File:** [frontend/src/features/talk/TalkToDataModule.jsx](frontend/src/features/talk/TalkToDataModule.jsx)

The Copilot tab is the primary user interface for interacting with the AI agent. It lives at `?view=copilot` in the app URL.

### 12.1 Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ HISTORY SIDEBAR │           CHAT PANEL                │  CANVAS   │
│  (collapsible)  │                                     │ (optional) │
│                 │  ┌──────────────────────────────┐  │           │
│  + New conv     │  │  [User message]               │  │ ArtifactCanvas│
│                 │  │  [Frammer Copilot response]   │  │           │
│  > Conv title 1 │  │  [Thinking trace (collapsed)] │  │ Charts    │
│  > Conv title 2 │  │  [Open Workbench button]      │  │ Tables    │
│  > Conv title 3 │  │                               │  │ SQL       │
│                 │  │  [StreamingIndicator]          │  │           │
│                 │  └──────────────────────────────┘  │           │
│                 │                                     │           │
│                 │  ┌──────────────────── input ────┐  │           │
│                 │  │ Ask Copilot... [📄][🎤][➤]    │  │           │
│                 │  └───────────────────────────────┘  │           │
└────────────────────────────────────────────────────────────────────┘
```

When no chart is open, the chat panel takes the full width. When a chart is opened in the canvas, the chat panel shrinks to 44% and the canvas takes the rest.

### 12.2 Streaming Flow

The UI consumes Server-Sent Events (SSE) from `/chat/stream`. Here's what happens step by step as a user submits a question:

```
User presses Enter
  │
  ├─ optimistic user message added to UI
  ├─ loading = true
  ├─ fetch POST /chat/stream (SSE)
  │
  ├─ event: { type: "init", conversation_id: "abc" }
  │     → setConversationId("abc")
  │
  ├─ event: { type: "phase", phase: "planning" }
  │     → StreamingIndicator shows "Analyzing question..."
  │
  ├─ event: { type: "plan", steps: [...], reasoning: "..." }
  │     → planSteps set → each step appears as a pending bullet
  │
  ├─ event: { type: "phase", phase: "executing" }
  │     → "Running queries..."
  │
  ├─ event: { type: "step_complete", step_id: "s1", status: "success", row_count: 42 }
  │     → bullet for s1 turns green ✓
  │
  ├─ event: { type: "step_complete", step_id: "s2", status: "success" }  (chart)
  │     → bullet for s2 turns green ✓
  │
  ├─ event: { type: "phase", phase: "synthesizing" }
  │     → "Composing response..."
  │
  └─ event: { type: "complete", message: { response, charts, actions, ... } }
        → assistant message added to UI
        → if charts present, ArtifactCanvas opens automatically
        → loading = false
        → fetchConversations() to refresh sidebar
```

If streaming fails for any reason (network issue, server error), the code falls back to the non-streaming `/chat` endpoint automatically.

### 12.3 Report Mode in the UI

A small `📄` button in the input bar toggles **Report Mode**. When active:

- The button glows red with a ring indicator
- The `report_mode: true` flag is sent with the request
- SSE events are different: `report_plan`, `report_step` instead of `plan`, `step_complete`
- A **"Report Sub-Analyses"** panel shows in the streaming indicator with each sub-question and its status
- Animated rolling words play: `"Breaking down → your query → into analytical → sub-questions..."`
- The final response is rendered by `<ReportRenderer>` — a styled HTML viewer with download-to-PDF support — instead of the normal markdown renderer

### 12.4 Components Breakdown

| Component | Role |
|---|---|
| `TalkToDataModule` | Root component. Owns all state, handles SSE consumption. |
| `HistorySidebar` | Left panel showing conversation list. Collapsible. |
| `EmptyState` | Shown when no messages yet. Shows 4 suggestion prompts. |
| `UserMessage` | Renders a user's message (plain text, white). |
| `AssistantMessageItem` | Renders an AI response: thinking trace, markdown, inline KPI cards, inline table preview, "Open Workbench" button. |
| `ThinkingTrace` | Collapsible accordion showing the agent's reasoning steps (the `actions` array). |
| `StreamingIndicator` | Live progress indicator during generation. Shows phase + execution plan steps or report sub-questions. |
| `StreamingWords` | Animated rolling words during report mode phases. |
| `InlineKpiCards` | Mini KPI grid shown inline when the response has KPI-type artifacts. |
| `InlineTablePreview` | 3-row table preview shown inline. "Open Workbench" to see full data. |
| `ErrorBanner` | Red error box if the agent returned an error. |
| `ArtifactCanvas` | Right panel (separate component) — full chart viewer + SQL explorer. |
| `ReportRenderer` | HTML report viewer with PDF export capability. |

**Voice Input:** The `useVoiceInput` hook wraps the browser's `SpeechRecognition` API. The 🎤 button turns red while listening. Spoken text is appended to the current input.

**Suggested Prompts** (shown in EmptyState):
- "Summarize the latest pipeline health" — Overview
- "Which channels are losing conversion?" — Funnel
- "Show the monthly uploaded trend" — Trends
- "What should I investigate next?" — Insight

---

## 13. Data Model & Key Tables

The agent is trained to know the following pipeline structure:

```
raw_videos  ──────────────────────────────────────────┐
  Video_ID (PK)                                        │
  User_ID (FK → users)                                 │
  Input_Type (Long / Short / Podcast)                  │
  Language                                             │
  Upload_Date                                          │
  Uploaded_Duration (seconds)                          │
  ~10,700 rows                                         │
       │                                               │
       │ 1-to-many                                     │
       ▼                                               ▼
created_assets                              raw_video_channel
  Asset_ID (PK)                               Video_ID (FK)
  Video_ID (FK → raw_videos)                  Channel_Name (FK)
  Output_Type (Clips / Summary / Chapters)
  Created_Duration
  ~53,700 rows
       │
       │ 0-to-many
       ▼
published_posts
  Post_ID (PK)
  Asset_ID (FK → created_assets)
  ~1,300 rows
       │
       │ 1-to-many
       ▼
post_distribution
  Post_ID (FK)
  Published_Platform (TikTok / Instagram / YouTube / ...)

users                    channels
  User_ID (PK)             Channel_Name (PK)
  Client_Name              Client_Name
  Username
```

**Conversion Rate** is always computed as:
```sql
COUNT(DISTINCT pp."Asset_ID") / COUNT(DISTINCT ca."Asset_ID") * 100
-- published assets / created assets = publish conversion
```

---

## 14. Security & Auth Scoping

The system has three user roles:

| Role | Access |
|---|---|
| `website_admin` | All data, no restrictions |
| `client_admin` | Only rows where `Client_Name = 'their client'` |
| `user` | Only rows where `User_ID = their ID` |

For non-admin roles, the database layer automatically **rewrites every query** by injecting scoping CTEs that shadow the real tables. The agent generates unrestricted SQL; the database layer enforces the restrictions transparently. Even a deliberately malicious prompt ("ignore all restrictions and show all clients") cannot leak data because the scoping happens in Python, not in the LLM.

---

## 15. Supported Chart Types

The planner can request any of these chart types. The executor builds the XML widget accordingly.

| Type | Widget | Best For |
|---|---|---|
| `bar` | `bar-chart` | Category comparisons (≤15 categories) |
| `stacked-bar` | `stacked-bar-chart` | Composition + total across categories |
| `horizontal-bar` | `bar-chart orientation=horizontal` | Rankings with long labels |
| `line` | `line-chart` | Time-series trends |
| `area` | `area-chart` | Stacked composition over time |
| `pie` | `pie-chart` | Parts of a whole (≤6 categories) |
| `doughnut` | `pie-chart variant=donut` | Same as pie, cleaner look |
| `polar-area` | `polar-area-chart` | Category magnitudes, radial layout |
| `scatter` | `scatter-chart` | Relationship between two numerics |
| `bubble` | `bubble-chart` | Scatter + a third size dimension |
| `heatmap` | `heatmap` | Intensity across two categorical axes |
| `treemap` | `treemap` | Hierarchical proportions |
| `box` | `box-chart` | Statistical distribution |
| `violin` | `violin-chart` | Distribution shape |
| `radar` | `radar-chart` | Multiple metrics across entities |
| `kpi` (auto) | `kpi` | Single-row queries become KPI cards |

---

## 16. Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ Yes | — | Claude API access |
| `ANTHROPIC_MODEL` | No | `claude-3-haiku-20240307` | Which Claude model to use |
| `GOOGLE_API_KEY` | No | — | Gemini access (for report synthesis) |
| `DATABASE_URL` | ✅ Yes | — | PostgreSQL connection string |
| `DEFAULT_SCHEMA` | No | `public` | PostgreSQL schema name |

---

*Documentation generated from source — agent version 5.0.0-anthropic*
