"""
test_kpi.py
-----------
Tests for the Custom KPI pipeline:
  - parser (formula + NL mocking)
  - validator
  - compiler (SQL structure)
  - service.compute_insights (pure logic, no DB)

All tests are unit tests — no database connection required.
"""

from __future__ import annotations

import json
import re
import pytest
from unittest.mock import MagicMock, patch


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestFormulaParser:
    def test_single_known_metric_returns_single_metric_type(self):
        from backend.kpi.parser import parse_formula_mode
        dsl = parse_formula_mode("uploaded_count")
        assert dsl["type"] == "single_metric"
        assert dsl["metric"] == "uploaded_count"
        assert dsl["time_granularity"] == "month"
        assert dsl["filters"] == []

    def test_single_derived_metric(self):
        from backend.kpi.parser import parse_formula_mode
        dsl = parse_formula_mode("publish_conversion_rate")
        assert dsl["type"] == "single_metric"
        assert dsl["metric"] == "publish_conversion_rate"

    def test_two_atom_formula_returns_formula_type(self):
        from backend.kpi.parser import parse_formula_mode
        dsl = parse_formula_mode("created_count / uploaded_count * 100")
        assert dsl["type"] == "formula"
        assert "created_count" in dsl["operands"]
        assert "uploaded_count" in dsl["operands"]
        assert "created_count / uploaded_count * 100" == dsl["formula"]

    def test_three_atom_formula(self):
        from backend.kpi.parser import parse_formula_mode
        dsl = parse_formula_mode("published_count + created_count - uploaded_count")
        assert dsl["type"] == "formula"
        assert set(dsl["operands"]) == {"published_count", "created_count", "uploaded_count"}

    def test_custom_granularity_respected(self):
        from backend.kpi.parser import parse_formula_mode
        dsl = parse_formula_mode("created_count / uploaded_count * 100", time_granularity="week")
        assert dsl["time_granularity"] == "week"

    def test_unknown_expression_raises(self):
        from backend.kpi.parser import parse_formula_mode
        with pytest.raises(ValueError, match="No known metric names"):
            parse_formula_mode("SELECT 1; DROP TABLE raw_videos;")

    def test_duration_metrics_formula(self):
        from backend.kpi.parser import parse_formula_mode
        dsl = parse_formula_mode("published_duration / created_duration * 100")
        assert dsl["type"] == "formula"
        assert set(dsl["operands"]) == {"published_duration", "created_duration"}


# ── NL parser tests (mocked LLM) ─────────────────────────────────────────────

class TestNLParser:
    def _mock_llm_response(self, dsl_dict: dict):
        """Helper: patch _call_llm to return a JSON string."""
        return patch(
            "backend.kpi.parser._call_llm",
            return_value=json.dumps(dsl_dict),
        )

    def test_nl_single_metric_parsed(self):
        from backend.kpi.parser import parse_nl_mode
        expected = {
            "type": "single_metric",
            "metric": "publish_conversion_rate",
            "time_granularity": "month",
            "filters": [],
        }
        with self._mock_llm_response(expected):
            dsl = parse_nl_mode("percentage of clips that get published")
        assert dsl["type"] == "single_metric"
        assert dsl["metric"] == "publish_conversion_rate"

    def test_nl_formula_parsed(self):
        from backend.kpi.parser import parse_nl_mode
        expected = {
            "type": "formula",
            "formula": "created_count / uploaded_count * 100",
            "operands": ["created_count", "uploaded_count"],
            "time_granularity": "month",
            "filters": [],
        }
        with self._mock_llm_response(expected):
            dsl = parse_nl_mode("creation success rate")
        assert dsl["type"] == "formula"

    def test_nl_llm_json_in_prose_extracted(self):
        """LLM sometimes wraps JSON in prose — parser should extract it."""
        from backend.kpi.parser import parse_nl_mode
        prose_response = (
            'Sure! Here is the DSL: {"type": "single_metric", '
            '"metric": "uploaded_count", "time_granularity": "month", "filters": []}'
        )
        with patch("backend.kpi.parser._call_llm", return_value=prose_response):
            dsl = parse_nl_mode("how many videos were uploaded")
        assert dsl["metric"] == "uploaded_count"

    def test_nl_missing_api_key_raises(self):
        from backend.kpi.parser import parse_nl_mode
        with patch("backend.kpi.parser._call_llm", side_effect=ValueError("ANTHROPIC_API_KEY is not set")):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                parse_nl_mode("total videos")


