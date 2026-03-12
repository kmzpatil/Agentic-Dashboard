"""
Tool: retrieve_metric_definitions
Simulates a semantic/vector search layer over business metric definitions.
Used to look up exact formulas and definitions before generating SQL.
"""

import json
import os
from typing import Dict, List

def _load_metric_dictionary() -> Dict[str, str]:
    """Load and aggregate metric definitions from data_schema.json."""
    # The file is in the parent directory of this tool
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data_schema.json")
    
    if not os.path.exists(schema_path):
        return {}

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        records = data.get("records", [])
        tables: Dict[str, List[str]] = {}
        
        for record in records:
            table_name = record.get("table_name")
            column_name = record.get("column_name")
            data_type = record.get("data_type")
            
            if table_name and column_name:
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append(f"{column_name} ({data_type})")
        
        return {
            table_name: f"Table `{table_name}` contains metrics/columns: {', '.join(cols)}"
            for table_name, cols in tables.items()
        }
    except Exception:
        return {}

# Load once at module level
METRIC_DICTIONARY: Dict[str, str] = _load_metric_dictionary()


def retrieve_metric_definitions(search_term: str) -> str:
    """
    Return matching business metric definitions for the given search term.

    Args:
        search_term: A natural-language keyword or phrase (e.g. 'conversion rate').

    Returns:
        A pipe-separated string of matched definitions, or a fallback message.
    """
    if not METRIC_DICTIONARY:
        return "No metric definitions available. Check data_schema.json."

    results = [
        desc
        for term, desc in METRIC_DICTIONARY.items()
        if term in search_term.lower()
    ]
    if results:
        return " | ".join(results)

    # Fallback: if no specific term matches, return a summary of all available domains
    return (
        "No specific metric matched exactly. Available domains are: "
        f"{', '.join(METRIC_DICTIONARY.keys())}. "
        "Use standard SQL counting/summing."
    )
