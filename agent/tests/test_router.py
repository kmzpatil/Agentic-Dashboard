"""Tests for the RouterAgent.

These tests mock the Anthropic API to validate routing logic
without requiring a live LLM connection.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.router_agent import RouterAgent


def _mock_anthropic_response(content: str):
    """Build a mock Anthropic messages.create response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    msg.usage = MagicMock(output_tokens=50)
    return msg


@pytest.fixture
def router():
    with patch("agent.agents.router_agent.anthropic.Anthropic") as mock_cls:
        r = RouterAgent()
        r._client = mock_cls.return_value
        yield r


SCHEMA_SUMMARY = "clients(client_id, client_name)\ncreated_assets(asset_id, client_id, create_date)"


@pytest.mark.asyncio
class TestRouterAgent:

    async def test_simple_lookup_fast(self, router):
        """'Total assets today' → FAST + AGGREGATION + requires_chart=false"""
        resp_json = json.dumps({
            "intent": "AGGREGATION",
            "complexity": "LOW",
            "requires_chart": False,
            "chart_types": [],
            "relevant_tables": ["created_assets"],
            "time_range_detected": True,
            "reasoning": "Simple count with date filter",
        })
        router._client.messages.create.return_value = _mock_anthropic_response(resp_json)

        decision = await router.route("Total assets today", "auto", SCHEMA_SUMMARY)
        assert decision.forced_path == "fast"
        assert decision.intent == "AGGREGATION"
        assert decision.requires_chart is False

    async def test_trend_deep(self, router):
        """'Show trend over 12 months' → DEEP + TREND + requires_chart=true + line"""
        resp_json = json.dumps({
            "intent": "TREND",
            "complexity": "HIGH",
            "requires_chart": True,
            "chart_types": ["line"],
            "relevant_tables": ["created_assets"],
            "time_range_detected": True,
            "reasoning": "Time series trend analysis",
        })
        router._client.messages.create.return_value = _mock_anthropic_response(resp_json)

        decision = await router.route("Show trend over 12 months", "auto", SCHEMA_SUMMARY)
        assert decision.forced_path == "deep"
        assert decision.intent == "TREND"
        assert decision.requires_chart is True
        assert "line" in decision.chart_types

    async def test_forced_fast_mode(self, router):
        """mode='fast' forces fast path even for HIGH complexity."""
        resp_json = json.dumps({
            "intent": "ANALYTICS",
            "complexity": "HIGH",
            "requires_chart": True,
            "chart_types": ["bar"],
            "relevant_tables": ["clients", "created_assets"],
            "time_range_detected": False,
            "reasoning": "Complex analytics query",
        })
        router._client.messages.create.return_value = _mock_anthropic_response(resp_json)

        decision = await router.route("Complex analysis", "fast", SCHEMA_SUMMARY)
        assert decision.forced_path == "fast"

    async def test_forced_deep_mode(self, router):
        """mode='deep' forces deep path even for LOW complexity."""
        resp_json = json.dumps({
            "intent": "SIMPLE_LOOKUP",
            "complexity": "LOW",
            "requires_chart": False,
            "chart_types": [],
            "relevant_tables": ["clients"],
            "time_range_detected": False,
            "reasoning": "Simple lookup",
        })
        router._client.messages.create.return_value = _mock_anthropic_response(resp_json)

        decision = await router.route("How many clients?", "deep", SCHEMA_SUMMARY)
        assert decision.forced_path == "deep"

    async def test_multiple_chart_types(self, router):
        """Query requesting multiple charts."""
        resp_json = json.dumps({
            "intent": "ANALYTICS",
            "complexity": "HIGH",
            "requires_chart": True,
            "chart_types": ["bar", "line"],
            "relevant_tables": ["clients", "created_assets"],
            "time_range_detected": True,
            "reasoning": "Multi-chart analytics",
        })
        router._client.messages.create.return_value = _mock_anthropic_response(resp_json)

        decision = await router.route(
            "Show me both a bar chart of top clients and a line chart of monthly growth",
            "auto",
            SCHEMA_SUMMARY,
        )
        assert decision.requires_chart is True
        assert len(decision.chart_types) == 2
        assert "bar" in decision.chart_types
        assert "line" in decision.chart_types

    async def test_fallback_on_llm_failure(self, router):
        """Router returns safe defaults when LLM fails."""
        router._client.messages.create.side_effect = Exception("API error")

        decision = await router.route("Some query", "auto", SCHEMA_SUMMARY)
        assert decision.forced_path == "fast"
        assert decision.intent == "SIMPLE_LOOKUP"