# ── Validator tests ───────────────────────────────────────────────────────────

class TestValidator:
    def test_valid_single_metric(self):
        from backend.kpi.validator import validate_dsl
        validate_dsl({
            "type": "single_metric",
            "metric": "uploaded_count",
            "time_granularity": "month",
            "filters": [],
        })  # should not raise

    def test_valid_formula(self):
        from backend.kpi.validator import validate_dsl
        validate_dsl({
            "type": "formula",
            "formula": "created_count / uploaded_count * 100",
            "operands": ["created_count", "uploaded_count"],
            "time_granularity": "month",
            "filters": [],
        })  # should not raise

    def test_unknown_type_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="Invalid DSL type"):
            validate_dsl({"type": "magic", "metric": "uploaded_count", "time_granularity": "month", "filters": []})

    def test_unknown_metric_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="Unknown metric"):
            validate_dsl({"type": "single_metric", "metric": "drop_table", "time_granularity": "month", "filters": []})

    def test_invalid_granularity_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="time_granularity"):
            validate_dsl({"type": "single_metric", "metric": "uploaded_count", "time_granularity": "quarter", "filters": []})

    def test_sql_injection_in_formula_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="disallowed SQL"):
            validate_dsl({
                "type": "formula",
                "formula": "uploaded_count; DROP TABLE raw_videos;--",
                "operands": ["uploaded_count"],
                "time_granularity": "month",
                "filters": [],
            })

    def test_non_composable_metric_in_formula_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="cannot be used in a formula"):
            validate_dsl({
                "type": "formula",
                "formula": "publish_conversion_rate + uploaded_count",
                "operands": ["publish_conversion_rate", "uploaded_count"],
                "time_granularity": "month",
                "filters": [],
            })

    def test_formula_missing_operands_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="'operands'"):
            validate_dsl({
                "type": "formula",
                "formula": "created_count / uploaded_count",
                "operands": [],
                "time_granularity": "month",
                "filters": [],
            })

    def test_operand_not_in_formula_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="not found in 'formula'"):
            validate_dsl({
                "type": "formula",
                "formula": "created_count * 100",
                "operands": ["created_count", "uploaded_count"],
                "time_granularity": "month",
                "filters": [],
            })

    def test_invalid_filter_dimension_raises(self):
        from backend.kpi.validator import validate_dsl
        with pytest.raises(ValueError, match="Unknown filter dimension"):
            validate_dsl({
                "type": "single_metric",
                "metric": "uploaded_count",
                "time_granularity": "month",
                "filters": [{"dimension": "unknown_dim", "value": "x"}],
            })

    def test_valid_filter_passes(self):
        from backend.kpi.validator import validate_dsl
        validate_dsl({
            "type": "single_metric",
            "metric": "uploaded_count",
            "time_granularity": "month",
            "filters": [{"dimension": "language", "value": "EN"}],
        })  # should not raise


# ── Compiler tests ────────────────────────────────────────────────────────────

