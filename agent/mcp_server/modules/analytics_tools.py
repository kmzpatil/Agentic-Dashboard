from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.express as px
from mcp.server.fastmcp import FastMCP

from ..config import ServerSettings
from ..database import DatabaseClient, QueryValidationError


@dataclass
class AnalyticsToolModule:
    db: DatabaseClient
    settings: ServerSettings

    def register(self, mcp: FastMCP) -> None:
        @mcp.tool()
        def profile_query_results(query: str, limit: int | None = None) -> str:
            """Profile a read-only query result with column types, null counts, uniques, and numeric summaries."""
            safe_limit = self.db.normalise_limit(
                limit,
                self.settings.default_query_limit,
                self.settings.max_query_limit,
            )
            try:
                dataframe = self.db.run_read_only_query(query, limit=safe_limit)
            except (QueryValidationError, Exception) as exc:
                return f"Error: {exc}"
            payload = _build_profile_payload(dataframe, safe_limit)
            return json.dumps(payload, indent=2, default=str)

        @mcp.tool()
        def generate_chart_config(
            records: list[dict[str, Any]],
            type_hint: str = "bar",
            x_axis: str | None = None,
            y_axis: str | None = None,
            title: str | None = None,
        ) -> str:
            """
            Build a Chart.js-compatible JSON configuration from query records.
            Use this for frontend rendering.
            """
            if not records:
                return json.dumps({"error": "No data to plot"})

            df = pd.DataFrame(records).fillna(0)
            
            # Resolve x_axis
            x_col = x_axis or df.columns[0]
            if x_col not in df.columns:
                x_col = df.columns[0]

            # Resolve y_axis (numeric columns)
            y_cols = []
            if y_axis:
                y_cols = [c.strip() for c in y_axis.split(",") if c.strip() in df.columns]
            
            if not y_cols:
                numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != x_col]
                y_cols = [numeric[0]] if numeric else []

            if not y_cols:
                return json.dumps({"error": "No numeric columns for Y axis"})

            # Normalize chart types
            chart_type = type_hint.lower()
            if "bar" in chart_type:
                chart_type = "bar"
            elif "pie" in chart_type or "donut" in chart_type:
                chart_type = "pie"
            elif "line" in chart_type:
                chart_type = "line"
            else:
                chart_type = "bar"

            final_title = title or f"{chart_type.title()} Chart"

            # Build Chart.js structure
            labels = [str(val) for val in df[x_col].tolist()]
            datasets = []
            colors = ['#58a6ff', '#bc8cff', '#39d353', '#f78166', '#ffc400', '#f85149']

            for i, y_col in enumerate(y_cols):
                datasets.append({
                    "label": y_col.replace("_", " ").title(),
                    "data": df[y_col].tolist(),
                    "backgroundColor": colors[i % len(colors)],
                    "borderColor": colors[i % len(colors)],
                    "borderWidth": 1
                })

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
                        "title": {"display": True, "text": final_title},
                        "legend": {"display": len(datasets) > 1}
                    }
                }
            }
            return json.dumps(config)


def _build_profile_payload(dataframe: pd.DataFrame, limit: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "row_count": len(dataframe.index),
        "limit_applied": limit,
        "columns": [],
        "sample_rows": DatabaseClient.dataframe_to_records(dataframe.head(10)),
    }

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        column_payload: dict[str, Any] = {
            "name": column_name,
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_numeric_dtype(series):
            stats = series.describe().to_dict()
            column_payload["summary"] = {key: _to_json_value(value) for key, value in stats.items()}
        else:
            top_values = series.astype("string").fillna("<null>").value_counts().head(5)
            column_payload["top_values"] = [
                {"value": str(index), "count": int(count)}
                for index, count in top_values.items()
            ]

        payload["columns"].append(column_payload)

    return payload


def _to_json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
