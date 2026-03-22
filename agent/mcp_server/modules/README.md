# MCP Server Modules

This directory contains the core tool modules for the MCP (Model Context Protocol) server. Each module groups together related features and makes them available as tools that an external AI agent or client can access and run through the FastMCP server.

## Overview

The modules package different capabilities ranging from advanced analytical features (such as executing queries and generating charts) to basic database operations and system utilities. Each module defines a class that is responsible for registering its corresponding tools onto a given FastMCP instance.

## Available Modules

### 1. `AgentToolModule` (`agent_tools.py`)
Exposes the primary data analysis tools utilized by ATLAS. It includes tools to query the database, retrieve schema semantics, and construct charts.
- **`get_schema`**: Retrieves the full database schema.
- **`get_metric_definitions`**: Looks up business metric formulas and definitions to accurately calculate metrics.
- **`search_relevant_schemas`**: Semantically searches for tables/columns relevant to an natural language query.
- **`run_sql_query`**: Executes read-only PostgreSQL `SELECT` queries and caches the results in-memory.
- **`build_chart`**: Generates a Plotly chart (`bar`, `line`, or `pie`) utilizing data from previously cached query results.

### 2. `AnalyticsToolModule` (`analytics_tools.py`)
Provides advanced analytical data profiling and chart rendering capabilities.
- **`profile_query_results`**: Profiles read-only query results, returning metadata such as row counts, null counts, unique distincts, and summary statistics for numeric data.
- **`generate_chart`**: Executes a query and auto-generates sophisticated Plotly charts based on inferring the appropriate visualization (supports auto, bar, line, scatter, histogram).

### 3. `DatabaseToolModule` (`database_tools.py`)
Offers general-usage interaction routines for database exploration.
- **`get_database_overview`**: Provides a general synopsis of the schemas, tables, and views.
- **`list_tables`**: Fetches the available tables within a schema to give the agent available dataset choices.
- **`describe_table`**: Exhaustively describes table columns, primary arrays, and foreign keys.
- **`search_table_schemas`**: Natural language semantic search wrapper over the database schemas using RAG.
- **`preview_table`**: Retrieves sample rows of data for a quick assessment of contents.
- **`execute_sql_query`**: A generic SQL query runner (capped limit) for inspecting ad-hoc results.

### 4. `SystemToolModule` (`system_tools.py`)
Offers general system-level utilities for contextual grounding.
- **`get_current_time`**: Exposes the current local date and time. Used to enrich temporal language queries like "yesterday" or "last month" with actual timestamp values.

## Usage

These modules are collected in `__init__.py` and are intended to be imported into the main MCP server setup script (usually `server.py`).

Example instantiation and registration:

```python
from modules import AgentToolModule, AnalyticsToolModule
from mcp.server.fastmcp import FastMCP

# Initialize fastMCP and your DatabaseClient
mcp = FastMCP("My Server")
db = ...
settings = ...

# Register tools
AgentToolModule(db, settings).register(mcp)
AnalyticsToolModule(db, settings).register(mcp)
```
