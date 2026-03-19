"""Router Agent — classifies intent, complexity, and selects fast vs deep path.

Uses Claude Haiku for sub-200ms JSON classification.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Literal

import anthropic

from config.settings import get_settings
from models.schemas import AgentError, RoutingDecision

logger = logging.getLogger("agent.router")

_ROUTER_SYSTEM_PROMPT = """\
You are a query router for a BI analytics system.
Classify the user query and output ONLY valid JSON matching this schema:

{
  "intent": "<SIMPLE_LOOKUP|AGGREGATION|FILTER|RANK|TREND|ANALYTICS|ANOMALY|FORECAST|SCHEMA_QUERY>",
  "complexity": "<LOW|MEDIUM|HIGH>",
  "requires_chart": <true|false>,
  "chart_types": ["<line|bar|stacked_bar|pie|scatter|area>"],
  "relevant_tables": ["<table_name>"],
  "time_range_detected": <true|false>,
  "reasoning": "<one line>"
}

AVAILABLE TABLES:
{schema_summary}

RULES:
- Do not hallucinate tables. Use ONLY tables from the list above.
- SIMPLE_LOOKUP = single value / list fetch. AGGREGATION = COUNT/SUM/AVG.
- FILTER = WHERE clause needed. RANK = ORDER BY + LIMIT.
- TREND = time-series. ANALYTICS = multi-step analysis. ANOMALY = outlier detection.
- requires_chart = true ONLY for trends, comparisons, distributions.
- chart_types: line for trends, bar for rankings/comparisons, pie for proportions.
- complexity: LOW = single table simple query. MEDIUM = joins or grouping. HIGH = multi-step, sub-queries, time comparisons.
- Response must be pure JSON. No markdown, no explanation.
"""


class RouterAgent:
    """Classify query intent and route to fast or deep path."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = anthropic.Anthropic(api_key=self._settings.ANTHROPIC_API_KEY)

    async def route(
        self,
        query: str,
        mode: Literal["fast", "deep", "auto"],
        schema_summary: str = "",
    ) -> RoutingDecision:
        """Produce a RoutingDecision for the incoming query."""
        start = time.time()

        # Build system prompt with available tables
        system = _ROUTER_SYSTEM_PROMPT.replace("{schema_summary}", schema_summary)

        try:
            response = self._client.messages.create(
                model=self._settings.FAST_MODEL,
                max_tokens=self._settings.ROUTER_MAX_TOKENS,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": query}],
            )
            raw = response.content[0].text.strip()
            elapsed = int((time.time() - start) * 1000)
            logger.info("Router responded in %dms | tokens=%d", elapsed, response.usage.output_tokens)
        except Exception as exc:
            logger.error("Router LLM call failed: %s", exc)
            # Fallback: default to fast path simple lookup
            return RoutingDecision(
                intent="SIMPLE_LOOKUP",
                complexity="LOW",
                requires_chart=False,
                chart_types=[],
                relevant_tables=[],
                time_range_detected=False,
                forced_path="fast" if mode != "deep" else "deep",
                reasoning="Fallback — router LLM unavailable",
            )

        # Parse JSON response
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown fences
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                logger.warning("Router returned non-JSON: %s", raw[:200])
                return RoutingDecision(
                    intent="SIMPLE_LOOKUP",
                    complexity="LOW",
                    requires_chart=False,
                    forced_path="fast" if mode != "deep" else "deep",
                    reasoning="Fallback — could not parse router output",
                )

        # Determine forced path
        intent = data.get("intent", "SIMPLE_LOOKUP")
        complexity = data.get("complexity", "LOW")

        if mode == "fast":
            forced = "fast"
        elif mode == "deep":
            forced = "deep"
        else:
            # Auto: deep for high complexity or analytical intents
            deep_intents = {"TREND", "ANALYTICS", "ANOMALY", "FORECAST"}
            if complexity == "HIGH" or intent in deep_intents:
                forced = "deep"
            else:
                forced = "fast"

        return RoutingDecision(
            intent=intent,
            complexity=complexity,
            requires_chart=data.get("requires_chart", False),
            chart_types=data.get("chart_types", []),
            relevant_tables=data.get("relevant_tables", []),
            time_range_detected=data.get("time_range_detected", False),
            forced_path=forced,
            reasoning=data.get("reasoning", ""),
        )
