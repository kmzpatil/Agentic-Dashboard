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
        def generate_chart(
            query: str,
            chart_type: str = "auto",
            x_axis: str | None = None,
            y_axis: str | None = None,
            color_by: str | None = None,
            limit: int | None = None,
        ) -> str:
            """Generate a Plotly chart JSON payload from a read-only SQL query result."""
            safe_limit = self.db.normalise_limit(
                limit,
                self.settings.default_chart_limit,
                self.settings.max_chart_limit,
            )
            try:
                dataframe = self.db.run_read_only_query(query, limit=safe_limit)
            except (QueryValidationError, Exception) as exc:
                return f"Error: {exc}"

            if dataframe.empty:
                return "Error: Query returned no rows to chart."

            try:
                figure = _build_figure(
                    dataframe=dataframe,
                    chart_type=chart_type,
                    x_axis=x_axis,
                    y_axis=y_axis,
                    color_by=color_by,
                )
            except ValueError as exc:
                return f"Error: {exc}"

            return figure.to_json()


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


def _build_figure(
    dataframe: pd.DataFrame,
    chart_type: str,
    x_axis: str | None,
    y_axis: str | None,
    color_by: str | None,
):
    selected_chart_type = _normalise_chart_type(chart_type)
    x_column, y_column = _resolve_axes(dataframe, x_axis=x_axis, y_axis=y_axis, chart_type=selected_chart_type)

    if color_by and color_by not in dataframe.columns:
        raise ValueError(f"Column '{color_by}' is not present in the query result.")

    title = f"{y_column or 'Count'} by {x_column}" if x_column else "Query Result Chart"

    if selected_chart_type == "auto":
        selected_chart_type = _pick_chart_type(dataframe, x_column, y_column)

    if selected_chart_type == "bar":
        return px.bar(dataframe, x=x_column, y=y_column, color=color_by, title=title)
    if selected_chart_type == "line":
        return px.line(dataframe, x=x_column, y=y_column, color=color_by, title=title)
    if selected_chart_type == "scatter":
        return px.scatter(dataframe, x=x_column, y=y_column, color=color_by, title=title)
    if selected_chart_type == "histogram":
        return px.histogram(dataframe, x=x_column, color=color_by, title=title)

    raise ValueError(f"Unsupported chart type '{selected_chart_type}'.")


def _normalise_chart_type(chart_type: str) -> str:
    supported = {"auto", "bar", "line", "scatter", "histogram"}
    normalised = chart_type.lower().strip()
    if normalised not in supported:
        raise ValueError(
            f"Unsupported chart_type '{chart_type}'. Use one of: {', '.join(sorted(supported))}."
        )
    return normalised


def _resolve_axes(
    dataframe: pd.DataFrame,
    x_axis: str | None,
    y_axis: str | None,
    chart_type: str,
) -> tuple[str, str | None]:
    columns = list(dataframe.columns)
    numeric_columns = [
        column_name
        for column_name in columns
        if pd.api.types.is_numeric_dtype(dataframe[column_name])
    ]

    if x_axis and x_axis not in columns:
        raise ValueError(f"Column '{x_axis}' is not present in the query result.")
    if y_axis and y_axis not in columns:
        raise ValueError(f"Column '{y_axis}' is not present in the query result.")

    if chart_type == "histogram":
        if x_axis:
            return x_axis, None
        if numeric_columns:
            return numeric_columns[0], None
        return columns[0], None

    resolved_x = x_axis or columns[0]
    resolved_y = y_axis

    if resolved_y is None:
        for column_name in columns:
            if column_name == resolved_x:
                continue
            if pd.api.types.is_numeric_dtype(dataframe[column_name]):
                resolved_y = column_name
                break

    if resolved_y is None:
        raise ValueError(
            "Could not infer a numeric y-axis. Pass y_axis explicitly or return a numeric column."
        )

    return resolved_x, resolved_y


def _pick_chart_type(dataframe: pd.DataFrame, x_axis: str, y_axis: str | None) -> str:
    if y_axis is None:
        return "histogram"
    if _looks_like_datetime(dataframe[x_axis]):
        return "line"
    if pd.api.types.is_numeric_dtype(dataframe[x_axis]):
        return "scatter"
    return "bar"


def _looks_like_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    parsed = pd.to_datetime(series, errors="coerce")
    return bool((parsed.notna().sum() / max(len(series), 1)) >= 0.8)


def _to_json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
