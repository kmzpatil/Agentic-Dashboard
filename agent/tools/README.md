# Agent Tools Repertoire

This folder houses the granular, standalone functional units powering the analytical operations of the Frammer AI agent. While the `mcp_server` directory handles the transport networking and broad server coordination, this directory represents the actual "hands" of the agent—the concrete functions it triggers to fetch your data, read schemas, and plot visual insights.

## Design Philosophy

The tools here are designed to be explicitly imported and handed as callables to the orchestrator layer. They are fiercely standardized: they lean on a unified singleton database client to maintain connection efficiency and respect firm security boundaries. 

## Component Breakdown

### 1. `_db.py` (The Singleton)
The global linchpin for data connections. Rather than each individual tool initializing its own heavy SQLAlchemy engine, `_db.py` exposes a cached `get_db()` function. This guarantees that all tools route through the same restrictive, pooled `DatabaseClient` instantiated during server startup.

### 2. `schema.py`
Exposes the `get_frammer_schema()` function. This is typically the very first tool the AI calls in an analytical workflow. It introspects the connected database and returns a human-readable string comprehensively detailing every table, column, and data type. Critically, it also appends strict developer-defined relationship rules (e.g., cardinality caveats regarding assets vs. posts) to prevent the AI from generating structurally flawed joins.

### 3. `metric_definitions.py`
A vital contextual shim acting as a lightweight knowledge base. The `retrieve_metric_definitions()` function allows the AI to search a dictionary of core business logic. If an end-user asks about "publish conversion," the AI queries this tool to receive exactly how "publish conversion" should be logically tabulated across underlying datasets before it starts writing SQL.

### 4. `sql_query.py`
The execution engine for the AI's generated logic. It exposes `execute_sql_query()` and `execute_exploration_queries()`. 
- **Preprocessing:** It strips hallucinated markdown code blocks from the AI string prompt generation. 
- **Type Safety:** It utilizes `_type_aware_fillna()` to preemptively catch NaNs returned by pandas and coerces them into robust defaults (`0` for numeric grids or `""` for string arrays), preventing critical JSON serialization crashes down the pipeline.
- It then executes the final secure SQL payload via the `_db.py` client and emits a bundled JSON payload.

### 5. `chart.py`
The visualization rendering engine. `generate_plotly_chart()` seamlessly converts standard dictionary row-records into the rigorous XML dashboard layout strings expected by the frontend templates (as seen in `agent/templates/index.html`). By parsing lightweight AI parameters (like defining the `x_axis`, `y_axis`, and `type`), it infers the exact structure necessary whether the payload should manifest as a multi-series line chart, a doughnut graph, or a grid of isolated KPI cards.

## Usage Interface

All critical tools are neatly collected and exposed within `__init__.py`. 

```python
from tools import execute_sql_query, generate_plotly_chart, get_frammer_schema

# Direct imports keep the action orchestration pipeline clean and isolated from the gritty pandas or SQLAlchemy syntax.
```
