"""
compiler.py
-----------
Compiles a validated KPI DSL JSON → parameterized SQL query.

STRICT RULES:
  - Deterministic only — NO LLM usage
  - NEVER stores raw SQL in the DSL
  - NEVER allows raw user input to reach SQL execution

SQL parameter convention (matches existing codebase):
  $1  = time_granularity string (e.g. 'month')
  $2+ = access-filter parameters (auth scope: client_name or user_id)

Caller must pass params = [granularity] + access_filter["params"]
"""

from __future__ import annotations

import re
from typing import Any

from backend.queries.analytics_shared import (
    build_access_filter,
    build_where_clause,
    get_metric_query,
)
from backend.kpi.validator import FORMULA_ATOMS, SINGLE_METRICS

# ── Metric atom CTEs ──────────────────────────────────────────────────────────
# Each entry produces (period, value) grouped by the $1 time granularity.
# These are embedded into the WITH clause after scoped_videos/assets/posts CTEs.

_ATOM_CTE_SQL: dict[str, str] = {
    "uploaded_count": """
    SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period,
           COUNT(*)::float8 AS value
    FROM scoped_videos sv
    GROUP BY 1""",

    "created_count": """
    SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period,
           COUNT(DISTINCT sa."Asset_ID")::float8 AS value
    FROM scoped_assets sa
    GROUP BY 1""",

    "published_count": """
    SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period,
           COUNT(DISTINCT sp."Post_ID")::float8 AS value
    FROM scoped_posts sp
    GROUP BY 1""",

    "uploaded_duration": """
    SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period,
           COALESCE(SUM(sv."Uploaded_Duration"), 0)::float8 AS value
    FROM scoped_videos sv
    GROUP BY 1""",

    "created_duration": """
    SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period,
           COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS value
    FROM scoped_assets sa
    GROUP BY 1""",

    "published_duration": """
    SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period,
           COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS value
    FROM scoped_posts sp
    GROUP BY 1""",
}


def compile_dsl(dsl: dict[str, Any], access_filter: dict[str, Any]) -> str:
    """
    Convert a validated DSL dict into a parameterized SQL string.

    The returned SQL uses:
      $1  — time granularity
      $2+ — access-filter auth params (already embedded in scoped CTEs)

    Args:
        dsl:           Validated KPI DSL JSON
        access_filter: Built by build_access_filter(auth, start_index=2)

    Returns:
        SQL string ready for backend.db.pool.query(sql, [granularity] + access_filter["params"])
    """
    kpi_type = dsl.get("type")

    if kpi_type == "single_metric":
        return _compile_single_metric(dsl, access_filter)
    elif kpi_type == "formula":
        return _compile_formula(dsl, access_filter)
    elif kpi_type == "raw_sql":
        return _compile_raw_sql(dsl, access_filter)
    else:
        raise ValueError(f"Unknown DSL type: {kpi_type}")


def _scoped_base_ctes(access_filter: dict[str, Any]) -> str:
    """Build the scoped_videos / scoped_assets / scoped_posts CTE block."""
    join_clause = access_filter.get("join", "")
    predicates = access_filter.get("predicates", [])
    where_clause = build_where_clause(predicates)

    return f"""
    scoped_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Upload_Date", rv."Uploaded_Duration"
      FROM raw_videos rv
      {join_clause}
      {where_clause}
    ),
    scoped_assets AS (
      SELECT DISTINCT ON (ca."Asset_ID") ca.*
      FROM created_assets ca
      JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
      ORDER BY ca."Asset_ID"
    ),
    scoped_posts AS (
      SELECT DISTINCT ON (pp."Post_ID") pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
      ORDER BY pp."Post_ID"
    )"""


def _compile_single_metric(dsl: dict[str, Any], access_filter: dict[str, Any]) -> str:
    """
    Delegate to get_metric_query for the 9 supported single metrics.
    get_metric_query expects access_filter with params starting at $2
    (granularity occupies $1 in its output SQL).
    """
    metric = dsl["metric"]
    return get_metric_query(metric, access_filter)


