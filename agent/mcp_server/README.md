# MCP Server

This directory contains the central integration mechanisms for the Frammer MCP (Model Context Protocol) server. It orchestrates database connections, enforces query security, and registers the analytical capabilities that the AI agent interacts with.

## Project Structure

This directory is composed of the following core components:

### 1. `server.py`
The orchestration component. It provides the `build_mcp_server()` function, which instantiates the FastMCP runtime. This script initializes the database client, applies the environment configurations, and binds the individual tool modules to the server.

### 2. `database.py`
The database management component. The `DatabaseClient` class safely handles SQLAlchemy connections and query executions. Key responsibilities include:
- **Query Scoping:** Automatically injects Common Table Expressions (CTEs) to append role-based and client-specific filters, ensuring secure data isolation before the AI executes its SQL.
- **Schema Indexing & Search:** Utilizes `sentence-transformers` for Retrieval-Augmented Generation (RAG). It maintains a semantic index of ta`ble structures, enabling natural-language schema discovery.
- **Exploration Tools:** Exposes utility functions for the AI to preview database views, summarize metadata, and describe specific table schema details.

### 3. `config.py`
The configuration component. It defines the `ServerSettings` dataclass and parses `.env` parameters. It resolves database URLs (managing Postgres overrides, hosts, and SSL protocols) and establishes required functional limits (e.g., maximum query return sizes) to ensure system stability.

### 4. `registry.py`
The interface component. It defines the minimalist `ToolModule` protocol. Any module that expects to be mounted onto the MCP server must implement a `register(mcp: FastMCP)` method, standardizing tool integration across the codebase.

### 5. `modules/` (Directory)
The capability component. This directory contains the specific logical functions exposed as tools to the AI agent. It is organized into distinct domains:
- **`AgentToolModule`**: Standard agent tools (charting, running SQL).
- **`AnalyticsToolModule`**: Data profiling and auto-rendering visualizations.
- **`DatabaseToolModule`**: Foundational schema and catalog inspection.
- **`SystemToolModule`**: System-level utilities (e.g., current local time).

For detailed documentation on these capabilities, refer to the [Modules README](modules/README.md).

## Usage

To start and integrate the MCP server into your orchestrator:

```python
from agent.mcp_server import build_mcp_server

# Instantiates the server utilizing environmental variables by default.
mcp_app = build_mcp_server()
```
