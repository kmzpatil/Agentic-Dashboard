"""
Tool: generate_chart_config
Builds a Chart.js-compatible JSON configuration from pre-fetched data records
and chart attributes decided by the orchestrator.
"""

from typing import Any, Dict, List

import pandas as pd


def _df_from_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of row-dicts to a DataFrame."""
    return pd.DataFrame(records)


def _resolve_y_cols(attrs: Dict, df: pd.DataFrame, x_col: str) -> List[str]:
    """
    Return a list of valid y-axis column names from chart attributes,
    falling back to the first numeric column if nothing matches.
    """
    raw_y = attrs.get("y_axis", "")
    if isinstance(raw_y, list):
        candidates = [c.strip() for c in raw_y if str(c).strip()]
    else:
        candidates = [c.strip() for c in str(raw_y).split(",") if c.strip()] if raw_y else []
    valid = [c for c in candidates if c in df.columns]

    if not valid:
        # If no valid Y column is specified, look for numeric ones.
        # Even if x_col is numeric, if it's the only numeric col, we might want to plot it.
        numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        
        # Priority: numeric columns that aren't the x_col
        others = [c for c in numeric if c != x_col]
        if others:
            valid = [others[0]]
        elif numeric:
            valid = [numeric[0]]

    return valid


def generate_chart_config(
    data_records: List[Dict[str, Any]],
    chart_attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build and return a Chart.js-compatible JSON configuration object.

    Args:
        data_records:     List of data rows as dicts.
        chart_attributes: Dict with keys: type, x_axis, y_axis, title.

    Returns:
        A dict matching common Chart.js JSON structures.
    """
    df = _df_from_records(data_records)
    if df.empty:
        return {"error": "No data to plot"}

    df = df.fillna(0)
    attrs = chart_attributes or {}

    # Resolve columns
    x_col = attrs.get("x_axis") or df.columns[0]
    if x_col not in df.columns:
        x_col = df.columns[0]

    y_cols = _resolve_y_cols(attrs, df, x_col)
    if not y_cols:
        return {"error": "No numeric columns for Y axis"}

    # Special case: if x_col and y_col are the same (e.g. SELECT total_views FROM...), 
    # and there's only one row, the labels should be "Total" or similar instead of the value itself.
    if x_col == y_cols[0] and len(df) == 1:
        labels = ["Total"]
    else:
        labels = [str(val) for val in df[x_col].tolist()]

    chart_type = attrs.get("type", "bar").lower()
    # Normalize chart types for Chart.js
    if "bar" in chart_type:
        chart_type = "bar"
    elif "pie" in chart_type or "donut" in chart_type:
        chart_type = "pie"
    elif "line" in chart_type:
        chart_type = "line"
    else:
        chart_type = "bar"

    title = attrs.get("title") or "Chart"

    # Build Chart.js structure
    # (labels are already defined above)
    datasets = []

    # Color palette matching the frontend PALETTES
    colors = [
        '#58a6ff', '#bc8cff', '#39d353', '#f78166', '#ffc400', '#f85149'
    ]

    for i, y_col in enumerate(y_cols):
        dataset = {
            "label": y_col.replace("_", " ").title(),
            "data": df[y_col].tolist(),
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)],
            "borderWidth": 1
        }
        datasets.append(dataset)

    config = {
        "type": chart_type,
        "x_axis": x_col,
        "y_axis": y_cols,
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": title
                },
                "legend": {
                    "display": len(datasets) > 1
                }
            }
        }
    }

    return config
