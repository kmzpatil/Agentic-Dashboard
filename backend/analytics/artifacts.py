from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.contracts import Artifact, Dataset, DatasetColumn


def _labelize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _sample_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (datetime, date)):
        return "date"
    return "string"


def _column_type(rows: list[dict[str, Any]], key: str) -> str:
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            lowered = key.lower()
            if "date" in lowered or "period" in lowered or "month" in lowered or "week" in lowered:
                return "date"
        return _sample_type(value)
    return "string"


def build_dataset(dataset_id: str, title: str, rows: list[dict[str, Any]]) -> Dataset:
    columns = list(rows[0].keys()) if rows else []
    schema = [
        DatasetColumn(key=column, label=_labelize(column), type=_column_type(rows, column))
        for column in columns
    ]
    return Dataset(id=dataset_id, title=title, rows=rows, schema=schema)


def _numeric_columns(dataset: Dataset) -> list[str]:
    return [column.key for column in dataset.columns if column.type == "number"]


def _dateish_columns(dataset: Dataset) -> list[str]:
    results = []
    for column in dataset.columns:
        lowered = column.key.lower()
        if column.type == "date" or any(token in lowered for token in ("date", "period", "month", "week", "day")):
            results.append(column.key)
    return results


def _dimension_columns(dataset: Dataset) -> list[str]:
    return [column.key for column in dataset.columns if column.type != "number"]


def _chart_spec(
    dataset: Dataset,
    chart_type_hint: str | None = None,
    extra_spec: dict[str, Any] | None = None,
    valid_chart_types: list[str] | None = None,
) -> dict[str, Any] | None:
    numeric_columns = _numeric_columns(dataset)
    if not numeric_columns:
        return None

    dateish = _dateish_columns(dataset)
    dimensions = _dimension_columns(dataset)
    x_field = (dateish or dimensions or [dataset.columns[0].key])[0]

    if chart_type_hint:
        chart_type = chart_type_hint
    else:
        chart_type = "line" if x_field in dateish else "bar"
        if chart_type == "bar" and len(dataset.rows) <= 6 and len(numeric_columns) == 1:
            chart_type = "pie"

    spec = {
        "chartType": chart_type,
        "xField": x_field,
        "yFields": numeric_columns[:4],
        "maxRows": 50,
    }
    if valid_chart_types:
        spec["validChartTypes"] = valid_chart_types
    if extra_spec:
        spec.update(extra_spec)
    return spec


def build_dataset_artifacts(
    dataset: Dataset,
    *,
    title_prefix: str,
    sql: str = "",
    confidence: float = 0.82,
    include_table: bool = True,
    chart_type_hint: str | None = None,
    extra_spec: dict[str, Any] | None = None,
    valid_chart_types: list[str] | None = None,
) -> list[Artifact]:
    artifacts: list[Artifact] = []
    numeric_columns = _numeric_columns(dataset)

    if dataset.rows and len(dataset.rows) == 1 and numeric_columns:
        values = [
            {
                "label": _labelize(column),
                "value": dataset.rows[0].get(column),
            }
            for column in numeric_columns[:4]
        ]
        artifacts.append(
            Artifact(
                id=f"{dataset.id}-kpi",
                kind="kpi-grid",
                title=f"{title_prefix} Snapshot",
                dataset_id=dataset.id,
                spec={"items": values},
                provenance={"dataset": dataset.id, "sql": sql},
                confidence=confidence,
            )
        )

    chart_spec = _chart_spec(
        dataset,
        chart_type_hint=chart_type_hint,
        extra_spec=extra_spec,
        valid_chart_types=valid_chart_types
    )
    if dataset.rows and len(dataset.rows) > 1 and chart_spec:
        artifacts.append(
            Artifact(
                id=f"{dataset.id}-chart",
                kind="chart",
                title=f"{title_prefix} Chart",
                dataset_id=dataset.id,
                spec=chart_spec,
                provenance={"dataset": dataset.id, "sql": sql},
                confidence=confidence,
            )
        )

    if include_table:
        artifacts.append(
            Artifact(
                id=f"{dataset.id}-table",
                kind="table",
                title=f"{title_prefix} Data",
                dataset_id=dataset.id,
                spec={"pageSize": 12},
                provenance={"dataset": dataset.id, "sql": sql},
                confidence=min(confidence + 0.06, 0.99),
            )
        )

    return artifacts[:3]


def build_assistant_artifacts(
    rows: list[dict[str, Any]],
    *,
    sql: str = "",
    dataset_id: str = "query_result",
    title: str = "Analysis",
    chart_type_hint: str | None = None,
    extra_spec: dict[str, Any] | None = None,
    valid_chart_types: list[str] | None = None,
) -> tuple[list[Dataset], list[Artifact]]:
    dataset = build_dataset(dataset_id, f"{title} Dataset", rows)
    artifacts = build_dataset_artifacts(
        dataset, title_prefix=title, sql=sql,
        chart_type_hint=chart_type_hint, extra_spec=extra_spec,
        valid_chart_types=valid_chart_types,
    )
    return [dataset], artifacts
