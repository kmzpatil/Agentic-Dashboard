"""Visualization Agent — produces chart artifacts from query results.

Each chart artifact represents one meaningful view of the data. The number
and types of charts are driven entirely by what the data and query need —
there is no fixed limit or fixed set of chart types.

Examples:
  - "waste index by users and channels" → 2 charts (one per x-axis)
  - "monthly trend" → 1 line chart
  - "top 5 clients" → 1 bar chart
  - "revenue by month and by channel" → 2 charts
  - "compare Q1 vs Q2 across all metrics" → as many as needed
"""

from __future__ import annotations

import logging
import uuid

from models.schemas import RoutingDecision

logger = logging.getLogger("agent.viz_agent")

_FE_MAP = {
    "bar": "bar", "stacked_bar": "bar", "line": "line",
    "area": "line", "pie": "pie", "scatter": "line", "heatmap": "bar",
}

_CHART_LABEL = {
    "bar": "Bar Chart", "line": "Line Chart", "pie": "Pie Chart",
    "area": "Area Chart", "scatter": "Scatter Plot", "heatmap": "Heatmap",
}


def _is_numeric(data: list[dict], col: str) -> bool:
    for row in data[:5]:
        v = row.get(col)
        if v is not None:
            try:
                float(v)
                return True
            except (TypeError, ValueError):
                return False
    return False


def _is_time_col(data: list[dict], col: str) -> bool:
    import re
    if any(k in col.lower() for k in ("date", "month", "week", "year", "day", "time", "period")):
        return True
    if data:
        return bool(re.match(r"\d{4}[-/]\d{2}", str(data[0].get(col, ""))))
    return False


def _pretty(col: str) -> str:
    return col.replace("_", " ").title()


def _best_chart_type(data: list[dict], x_col: str, y_cols: list[str]) -> str:
    """Pick the single best chart type for one dataset."""
    if _is_time_col(data, x_col):
        return "line"
    if len(data) <= 8 and len(y_cols) == 1:
        return "pie"
    return "bar"


def _detect_x_y(data: list[dict], x_hint: str | None, y_hint: str | None) -> tuple[str, list[str]]:
    if not data:
        return (x_hint or "x", [y_hint] if y_hint else [])
    cols = list(data[0].keys())
    if x_hint and x_hint in cols:
        x = x_hint
    else:
        date_cols = [c for c in cols if _is_time_col(data, c)]
        str_cols = [c for c in cols if not _is_numeric(data, c)]
        x = date_cols[0] if date_cols else (str_cols[0] if str_cols else cols[0])
    if y_hint and y_hint in cols:
        ys = [y_hint]
    else:
        ys = [c for c in cols if c != x and _is_numeric(data, c)]
        if not ys and len(cols) > 1:
            ys = [cols[-1]]
    return x, ys


def _build_artifact(data, chart_type, title, x_col, y_cols, ds_id):
    art_id = f"art-{uuid.uuid4().hex[:8]}"
    fe_type = _FE_MAP.get(chart_type, "bar")
    all_cols = list(data[0].keys()) if data else []
    schema = [{"key": c, "label": _pretty(c)} for c in all_cols]
    artifact = {
        "id": art_id, "kind": "chart", "title": title,
        "confidence": 0.9, "dataset_id": ds_id,
        "spec": {"chartType": fe_type, "xField": x_col, "yFields": y_cols, "maxRows": min(len(data), 50)},
    }
    dataset = {"id": ds_id, "rows": data[:50], "schema": schema}
    return artifact, dataset


def build_table_artifact(data: list[dict], title: str) -> tuple[dict, dict]:
    ds_id = f"ds-{uuid.uuid4().hex[:8]}"
    art_id = f"art-{uuid.uuid4().hex[:8]}"
    all_cols = list(data[0].keys()) if data else []
    schema = [{"key": c, "label": _pretty(c)} for c in all_cols]
    return (
        {"id": art_id, "kind": "table", "title": title, "confidence": 0.95,
         "dataset_id": ds_id, "spec": {"pageSize": 12}},
        {"id": ds_id, "rows": data[:100], "schema": schema},
    )


