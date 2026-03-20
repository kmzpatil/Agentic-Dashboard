"""
test_agent.py
─────────────
End-to-end test suite for the Frammer Analytics Agent.

Runs real queries through the full ReAct loop (LLM + tools + DB) and
validates that the agent produces correct, non-empty responses with
expected characteristics (charts when appropriate, correct numbers, etc.).

Usage:
    cd agent/
    python test_agent.py              # run all tests
    python test_agent.py -k funnel    # run only tests matching "funnel"
    python test_agent.py -v           # verbose output
"""

import asyncio
import json
import sys
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# ── Path setup ───────────────────────────────────────────────────────────────
_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from dotenv import load_dotenv
load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

from agent import run_agent, AgentResult

# ── Test infrastructure ──────────────────────────────────────────────────────

@dataclass
class TestCase:
    name: str
    question: str
    expect_chart: Optional[bool] = None      # True = must chart, False = must NOT chart, None = don't care
    expect_sql: bool = True                   # expect SQL was executed
    expect_keywords: list = None              # words that should appear in response (case-insensitive)
    expect_no_error: bool = True              # response should not contain error text
    auth: Optional[object] = None             # auth object for scoped tests
    max_seconds: float = 60.0                 # timeout

@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    response: str
    actions: list
    has_chart: bool
    has_sql: bool
    failure_reason: str = ""


class MockAuth:
    """Simulate auth objects for scoped access tests."""
    def __init__(self, role="website_admin", username="test", client_name=None, user_id=None):
        self.role = role
        self.username = username
        self.client_name = client_name
        self.user_id = user_id


# ── Test cases ───────────────────────────────────────────────────────────────

TESTS = [
    # ── Conversational (should NOT call tools) ────────────────────────────
    TestCase(
        name="conversational_greeting",
        question="Hey! What can you help me with?",
        expect_chart=False,
        expect_sql=False,
        expect_keywords=["analytics", "data"],
    ),
    TestCase(
        name="conversational_thanks",
        question="Thanks, that was helpful!",
        expect_chart=False,
        expect_sql=False,
    ),

    # ── Single KPI (should NOT chart — single number) ────────────────────
    TestCase(
        name="kpi_total_uploads",
        question="How many total videos have been uploaded?",
        expect_chart=False,
        expect_sql=True,
        expect_keywords=["10"],  # ~10,683
    ),
    TestCase(
        name="kpi_total_assets",
        question="How many total assets have been created?",
        expect_chart=False,
        expect_sql=True,
        expect_keywords=["53"],  # ~53,669
    ),
    TestCase(
        name="kpi_total_published",
        question="How many posts have been published in total?",
        expect_chart=False,
        expect_sql=True,
        expect_keywords=["1"],   # ~1,294
    ),

    # ── Category breakdowns (SHOULD chart — bar) ─────────────────────────
    TestCase(
        name="breakdown_uploads_by_language",
        question="Show me the breakdown of uploads by language",
        expect_chart=True,
        expect_sql=True,
    ),
    TestCase(
        name="breakdown_uploads_by_input_type",
        question="How many videos were uploaded for each input type? Show me a chart.",
        expect_chart=True,
        expect_sql=True,
    ),
    TestCase(
        name="breakdown_assets_by_output_type",
        question="Break down created assets by output type",
        expect_chart=True,
        expect_sql=True,
    ),

    # ── Trends over time (SHOULD chart — line) ───────────────────────────
    TestCase(
        name="trend_monthly_uploads",
        question="Show me the monthly upload trend",
        expect_chart=True,
        expect_sql=True,
        expect_keywords=["month"],
    ),
    TestCase(
        name="trend_monthly_published",
        question="How has publishing volume changed month over month?",
        expect_chart=True,
        expect_sql=True,
    ),

    # ── Conversion / funnel metrics ──────────────────────────────────────
    TestCase(
        name="funnel_conversion_rate",
        question="What is the overall conversion rate from created assets to published posts?",
        expect_sql=True,
        expect_keywords=["%"],
    ),
    TestCase(
        name="funnel_conversion_by_channel",
        question="Which channels have the highest publish conversion rate?",
        expect_chart=True,
        expect_sql=True,
    ),

    # ── Multi-table joins ────────────────────────────────────────────────
    TestCase(
        name="join_published_by_language",
        question="How many posts were published for each language? Visualize this.",
        expect_chart=True,
        expect_sql=True,
    ),
    TestCase(
        name="join_platform_distribution",
        question="Which platforms have the most published posts? Show a chart.",
        expect_chart=True,
        expect_sql=True,
    ),

    # ── Top-N queries ────────────────────────────────────────────────────
    TestCase(
        name="top_users_by_uploads",
        question="Who are the top 5 users by number of uploads?",
        expect_sql=True,
    ),
    TestCase(
        name="top_channels_by_assets",
        question="What are the top 10 channels by number of created assets?",
        expect_sql=True,
    ),

    # ── Proportional / pie chart ─────────────────────────────────────────
    TestCase(
        name="proportion_input_type_share",
        question="What is the share of each input type as a percentage of total uploads? Show a pie chart.",
        expect_chart=True,
        expect_sql=True,
    ),

    # ── Complex analytics ────────────────────────────────────────────────
    TestCase(
        name="analytics_creation_rate",
        question="What is the average number of assets created per uploaded video?",
        expect_sql=True,
    ),
    TestCase(
        name="analytics_publish_lag",
        question="What is the average number of days between asset creation and publication?",
        expect_sql=True,
    ),

    # ── Discovery (schema / metric lookups — may or may not use SQL) ─────
    TestCase(
        name="discovery_tables",
        question="What tables are available in the database?",
        expect_chart=False,
        expect_sql=False,
    ),
    TestCase(
        name="discovery_metric_definition",
        question="How is the conversion rate calculated?",
        expect_chart=False,
        expect_sql=False,
    ),

    # ── Auth scoping: Client admin ───────────────────────────────────────
    TestCase(
        name="auth_client_scoped",
        question="How many videos have been uploaded?",
        expect_sql=True,
        auth=MockAuth(role="client_admin", username="client1_admin", client_name="Client 1"),
    ),

    # ── Auth scoping: User-level ─────────────────────────────────────────
    TestCase(
        name="auth_user_scoped",
        question="How many videos have I uploaded?",
        expect_sql=True,
        auth=MockAuth(role="user", username="chandan", user_id=1),
    ),
]


