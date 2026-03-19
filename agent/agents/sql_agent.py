"""SQL Agent — generates, validates, and executes SQL with self-repair retries.

Uses Claude Haiku (fast path) or Sonnet (deep path) with temperature=0.
"""

from __future__ import annotations

import logging
import time

import anthropic

from config.settings import get_settings
from models.schemas import AgentError, SQLResult
from tools.database_tool import DatabaseTool
from tools.sql_validator import SQLValidator

logger = logging.getLogger("agent.sql_agent")

FEW_SHOT_EXAMPLES = [
    {
        "question": "How many assets were created this month?",
        "sql": "SELECT COUNT(*) AS asset_count FROM created_assets WHERE DATE_TRUNC('month', create_date) = DATE_TRUNC('month', CURRENT_DATE)",
    },
    {
        "question": "Top 10 clients by number of assets",
        "sql": "SELECT c.client_name, COUNT(ca.asset_id) AS total_assets FROM clients c JOIN created_assets ca ON c.client_id = ca.client_id GROUP BY c.client_name ORDER BY total_assets DESC LIMIT 10",
    },
    {
        "question": "Revenue trend by month",
        "sql": "SELECT DATE_TRUNC('month', billing_date) AS month, SUM(amount) AS total_revenue FROM billing_events GROUP BY month ORDER BY month ASC LIMIT 24",
    },
    {
        "question": "Asset creation trend last 6 months",
        "sql": "SELECT DATE_TRUNC('month', create_date) AS month, COUNT(*) AS count FROM created_assets WHERE create_date >= CURRENT_DATE - INTERVAL '6 months' GROUP BY month ORDER BY month ASC",
    },
    {
        "question": "Which output types are most used?",
        "sql": "SELECT ot.output_type_name, COUNT(ca.asset_id) AS count FROM output_types ot JOIN created_assets ca ON ot.output_type_id = ca.output_type_id GROUP BY ot.output_type_name ORDER BY count DESC LIMIT 20",
    },
]

_SQL_SYSTEM_PROMPT = """\
You are a PostgreSQL expert. Generate a single SQL SELECT query.

RULES (NEVER VIOLATE):
1. Only use tables that exist in the schema below
2. Only use columns that exist in those tables
3. Always include a LIMIT clause (max 500)
4. Never use SELECT *
5. Use explicit table aliases
6. Handle NULL values with COALESCE where appropriate
7. For date operations, use PostgreSQL date functions only
8. Never generate DML statements (INSERT/UPDATE/DELETE/DROP)
9. Return ONLY the SQL query, no explanation, no markdown fences

SCHEMA:
{schema}

FEW-SHOT EXAMPLES:
{examples}
"""

_REPAIR_PROMPT = """\
The previous SQL query failed validation.

PREVIOUS SQL:
{sql}

ERROR:
{error}

SCHEMA:
{schema}

Fix the SQL query. Return ONLY the corrected SQL, no explanation.
"""


def _format_examples(examples: list[dict]) -> str:
    lines = []
    for ex in examples:
        lines.append(f"Q: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
        lines.append("")
    return "\n".join(lines)


class SQLAgent:
    """Generate and execute SQL with retry-based self-repair."""

    def __init__(self, db_tool: DatabaseTool, validator: SQLValidator) -> None:
        self._db = db_tool
        self._validator = validator
        self._settings = get_settings()
        self._client = anthropic.Anthropic(api_key=self._settings.ANTHROPIC_API_KEY)

    async def generate_and_execute(
        self,
        query: str,
        relevant_tables: list[str],
        schema_context: str,
        few_shot_examples: list[dict] | None = None,
        max_retries: int | None = None,
        use_deep_model: bool = False,
    ) -> SQLResult:
        """Generate SQL from natural language, validate, execute with retries."""
        retries = max_retries or self._settings.SQL_MAX_RETRIES
        examples = few_shot_examples or FEW_SHOT_EXAMPLES
        model = self._settings.DEEP_MODEL if use_deep_model else self._settings.FAST_MODEL

        system = _SQL_SYSTEM_PROMPT.replace("{schema}", schema_context).replace(
            "{examples}", _format_examples(examples)
        )

        total_start = time.time()
        last_error: str | None = None
        last_sql: str | None = None

        for attempt in range(1, retries + 1):
            # Build prompt
            if attempt == 1:
                user_msg = f"Question: {query}\nSQL:"
            else:
                user_msg = _REPAIR_PROMPT.replace("{sql}", last_sql or "").replace(
                    "{error}", last_error or ""
                ).replace("{schema}", schema_context)

            try:
                llm_start = time.time()
                response = self._client.messages.create(
                    model=model,
                    max_tokens=512,
                    temperature=0,
                    system=system,
                    messages=[{"role": "user", "content": user_msg}],
                )
                sql = response.content[0].text.strip()
                llm_ms = int((time.time() - llm_start) * 1000)
                logger.info(
                    "SQL gen attempt=%d model=%s llm_ms=%d tokens=%d",
                    attempt, model, llm_ms, response.usage.output_tokens,
                )
            except Exception as exc:
                logger.error("LLM call failed attempt=%d: %s", attempt, exc)
                last_error = str(exc)
                continue

            # Strip markdown fences if present
            sql = sql.strip("`").strip()
            if sql.lower().startswith("sql"):
                sql = sql[3:].strip()

            # Validate
            validation = self._validator.validate(sql)
            if validation.valid:
                exec_sql = validation.fixed_sql or sql
                try:
                    qr = await self._db.execute(exec_sql)
                    total_ms = int((time.time() - total_start) * 1000)
                    return SQLResult(
                        sql=exec_sql,
                        columns=qr.columns,
                        rows=qr.rows,
                        row_count=qr.row_count,
                        execution_ms=total_ms,
                        attempts=attempt,
                    )
                except AgentError as exc:
                    last_error = str(exc)
                    last_sql = exec_sql
                    logger.warning("DB execution failed attempt=%d: %s", attempt, exc)
                    continue
            else:
                last_error = validation.error
                last_sql = sql
                logger.warning(
                    "Validation failed attempt=%d: %s | sql=%s", attempt, validation.error, sql[:200]
                )
                continue

        # All retries exhausted
        raise AgentError(
            message=f"SQL generation failed after {retries} attempts: {last_error}",
            agent="SQLAgent",
            recoverable=False,
            user_message="Couldn't generate a valid query. Try rephrasing your question.",
        )
