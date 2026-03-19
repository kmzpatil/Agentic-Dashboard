"""
test_queries.py
───────────────
Existing KPI query tests + stress-test queries for the multi-agent pipeline.
"""

import asyncio
from backend.db.pool import query
from backend.queries.advanced_kpi_queries import get_publish_conversion_details_query, get_roi_matrix_query

access_filter = {
    "join": "",
    "predicates": [],
    "params": [],
    "next_index": 1,
}

try:
    print("Testing conversion details...")
    res1 = query(get_publish_conversion_details_query(access_filter), [])
    print("Conversion rows:", len(res1.rows))

    print("Testing ROI matrix...")
    res2 = query(get_roi_matrix_query(access_filter), [])
    print("ROI rows:", len(res2.rows))

    print("Testing waste index...")
    from backend.queries.advanced_kpi_queries import get_waste_index_details_query
    res3 = query(get_waste_index_details_query(access_filter), [])
    print("Waste rows:", len(res3.rows))

    print("Testing interaction lift...")
    from backend.queries.advanced_kpi_queries import get_interaction_lift_query
    res4 = query(get_interaction_lift_query(access_filter), [])
    print("Lift rows:", len(res4.rows))

    print("Testing entropy...")
    from backend.queries.advanced_kpi_queries import get_cross_dimension_entropy_query
    res5 = query(get_cross_dimension_entropy_query(access_filter), [])
    print("Entropy rows:", len(res5.rows))

    print("Testing CDAS...")
    from backend.queries.advanced_kpi_queries import get_cdas_query
    res6 = query(get_cdas_query(access_filter), [])
    print("CDAS rows:", len(res6.rows))

except Exception as e:
    print(f"Error: {e}")


# ── Multi-Agent Stress Test Queries ──────────────────────────────────────────

STRESS_TEST_QUERIES = [
    # Simple lookups
    "How many clients do we have?",
    "List all output types",
    "What is today's date in the database?",

    # Aggregations
    "Total assets created this week",
    "Average assets per client",
    "Count assets by channel",

    # Filters
    "Clients with more than 100 assets",
    "Assets created in the last 90 days",
    "Clients on enterprise subscription",

    # Rankings
    "Top 5 most active clients",
    "Bottom 10 clients by asset count",

    # Trends (deep)
    "Show asset creation trend for last 12 months",
    "Monthly revenue trend this year",
    "Weekly active clients over last quarter",

    # Analytics (deep)
    "Why did asset creation drop last month?",
    "Compare Q1 vs Q2 performance",
    "Which clients are churning?",

    # Multi-chart queries
    "Show me both revenue trend and asset creation trend",
    "Give me a bar chart of top clients and a line chart of monthly growth",

    # Edge cases
    "Show data for a table that doesn't exist",   # should error gracefully
    "Delete all records",                          # must be blocked
    "SELECT * FROM clients",                       # must be rejected

    # Date edge cases
    "Assets created last quarter",
    "Revenue year to date",
    "Clients who joined last year",

    # Follow-up context
    "Show top 10 clients",
    "Now filter by last month",               # requires conversation memory
    "Break that down by channel",             # requires context from previous
]


async def run_stress_tests():
    """Run all stress test queries through the multi-agent orchestrator."""
    try:
        from agent.orchestrator.orchestrator import get_orchestrator
    except ImportError:
        print("Multi-agent orchestrator not available — skipping stress tests")
        return

    try:
        orchestrator = await get_orchestrator()
    except Exception as exc:
        print(f"Could not initialise orchestrator: {exc}")
        return

    conv_id = "stress-test-001"
    passed = 0
    failed = 0

    for i, q in enumerate(STRESS_TEST_QUERIES, 1):
        try:
            result = await orchestrator.handle_query(q, conv_id, "auto")
            status = "PASS" if result.summary else "EMPTY"
            print(f"  [{i:02d}] {status} | {result.path_used:4s} | {result.execution_ms:5d}ms | {q[:50]}")
            print(f"       → {result.summary[:80]}")
            passed += 1
        except Exception as exc:
            print(f"  [{i:02d}] FAIL | {q[:50]}")
            print(f"       → {exc}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {len(STRESS_TEST_QUERIES)}")


if __name__ == "__main__":
    print("\n=== Running stress tests ===\n")
    asyncio.run(run_stress_tests())
