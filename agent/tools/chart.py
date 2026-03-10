"""
Tool: generate_plotly_chart
Builds an XML dashboard string from pre-fetched data records and chart
attributes decided by the orchestrator.

The XML schema follows the Frammer dashboard format:
  <dashboard> → <meta> + <layout> → <row> → <widget>

Supported widget types (auto-selected from chart_attributes.type):
  bar-chart   → bar / grouped bar
  pie-chart   → pie / donut
  kpi         → single-value KPI cards (when query returns 1 row)
  heatmap     → cross-tabular / pivot data
  line-chart  → time-series line

Returns the dashboard XML string, or an error JSON string on failure.
"""

import json
import os
import re
from datetime import date
from typing import Any, Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, indent, tostring

import pandas as pd
import psycopg2

FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"}


def _get_connection() -> psycopg2.extensions.connection:
    """Open a connection to the Frammer PostgreSQL database using env variables."""
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
    )


def _df_from_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of row-dicts (from execute_sql_query) to a DataFrame."""
    return pd.DataFrame(records)


def _resolve_y_cols(attrs: Dict, df: pd.DataFrame, x_col: str) -> List[str]:
    """
    Return a list of valid y-axis column names from chart attributes,
    falling back to the first numeric column if nothing matches.
    """
    raw_y = attrs.get("y_axis", "")
    # y_axis may arrive as a string "col1, col2" or already as a list
    if isinstance(raw_y, list):
        candidates = [c.strip() for c in raw_y if str(c).strip()]
    else:
        candidates = [c.strip() for c in str(raw_y).split(",") if c.strip()] if raw_y else []
    valid = [c for c in candidates if c in df.columns]

    if not valid:
        numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != x_col]
        valid = [numeric[0]] if numeric else []

    return valid


def _build_dashboard_xml(
    df: pd.DataFrame,
    attrs: Dict[str, Any],
    title: str,
    chart_type: str,
    x_col: str,
    y_cols: List[str],
) -> str:
    """Build and return the dashboard XML string."""
    today = date.today().isoformat()

    # ── Root ─────────────────────────────────────────────────────────────────
    root = Element("dashboard", {"version": "1.0", "theme": "light", "cols": "12"})

    # ── Meta ─────────────────────────────────────────────────────────────────
    meta = SubElement(root, "meta")
    SubElement(meta, "title").text = title
    SubElement(meta, "description").text = f"Auto-generated analytics: {title}"
    SubElement(meta, "created").text = today

    layout = SubElement(root, "layout")

    widget_id = 1

    # ── KPI row — if query returns a single row, show every column as a KPI ─
    if len(df) == 1:
        row_kpi = SubElement(layout, "row", {"id": "r1", "label": "Summary"})
        cols_per_kpi = max(3, 12 // max(len(df.columns), 1))
        col_cursor = 1
        color_cycle = ["blue", "purple", "teal", "green", "orange", "red"]
        for i, col in enumerate(df.columns):
            SubElement(row_kpi, "widget", {
                "id":           f"w{widget_id}",
                "type":         "kpi",
                "col":          str(col_cursor),
                "span":         str(cols_per_kpi),
                "title":        col.replace("_", " ").title(),
                "data-source":  "query_result",
                "metric":       col,
                "color-scheme": color_cycle[i % len(color_cycle)],
            })
            widget_id += 1
            col_cursor += cols_per_kpi
        # Also add main chart row below KPI
        chart_row_id = "r2"
    else:
        chart_row_id = "r1"

    # ── Main chart row ────────────────────────────────────────────────────────
    row_chart = SubElement(layout, "row", {"id": chart_row_id, "label": title})

    y_fields_str = ",".join(y_cols)
    y_labels_str = ",".join(c.replace("_", " ").title() for c in y_cols)

    if chart_type in ("bar", "bar-chart"):
        SubElement(row_chart, "widget", {
            "id":           f"w{widget_id}",
            "type":         "bar-chart",
            "col":          "1",
            "span":         "12",
            "title":        title,
            "data-source":  "query_result",
            "x-field":      x_col,
            "y-fields":     y_fields_str,
            "y-labels":     y_labels_str,
            "color-scheme": "multi" if len(y_cols) > 1 else "blue",
            "show-legend":  "true" if len(y_cols) > 1 else "false",
            "x-tick-short": "true",
        })

    elif chart_type in ("pie", "pie-chart"):
        SubElement(row_chart, "widget", {
            "id":          f"w{widget_id}",
            "type":        "pie-chart",
            "col":         "1",
            "span":        "12",
            "title":       title,
            "data-source": "query_result",
            "name-field":  x_col,
            "value-field": y_cols[0] if y_cols else "",
            "color-scheme": "multi",
            "show-legend": "true",
            "variant":     "donut",
        })

    elif chart_type in ("line", "line-chart"):
        SubElement(row_chart, "widget", {
            "id":           f"w{widget_id}",
            "type":         "line-chart",
            "col":          "1",
            "span":         "12",
            "title":        title,
            "data-source":  "query_result",
            "x-field":      x_col,
            "y-fields":     y_fields_str,
            "y-labels":     y_labels_str,
            "color-scheme": "multi" if len(y_cols) > 1 else "blue",
            "show-legend":  "true",
        })

    else:
        # Default: bar
        SubElement(row_chart, "widget", {
            "id":           f"w{widget_id}",
            "type":         "bar-chart",
            "col":          "1",
            "span":         "12",
            "title":        title,
            "data-source":  "query_result",
            "x-field":      x_col,
            "y-fields":     y_fields_str,
            "y-labels":     y_labels_str,
            "color-scheme": "multi" if len(y_cols) > 1 else "blue",
            "show-legend":  "true" if len(y_cols) > 1 else "false",
            "x-tick-short": "true",
        })

    # ── Pretty-print ─────────────────────────────────────────────────────────
    indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")


def generate_plotly_chart(
    query: Optional[str] = None,
    *,
    data_records: Optional[List[Dict[str, Any]]] = None,
    chart_attributes: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build and return a dashboard XML string for the given data.

    Call patterns:
      - generate_plotly_chart(data_records=[...], chart_attributes={...})
          → preferred: uses pre-fetched data + LLM-decided attributes
      - generate_plotly_chart(query="SELECT ...")
          → fallback: queries PostgreSQL and auto-guesses chart config

    Args:
        query:            A valid PostgreSQL SELECT statement (fallback mode).
        data_records:     Pre-fetched rows as a list of dicts (preferred mode).
        chart_attributes: Dict with optional keys:
                            - type:   "bar" | "line" | "scatter" | "pie"
                            - x_axis: column name for the X axis
                            - y_axis: column name(s) for the Y axis (comma-separated)
                            - title:  chart title string

    Returns:
        Dashboard XML string on success, or an error JSON string on failure.
    """
    attrs = chart_attributes or {}

    # ── 1. Obtain the DataFrame ───────────────────────────────────────────────
    if data_records is not None:
        df = _df_from_records(data_records)
    elif query:
        if any(re.search(rf"\b{kw}\b", query.upper()) for kw in FORBIDDEN_KEYWORDS):
            return json.dumps({"error": "Only read-only SELECT queries are allowed."})
        try:
            conn = _get_connection()
            df = pd.read_sql_query(query, conn)
            conn.close()
        except psycopg2.OperationalError as exc:
            return json.dumps({"error": f"Chart DB connection failed: {exc}"})
        except Exception as exc:
            return json.dumps({"error": f"Chart DB query failed: {exc}"})
    else:
        return json.dumps({"error": "Either query or data_records must be provided."})

    if df.empty:
        return json.dumps({"error": "Query returned no rows — nothing to plot."})

    df = df.fillna(0)

    # ── 2. Resolve chart config ───────────────────────────────────────────────
    x_col = attrs.get("x_axis") or df.columns[0]
    if x_col not in df.columns:
        x_col = df.columns[0]

    y_cols = _resolve_y_cols(attrs, df, x_col)
    if not y_cols:
        return json.dumps({"error": "No numeric column available for the Y axis."})

    chart_type = attrs.get("type", "bar").lower()
    chart_title = attrs.get("title") or f"{y_cols[0].replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}"

    # ── 3. Auto-detect line chart for time-series data ───────────────────────
    if not attrs.get("type"):
        is_time = (
            "date" in x_col.lower()
            or "month" in x_col.lower()
            or "time" in x_col.lower()
            or pd.api.types.is_datetime64_any_dtype(df[x_col])
        )
        if is_time:
            chart_type = "line"

    # ── 4. Build XML ─────────────────────────────────────────────────────────
    try:
        return _build_dashboard_xml(df, attrs, chart_title, chart_type, x_col, y_cols)
    except Exception as exc:
        return json.dumps({"error": f"XML generation failed: {exc}"})