def build_kpi_artifact(data: list[dict], title: str) -> dict:
    if not data:
        return {}
    row = data[0]
    items = [{"label": _pretty(k), "value": v} for k, v in row.items()]
    return {"id": f"art-{uuid.uuid4().hex[:8]}", "kind": "kpi-grid",
            "title": title, "confidence": 0.95, "spec": {"items": items}}


class VisualizationAgent:
    """Generate chart artifacts driven by the data and query context.

    The agent generates as many charts as are meaningful — no fixed limit.
    Each chart gets a descriptive title derived from the actual columns.
    """

    def generate_artifacts(
        self,
        data: list[dict],
        requested_types: list[str] | None = None,
        title: str = "Chart",
        x_col: str | None = None,
        y_col: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Generate chart + table artifacts for one dataset."""
        if not data:
            return [], []

        # Single row → KPI
        if len(data) == 1 and not requested_types:
            kpi = build_kpi_artifact(data, title)
            return ([kpi], []) if kpi else ([], [])

        x, y_cols = _detect_x_y(data, x_col, y_col)
        chart_type = _best_chart_type(data, x, y_cols)

        # If explicit types requested, generate one chart per type
        if requested_types:
            types_to_use = []
            seen_fe = set()
            for t in requested_types:
                fe = _FE_MAP.get(t.lower().strip(), t.lower().strip())
                if fe not in seen_fe:
                    seen_fe.add(fe)
                    types_to_use.append(t.lower().strip())
            if not types_to_use:
                types_to_use = [chart_type]
        else:
            types_to_use = [chart_type]

        ds_id = f"ds-{uuid.uuid4().hex[:8]}"
        artifacts, datasets = [], []
        ds_done = False

        for ct in types_to_use:
            label = _CHART_LABEL.get(ct, ct.title())
            t = f"{_pretty(y_cols[0])} by {_pretty(x)} — {label}" if len(types_to_use) > 1 else title
            art, ds = _build_artifact(data, ct, t, x, y_cols, ds_id)
            artifacts.append(art)
            if not ds_done:
                datasets.append(ds)
                ds_done = True

        # Always include a data table
        t_art, t_ds = build_table_artifact(data, f"{title} — Data")
        artifacts.append(t_art)
        datasets.append(t_ds)
        return artifacts, datasets

    def generate_multi_artifacts(
        self,
        datasets_info: list[dict],
        routing: RoutingDecision | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Generate artifacts for multiple datasets (deep path).

        Each dataset in the analytics result becomes its own chart with the
        best-fit chart type. The dropdown will show one entry per dataset.
        No artificial limit — as many charts as datasets.
        """
        all_arts: list[dict] = []
        all_ds: list[dict] = []

        for i, ds_info in enumerate(datasets_info):
            data = ds_info.get("data", [])
            columns = ds_info.get("columns", [])
            ds_title = ds_info.get("title", f"Chart {i + 1}")
            if not data:
                continue

            x_col = columns[0] if columns else None
            y_col = columns[-1] if len(columns) > 1 else None
            x, y_cols = _detect_x_y(data, x_col, y_col)
            chart_type = _best_chart_type(data, x, y_cols)

            ds_id = f"ds-{uuid.uuid4().hex[:8]}"
            art, ds = _build_artifact(data, chart_type, ds_title, x, y_cols, ds_id)
            all_arts.append(art)
            all_ds.append(ds)

        # One table for the first dataset
        if datasets_info and datasets_info[0].get("data"):
            t_art, t_ds = build_table_artifact(datasets_info[0]["data"], "Data")
            all_arts.append(t_art)
            all_ds.append(t_ds)

        return all_arts, all_ds
