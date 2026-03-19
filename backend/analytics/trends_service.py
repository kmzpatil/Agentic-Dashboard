from __future__ import annotations

from typing import Any

from backend.analytics.artifacts import build_assistant_artifacts
from backend.contracts import Artifact, Dataset
from backend.db.pool import query
from backend.middleware.auth import AuthContext
from backend.queries.analytics_shared import (
    build_access_filter,
    build_client_name_expr,
    get_metric_query,
    get_trend_insights,
)


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


def _normalize_filter_list(values: list[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        raw_values = values
    else:
        raw_values = [values]
    return [
        value
        for value in raw_values
        if value and value.strip().lower() not in {"all", ""}
    ]


def _build_trends_filters(
    auth: AuthContext,
    *,
    company: list[str] | str | None = None,
    channel: list[str] | str | None = None,
    user: list[str] | str | None = None,
    language: list[str] | str | None = None,
    input_type: list[str] | str | None = None,
    output_type: list[str] | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    access_filter = build_access_filter(auth, 2, "rv")
    join_parts: list[str] = []
    if access_filter["join"]:
        join_parts.append(access_filter["join"])
    predicates = list(access_filter["predicates"])
    params = list(access_filter["params"])
    next_index = access_filter["next_index"]

    needs_user_join = False
    needs_channel_join = False
    needs_client_channel_join = False

    def ensure_user_join() -> None:
        nonlocal needs_user_join
        if not needs_user_join:
            join_parts.append('LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"')
            needs_user_join = True

    def ensure_channel_join() -> None:
        nonlocal needs_channel_join
        if not needs_channel_join:
            join_parts.append('LEFT JOIN raw_video_channel rvc_filter ON rv."Video_ID" = rvc_filter."Video_ID"')
            needs_channel_join = True

    def ensure_client_channel_join() -> None:
        nonlocal needs_client_channel_join
        if not needs_client_channel_join:
            join_parts.append('LEFT JOIN channels ch_filter ON ch_filter."Channel_Name" = rvc_filter."Channel_Name"')
            needs_client_channel_join = True

    def add_any_predicate(column: str, values: list[str]) -> None:
        nonlocal next_index
        if not values:
            return
        predicates.append(f'{column} = ANY(${next_index})')
        params.append(values)
        next_index += 1

    def add_date_predicate(op: str, value: str | None) -> None:
        nonlocal next_index
        if not value:
            return
        predicates.append(f'to_date(rv."Upload_Date", \'YYYY-MM-DD\') {op} ${next_index}')
        params.append(value)
        next_index += 1

    company_list = _normalize_filter_list(company)
    channel_list = _normalize_filter_list(channel)
    user_list = _normalize_filter_list(user)
    language_list = _normalize_filter_list(language)
    input_type_list = _normalize_filter_list(input_type)
    output_type_list = _normalize_filter_list(output_type)

    if company_list:
        ensure_user_join()
        ensure_channel_join()
        ensure_client_channel_join()
        add_any_predicate(build_client_name_expr("ch_filter", "u_filter"), company_list)

    if channel_list:
        ensure_channel_join()
        add_any_predicate('rvc_filter."Channel_Name"', channel_list)

    if user_list:
        ensure_user_join()
        add_any_predicate('u_filter."User_Name"', user_list)

    add_any_predicate('rv."Language"', language_list)
    add_any_predicate('rv."Input_Type"', input_type_list)
    add_date_predicate(">=", date_from)
    add_date_predicate("<=", date_to)

    asset_predicates: list[str] = []
    if output_type_list:
        asset_predicates.append(f'ca."Output_Type" = ANY(${next_index})')
        params.append(output_type_list)
        next_index += 1

    access_filter["join"] = "\n".join([part for part in join_parts if part])
    access_filter["predicates"] = predicates
    access_filter["params"] = params
    access_filter["next_index"] = next_index
    return access_filter, asset_predicates


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
    company: list[str] | str | None = None,
    channel: list[str] | str | None = None,
    user: list[str] | str | None = None,
    language: list[str] | str | None = None,
    input_type: list[str] | str | None = None,
    output_type: list[str] | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    safe_metric = _safe_metric(metric)
    safe_granularity = _safe_granularity(granularity)
    if auth.role in {"client_admin", "user"} and auth.client_name:
        company = [auth.client_name]

    access_filter, asset_predicates = _build_trends_filters(
        auth,
        company=company,
        channel=channel,
        user=user,
        language=language,
        input_type=input_type,
        output_type=output_type,
        date_from=date_from,
        date_to=date_to,
    )
    sql = get_metric_query(safe_metric, access_filter, asset_predicates)
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