def generate_chartjs_json(
    query: Optional[str] = None,
    *,
    data_records: Optional[List[Dict[str, Any]]] = None,
    chart_attributes: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build and return a Chart.js compatible JSON string for the given data.

    Args:
        query:            A valid PostgreSQL SELECT statement (fallback mode).
        data_records:     Pre-fetched rows as a list of dicts (preferred mode).
        chart_attributes: Dict with optional keys:
                            - type:   "bar" | "line" | "scatter" | "pie"
                            - x_axis: column name for the X axis
                            - y_axis: column name(s) for the Y axis (comma-separated)
                            - title:  chart title string

    Returns:
        Chart.js JSON string on success, or an error JSON string on failure.
    """
    attrs = chart_attributes or {}

    # 1. Obtain the DataFrame
    if data_records is not None:
        df = _df_from_records(data_records)
    elif query:
        if any(re.search(rf"\b{kw}\b", query.upper()) for kw in FORBIDDEN_KEYWORDS):
            return json.dumps({"error": "Only read-only SELECT queries are allowed."})
        try:
            conn = _get_connection()
            df = pd.read_sql_query(query, conn)
            conn.close()
        except Exception as exc:
            return json.dumps({"error": f"DB query failed: {exc}"})
    else:
        return json.dumps({"error": "Either query or data_records must be provided."})

    if df.empty:
        return json.dumps({"error": "Query returned no rows — nothing to plot."})

    df = df.fillna(0)

    # 2. Resolve chart config
    x_col = attrs.get("x_axis") or df.columns[0]
    if x_col not in df.columns:
        x_col = df.columns[0]

    y_cols = _resolve_y_cols(attrs, df, x_col)
    if not y_cols:
        return json.dumps({"error": "No numeric column available for the Y axis."})

    chart_type = attrs.get("type", "bar").lower()
    if chart_type not in ("bar", "line", "pie", "doughnut"):
        # Map scatter to line for simplest Chart.js support here
        if chart_type == "scatter":
            chart_type = "line"
        else:
            chart_type = "bar"

    chart_title = attrs.get("title") or f"{y_cols[0].replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}"

    # 3. Construct Chart.js payload (no data, only config)
    datasets = []
    colors = ["#e00000", "#ffffff", "#a3a3a3", "#525252", "#991b1b"]
    labels = []

    # Special logic for Pie/Doughnut with "wide" data (one row, multiple numeric columns)
    if chart_type in ["pie", "doughnut"] and len(df) == 1 and len(y_cols) > 1:
        labels = [col.replace("_", " ").title() for col in y_cols]
        datasets = [{
            "label": chart_title,
            "data": [],  # Empty; frontend fetches this
            "backgroundColor": [colors[i % len(colors)] for i in range(len(y_cols))],
            "borderWidth": 1
        }]
    else:
        # Standard multi-row or single-column data
        for i, y_col in enumerate(y_cols):
            dataset = {
                "label": y_col.replace("_", " ").title(),
                "data": [],  # Empty; frontend fetches this
                "backgroundColor": colors[i % len(colors)],
                "borderColor": colors[i % len(colors)],
                "borderWidth": 1
            }
            if chart_type == "line":
                dataset["fill"] = False
                dataset["tension"] = 0.1
            datasets.append(dataset)

    payload = {
        "type": chart_type,
        "x_axis": x_col,
        "y_axis": y_cols,
        "data": {
            "labels": labels, # May be column names for wide pie charts
            "datasets": datasets
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": chart_title
                },
                "legend": {
                    "display": len(y_cols) > 1 or chart_type in ["pie", "doughnut"]
                }
            }
        }
    }

    return json.dumps(payload, default=str)
