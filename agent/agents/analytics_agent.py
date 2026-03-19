"""Analytics Agent — deep-path multi-step analysis with parallel SQL execution.

Uses Claude Sonnet for planning and pandas for computation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

import anthropic
import pandas as pd

from config.settings import get_settings
from models.schemas import (
    AgentError,
    AnalyticsPlan,
    AnalyticsResult,
    RoutingDecision,
    SQLResult,
)
from agents.sql_agent import SQLAgent
from tools.analysis_tools import (
    compute_growth_rate,
    compute_period_comparison,
    compute_trend,
    detect_anomalies,
    rows_to_dataframe,
)

logger = logging.getLogger("agent.analytics")

_PLANNER_SYSTEM_PROMPT = """\
You are an analytics planner for a BI system. Given a user question and database schema,
produce a JSON execution plan.

OUTPUT FORMAT (return ONLY this JSON):
{
  "steps": [
    {"step": 1, "description": "Fetch monthly asset counts", "sql_needed": true, "query_hint": "natural language hint for SQL agent"},
    {"step": 2, "description": "Compare with previous period", "sql_needed": true, "query_hint": "..."},
    {"step": 3, "description": "Identify trend direction", "sql_needed": false}
  ],
  "parallel_steps": [1, 2]
}

RULES:
- Maximum 5 steps
- Mark steps that can run in parallel in parallel_steps
- sql_needed = false for computation-only steps (trend detection, comparisons)
- query_hint should be a clear natural language question for each SQL step
- Return ONLY valid JSON, no markdown
"""


class AnalyticsAgent:
    """Deep-path analytics: plan → parallel SQL → pandas analysis → result."""

    def __init__(self, sql_agent: SQLAgent) -> None:
        self._sql_agent = sql_agent
        self._settings = get_settings()
        self._client = anthropic.Anthropic(api_key=self._settings.ANTHROPIC_API_KEY)

    async def analyze(
        self,
        query: str,
        routing: RoutingDecision,
        schema_context: str,
    ) -> AnalyticsResult:
        """Execute a multi-step analytical pipeline."""
        total_start = time.time()

        # 1. Generate execution plan
        plan = await self._generate_plan(query, schema_context)
        logger.info("Analytics plan: %d steps, parallel=%s", len(plan.steps), plan.parallel_steps)

        # 2. Execute SQL steps (parallel where possible)
        sql_results: dict[int, SQLResult] = {}
        parallel_nums = set(plan.parallel_steps)
        sequential_steps = [s for s in plan.steps if s.sql_needed and s.step not in parallel_nums]
        parallel_steps = [s for s in plan.steps if s.sql_needed and s.step in parallel_nums]

        # Parallel execution
        if parallel_steps and self._settings.ENABLE_PARALLEL_SQL:
            tasks = [
                self._execute_step(step.query_hint if hasattr(step, "query_hint") else step.description, routing, schema_context)
                for step in parallel_steps
            ]
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            for step, result in zip(parallel_steps, parallel_results):
                if isinstance(result, Exception):
                    logger.warning("Parallel step %d failed: %s", step.step, result)
                else:
                    sql_results[step.step] = result
        elif parallel_steps:
            for step in parallel_steps:
                try:
                    hint = step.query_hint if hasattr(step, "query_hint") else step.description
                    sql_results[step.step] = await self._execute_step(hint, routing, schema_context)
                except Exception as exc:
                    logger.warning("Step %d failed: %s", step.step, exc)

        # Sequential execution
        for step in sequential_steps:
            try:
                hint = step.query_hint if hasattr(step, "query_hint") else step.description
                sql_results[step.step] = await self._execute_step(hint, routing, schema_context)
            except Exception as exc:
                logger.warning("Step %d failed: %s", step.step, exc)

        if not sql_results:
            raise AgentError(
                message="All analytics SQL steps failed",
                agent="AnalyticsAgent",
                recoverable=False,
                user_message="Could not retrieve the data needed for this analysis.",
            )

        # 3. Pick primary result and build datasets
        primary_key = min(sql_results.keys())
        primary = sql_results[primary_key]

        datasets: list[dict] = []
        computed: dict[str, Any] = {}

        for step_num, sr in sorted(sql_results.items()):
            ds = {
                "step": step_num,
                "columns": sr.columns,
                "data": sr.rows_as_dicts(),
                "row_count": sr.row_count,
                "title": next(
                    (s.description for s in plan.steps if s.step == step_num),
                    f"Step {step_num}",
                ),
            }
            datasets.append(ds)

            # Run pandas analysis on each dataset
            if sr.columns and sr.rows:
                df = rows_to_dataframe(sr.columns, sr.rows)
                # Auto-detect date and value columns for trend analysis
                date_cols = [c for c in sr.columns if any(k in c.lower() for k in ("date", "month", "week", "year", "day"))]
                num_cols = [c for c in df.select_dtypes(include=["number"]).columns]
                if date_cols and num_cols:
                    trend = compute_trend(df, date_cols[0], num_cols[0])
                    computed[f"step_{step_num}_trend"] = trend

                # Anomaly detection
                if self._settings.ENABLE_ANOMALY_DETECTION and num_cols:
                    anomalies = detect_anomalies(df, num_cols[0])
                    if anomalies:
                        computed[f"step_{step_num}_anomalies"] = anomalies

        # Growth rate across primary dataset
        if primary.rows and len(primary.columns) >= 2:
            df = rows_to_dataframe(primary.columns, primary.rows)
            num_cols = [c for c in df.select_dtypes(include=["number"]).columns]
            if num_cols:
                vals = df[num_cols[0]].tolist()
                vals_float = [float(v) for v in vals if v is not None]
                if len(vals_float) >= 2:
                    computed["growth_rate"] = compute_growth_rate(vals_float)

        total_ms = int((time.time() - total_start) * 1000)
        logger.info("Analytics completed in %dms, %d datasets", total_ms, len(datasets))

        return AnalyticsResult(
            primary_result=primary,
            datasets=datasets,
            computed_metrics=computed,
            plan=plan,
        )

    async def _generate_plan(self, query: str, schema_context: str) -> AnalyticsPlan:
        """Use Sonnet to create an execution plan."""
        try:
            response = self._client.messages.create(
                model=self._settings.DEEP_MODEL,
                max_tokens=512,
                temperature=0,
                system=_PLANNER_SYSTEM_PROMPT + f"\n\nSCHEMA:\n{schema_context}",
                messages=[{"role": "user", "content": query}],
            )
            raw = response.content[0].text.strip()
            data = json.loads(raw)
            return AnalyticsPlan(**data)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)  # type: ignore[possibly-undefined]
            if match:
                data = json.loads(match.group())
                return AnalyticsPlan(**data)
            logger.warning("Planner returned non-JSON, using single-step fallback")
            return AnalyticsPlan(
                steps=[{"step": 1, "description": query, "sql_needed": True}],
                parallel_steps=[],
            )
        except Exception as exc:
            logger.error("Plan generation failed: %s", exc)
            return AnalyticsPlan(
                steps=[{"step": 1, "description": query, "sql_needed": True}],
                parallel_steps=[],
            )

    async def _execute_step(
        self, query_hint: str, routing: RoutingDecision, schema_context: str
    ) -> SQLResult:
        """Execute a single plan step via the SQL agent."""
        return await self._sql_agent.generate_and_execute(
            query=query_hint,
            relevant_tables=routing.relevant_tables,
            schema_context=schema_context,
            use_deep_model=True,
        )