# ── Test runner ──────────────────────────────────────────────────────────────

async def run_single_test(tc: TestCase) -> TestResult:
    """Run a single test case through the agent and validate expectations."""
    start = time.time()
    try:
        result: AgentResult = await asyncio.wait_for(
            run_agent(tc.question, auth=tc.auth),
            timeout=tc.max_seconds,
        )
    except asyncio.TimeoutError:
        return TestResult(
            name=tc.name, passed=False, duration=time.time() - start,
            response="", actions=[], has_chart=False, has_sql=False,
            failure_reason=f"TIMEOUT after {tc.max_seconds}s",
        )
    except Exception as exc:
        return TestResult(
            name=tc.name, passed=False, duration=time.time() - start,
            response="", actions=[], has_chart=False, has_sql=False,
            failure_reason=f"EXCEPTION: {exc}",
        )

    duration = time.time() - start
    has_chart = bool(result.chart_xml)
    has_sql = bool(result.sql)
    failures = []

    # 1. Must have a non-empty response
    if not result.response or len(result.response.strip()) < 5:
        failures.append("Empty or trivial response")

    # 2. Should not contain error text
    if tc.expect_no_error and result.error:
        failures.append(f"Agent returned error: {result.error[:100]}")

    # 3. Chart expectation
    if tc.expect_chart is True and not has_chart:
        failures.append("Expected chart but none was generated")
    if tc.expect_chart is False and has_chart:
        failures.append("Expected NO chart but one was generated")

    # 4. SQL expectation
    if tc.expect_sql and not has_sql:
        # Check actions for SQL activity even if ctx.sql wasn't set
        sql_actions = [a for a in result.actions if "SQL" in a]
        if not sql_actions:
            failures.append("Expected SQL execution but none detected")

    # 5. Keyword checks
    if tc.expect_keywords:
        response_lower = result.response.lower()
        for kw in tc.expect_keywords:
            if kw.lower() not in response_lower:
                failures.append(f"Expected keyword '{kw}' not in response")

    passed = len(failures) == 0
    return TestResult(
        name=tc.name,
        passed=passed,
        duration=duration,
        response=result.response[:500],
        actions=result.actions,
        has_chart=has_chart,
        has_sql=has_sql,
        failure_reason=" | ".join(failures) if failures else "",
    )


async def run_all_tests(filter_keyword: str = "") -> list[TestResult]:
    """Run all test cases sequentially."""
    cases = TESTS
    if filter_keyword:
        cases = [t for t in TESTS if filter_keyword.lower() in t.name.lower()]

    print(f"\n{'='*70}")
    print(f"  FRAMMER AGENT TEST SUITE — {len(cases)} test(s)")
    print(f"{'='*70}\n")

    results = []
    for i, tc in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {tc.name}")
        print(f"  Q: \"{tc.question}\"")

        tr = await run_single_test(tc)
        results.append(tr)

        status = "✅ PASS" if tr.passed else "❌ FAIL"
        print(f"  {status} ({tr.duration:.1f}s)")
        if tr.actions:
            print(f"  Actions: {tr.actions}")
        print(f"  Chart: {'yes' if tr.has_chart else 'no'} | SQL: {'yes' if tr.has_sql else 'no'}")
        print(f"  Response: {tr.response[:200]}{'...' if len(tr.response) > 200 else ''}")
        if not tr.passed:
            print(f"  REASON: {tr.failure_reason}")
        print()

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total_time = sum(r.duration for r in results)

    print(f"{'='*70}")
    print(f"  RESULTS: {passed}/{len(results)} passed, {failed} failed")
    print(f"  Total time: {total_time:.1f}s (avg {total_time/len(results):.1f}s per test)")
    print(f"{'='*70}\n")

    if failed:
        print("FAILURES:")
        for r in results:
            if not r.passed:
                print(f"  ❌ {r.name}: {r.failure_reason}")
        print()

    return results


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    filter_kw = ""
    verbose = False

    for arg in sys.argv[1:]:
        if arg == "-v":
            verbose = True
        elif arg == "-k" and sys.argv.index(arg) + 1 < len(sys.argv):
            filter_kw = sys.argv[sys.argv.index(arg) + 1]
        elif sys.argv[sys.argv.index(arg) - 1] == "-k":
            continue  # already consumed
        else:
            filter_kw = arg

    results = asyncio.run(run_all_tests(filter_keyword=filter_kw))

    # Exit code: 0 if all passed, 1 if any failed
    sys.exit(0 if all(r.passed for r in results) else 1)