class TestCompiler:
    """Verify compiler produces structurally correct SQL — no DB connection needed."""

    def _make_access_filter(self, role="website_admin"):
        """Build a minimal access filter as if build_access_filter() was called."""
        return {"join": "", "predicates": [], "params": [], "next_index": 2}

    def test_single_metric_returns_non_empty_sql(self):
        from backend.kpi.compiler import compile_dsl
        dsl = {"type": "single_metric", "metric": "uploaded_count", "time_granularity": "month", "filters": []}
        sql = compile_dsl(dsl, self._make_access_filter())
        assert "scoped_videos" in sql
        assert "Upload_Date" in sql
        assert "$1" in sql  # granularity placeholder

    def test_formula_two_operands_sql_structure(self):
        from backend.kpi.compiler import compile_dsl
        dsl = {
            "type": "formula",
            "formula": "created_count / uploaded_count * 100",
            "operands": ["created_count", "uploaded_count"],
            "time_granularity": "month",
            "filters": [],
        }
        sql = compile_dsl(dsl, self._make_access_filter())
        assert "m_created_count" in sql
        assert "m_uploaded_count" in sql
        assert "FULL OUTER JOIN" in sql
        assert "COALESCE(m_created_count.value, 0)" in sql
        assert "COALESCE(m_uploaded_count.value, 0)" in sql
        assert "scoped_videos" in sql
        assert "scoped_assets" in sql

    def test_formula_no_sql_injection_passthrough(self):
        """Formula atoms are replaced — raw user strings never reach SQL."""
        from backend.kpi.compiler import compile_dsl
        dsl = {
            "type": "formula",
            "formula": "created_count / uploaded_count * 100",
            "operands": ["created_count", "uploaded_count"],
            "time_granularity": "month",
            "filters": [],
        }
        sql = compile_dsl(dsl, self._make_access_filter())
        # The raw formula string should NOT appear verbatim in the SQL
        # because atom names are replaced with CTE references
        assert "created_count / uploaded_count" not in sql

    def test_execution_params_structure(self):
        from backend.kpi.compiler import build_execution_params
        access_filter = {"join": "", "predicates": [], "params": ["some_client"], "next_index": 3}
        dsl = {"time_granularity": "week"}
        params = build_execution_params(dsl, access_filter)
        assert params[0] == "week"      # $1 = granularity
        assert params[1] == "some_client"  # $2 = auth param

    def test_unknown_dsl_type_raises(self):
        from backend.kpi.compiler import compile_dsl
        with pytest.raises(ValueError, match="Unknown DSL type"):
            compile_dsl({"type": "bad"}, self._make_access_filter())


# ── Insights tests ────────────────────────────────────────────────────────────

class TestComputeInsights:
    def _make_series(self, values: list[float]) -> list[dict]:
        return [{"period": f"2024-{i+1:02d}-01", "value": v} for i, v in enumerate(values)]

    def test_upward_trend_detected(self):
        from backend.kpi.service import compute_insights
        series = self._make_series([10, 11, 12, 30, 31, 32])
        result = compute_insights(series, "Test KPI")
        assert result["trend"] == "up"
        assert result["percentage_change"] > 0

    def test_downward_trend_detected(self):
        from backend.kpi.service import compute_insights
        series = self._make_series([50, 48, 46, 10, 9, 8])
        result = compute_insights(series, "Test KPI")
        assert result["trend"] == "down"
        assert result["percentage_change"] < 0

    def test_stable_trend(self):
        from backend.kpi.service import compute_insights
        series = self._make_series([20, 21, 20, 21, 20, 21])
        result = compute_insights(series, "Test KPI")
        assert result["trend"] == "stable"
        assert abs(result["percentage_change"]) <= 5

    def test_max_min_correctly_identified(self):
        from backend.kpi.service import compute_insights
        series = self._make_series([5, 100, 3, 50, 1])
        result = compute_insights(series, "Test KPI")
        assert result["max_point"]["value"] == 100.0
        assert result["min_point"]["value"] == 1.0

    def test_upward_trend_values(self):
        from backend.kpi.service import compute_insights
        # values: [10, 20, 30, 40, 50, 60]
        series = self._make_series([10, 20, 30, 40, 50, 60])
        result = compute_insights(series, "Rising KPI")
        assert result["max_point"]["value"] == 60.0
        assert result["min_point"]["value"] == 10.0

    def test_empty_series_returns_no_data(self):
        from backend.kpi.service import compute_insights
        result = compute_insights([], "Test KPI")
        assert result["trend"] == "no_data"
        assert result["summary"] == "No data available for this KPI."

    def test_single_point_series(self):
        from backend.kpi.service import compute_insights
        series = self._make_series([42.5])
        result = compute_insights(series, "Test KPI")
        assert result["max_point"]["value"] == 42.5
        assert result["min_point"]["value"] == 42.5

    def test_summary_text_contains_kpi_name(self):
        from backend.kpi.service import compute_insights
        series = self._make_series([10, 11, 12, 30, 31, 32])
        result = compute_insights(series, "My Metric")
        assert "My Metric" in result["summary"]
