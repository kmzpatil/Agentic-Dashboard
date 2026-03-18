# Testing Suite Directory

This directory contains the Python testing logic intended to validate the core routing, security, and data integrity modifications within the Frammer AI agent and its backing Model Context Protocol (MCP) server. 

## Structure & Purpose

The tests here operate as a set of rigorous, targeted validation checks (often leveraging `pytest`) designed to ensure that the agent interactions with the SQL database remain tightly constrained, secure, and accurate.

### 1. `test_auth_enforcement.py`
This suite verifies that the security isolation boundary functions correctly. Since the AI builds dynamic query strings, it's absolutely critical that data isolation isn't bypassed.
- **SQL Scoping:** It runs tests against the `DatabaseClient` by injecting mocked authentication profiles (e.g., `website_admin`, `client_admin`, specific `user`). 
- **Validation Check:** Instead of running the queries against a real database, it mocks out the internal `pd.read_sql_query` to silently intercept the finalized SQL string. It guarantees that the internal engine dynamically wrapped non-admin queries in restrictive Common Table Expressions (CTEs) like `scoped_videos` based strictly on the user ID or client perimeter.

### 2. `test_improvements.py`
This collection serves as a broader smoke test for the analytical layer logic and agent memory functions. Rather than testing specific SQL outputs, it tests the preprocessing and parsing mechanisms surrounding them:
- **Sanitization Check:** Tests the `_strip_comments` layer to verify that destructive behaviors (like `DROP TABLE` or `DELETE`) hidden within multiline SQL comments are neutralized before runtime.
- **Query Wrappers:** Guarantees that the CTE packaging engine (appending `WITH mcp_cte AS ...`) preserves syntax features like `ORDER BY` without silently dropping or erroring out.
- **Data Coercion:** Asserts that missing DataFrame values (`NaN`) are explicitly backfilled accurately by type—`0` for numeric columns and `""` (empty string) for generic objects/strings via `_type_aware_fillna` to prevent frontend serialization errors.
- **Memory Context Validation:** Ensures that the agent's context array safely persists sub-query maps per turn and respects standard action counts to prevent context window blowouts.

## Running the Tests

To execute the suites locally to confirm your changes haven't broken the pipeline, simply execute `pytest` from the `agent` root:

```bash
python -m pytest tests/ -v
```
