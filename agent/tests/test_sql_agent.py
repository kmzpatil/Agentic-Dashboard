"""Tests for the SQL Agent with mocked LLM and database."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.sql_agent import SQLAgent, FEW_SHOT_EXAMPLES
from models.schemas import AgentError, QueryResult
from tools.sql_validator import SQLValidator

SAMPLE_SCHEMA = {
    "clients": ["client_id", "client_name", "created_at"],
    "created_assets": ["asset_id", "client_id", "create_date", "output_type_id"],
    "billing_events": ["billing_id", "client_id", "amount", "billing_date"],
    "output_types": ["output_type_id", "output_type_name"],
    "channels": ["channel_id", "channel_name"],
}

SCHEMA_CONTEXT = "\n".join(f"{t}({', '.join(cols)})" for t, cols in SAMPLE_SCHEMA.items())


def _mock_llm_response(sql: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=sql)]
    msg.usage = MagicMock(output_tokens=30)
    return msg


@pytest.fixture
def validator():
    return SQLValidator(schema=SAMPLE_SCHEMA)


@pytest.fixture
def db_tool(validator):
    tool = MagicMock()
    tool.execute = AsyncMock(return_value=QueryResult(
        columns=["cnt"], rows=[[42]], row_count=1, execution_ms=10,
    ))
    return tool


@pytest.fixture
def sql_agent(db_tool, validator):
    with patch("agent.agents.sql_agent.anthropic.Anthropic") as mock_cls:
        agent = SQLAgent(db_tool, validator)
        agent._client = mock_cls.return_value
        yield agent


@pytest.mark.asyncio
class TestSQLAgent:

    async def test_few_shot_asset_count(self, sql_agent):
        """Valid SQL generation for 'How many assets were created this month?'"""
        sql = "SELECT COUNT(*) AS asset_count FROM created_assets WHERE DATE_TRUNC('month', create_date) = DATE_TRUNC('month', CURRENT_DATE) LIMIT 500"
        sql_agent._client.messages.create.return_value = _mock_llm_response(sql)

        result = await sql_agent.generate_and_execute(
            query="How many assets were created this month?",
            relevant_tables=["created_assets"],
            schema_context=SCHEMA_CONTEXT,
        )
        assert result.row_count == 1
        assert result.attempts == 1

    async def test_few_shot_top_clients(self, sql_agent):
        """Valid SQL for 'Top 10 clients by number of assets'."""
        sql = "SELECT c.client_name, COUNT(ca.asset_id) AS total_assets FROM clients c JOIN created_assets ca ON c.client_id = ca.client_id GROUP BY c.client_name ORDER BY total_assets DESC LIMIT 10"
        sql_agent._client.messages.create.return_value = _mock_llm_response(sql)

        result = await sql_agent.generate_and_execute(
            query="Top 10 clients by number of assets",
            relevant_tables=["clients", "created_assets"],
            schema_context=SCHEMA_CONTEXT,
        )
        assert result.attempts == 1

    async def test_rejects_drop_table(self, sql_agent):
        """SQLGlot rejects DROP TABLE — all retries fail."""
        sql_agent._client.messages.create.return_value = _mock_llm_response("DROP TABLE clients")

        with pytest.raises(AgentError, match="SQL generation failed"):
            await sql_agent.generate_and_execute(
                query="Drop the clients table",
                relevant_tables=["clients"],
                schema_context=SCHEMA_CONTEXT,
                max_retries=2,
            )

    async def test_rejects_delete(self, sql_agent):
        """SQLGlot rejects DELETE FROM."""
        sql_agent._client.messages.create.return_value = _mock_llm_response("DELETE FROM clients WHERE 1=1")

        with pytest.raises(AgentError):
            await sql_agent.generate_and_execute(
                query="Delete all clients",
                relevant_tables=["clients"],
                schema_context=SCHEMA_CONTEXT,
                max_retries=2,
            )

    async def test_rejects_select_star(self, sql_agent):
        """SQLGlot rejects SELECT *."""
        sql_agent._client.messages.create.return_value = _mock_llm_response("SELECT * FROM clients")

        with pytest.raises(AgentError):
            await sql_agent.generate_and_execute(
                query="Show all clients",
                relevant_tables=["clients"],
                schema_context=SCHEMA_CONTEXT,
                max_retries=2,
            )

    async def test_retry_self_repair(self, sql_agent):
        """Bad SQL on attempt 1, fixed on attempt 2."""
        bad_sql = "SELECT c.fake_col FROM clients c LIMIT 10"
        good_sql = "SELECT c.client_name FROM clients c LIMIT 10"

        sql_agent._client.messages.create.side_effect = [
            _mock_llm_response(bad_sql),
            _mock_llm_response(good_sql),
        ]

        result = await sql_agent.generate_and_execute(
            query="List client names",
            relevant_tables=["clients"],
            schema_context=SCHEMA_CONTEXT,
        )
        assert result.attempts == 2

    async def test_nonexistent_table_fails(self, sql_agent):
        """Reference to non-existent table raises AgentError."""
        sql_agent._client.messages.create.return_value = _mock_llm_response(
            "SELECT col FROM nonexistent_table LIMIT 10"
        )

        with pytest.raises(AgentError):
            await sql_agent.generate_and_execute(
                query="Query nonexistent table",
                relevant_tables=["nonexistent_table"],
                schema_context=SCHEMA_CONTEXT,
                max_retries=2,
            )

    async def test_limit_auto_injection(self, sql_agent):
        """Query without LIMIT gets one auto-injected."""
        sql = "SELECT client_name FROM clients"
        sql_agent._client.messages.create.return_value = _mock_llm_response(sql)

        result = await sql_agent.generate_and_execute(
            query="List clients",
            relevant_tables=["clients"],
            schema_context=SCHEMA_CONTEXT,
        )
        assert "LIMIT" in result.sql.upper()
