"""Tests for the AgentOrchestrator (mocked dependencies)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.schemas import (
    AnalyticsResult,
    AgentError,
    InsightResponse,
    RoutingDecision,
    SQLResult,
)
from orchestrator.orchestrator import AgentOrchestrator


@pytest.fixture
def orchestrator():
    """Build an orchestrator with all dependencies mocked."""
    orch = AgentOrchestrator()

    # Mock schema loader
    orch.schema_loader = MagicMock()
    orch.schema_loader.get_compressed_schema.return_value = "clients(client_id, client_name)"
    orch.schema_loader.get_rich_schema.return_value = "TABLE clients (~100 rows)\n  - client_id\n  - client_name"
    orch.schema_loader.get_relevant_tables.return_value = ["clients"]
    orch.schema_loader.load_schema.return_value = {"clients": ["client_id", "client_name"]}

    # Mock router
    orch.router = AsyncMock()

    # Mock sql agent
    orch.sql_agent = AsyncMock()
    orch.sql_agent.generate_and_execute = AsyncMock(return_value=SQLResult(
        sql="SELECT COUNT(*) FROM clients LIMIT 500",
        columns=["count"],
        rows=[[42]],
        row_count=1,
        execution_ms=50,
        attempts=1,
    ))

    # Mock analytics agent
    orch.analytics_agent = AsyncMock()

    # Mock viz agent — use real VisualizationAgent for artifact generation
    from agents.visualization_agent import VisualizationAgent
    orch.viz_agent = VisualizationAgent()

    # Mock insight agent
    orch.insight_agent = AsyncMock()
    orch.insight_agent.generate = AsyncMock(return_value=InsightResponse(
        summary="There are 42 clients.",
        insights=["Total client count is 42"],
        has_charts=False,
        confidence="HIGH",
        query_used="SELECT COUNT(*) FROM clients LIMIT 500",
        execution_ms=100,
    ))

    # Mock memory
    orch.memory = AsyncMock()
    orch.memory.get_context = AsyncMock(return_value=[])

    return orch


@pytest.mark.asyncio
class TestOrchestrator:

    async def test_fast_path(self, orchestrator):
        """Fast path: simple lookup returns dict with expected keys."""
        orchestrator.router.route = AsyncMock(return_value=RoutingDecision(
            intent="AGGREGATION",
            complexity="LOW",
            requires_chart=False,
            forced_path="fast",
            reasoning="Simple count",
        ))

        result = await orchestrator.handle_query("How many clients?", "conv-1", "auto")
        # Simple single-value result uses deterministic insight (no LLM call)
        assert "42" in result["response"]
        assert result["path_used"] == "fast"
        assert isinstance(result["artifacts"], list)

    async def test_fast_path_with_chart(self, orchestrator):
        """Fast path with chart requested generates artifacts."""
        orchestrator.sql_agent.generate_and_execute = AsyncMock(return_value=SQLResult(
            sql="SELECT client_name, total FROM clients LIMIT 10",
            columns=["client_name", "total"],
            rows=[["Acme", 42], ["Beta", 30], ["Gamma", 20]],
            row_count=3,
            execution_ms=50,
            attempts=1,
        ))
        orchestrator.router.route = AsyncMock(return_value=RoutingDecision(
            intent="RANK",
            complexity="LOW",
            requires_chart=True,
            chart_types=["bar"],
            forced_path="fast",
            reasoning="Ranking query",
        ))
        orchestrator.insight_agent.generate = AsyncMock(return_value=InsightResponse(
            summary="Acme leads with 42.",
            insights=["Acme is top"],
            has_charts=True,
            confidence="HIGH",
            query_used="SELECT ...",
            execution_ms=200,
        ))

        result = await orchestrator.handle_query("Top clients", "conv-1", "fast")
        assert result["has_charts"] is True
        assert result["path_used"] == "fast"
        assert len(result["artifacts"]) > 0
        assert len(result["datasets"]) > 0

    async def test_deep_path_forced(self, orchestrator):
        """Deep path via mode='deep'."""
        orchestrator.router.route = AsyncMock(return_value=RoutingDecision(
            intent="TREND",
            complexity="HIGH",
            requires_chart=True,
            chart_types=["line"],
            forced_path="deep",
            reasoning="Trend analysis",
        ))
        orchestrator.analytics_agent.analyze = AsyncMock(return_value=AnalyticsResult(
            primary_result=SQLResult(
                sql="SELECT month, count FROM ...", columns=["month", "count"],
                rows=[["2024-01", 10], ["2024-02", 20]], row_count=2, execution_ms=200, attempts=1,
            ),
            datasets=[{
                "columns": ["month", "count"],
                "data": [{"month": "2024-01", "count": 10}, {"month": "2024-02", "count": 20}],
                "title": "Monthly Trend",
            }],
        ))
        orchestrator.insight_agent.generate = AsyncMock(return_value=InsightResponse(
            summary="Asset creation is trending up.",
            insights=["Growth observed"],
            has_charts=True,
            confidence="HIGH",
            execution_ms=500,
        ))

        result = await orchestrator.handle_query("Show asset trend", "conv-1", "deep")
        assert result["path_used"] == "deep"
        assert len(result["artifacts"]) > 0

    async def test_error_returns_friendly_message(self, orchestrator):
        """Pipeline error returns user-friendly response."""
        orchestrator.router.route = AsyncMock(return_value=RoutingDecision(
            intent="SIMPLE_LOOKUP", complexity="LOW",
            requires_chart=False, forced_path="fast", reasoning="test",
        ))
        orchestrator.sql_agent.generate_and_execute = AsyncMock(
            side_effect=AgentError("fail", "SQLAgent", user_message="Couldn't generate a valid query. Try rephrasing.")
        )

        result = await orchestrator.handle_query("Bad query", "conv-1", "auto")
        assert result["confidence"] == "LOW"
        assert "rephras" in result["response"].lower() or "wrong" in result["response"].lower()

    async def test_memory_save_called(self, orchestrator):
        """Memory.save is called after every query."""
        orchestrator.router.route = AsyncMock(return_value=RoutingDecision(
            intent="SIMPLE_LOOKUP", complexity="LOW",
            requires_chart=False, forced_path="fast", reasoning="test",
        ))

        await orchestrator.handle_query("Test query", "conv-1", "auto")
        orchestrator.memory.save.assert_called_once()
