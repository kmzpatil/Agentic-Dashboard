"""
tools package
Exports all Frammer Analytics tool functions for direct import.
"""

try:
    from tools.metric_definitions import retrieve_metric_definitions
    from tools.schema import get_frammer_schema
    from tools.sql_query import execute_sql_query, execute_exploration_queries
    from tools.chart import generate_plotly_chart
    from tools._db import get_db

    __all__ = [
        "retrieve_metric_definitions",
        "get_frammer_schema",
        "execute_sql_query",
        "execute_exploration_queries",
        "generate_plotly_chart",
        "get_db",
    ]
except ImportError:
    # When imported as agent.tools from the project root, the legacy
    # relative imports are unavailable. The new pipeline modules
    # (sql_validator, schema_loader, etc.) use fully-qualified imports.
    __all__ = []
