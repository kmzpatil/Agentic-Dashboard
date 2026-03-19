# Frammer Analytics Agent Architecture

This directory contains the root orchestration architecture for the Frammer AI Analytics Agent. It governs the entire lifecycle of an analytical request, establishing secure HTTP topologies and managing the intricate ReAct (Reasoning and Acting) loops executed by the underlying Large Language Model.

## Subdirectory Overview

The repository is modularized into distinct functional boundaries to isolate operational concerns:

*   **`mcp_server/`**: The Model Context Protocol (MCP) server environment. Encapsulates connection pooling, query security (proactive CTE injection), Retrieval-Augmented Generation (RAG) schema indexing, and module definitions to be consumed by the FastMCP runtime.
*   **`tools/`**: The standalone functional units (the "hands" of the agent). Contains the executable logic to run read-only PostgreSQL queries, retrieve metric formulas, fetch schemas, and translate tabular data into structured Plotly XML chart payloads.
*   **`templates/`**: The frontend viewport. Houses `index.html`, a vanilla Single Page Application (SPA) that acts as the user interface. It dynamically renders agent-generated XML layout strings into interactive, multi-dimensional Chart.js dashboards.
*   **`tests/`**: The validation suite. Contains rigorous `pytest` modules confirming the integrity of dynamic SQL scoping, isolated authentication boundaries, and query sanitization (e.g., stripping malicious inline SQL comments).

## Core Modules

The files located at the root of the `agent` directory operate as the central control plane, tying the subdirectories together into a functional API.

### 1. `agent.py` (The Orchestrator)
The foundational logic core of the application. It constructs a `LangGraph StateGraph` to systematically route the Anthropic model (Claude 3 Haiku) through an iterative ReAct loop.
*   **Context Injection:** Injects dynamic database schemas, SQL cardinality rules, and real-time metric definitions into the `SystemMessage` payload prior to generation.
*   **Authentication & Security Scoping:** Intercepts authentication contexts to proactively append row-level filtering instructions to the system prompt (e.g., dynamically enforcing `Client_Name` constraints based on token roles).
*   **Workflow Routing:** Classifies incoming natural-language prompts to determine the routing intention (Analytics vs. Conversational) and securely coordinates the invocation of external MCP tools.
*   **Planning Constraints:** Implements a fast, low-temperature LLM planning pass (`_generate_plan`) to structure complex queries prior to autonomous tool execution.

### 2. `api_server.py` (The Primary Transport Layer)
The principal `FastAPI` instance exposing the interaction endpoints.
*   Initializes CORS middleware and manages ASGI lifecycle events, ensuring database dependencies are resolved upon worker startup.
*   Mounts the primary LLM-driven REST endpoints (`/api/query`, `/api/chat`), acting as the ingress for the `agent.py` orchestrator.
*   Provides RESTful conversation state endpoints (`/api/conversations/*`) connecting to the persistence layer.

### 3. `analytics_routes.py` (The Auxiliary Transport Layer)
A secondary `FastAPI` sub-router designed for deterministic, low-latency UI operations.
*   Executes hardcoded, parameterized `sqlite3` queries strictly for static UI widget populations (e.g., top-level Key Performance Indicators, generic funnel dimension breakdowns).
*   Operates entirely outside the ReAct loop to maintain strictly bounded response times for dashboard initializations.

### 4. `client.py` (The LLM Interface)
A hardened network wrapper extending the `langchain_anthropic` configuration.
*   Guarantees operational stability by implementing deterministic exponential backoff routines specifically mitigating HTTP 429 (Rate Limit) errors.
*   Exposes operational factory methods (`LLMClient.fast()`, `LLMClient.creative()`, `LLMClient.thinking()`) to strictly align architectural temperature parameters with the mathematical or creative requirements of the executing node.

### 5. `conversations.py` (The Persistence Layer)
Manages robust tracking of conversational state via `SQLAlchemy`.
*   Materializes conversation sessions into a structured PostgreSQL schema (`conversations`, `conversation_messages`).
*   Utilizes optimized append-only database architectures for chat messaging, guaranteeing O(1) transactional insert speeds rather than forcing the engine to deserialize/serialize heavy JSON arrays on every conversational turn.

### 6. `memory.py` (The Context Manager)
Manages the active contextual token window mapped to the LLM interaction layer.
*   Continuously monitors accumulated character volume across conversation arrays.
*   When the context exceeds structural safety constraints (`MAX_MEMORY_CHARS`), it automatically spawns an asynchronous, low-temperature LLM compaction call (`_compact_memory`) to synthetically summarize and truncate historical turns. This ensures the primary agent loop never throws a hard token-limit overflow exception while preserving critical business context.

### 7. `logger_setup.py` (The Telemetry Bus)
Standardizes diagnostic tracing across the Frammer stack.
*   Injects an ANSI colorized formatter (`FrammerColorFormatter`), dynamically altering log hues based on `logging.LogRecord` prefixes (e.g., LLM iteration loops vs. Tool calls).
*   Explicitly patches excessively noisy third-party dependencies (`httpx`, `httpcore`, `openai`, `langchain`) to `WARNING` levels, ensuring that primary agent operation traces remain legible and immediately actionable in production environments.

## Supplemental Assets

*   **`frammer_data.sql` / `frammer_database.dump`**: Initial seed data blocks providing the baseline transactional structures and mock analytics data required to initialize new instances of the `DatabaseClient`.

## Service Initialization

The system components are designed to be aggregated and executed via standard ASGI servers. To boot the primary analytic backend locally:

```bash
uvicorn api_server:app --host 0.0.0.0 --port 4001
```