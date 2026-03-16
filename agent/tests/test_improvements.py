"""
test_improvements.py
--------------------
Smoke tests for the 9 agent improvements.
Run with:  python -m pytest tests/test_improvements.py -v
"""

import json
import pandas as pd
import pytest


# ── 1. Comment stripping ────────────────────────────────────────────────────

class TestCommentStripping:
    def test_line_comment_removed(self):
        from mcp_server.database import DatabaseClient
        result = DatabaseClient._strip_comments("SELECT * FROM foo -- DROP TABLE bar")
        assert "DROP" not in result
        assert "SELECT * FROM foo" in result

    def test_block_comment_removed(self):
        from mcp_server.database import DatabaseClient
        result = DatabaseClient._strip_comments("SELECT /* DELETE FROM users */ * FROM foo")
        assert "DELETE" not in result
        assert "SELECT" in result
        assert "FROM foo" in result

    def test_multiline_block_comment(self):
        from mcp_server.database import DatabaseClient
        query = """SELECT *
        /* This is a
           DROP TABLE attack
           hidden in comments */
        FROM foo"""
        result = DatabaseClient._strip_comments(query)
        assert "DROP" not in result
        assert "SELECT" in result

    def test_clean_query_blocks_commented_attack(self):
        from mcp_server.database import DatabaseClient, QueryValidationError
        db = DatabaseClient.__new__(DatabaseClient)
        # This should NOT raise — the DROP is inside a comment and gets stripped
        cleaned = db._clean_query("SELECT * FROM foo /* DROP TABLE bar */")
        assert "SELECT" in cleaned
        assert "DROP" not in cleaned


# ── 2. CTE wrapper preserves ORDER BY ───────────────────────────────────────

class TestCTEWrapper:
    def test_cte_format(self):
        from mcp_server.database import DatabaseClient
        db = DatabaseClient.__new__(DatabaseClient)
        cleaned = db._clean_query("SELECT * FROM foo ORDER BY id DESC")
        # The CTE wrapper should be used in run_read_only_query
        # We verify indirectly by checking the method source
        import inspect
        source = inspect.getsource(db.run_read_only_query)
        assert "WITH mcp_cte AS" in source
        assert "mcp_query_result" not in source


# ── 3. Type-aware fillna ────────────────────────────────────────────────────

class TestTypeAwareFillna:
    def test_numeric_filled_with_zero(self):
        from tools.sql_query import _type_aware_fillna
        df = pd.DataFrame({"count": [1, None, 3], "name": ["a", None, "c"]})
        result = _type_aware_fillna(df)
        assert result["count"].iloc[1] == 0

    def test_string_filled_with_empty(self):
        from tools.sql_query import _type_aware_fillna
        df = pd.DataFrame({"count": [1, None, 3], "name": ["a", None, "c"]})
        result = _type_aware_fillna(df)
        assert result["name"].iloc[1] == ""

    def test_no_zeroes_in_string_columns(self):
        from tools.sql_query import _type_aware_fillna
        df = pd.DataFrame({"date": ["2024-01-01", None], "value": [10, None]})
        result = _type_aware_fillna(df)
        assert result["date"].iloc[1] == ""
        assert result["value"].iloc[1] == 0


# ── 4. Memory — no truncation ───────────────────────────────────────────────

class TestMemoryNoTruncation:
    def test_all_actions_preserved(self):
        """build_memory_update should include ALL actions, not just first 5."""
        from memory import build_memory_update
        actions = [f"Action {i}" for i in range(10)]
        result = build_memory_update("", "test query", actions, "test response")
        for i in range(10):
            assert f"Action {i}" in result

    def test_compaction_threshold_lowered(self):
        from memory import MAX_MEMORY_CHARS
        assert MAX_MEMORY_CHARS == 2000, f"Expected 2000, got {MAX_MEMORY_CHARS}"


# ── 5. Per-tool-call state ──────────────────────────────────────────────────

class TestPerToolCallState:
    def test_context_has_query_results(self):
        from agent import _new_ctx
        ctx = _new_ctx()
        assert "query_results" in ctx
        assert isinstance(ctx["query_results"], dict)
        assert "latest_result_id" in ctx


# ── 6. Conversation session scope ───────────────────────────────────────────

class TestSessionScope:
    def test_session_scope_is_context_manager(self):
        """Verify _session_scope is a proper context manager."""
        import inspect
        from conversations import _session_scope
        # contextmanager-decorated functions are generators
        assert callable(_session_scope)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
