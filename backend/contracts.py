from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DatasetColumn(BaseModel):
    key: str
    label: str
    type: str


class Dataset(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[DatasetColumn] = Field(default_factory=list, alias="schema")


class Artifact(BaseModel):
    id: str
    kind: str
    title: str
    dataset_id: str | None = None
    spec: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class InsightAction(BaseModel):
    type: str
    label: str
    target: str
    filter_state: dict[str, Any] = Field(default_factory=dict)


class InsightCard(BaseModel):
    id: str
    surface: str
    title: str
    summary: str
    severity: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    cta: InsightAction


class AssistantMessage(BaseModel):
    role: str = "assistant"
    markdown: str
    artifacts: list[Artifact] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    suggested_actions: list[InsightAction] = Field(default_factory=list)
    intent: str = "analytics"
    sql: str = ""
    error: str = ""


class ChatEnvelope(BaseModel):
    conversation_id: str
    message: AssistantMessage
    response: str
    actions: list[str] = Field(default_factory=list)
    chart_data: dict[str, Any] = Field(default_factory=dict)
    chart_xml: str = ""  # Legacy: first chart XML
    chart_xmls: list[str] = Field(default_factory=list)  # All chart XMLs
    error: str = ""


class ServiceStatus(BaseModel):
    ok: bool
    detail: str | None = None
    error: str | None = None
    configured: bool | None = None
    missing_tables: list[str] = Field(default_factory=list)
    database: str | None = None


class HealthStatus(BaseModel):
    ok: bool
    services: dict[str, ServiceStatus]


# ── Custom KPI ────────────────────────────────────────────────────────────────

class KPICreateRequest(BaseModel):
    name: str
    description: str | None = None
    mode: Literal["formula", "natural_language"]
    expression: str
    time_granularity: Literal["day", "week", "month"] = "month"


class KPIResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    dsl_json: dict[str, Any]
    created_at: str | None = None


class KPIExecuteResponse(BaseModel):
    id: int
    name: str
    dsl_json: dict[str, Any]
    time_series: list[dict[str, Any]] = Field(default_factory=list)
    insights: dict[str, Any] = Field(default_factory=dict)
