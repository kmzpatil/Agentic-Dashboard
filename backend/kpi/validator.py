"""
validator.py
------------
Validates a KPI DSL JSON before it is persisted or compiled.

Rules enforced:
  - Formula/metric references only known, schema-backed metric atoms
  - Arithmetic tokens only (operators, parentheses, numbers, known metrics)
  - No SQL injection patterns (keywords, quotes, semicolons, comments)
  - time_granularity is one of day|week|month
  - filters reference valid dimension names
"""

from __future__ import annotations

import re
from typing import Any

# Metrics that can appear as atoms in formulas
FORMULA_ATOMS: set[str] = {
    "uploaded_count",
    "created_count",
    "published_count",
    "uploaded_duration",
    "created_duration",
    "published_duration",
}

# Metrics valid as standalone single-metric KPIs (not composable in formulas)
SINGLE_METRICS: set[str] = {
    "publish_conversion_rate",
    "creation_rate",
    "processing_efficiency",
    "waste_index",
}

ALL_KNOWN_METRICS: set[str] = FORMULA_ATOMS | SINGLE_METRICS

VALID_GRANULARITIES: set[str] = {"day", "week", "month"}

VALID_DIMENSIONS: set[str] = {
    "channel",
    "language",
    "input_type",
    "output_type",
    "user",
    "client",
    "team",
}

# SQL injection guard — reject any formula containing these
_SQL_INJECTION_PATTERNS = re.compile(
    r"(--|;|/\*|\*/|'|\"|`|\\|"
    r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bCREATE\b|"
    r"\bALTER\b|\bEXEC\b|\bEXECUTE\b|\bGRANT\b|\bREVOKE\b|\bUNION\b|"
    r"\bOR\b|\bAND\b|\bWHERE\b|\bFROM\b|\bJOIN\b)",
    re.IGNORECASE,
)

# Valid formula tokens: metric names, numbers, operators, whitespace
_VALID_FORMULA_TOKEN = re.compile(
    r"^[a-z0-9_\s\+\-\*\/\(\)\.]+$", re.IGNORECASE
)


def validate_dsl(dsl: dict[str, Any]) -> None:
    """
    Validate a KPI DSL JSON dict.
    Raises ValueError with a human-readable message on any violation.
    """
    kpi_type = dsl.get("type")
    if kpi_type not in ("single_metric", "formula", "raw_sql"):
        raise ValueError(f"Invalid DSL type '{kpi_type}'. Must be 'single_metric', 'formula', or 'raw_sql'.")

    granularity = dsl.get("time_granularity", "month")
    if granularity not in VALID_GRANULARITIES:
        raise ValueError(
            f"Invalid time_granularity '{granularity}'. Must be one of {sorted(VALID_GRANULARITIES)}."
        )

    if kpi_type == "single_metric":
        _validate_single_metric(dsl)
    elif kpi_type == "formula":
        _validate_formula(dsl)
    elif kpi_type == "raw_sql":
        _validate_raw_sql(dsl)

    _validate_filters(dsl.get("filters", []))


def _validate_single_metric(dsl: dict[str, Any]) -> None:
    metric = dsl.get("metric", "").strip()
    if not metric:
        raise ValueError("DSL type 'single_metric' requires a non-empty 'metric' field.")
    if metric not in ALL_KNOWN_METRICS:
        raise ValueError(
            f"Unknown metric '{metric}'. Supported: {sorted(ALL_KNOWN_METRICS)}."
        )


def _validate_formula(dsl: dict[str, Any]) -> None:
    formula = dsl.get("formula", "").strip()
    if not formula:
        raise ValueError("DSL type 'formula' requires a non-empty 'formula' field.")

    # Block SQL injection
    if _SQL_INJECTION_PATTERNS.search(formula):
        raise ValueError("Formula contains disallowed SQL keywords or characters.")

    # Only allow safe characters in formula
    if not _VALID_FORMULA_TOKEN.match(formula):
        raise ValueError(
            "Formula contains invalid characters. "
            "Only metric names, numbers, and +, -, *, /, (, ) are allowed."
        )

    # Ensure at least one known metric atom is referenced
    operands = dsl.get("operands", [])
    if not operands:
        raise ValueError("Formula DSL must include 'operands' listing the metric atoms used.")

    for atom in operands:
        if atom not in FORMULA_ATOMS:
            raise ValueError(
                f"Metric '{atom}' cannot be used in a formula. "
                f"Formula-composable atoms: {sorted(FORMULA_ATOMS)}. "
                f"Use 'single_metric' type for derived metrics like publish_conversion_rate."
            )

    # All operands must appear in the formula string
    for atom in operands:
        if atom not in formula:
            raise ValueError(f"Operand '{atom}' listed in 'operands' but not found in 'formula'.")

def _validate_raw_sql(dsl: dict[str, Any]) -> None:
    sql = dsl.get("sql", "").strip()
    if not sql:
        raise ValueError("DSL type 'raw_sql' requires a non-empty 'sql' field.")


def _validate_filters(filters: list[Any]) -> None:
    if not isinstance(filters, list):
        raise ValueError("'filters' must be a list.")
    for f in filters:
        if not isinstance(f, dict):
            raise ValueError("Each filter must be a dict with 'dimension' and 'value' keys.")
        dim = f.get("dimension", "")
        if dim not in VALID_DIMENSIONS:
            raise ValueError(
                f"Unknown filter dimension '{dim}'. Supported: {sorted(VALID_DIMENSIONS)}."
            )
        if not f.get("value"):
            raise ValueError(f"Filter for dimension '{dim}' has an empty value.")
