"""Orchestrator — coordinates the multi-agent pipeline (fast and deep paths).

This is the single entry point called by the API server. It owns the lifecycle
of all agents and shared resources (DB pool, schema cache, etc.).

The orchestrator produces a response dict that maps directly to the frontend
contract expected by TalkToDataModule.jsx / ArtifactCanvas.jsx.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Literal, Optional

import asyncpg

from agents.analytics_agent import AnalyticsAgent
from agents.insight_agent import InsightAgent
from agents.router_agent import RouterAgent
from agents.sql_agent import SQLAgent, FEW_SHOT_EXAMPLES
from agents.visualization_agent import VisualizationAgent
from config.settings import get_settings
from memory import ConversationMemory
from models.schemas import AgentError, InsightResponse, RoutingDecision
from tools.database_tool import DatabaseTool
from tools.schema_loader import SchemaLoader
from tools.sql_validator import SQLValidator

logger = logging.getLogger("agent.orchestrator")


class AgentOrchestrator:
    """Coordinates router → sql/analytics → viz → insight pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._pool: Optional[asyncpg.Pool] = None

        # Agents (initialised in .init())
        self.schema_loader = SchemaLoader()
        self.validator = SQLValidator()
        self.router = RouterAgent()
        self.viz_agent = VisualizationAgent()
        self.insight_agent = InsightAgent()
        self.memory = ConversationMemory()

        # These depend on pool — set in init()
        self.db_tool: Optional[DatabaseTool] = None
        self.sql_agent: Optional[SQLAgent] = None
        self.analytics_agent: Optional[AnalyticsAgent] = None

        self._schema_refresh_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def init(self) -> None:
        """Initialise DB pool, load schema, wire agents. Call once at startup."""
        db_url = self._settings.get_database_url()
        self._pool = await asyncpg.create_pool(
            dsn=db_url,
            min_size=self._settings.DB_POOL_MIN,
            max_size=self._settings.DB_POOL_MAX,
        )
        logger.info("DB pool created (min=%d, max=%d)", self._settings.DB_POOL_MIN, self._settings.DB_POOL_MAX)

        # Schema
        await self.schema_loader.init(self._pool)
        schema = self.schema_loader.load_schema()
        self.validator.update_schema(schema)

        # Wire agents
        self.db_tool = DatabaseTool(self._pool, self.validator)
        self.sql_agent = SQLAgent(self.db_tool, self.validator)
        self.analytics_agent = AnalyticsAgent(self.sql_agent)

        # Background schema refresh
        self._schema_refresh_task = asyncio.create_task(self._periodic_schema_refresh())
        logger.info("Orchestrator initialised successfully")

    async def shutdown(self) -> None:
        """Clean up resources."""
        if self._schema_refresh_task:
            self._schema_refresh_task.cancel()
        if self._pool:
            await self._pool.close()
        logger.info("Orchestrator shut down")

    # ── Main entry point ──────────────────────────────────────────────────────

    async def handle_query(
        self,
        query: str,
        conversation_id: str,
        mode: Literal["fast", "deep", "auto"] = "auto",
    ) -> dict[str, Any]:
        """Process a user query and return a dict compatible with the frontend.

        The returned dict has these keys (matching ChatResponse / TalkToDataModule):
          response     — markdown summary text
          artifacts    — list of artifact dicts for ArtifactCanvas
          datasets     — list of dataset dicts for ArtifactCanvas
          insights     — list of bullet-point strings
          has_charts   — bool (whether the chart panel should open)
          path_used    — "fast" | "deep"
          confidence   — "HIGH" | "MEDIUM" | "LOW"
          query_used   — the SQL that was executed
          execution_ms — total pipeline time
        """
        assert self.sql_agent is not None, "Orchestrator not initialised — call init() first"
        total_start = time.time()

        # 1. Run conversation context + routing + table relevance in parallel
        schema_summary = self.schema_loader.get_compressed_schema()

        async def _route():
            history = await self.memory.get_context(conversation_id, last_n=5)
            ctx = query
            if history:
                hist = "\n".join(f"User: {h['query']}\nAnswer: {h['summary']}" for h in history)
                ctx = f"CONVERSATION HISTORY:\n{hist}\n\nCurrent question: {query}"
            return await self.router.route(ctx, mode, schema_summary)

        # schema_loader.get_relevant_tables is sync/fast — run alongside router LLM call
        try:
            routing, keyword_tables = await asyncio.gather(
                _route(),
                asyncio.to_thread(self.schema_loader.get_relevant_tables, query),
            )
        except Exception as exc:
            logger.error("Router/table lookup failed: %s", exc)
            routing = RoutingDecision(
                intent="SIMPLE_LOOKUP",
                complexity="LOW",
                requires_chart=False,
                forced_path="fast" if mode != "deep" else "deep",
                reasoning="Router fallback",
            )
            keyword_tables = self.schema_loader.get_relevant_tables(query)

        logger.info(
            "Routed: intent=%s complexity=%s path=%s chart=%s",
            routing.intent, routing.complexity, routing.forced_path, routing.requires_chart,
        )

        # Merge schema-loader relevant tables with router's
        relevant = list(dict.fromkeys(routing.relevant_tables + keyword_tables))

        try:
            if routing.forced_path == "fast":
                result = await self._fast_path(query, routing, relevant, schema_summary)
            else:
                result = await self._deep_path(query, routing, relevant)
        except AgentError as exc:
            logger.error("[%s] %s", exc.agent, exc)
            result = {
                "response": exc.user_message,
                "artifacts": [],
                "datasets": [],
                "insights": [],
                "has_charts": False,
                "path_used": routing.forced_path,
                "confidence": "LOW",
                "query_used": "",
                "execution_ms": 0,
            }
        except Exception as exc:
            logger.error("Unhandled error in pipeline: %s", exc, exc_info=True)
            result = {
                "response": "Something went wrong processing your query. Please try again.",
                "artifacts": [],
                "datasets": [],
                "insights": [],
                "has_charts": False,
                "path_used": routing.forced_path,
                "confidence": "LOW",
                "query_used": "",
                "execution_ms": 0,
            }

        total_ms = int((time.time() - total_start) * 1000)
        result["execution_ms"] = total_ms

        # Save to memory
        await self.memory.save(conversation_id, query, type("R", (), {"summary": result.get("response", "")})())

        logger.info("Query completed in %dms via %s path", total_ms, result.get("path_used"))
        return result

    # ── Fast path ─────────────────────────────────────────────────────────────

    async def _fast_path(
        self,
        query: str,
        routing: RoutingDecision,
        relevant_tables: list[str],
        schema_context: str,
    ) -> dict[str, Any]:
        """Quick single-SQL path (<2s target).

        Latency optimisations:
        - For simple results (≤5 rows), generate a deterministic summary
          instead of calling the LLM insight agent (saves ~500-1000ms).
        - Artifact generation is pure Python (no LLM), runs instantly.
        """
        sql_result = await self.sql_agent.generate_and_execute(
            query=query,
            relevant_tables=relevant_tables,
            schema_context=schema_context,
            few_shot_examples=FEW_SHOT_EXAMPLES,
        )

        # Build artifacts (pure Python, <1ms)
        artifacts: list[dict] = []
        datasets: list[dict] = []

        if sql_result.row_count > 0:
            data_dicts = sql_result.rows_as_dicts()
            x_col = sql_result.columns[0] if sql_result.columns else None
            y_col = sql_result.columns[-1] if len(sql_result.columns) > 1 else None

            # Pass ALL user-requested chart types (or None to auto-detect)
            req_types = routing.chart_types if routing.requires_chart else None

            arts, dss = self.viz_agent.generate_artifacts(
                data=data_dicts,
                requested_types=req_types,
                title=query[:60],
                x_col=x_col,
                y_col=y_col,
            )
            artifacts = arts
            datasets = dss

        has_artifacts = len(artifacts) > 0

        # For simple results, skip the LLM insight call to save latency
        is_simple = (
            routing.complexity == "LOW"
            and sql_result.row_count <= 5
            and routing.intent in ("SIMPLE_LOOKUP", "AGGREGATION", "FILTER")
        )

        if is_simple and sql_result.row_count > 0:
            summary, insights = self._build_fast_insight(query, sql_result)
            return {
                "response": summary,
                "artifacts": artifacts,
                "datasets": datasets,
                "insights": insights,
                "has_charts": has_artifacts,
                "path_used": "fast",
                "confidence": "HIGH",
                "query_used": sql_result.sql,
                "execution_ms": sql_result.execution_ms,
            }

        # Otherwise use the LLM insight agent for richer narratives
        insight = await self.insight_agent.generate(
            query, sql_result, None, has_artifacts=has_artifacts,
        )

        return {
            "response": insight.summary,
            "artifacts": artifacts,
            "datasets": datasets,
            "insights": insight.insights,
            "has_charts": has_artifacts,
            "path_used": "fast",
            "confidence": insight.confidence,
            "query_used": sql_result.sql,
            "execution_ms": sql_result.execution_ms,
        }

    @staticmethod
    def _build_fast_insight(_query: str, sql_result) -> tuple[str, list[str]]:
        """Deterministic insight for simple results — no LLM call needed."""
        data = sql_result.rows_as_dicts()
        cols = sql_result.columns

        if sql_result.row_count == 1 and len(cols) == 1:
            # Single scalar: "COUNT(*) → 42"
            val = data[0][cols[0]]
            return f"**{val:,}**" if isinstance(val, (int, float)) else str(val), []

        if sql_result.row_count == 1:
            # Single row, multiple columns → summarise as key-value pairs
            row = data[0]
            parts = [f"**{k.replace('_', ' ').title()}**: {v:,}" if isinstance(v, (int, float)) else f"**{k.replace('_', ' ').title()}**: {v}" for k, v in row.items()]
            return " · ".join(parts), []

        # Multiple rows → first column as label, last numeric as value
        insights = []
        for row in data[:5]:
            vals = list(row.values())
            label = str(vals[0])
            value = vals[-1]
            if isinstance(value, (int, float)):
                insights.append(f"{label}: **{value:,}**")
            else:
                insights.append(f"{label}: {value}")

        summary = f"Found {sql_result.row_count} results."
        if sql_result.row_count <= 5:
            summary = f"Here are the {sql_result.row_count} results:"

        return summary, insights

    # ── Deep path ─────────────────────────────────────────────────────────────

    async def _deep_path(
        self,
        query: str,
        routing: RoutingDecision,
        relevant_tables: list[str],
    ) -> dict[str, Any]:
        """Multi-step analytical path (10-40s)."""
        schema_ctx = self.schema_loader.get_rich_schema()

        analytics = await self.analytics_agent.analyze(query, routing, schema_ctx)

        # Build artifacts from all datasets
        artifacts: list[dict] = []
        datasets_out: list[dict] = []

        if routing.requires_chart and analytics.datasets:
            arts, dss = self.viz_agent.generate_multi_artifacts(
                analytics.datasets, routing,
            )
            artifacts = arts
            datasets_out = dss
        elif analytics.datasets:
            # Even without chart request, generate table artifacts
            for ds_info in analytics.datasets:
                data = ds_info.get("data", [])
                if data:
                    from agents.visualization_agent import build_table_artifact
                    art, ds = build_table_artifact(data, ds_info.get("title", "Results"))
                    artifacts.append(art)
                    datasets_out.append(ds)

        has_artifacts = len(artifacts) > 0

        insight = await self.insight_agent.generate(
            query, analytics.primary_result, analytics, has_artifacts=has_artifacts,
        )

        return {
            "response": insight.summary,
            "artifacts": artifacts,
            "datasets": datasets_out,
            "insights": insight.insights,
            "has_charts": has_artifacts,
            "path_used": "deep",
            "confidence": insight.confidence,
            "query_used": analytics.primary_result.sql,
            "execution_ms": analytics.primary_result.execution_ms,
        }

    # ── Background tasks ──────────────────────────────────────────────────────

    async def _periodic_schema_refresh(self) -> None:
        """Refresh schema cache periodically."""
        interval = self._settings.SCHEMA_REFRESH_INTERVAL_SECONDS
        while True:
            await asyncio.sleep(interval)
            try:
                await self.schema_loader.refresh()
                schema = self.schema_loader.load_schema()
                self.validator.update_schema(schema)
                logger.info("Schema cache refreshed")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Schema refresh failed: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_ORCHESTRATOR: Optional[AgentOrchestrator] = None


async def get_orchestrator() -> AgentOrchestrator:
    """Return the singleton orchestrator, initialising on first call."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = AgentOrchestrator()
        await _ORCHESTRATOR.init()
    return _ORCHESTRATOR


async def shutdown_orchestrator() -> None:
    """Shut down the singleton orchestrator."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is not None:
        await _ORCHESTRATOR.shutdown()
        _ORCHESTRATOR = None
