"""Insight Agent — generates human-readable narrative from query results.

Uses Claude Sonnet with temperature=0.3 for natural language output.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

import anthropic

from config.settings import get_settings
from models.schemas import (
    AnalyticsResult,
    InsightResponse,
    SQLResult,
)

logger = logging.getLogger("agent.insight")

_INSIGHT_SYSTEM_PROMPT = """\
You are a data analyst. Given a user question and SQL result data, generate insights.

OUTPUT FORMAT (return ONLY this JSON):
{
  "summary": "One sentence direct answer with a specific number if possible",
  "insights": [
    "Key finding 1 with specific numbers",
    "Key finding 2 with comparison",
    "Key finding 3 with trend direction"
  ],
  "confidence": "HIGH"
}

RULES:
- Do NOT invent numbers — only use values present in the provided data
- Be concise — each insight must be under 20 words
- If data is empty, say "No data found for this period"
- confidence: HIGH if data fully answers the question, MEDIUM if partial, LOW if uncertain
- summary must directly answer the question asked
- Return JSON only, no markdown
"""


class InsightAgent:
    """Generate narrative insights from structured data."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = anthropic.Anthropic(api_key=self._settings.ANTHROPIC_API_KEY)

    async def generate(
        self,
        query: str,
        sql_result: SQLResult,
        analytics_result: Optional[AnalyticsResult] = None,
        has_artifacts: bool = False,
    ) -> InsightResponse:
        """Produce an InsightResponse from query results."""
        start = time.time()

        # Handle empty results
        if sql_result.row_count == 0:
            return InsightResponse(
                summary="No data found matching your query for this period.",
                insights=[],
                has_charts=False,
                confidence="LOW",
                query_used=sql_result.sql,
                execution_ms=sql_result.execution_ms,
            )

        # Build context for LLM
        data_preview = json.dumps(sql_result.rows_as_dicts()[:30], default=str)
        analytics_context = ""
        if analytics_result and analytics_result.computed_metrics:
            analytics_context = f"\nComputed metrics: {json.dumps(analytics_result.computed_metrics, default=str)}"

        user_prompt = (
            f"Question: {query}\n\n"
            f"SQL used: {sql_result.sql}\n\n"
            f"Columns: {sql_result.columns}\n"
            f"Row count: {sql_result.row_count}\n"
            f"Data (up to 30 rows): {data_preview}"
            f"{analytics_context}"
        )

        try:
            response = self._client.messages.create(
                model=self._settings.DEEP_MODEL,
                max_tokens=self._settings.INSIGHT_MAX_TOKENS,
                temperature=0.3,
                system=_INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text.strip()
            elapsed = int((time.time() - start) * 1000)
            logger.info("Insight LLM responded in %dms, tokens=%d", elapsed, response.usage.output_tokens)
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)  # type: ignore[possibly-undefined]
            if match:
                data = json.loads(match.group())
            else:
                logger.warning("Insight agent returned non-JSON: %s", raw[:200])
                data = {
                    "summary": f"Found {sql_result.row_count} results for your query.",
                    "insights": [],
                    "confidence": "MEDIUM",
                }
        except Exception as exc:
            logger.error("Insight LLM failed: %s", exc)
            data = {
                "summary": f"Found {sql_result.row_count} results for your query.",
                "insights": [],
                "confidence": "MEDIUM",
            }

        total_ms = int((time.time() - start) * 1000)

        # Build data table
        data_table = None
        if sql_result.columns and sql_result.rows:
            data_table = {
                "columns": sql_result.columns,
                "rows": sql_result.rows[:100],  # Cap for frontend
            }

        return InsightResponse(
            summary=data.get("summary", ""),
            insights=data.get("insights", []),
            data_table=data_table,
            has_charts=has_artifacts,
            confidence=data.get("confidence", "HIGH"),
            query_used=sql_result.sql,
            execution_ms=sql_result.execution_ms + total_ms,
            warnings=[],
        )
