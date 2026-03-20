#!/usr/bin/env python3
"""
test_report.py
--------------
End-to-end test for the Report Agent.

Runs the report agent against the real database with a sample query,
then generates an HTML report file that can be opened in a browser
and exported to PDF via Ctrl+P / Cmd+P.

Usage:
    python -m agent.test_report
    # or from agent/ directory:
    python test_report.py
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path

# Setup path
_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from dotenv import load_dotenv
load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_report")


async def test_with_real_data():
    """Run the full report agent against the real database."""
    from report_agent import run_report_agent, save_report_html

    question = "Full analysis of channel A: show upload trend, asset breakdown by type, and conversion rate comparison"

    logger.info("=" * 60)
    logger.info("RUNNING REPORT AGENT")
    logger.info("Question: %s", question)
    logger.info("=" * 60)

    result = await run_report_agent(question)

    logger.info("\n=== RESULT ===")
    logger.info("Intent: %s", result.intent)
    logger.info("Mode: %s", getattr(result, 'mode', 'normal'))
    logger.info("Actions: %s", result.actions)
    logger.info("Response: %s", result.response[:200] if result.response else "(empty)")

    report = getattr(result, 'report', None)
    if report:
        logger.info("\n=== REPORT STRUCTURE ===")
        logger.info("Title: %s", report.get("title"))
        logger.info("Sections: %d", len(report.get("sections", [])))
        logger.info("Recommendations: %d", len(report.get("recommendations", [])))

        # Save HTML — extract query results stashed by report agent
        output_path = str(_AGENT_DIR / "outputs" / "test_report.html")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        query_results = report.get("_query_results", [])
        logger.info("Query results available for charts/tables: %d", len(query_results))

        # Log what Gemini's sections reference
        for si, section in enumerate(report.get("sections", [])):
            chart = section.get("chart")
            if chart:
                logger.info("  Section %d chart: type=%s, source_query_index=%s, x=%s, y=%s",
                    si, chart.get("chart_type"), chart.get("source_query_index"),
                    chart.get("x_column"), chart.get("y_columns"))
            else:
                logger.info("  Section %d: NO chart spec", si)

        path = save_report_html(report, query_results, output_path)
        logger.info("\n✅ Report saved to: %s", path)
        logger.info("Open in browser and press Cmd+P / Ctrl+P to export as PDF")
    else:
        logger.warning("No report data in result")
        if result.error:
            logger.error("Error: %s", result.error)

    return result


async def test_with_mock_data():
    """Generate a sample HTML report using mock data to test formatting."""
    from report_agent import render_report_html, save_report_html

    logger.info("Generating mock report for formatting test...")

    mock_report = {
        "title": "Channel Performance Analysis: Why Channel D is Underperforming",
        "executive_summary": (
            "Channel D is significantly underperforming across all key metrics. "
            "With only **847 uploads** (vs. the platform average of **2,140**), it ranks last among active channels. "
            "Its asset creation rate of **62%** is below the platform average of **78%**, "
            "and its publishing conversion sits at a critically low **4.2%** compared to the platform-wide **12.8%**. "
            "Immediate intervention is needed to address the content pipeline bottleneck."
        ),
        "sections": [
            {
                "title": "Upload Volume Comparison",
                "content": (
                    "Channel D has uploaded **847 videos** over the analysis period, making it the lowest-performing channel by raw volume. "
                    "For comparison, Channel A leads with **3,412 uploads**, followed by Channel B at **2,891** and Channel C at **1,850**.\n\n"
                    "The upload cadence has also been declining. In the most recent month, Channel D uploaded only **52 videos**, "
                    "down **38%** from its average of **84 per month**. This suggests either reduced content production capacity or "
                    "a shift in channel strategy that has not been reflected in the platform configuration."
                ),
                "chart": {
                    "source_query_index": 0,
                    "chart_type": "bar",
                    "x_column": "channel",
                    "y_columns": "upload_count",
                    "title": "Upload Volume by Channel",
                },
                "table": {
                    "source_query_index": 0,
                    "max_rows": 5,
                    "title": "Channel Upload Summary",
                },
            },
            {
                "title": "Asset Creation Efficiency",
                "content": (
                    "The asset creation rate measures how effectively raw uploads are converted into distributable assets "
                    "(clips, summaries, chapters). Channel D achieves a **62% creation rate**, meaning roughly **4 out of 10** "
                    "uploads fail to produce any usable asset.\n\n"
                    "This is substantially below the platform average of **78%**. The top performer, Channel A, achieves **91%**. "
                    "The gap suggests that Channel D's content may be of lower quality, in unsupported formats, or encountering "
                    "processing errors at a higher rate than other channels.\n\n"
                    "Breaking down by content format, Channel D's video uploads have a **58%** creation rate while its audio "
                    "uploads fare slightly better at **71%**. This indicates the issue is more pronounced for video content."
                ),
                "chart": {
                    "source_query_index": 1,
                    "chart_type": "horizontal-bar",
                    "x_column": "channel",
                    "y_columns": "creation_rate",
                    "title": "Asset Creation Rate by Channel (%)",
                },
            },
            {
                "title": "Publishing Conversion Bottleneck",
                "content": (
                    "The most critical finding is Channel D's **4.2% publishing conversion rate** — the percentage of created "
                    "assets that actually get published. This is less than a third of the platform average of **12.8%**.\n\n"
                    "In absolute numbers, out of **525 assets** created from Channel D's uploads, only **22** were published. "
                    "This suggests a severe bottleneck in the publishing workflow, possibly due to:\n"
                    "- Stricter editorial review for Channel D's content type\n"
                    "- Missing metadata required for distribution\n"
                    "- Platform compatibility issues with Channel D's output formats\n\n"
                    "By contrast, Channel A converts **18.4%** of its assets to published content, and Channel B achieves **15.1%**."
                ),
                "chart": {
                    "source_query_index": 2,
                    "chart_type": "bar",
                    "x_column": "channel",
                    "y_columns": "conversion_rate",
                    "title": "Publishing Conversion Rate by Channel (%)",
                },
            },
            {
                "title": "Monthly Trend Analysis",
                "content": (
                    "Looking at Channel D's performance over the past 6 months reveals a **declining trajectory**. "
                    "Upload volume peaked in October at **112 videos**, then dropped steadily to **52 in March** — a **54% decline**.\n\n"
                    "Asset creation rates have also deteriorated, from **72%** in October to **55%** in March. "
                    "The publishing conversion rate, already low, dropped from **6.1%** to **2.8%** over the same period.\n\n"
                    "This accelerating decline suggests the issue is worsening and may require urgent investigation into "
                    "whether there have been changes in Channel D's content strategy, team capacity, or technical pipeline configuration."
                ),
                "chart": {
                    "source_query_index": 3,
                    "chart_type": "line",
                    "x_column": "month",
                    "y_columns": "uploads,creation_rate,conversion_rate",
                    "title": "Channel D — Monthly Performance Trend",
                },
            },
        ],
        "recommendations": [
            "Audit Channel D's recent uploads for quality issues — check for format incompatibilities, corrupted files, or content that fails processing.",
            "Review the publishing workflow for Channel D specifically — identify whether editorial bottlenecks or missing metadata are blocking publications.",
            "Schedule a review with Channel D's content team to understand the 54% drop in upload volume since October.",
            "Consider setting up automated alerts when any channel's publishing conversion drops below 5% for more than 2 consecutive weeks.",
            "Compare Channel D's technical pipeline configuration with Channel A's (highest performer) to identify configuration gaps.",
        ],
        "metadata": {
            "generated_at": "2026-03-20 14:30",
            "caveats": [
                "Analysis covers the trailing 6-month period (October 2025 – March 2026).",
                "Channel names have been anonymized. 'Channel D' refers to the lowest-performing active channel.",
                "Publishing conversion rates may be affected by seasonal content strategies not captured in this data.",
            ],
        },
    }

    mock_query_results = [
        {
            "status": "success",
            "description": "Upload volume by channel",
            "columns": ["Channel", "Upload Count", "Avg Monthly"],
            "row_count": 4,
            "data": [
                {"Channel": "Channel A", "Upload Count": 3412, "Avg Monthly": 569},
                {"Channel": "Channel B", "Upload Count": 2891, "Avg Monthly": 482},
                {"Channel": "Channel C", "Upload Count": 1850, "Avg Monthly": 308},
                {"Channel": "Channel D", "Upload Count": 847, "Avg Monthly": 141},
            ],
        },
        {
            "status": "success",
            "description": "Asset creation rate by channel",
            "columns": ["Channel", "Creation Rate", "Total Assets"],
            "row_count": 4,
            "data": [
                {"Channel": "Channel A", "Creation Rate": "91%", "Total Assets": 15621},
                {"Channel": "Channel B", "Creation Rate": "82%", "Total Assets": 11894},
                {"Channel": "Channel C", "Creation Rate": "76%", "Total Assets": 7062},
                {"Channel": "Channel D", "Creation Rate": "62%", "Total Assets": 2632},
            ],
        },
        {
            "status": "success",
            "description": "Publishing conversion rate by channel",
            "columns": ["Channel", "Conversion Rate", "Published", "Total Assets"],
            "row_count": 4,
            "data": [
                {"Channel": "Channel A", "Conversion Rate": "18.4%", "Published": 478, "Total Assets": 2598},
                {"Channel": "Channel B", "Conversion Rate": "15.1%", "Published": 352, "Total Assets": 2331},
                {"Channel": "Channel C", "Conversion Rate": "9.7%", "Published": 118, "Total Assets": 1216},
                {"Channel": "Channel D", "Conversion Rate": "4.2%", "Published": 22, "Total Assets": 525},
            ],
        },
        {
            "status": "success",
            "description": "Channel D monthly trend",
            "columns": ["Month", "Uploads", "Creation Rate", "Conversion Rate"],
            "row_count": 6,
            "data": [
                {"Month": "Oct 2025", "Uploads": 112, "Creation Rate": "72%", "Conversion Rate": "6.1%"},
                {"Month": "Nov 2025", "Uploads": 98, "Creation Rate": "69%", "Conversion Rate": "5.4%"},
                {"Month": "Dec 2025", "Uploads": 87, "Creation Rate": "67%", "Conversion Rate": "4.8%"},
                {"Month": "Jan 2026", "Uploads": 76, "Creation Rate": "63%", "Conversion Rate": "4.1%"},
                {"Month": "Feb 2026", "Uploads": 64, "Creation Rate": "59%", "Conversion Rate": "3.5%"},
                {"Month": "Mar 2026", "Uploads": 52, "Creation Rate": "55%", "Conversion Rate": "2.8%"},
            ],
        },
    ]

    output_path = str(_AGENT_DIR / "outputs" / "test_report_mock.html")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    path = save_report_html(mock_report, mock_query_results, output_path)
    logger.info("✅ Mock report saved to: %s", path)
    logger.info("Open in browser and press Cmd+P / Ctrl+P to export as PDF")
    return path


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test the Frammer AI Report Agent")
    parser.add_argument("--mock", action="store_true", help="Use mock data (no database needed)")
    parser.add_argument("--real", action="store_true", help="Run against real database")
    parser.add_argument("--both", action="store_true", help="Run both mock and real tests")
    args = parser.parse_args()

    if args.mock or (not args.real and not args.both):
        await test_with_mock_data()

    if args.real or args.both:
        await test_with_real_data()


if __name__ == "__main__":
    asyncio.run(main())