def _compile_raw_sql(dsl: dict[str, Any], access_filter: dict[str, Any]) -> str:
    """
    Wrap agent-generated raw SQL with the scoped base CTEs to enforce auth rules.
    Replaces references to raw_videos, created_assets, published_posts with 
    their scoped equivalents.
    """
    base_ctes = _scoped_base_ctes(access_filter)
    raw_sql = dsl.get("sql", "")
    
    # Secure the agent's SQL by redirecting raw table reads to the auth CTEs
    safe_sql = re.sub(r'\braw_videos\b', 'scoped_videos', raw_sql, flags=re.IGNORECASE)
    safe_sql = re.sub(r'\bcreated_assets\b', 'scoped_assets', safe_sql, flags=re.IGNORECASE)
    safe_sql = re.sub(r'\bpublished_posts\b', 'scoped_posts', safe_sql, flags=re.IGNORECASE)

    # If agent SQL starts with WITH, merge CTEs into single WITH block
    stripped = safe_sql.lstrip()
    if re.match(r'(?i)^WITH\s', stripped):
        agent_ctes_and_body = re.sub(r'(?i)^WITH\s+', '', stripped, count=1)
        return f"WITH {base_ctes},\n{agent_ctes_and_body}"
    else:
        return f"WITH {base_ctes}\n{safe_sql}"


def _compile_formula(dsl: dict[str, Any], access_filter: dict[str, Any]) -> str:
    """
    Build a custom SQL for an arithmetic formula over metric atoms.

    Strategy:
      1. Emit scoped base CTEs (scoped_videos, scoped_assets, scoped_posts)
      2. Emit one metric CTE per operand  (m_<atom_name>)
      3. FULL OUTER JOIN all metric CTEs on period
      4. Apply the formula expression in the final SELECT, replacing atom names
         with COALESCE(m_<atom>.value, 0)
    """
    formula: str = dsl["formula"]
    operands: list[str] = dsl["operands"]

    base_ctes = _scoped_base_ctes(access_filter)

    # Build individual metric CTEs
    atom_cte_parts: list[str] = []
    for atom in operands:
        if atom not in _ATOM_CTE_SQL:
            raise ValueError(f"No CTE definition for metric atom '{atom}'.")
        atom_cte_parts.append(f"    m_{atom} AS ({_ATOM_CTE_SQL[atom]})")

    # Detect which atoms are used as denominators (appear immediately after /)
    # to guard against division-by-zero with NULLIF.
    denominator_atoms = _find_denominators(formula, operands)

    # Build the SELECT expression by replacing metric names with CTE value refs.
    # Sort by length descending to avoid partial-name collisions.
    sql_expr = formula
    for atom in sorted(operands, key=len, reverse=True):
        if atom in denominator_atoms:
            # NULLIF turns 0 → NULL so the division yields NULL, not an error
            ref = f"NULLIF(COALESCE(m_{atom}.value, 0), 0)"
        else:
            ref = f"COALESCE(m_{atom}.value, 0)"
        sql_expr = re.sub(rf"\b{re.escape(atom)}\b", ref, sql_expr)

    # Wrap final expression: COALESCE turns NULL (from divide-by-zero) → 0
    safe_expr = f"COALESCE(({sql_expr})::float8, 0)"

    # Build period coalesce and JOINs
    primary = f"m_{operands[0]}"
    period_coalesce = _build_period_coalesce(operands)
    joins = _build_full_outer_joins(operands)

    sql = f"""
WITH {base_ctes},
{",".join(atom_cte_parts)}
SELECT
  {period_coalesce} AS period,
  {safe_expr} AS value
FROM {primary}
{joins}
ORDER BY 1;
"""
    return sql


def _build_period_coalesce(operands: list[str]) -> str:
    """COALESCE(m_a.period, m_b.period, ...) for all operands."""
    refs = [f"m_{op}.period" for op in operands]
    if len(refs) == 1:
        return refs[0]
    return f"COALESCE({', '.join(refs)})"


def _build_full_outer_joins(operands: list[str]) -> str:
    """FULL OUTER JOIN for operands[1..] against operands[0]."""
    if len(operands) <= 1:
        return ""
    primary = f"m_{operands[0]}"
    lines: list[str] = []
    for op in operands[1:]:
        lines.append(
            f"FULL OUTER JOIN m_{op} ON m_{op}.period = {primary}.period"
        )
    return "\n".join(lines)


def _find_denominators(formula: str, operands: list[str]) -> set[str]:
    """
    Return the subset of operands that appear as denominators (right after /)
    in the formula string.  Used to wrap them in NULLIF(..., 0) to prevent
    division-by-zero errors when a period has a zero count.

    Handles patterns like:  a / b,  a / (b),  (a + b) / c * 100
    """
    denominators: set[str] = set()
    for atom in operands:
        # Match: '/' followed by optional whitespace/open-parens, then the atom name
        if re.search(rf"/\s*\(?\s*{re.escape(atom)}\b", formula):
            denominators.add(atom)
    return denominators


def build_execution_params(dsl: dict[str, Any], access_filter: dict[str, Any]) -> list[Any]:
    """
    Return the ordered params list for query(sql, params):
      [granularity_string] + auth_params
    """
    granularity = dsl.get("time_granularity", "month")
    return [granularity] + list(access_filter.get("params", []))
