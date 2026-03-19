# Agent Architecture & Database Partitioning Analysis

This document outlines the current state of the Frammer Analytics Agent, its data flow, and the underlying database partitioning (scoping) mechanism.

## 1. Agent Flow & Data Movement

The agent operates as a **ReAct (Reasoning + Acting)** system built with **LangGraph** and powered by **Anthropic Claude 3 Haiku**.

### Agent Workflow Diagram

```mermaid
graph TD
    User([User Request]) -->|JSON| API[FastAPI: api_server.py]
    API -->|Intent Check| Classifier{Classifier}
    
    Classifier -->|Conversational| Chat[Direct Chat Response]
    Classifier -->|Analytics| Orchestrator[Agent: agent.py]
    
    Orchestrator -->|Schema & Metrics| Context[Context Injection]
    Context -->|System Prompt| Loop[LangGraph ReAct Loop]
    
    subgraph "ReAct Loop (StateGraph)"
        Agent[Agent Node: LLM] <-->|Tool Calls| Tools[Tool Node]
    end
    
    subgraph "Tools"
        SQL[run_sql_query]
        Metric[get_metric_definitions]
        Meta[get_schema]
        Chart[build_chart]
    end
    
    SQL -->|SQL Request| DBClient[DatabaseClient]
    DBClient -->|CTE Injection| Scoping[Virtual Scoping Layer]
    Scoping -->|Scoped SQL| PG[(PostgreSQL)]
    
    PG -->|Records| DBClient
    DBClient -->|JSON Result| SQL
    
    Loop -->|Final Answer| Summary[Markdown Summary]
    Summary --> API
    API -->|JSON Response| User
```

### Data Flow Keys
- **Input**: Natural language questions (standard or filtered).
- **Context**: Dynamic injection of database schema, business metrics, and conversation memory.
- **Security**: Proactive injection of `WITH` clauses (CTEs) to ensure tenant isolation.
- **Output**: Markdown summaries, SQL queries (internal), and Plotly chart XML.

---

## 2. Database Partitioning Research

### Current State: Virtual Scoping (CTEs)
Research confirms that the database does **not** use physical partitioning (e.g., `PARTITION BY`). Instead, it employs **Virtual Partitioning** at the application layer through **Proactive Scoping**.

### Procedural Flowchart: Data Scoping Logic

```mermaid
flowchart TD
    Start[Execute Tool: run_sql_query] --> GetAuth[Extract Auth: role, client_name, user_id]
    GetAuth --> IsAdmin{Is website_admin?}
    
    IsAdmin -->|Yes| ExecRaw[Execute Query Directly]
    IsAdmin -->|No| BuildCTE[Generate Scoping CTEs]
    
    subgraph "Scoping Engine"
        BuildCTE --> DefineBase[Define 'scoped_videos' based on Client/User]
        DefineBase --> Alias[Alias base tables: 'raw_videos', 'users', etc.]
        Alias --> Wrap[Wrap Agent SQL with CTE block]
    end
    
    Wrap --> Validate[Read-only Validation]
    Validate --> RunPG[Run on PostgreSQL]
    RunPG --> Return[Return Filtered JSON]
```

### Assumption Verification
| Assumption | Reality | Status |
| :--- | :--- | :--- |
| **Physical Partitioning** | None found in schema. | ❌ Not Followed |
| **Database-Level RLS** | RLS is disabled (`SET row_security = off`). | ❌ Not Followed |
| **CTE-Based Scoping** | Active and enforced in [mcp_server/database.py](file:///c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent/mcp_server/database.py). | ✅ Followed |
| **PostgreSQL Usage** | Confirmed PostgreSQL is the primary store. | ✅ Followed |

> [!WARNING]
> **Security Gap Identified**: The current implementation relies on **CTE Injection** in the Python layer. Previous project goals suggested a move to **PostgreSQL Row-Level Security (RLS)** for robustness, but the code shows this transition is incomplete or reverted.

---

## 3. Implementation Details

- **Database Client**: [mcp_server/database.py](file:///c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent/mcp_server/database.py) contains the logic that intercepts SQL queries and prepends the scoping block.
- **Agent Loop**: [agent/agent.py](file:///c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent/agent.py) manages the recursion and tool sequencing.
- **MCP Server**: Infrastructure used to bridge the LLM with database tools.
