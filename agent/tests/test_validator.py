"""Tests for the 6-layer SQL validator."""

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.sql_validator import SQLValidator

SAMPLE_SCHEMA = {
    "clients": ["client_id", "client_name", "created_at"],
    "created_assets": ["asset_id", "client_id", "create_date", "output_type_id"],
    "billing_events": ["billing_id", "client_id", "amount", "billing_date"],
    "output_types": ["output_type_id", "output_type_name"],
    "channels": ["channel_id", "channel_name"],
}


@pytest.fixture
def validator():
    return SQLValidator(schema=SAMPLE_SCHEMA)


# ── Layer 1: Syntax ──────────────────────────────────────────────────────────

class TestSyntaxValidation:
    def test_valid_sql(self, validator):
        r = validator.validate("SELECT client_name FROM clients LIMIT 10")
        assert r.valid

    def test_invalid_syntax(self, validator):
        r = validator.validate("SELECTT client_name FORM clients")
        assert not r.valid
        assert "Syntax" in (r.error or "") or r.error is not None


# ── Layer 2: Table existence ─────────────────────────────────────────────────

class TestTableValidation:
    def test_valid_table(self, validator):
        r = validator.validate("SELECT client_name FROM clients LIMIT 10")
        assert r.valid

    def test_invalid_table(self, validator):
        r = validator.validate("SELECT col FROM nonexistent_table LIMIT 10")
        assert not r.valid
        assert "nonexistent_table" in (r.error or "")


# ── Layer 3: Column existence ────────────────────────────────────────────────

class TestColumnValidation:
    def test_valid_column(self, validator):
        r = validator.validate("SELECT c.client_name FROM clients c LIMIT 10")
        assert r.valid

    def test_invalid_column(self, validator):
        r = validator.validate("SELECT c.fake_col FROM clients c LIMIT 10")
        assert not r.valid
        assert "fake_col" in (r.error or "")


# ── Layer 4: DML blocking ───────────────────────────────────────────────────

class TestDMLBlocking:
    @pytest.mark.parametrize("sql", [
        "DROP TABLE clients",
        "DELETE FROM clients WHERE 1=1",
        "UPDATE clients SET client_name = 'x'",
        "INSERT INTO clients VALUES (1, 'test', NOW())",
        "TRUNCATE clients",
    ])
    def test_blocks_dml(self, validator, sql):
        r = validator.validate(sql)
        assert not r.valid
        assert "Blocked" in (r.error or "") or "blocked" in (r.error or "").lower()


# ── Layer 5: LIMIT enforcement ───────────────────────────────────────────────

class TestLimitEnforcement:
    def test_auto_injects_limit(self, validator):
        r = validator.validate("SELECT client_name FROM clients")
        assert r.valid
        assert r.fixed_sql is not None
        assert "LIMIT" in r.fixed_sql.upper()
        assert "auto-injected" in (r.warnings[0] if r.warnings else "")

    def test_keeps_existing_limit(self, validator):
        r = validator.validate("SELECT client_name FROM clients LIMIT 10")
        assert r.valid
        assert not r.warnings or "auto-injected" not in str(r.warnings)


# ── Layer 6: SELECT * rejection ──────────────────────────────────────────────

class TestSelectStarRejection:
    def test_rejects_select_star(self, validator):
        r = validator.validate("SELECT * FROM clients LIMIT 10")
        assert not r.valid
        assert "SELECT *" in (r.error or "")

    def test_allows_count_star(self, validator):
        r = validator.validate("SELECT COUNT(*) AS cnt FROM clients LIMIT 10")
        assert r.valid


# ── Utility methods ──────────────────────────────────────────────────────────

class TestUtilities:
    def test_extract_tables(self, validator):
        tables = validator.extract_tables(
            "SELECT c.client_name FROM clients c JOIN created_assets ca ON c.client_id = ca.client_id"
        )
        assert "clients" in tables
        assert "created_assets" in tables

    def test_extract_columns(self, validator):
        cols = validator.extract_columns("SELECT c.client_name, ca.asset_id FROM clients c JOIN created_assets ca ON c.client_id = ca.client_id")
        assert "client_name" in cols
        assert "asset_id" in cols

    def test_is_safe(self, validator):
        assert validator.is_safe("SELECT 1")
        assert not validator.is_safe("DROP TABLE clients")

    def test_auto_fix(self, validator):
        fixed = validator.auto_fix("SELECT client_name FROM clients")
        assert "LIMIT" in fixed.upper()
