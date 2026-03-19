"""Six-layer SQL validation pipeline powered by SQLGlot.

Layer 1: Syntax parse
Layer 2: Table existence
Layer 3: Column existence
Layer 4: DML / DDL blocking
Layer 5: LIMIT enforcement
Layer 6: SELECT * rejection
"""

from __future__ import annotations

import logging
from typing import Optional

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from models.schemas import ValidationResult

logger = logging.getLogger("agent.sql_validator")

# Statements that must never be executed.
_BLOCKED_STATEMENT_TYPES = (
    exp.Drop,
    exp.Delete,
    exp.Update,
    exp.Insert,
    exp.Alter,
    exp.Grant,
)

_BLOCKED_KEYWORDS = {"TRUNCATE", "GRANT", "REVOKE", "ALTER", "DROP", "DELETE", "UPDATE", "INSERT"}


class SQLValidator:
    """Validates and optionally auto-fixes SQL before execution."""

    def __init__(self, schema: dict[str, list[str]] | None = None):
        self._schema = schema or {}

    def update_schema(self, schema: dict[str, list[str]]) -> None:
        self._schema = schema

    # ── Public API ────────────────────────────────────────────────────────────

    def validate(self, sql: str, schema: dict[str, list[str]] | None = None) -> ValidationResult:
        """Run the full 6-layer validation pipeline."""
        active_schema = schema or self._schema
        warnings: list[str] = []

        # Layer 1 – syntax
        try:
            parsed = sqlglot.parse(sql, dialect="postgres")
        except ParseError as exc:
            return ValidationResult(valid=False, error=f"Syntax error: {exc}")

        if not parsed or parsed[0] is None:
            return ValidationResult(valid=False, error="Empty or unparseable SQL")

        stmt = parsed[0]

        # Layer 4 – block dangerous statements (before table/col checks)
        block_err = self._check_blocked(stmt, sql)
        if block_err:
            return ValidationResult(valid=False, error=block_err)

        # Layer 2 – table existence
        tables = self.extract_tables(sql)
        if active_schema:
            for t in tables:
                clean = t.split(".")[-1].lower()
                if clean not in {k.lower() for k in active_schema}:
                    return ValidationResult(
                        valid=False,
                        error=f"Table '{t}' does not exist in the schema",
                    )

        # Layer 3 – column existence
        if active_schema:
            col_err = self._check_columns(stmt, active_schema)
            if col_err:
                return ValidationResult(valid=False, error=col_err)

        # Layer 6 – reject SELECT *
        if self._has_select_star(stmt):
            return ValidationResult(
                valid=False,
                error="SELECT * is not allowed. Please specify explicit columns.",
            )

        # Layer 5 – enforce LIMIT
        fixed_sql = sql
        if isinstance(stmt, exp.Select) and not stmt.find(exp.Limit):
            fixed_sql = f"{sql.rstrip().rstrip(';')} LIMIT 500"
            warnings.append("LIMIT 500 auto-injected")

        return ValidationResult(valid=True, fixed_sql=fixed_sql, warnings=warnings)

    def extract_tables(self, sql: str) -> list[str]:
        """Return all table names referenced in the SQL."""
        try:
            parsed = sqlglot.parse(sql, dialect="postgres")
        except ParseError:
            return []
        if not parsed or parsed[0] is None:
            return []
        tables: list[str] = []
        for table_node in parsed[0].find_all(exp.Table):
            name = table_node.name
            if name:
                tables.append(name)
        return list(dict.fromkeys(tables))  # deduplicate preserving order

    def extract_columns(self, sql: str) -> list[str]:
        """Return all column names referenced in the SQL."""
        try:
            parsed = sqlglot.parse(sql, dialect="postgres")
        except ParseError:
            return []
        if not parsed or parsed[0] is None:
            return []
        cols: list[str] = []
        for col_node in parsed[0].find_all(exp.Column):
            cols.append(col_node.name)
        return list(dict.fromkeys(cols))

    def is_safe(self, sql: str) -> bool:
        """Quick safety check without full validation."""
        upper = sql.upper().strip()
        return not any(kw in upper.split() for kw in _BLOCKED_KEYWORDS)

    def auto_fix(self, sql: str) -> str:
        """Attempt minor auto-corrections (e.g. inject LIMIT)."""
        result = self.validate(sql)
        return result.fixed_sql or sql

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _check_blocked(stmt: exp.Expression, raw_sql: str) -> Optional[str]:
        if isinstance(stmt, _BLOCKED_STATEMENT_TYPES):
            return f"Blocked statement type: {type(stmt).__name__}"
        upper = raw_sql.upper().strip()
        for kw in _BLOCKED_KEYWORDS:
            tokens = upper.split()
            if kw in tokens and kw not in ("UPDATE", "DELETE"):
                # UPDATE/DELETE caught by isinstance above; double-check raw
                pass
            if tokens and tokens[0] == kw:
                return f"Blocked statement: {kw}"
        if upper.startswith("TRUNCATE"):
            return "Blocked statement: TRUNCATE"
        return None

    @staticmethod
    def _has_select_star(stmt: exp.Expression) -> bool:
        for star in stmt.find_all(exp.Star):
            # Allow COUNT(*) but reject SELECT *
            parent = star.parent
            if isinstance(parent, exp.Column) or (
                parent is not None and not isinstance(parent, (exp.Count, exp.Anonymous))
            ):
                return True
            # Star directly under Select
            if isinstance(parent, exp.Select):
                return True
        return False

    def _check_columns(self, stmt: exp.Expression, schema: dict[str, list[str]]) -> Optional[str]:
        """Validate referenced columns against the schema.

        Only flags columns whose table alias can be resolved to a known table
        and whose name is not found in that table's column list.  Unqualified
        columns or those attached to unknown aliases are allowed through to
        avoid false positives on expressions like aggregates and sub-selects.
        """
        # Build alias→table mapping from FROM / JOIN clauses
        alias_map: dict[str, str] = {}
        for table_node in stmt.find_all(exp.Table):
            tname = table_node.name.lower()
            alias = (table_node.alias or tname).lower()
            alias_map[alias] = tname

        schema_lower = {k.lower(): [c.lower() for c in v] for k, v in schema.items()}

        for col_node in stmt.find_all(exp.Column):
            col_name = col_node.name.lower()
            table_ref = col_node.table.lower() if col_node.table else None

            if table_ref and table_ref in alias_map:
                real_table = alias_map[table_ref]
                if real_table in schema_lower and col_name not in schema_lower[real_table]:
                    return f"Column '{col_node.name}' does not exist in table '{real_table}'"

        return None
