from __future__ import annotations

from backend.analytics.artifacts import build_assistant_artifacts
from backend.contracts import Artifact, Dataset
from backend.db.pool import query
from backend.middleware.auth import AuthContext
from backend.queries.analytics_shared import build_access_filter, get_metric_query, get_trend_insights


METRIC_LABELS = {
    "uploaded_count": "Uploaded Volume",
    "created_count": "Created Assets",
    "published_count": "Published Posts",
    "uploaded_duration": "Uploaded Duration",
    "created_duration": "Created Duration",
    "published_duration": "Published Duration",
    "publish_conversion_rate": "Publish Conversion Rate",
    "creation_rate": "Creation Rate",
    "processing_efficiency": "Processing Efficiency",
    "waste_index": "Waste Index",
}

VALID_GRANULARITIES = {"day", "week", "month", "quarter"}
DEFAULT_METRIC = "uploaded_count"


def _safe_metric(metric: str | None) -> str:
    if metric in METRIC_LABELS:
        return str(metric)
    return DEFAULT_METRIC


def _safe_granularity(granularity: str | None) -> str:
    if granularity in VALID_GRANULARITIES:
        return str(granularity)
    return "month"


def _to_points(rows: list[dict]) -> list[dict]:
    points = []
    for row in rows:
        period = row.get("period")
        value = float(row.get("value") or 0)
        points.append({"period": str(period), "value": round(value, 4)})
    return points


def _summary(points: list[dict]) -> dict:
    latest = points[-1] if points else None
    previous = points[-2] if len(points) > 1 else None
    delta_pct = 0.0
    if latest and previous and float(previous["value"]) != 0:
        delta_pct = ((float(latest["value"]) - float(previous["value"])) / float(previous["value"])) * 100
    return {
        "latest": latest,
        "previous": previous,
        "deltaPct": round(delta_pct, 2),
    }


def get_trends_snapshot(
    auth: AuthContext,
    *,
    metric: str | None = None,
    granularity: str | None = None,
) -> dict:
    safe_metric = _safe_metric(metric)
    safe_granularity = _safe_granularity(granularity)
    access_filter = build_access_filter(auth, 2, "rv")
    sql = get_metric_query(safe_metric, access_filter)
    rows = query(sql, [safe_granularity, *access_filter["params"]]).rows
    points = _to_points(rows)
    datasets, artifacts = build_assistant_artifacts(
        points,
        sql=sql,
        dataset_id=f"{safe_metric}_{safe_granularity}",
        title=METRIC_LABELS[safe_metric],
    )
    primary_artifacts: list[Artifact] = []
    for artifact in artifacts:
        if artifact.kind == "chart":
            artifact.title = f"{METRIC_LABELS[safe_metric]} Trend"
            artifact.spec["chartType"] = "line"
            primary_artifacts.append(artifact)
            break
    primary_artifacts.extend([artifact for artifact in artifacts if artifact.kind != "chart"][:2])

    return {
        "metric": safe_metric,
        "metricLabel": METRIC_LABELS[safe_metric],
        "granularity": safe_granularity,
        "series": points,
        "summary": _summary(points),
        "anomalies": get_trend_insights(points),
        "datasets": [dataset.model_dump(by_alias=True) if isinstance(dataset, Dataset) else dataset for dataset in datasets],
        "artifacts": [artifact.model_dump() if isinstance(artifact, Artifact) else artifact for artifact in primary_artifacts],
    }
