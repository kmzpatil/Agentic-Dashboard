"""
test_report.py — Generate mock reports to visually inspect the HTML template.
Usage: python test_report.py [--mock]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from report_formatter import save_report_html


def test_with_mock_data():
    """Generate a report using hardcoded mock data — no database needed."""

    mock_query_results = [
        # Query 0: Monthly upload trend
        {
            "status": "success",
            "row_count": 6,
            "columns": ["month", "upload_count"],
            "data": [
                {"month": "2025-10", "upload_count": 1245},
                {"month": "2025-11", "upload_count": 1389},
                {"month": "2025-12", "upload_count": 1102},
                {"month": "2026-01", "upload_count": 1567},
                {"month": "2026-02", "upload_count": 1823},
                {"month": "2026-03", "upload_count": 1651},
            ],
        },
        # Query 1: Asset breakdown by type
        {
            "status": "success",
            "row_count": 5,
            "columns": ["asset_type", "count", "percentage"],
            "data": [
                {"asset_type": "Short Video", "count": 4523, "percentage": "38.2%"},
                {"asset_type": "Long Video", "count": 2891, "percentage": "24.4%"},
                {"asset_type": "Image Post", "count": 2156, "percentage": "18.2%"},
                {"asset_type": "Story", "count": 1344, "percentage": "11.3%"},
                {"asset_type": "Carousel", "count": 934, "percentage": "7.9%"},
            ],
        },
        # Query 2: Channel comparison
        {
            "status": "success",
            "row_count": 4,
            "columns": ["channel", "uploads", "published", "conversion_rate"],
            "data": [
                {"channel": "Channel Alpha", "uploads": 3200, "published": 2400, "conversion_rate": "75.0%"},
                {"channel": "Channel Beta", "uploads": 2800, "published": 1960, "conversion_rate": "70.0%"},
                {"channel": "Channel Gamma", "uploads": 1900, "published": 1520, "conversion_rate": "80.0%"},
                {"channel": "Channel Delta", "uploads": 950, "published": 475, "conversion_rate": "50.0%"},
            ],
        },
        # Query 3: Weekly anomaly data
        {
            "status": "success",
            "row_count": 4,
            "columns": ["week", "uploads", "change_pct"],
            "data": [
                {"week": "2026-W09", "uploads": 412, "change_pct": "+5.1%"},
                {"week": "2026-W10", "uploads": 389, "change_pct": "-5.6%"},
                {"week": "2026-W11", "uploads": 523, "change_pct": "+34.4%"},
                {"week": "2026-W12", "uploads": 401, "change_pct": "-23.3%"},
            ],
        },
    ]

    mock_report = {
        "title": "Content Pipeline Performance: Q1 2026 Analysis",
        "executive_summary": (
            "The content pipeline processed **8,777 uploads** across Q1 2026, representing a "
            "**18.3% increase** over Q4 2025. Channel Alpha leads with **3,200 uploads** and a "
            "**75% conversion rate**. Asset generation is dominated by short videos at **38.2%** "
            "of total output. However, Channel Delta shows a concerning **50% conversion rate** "
            "that requires attention."
        ),
        "sections": [
            {
                "type": "trend",
                "title": "Upload Volume Trend",
                "content": (
                    "Monthly upload volume shows a strong upward trajectory through Q1 2026. "
                    "February recorded the peak at **1,823 uploads**, driven by a seasonal content push. "
                    "The slight dip in March to **1,651** is consistent with end-of-quarter patterns.\n\n"
                    "Compared to Q4 2025 averages, every month in Q1 exceeded the baseline by at least **12%**, "
                    "indicating healthy pipeline growth."
                ),
                "chart": {
                    "source_query_index": 0,
                    "chart_type": "line",
                    "x_column": "month",
                    "y_columns": "upload_count",
                    "title": "Monthly Upload Volume",
                },
                "findings": [
                    {"severity": "high", "text": "February peak of 1,823 uploads is 47% above October baseline."},
                    {"severity": "info", "text": "March dip of 9.4% is within normal seasonal variance."},
                ],
            },
            {
                "type": "breakdown",
                "title": "Asset Type Distribution",
                "content": (
                    "Short videos dominate the asset mix at **38.2%** of all generated content, "
                    "followed by long videos at **24.4%**. Image posts account for **18.2%** while "
                    "stories and carousels together make up the remaining **19.2%**.\n\n"
                    "This distribution aligns with the industry shift toward short-form video content, "
                    "though the strong long video presence suggests a healthy mix of formats."
                ),
                "chart": {
                    "source_query_index": 1,
                    "chart_type": "doughnut",
                    "x_column": "asset_type",
                    "y_columns": "count",
                    "title": "Asset Type Breakdown",
                },
                "table": {
                    "source_query_index": 1,
                    "max_rows": 5,
                    "title": "Asset Distribution Details",
                },
                "findings": [
                    {"severity": "medium", "text": "Short video dominance at 38.2% may indicate over-reliance on a single format."},
                    {"severity": "low", "text": "Carousel content at 7.9% could be expanded for engagement diversity."},
                ],
            },
            {
                "type": "comparison",
                "title": "Channel Performance Comparison",
                "content": (
                    "Channel Gamma leads efficiency with an **80% conversion rate** despite lower volume. "
                    "Channel Alpha processes the most content at **3,200 uploads** with a solid **75% conversion**. "
                    "Channel Delta is the clear underperformer with only **50% conversion** on **950 uploads**."
                ),
                "chart": {
                    "source_query_index": 2,
                    "chart_type": "horizontal-bar",
                    "x_column": "channel",
                    "y_columns": "uploads,published",
                    "title": "Uploads vs Published by Channel",
                },
                "table": {
                    "source_query_index": 2,
                    "max_rows": 4,
                    "title": "Channel Metrics",
                },
                "findings": [
                    {"severity": "critical", "text": "Channel Delta's 50% conversion rate is 20+ points below average — investigate content quality or pipeline bottlenecks."},
                    {"severity": "high", "text": "Channel Gamma achieves highest efficiency (80%) with the second-lowest volume — potential for scaling."},
                ],
            },
            {
                "type": "anomaly",
                "title": "Weekly Volume Anomalies",
                "content": (
                    "Week 11 (2026-W11) recorded a **34.4% spike** to 523 uploads, significantly above the "
                    "trailing average. This was followed by a **23.3% drop** in Week 12, suggesting the spike "
                    "was a one-time event rather than a sustained trend.\n\n"
                    "Investigation suggests the spike correlates with a bulk upload campaign by Channel Alpha."
                ),
                "chart": {
                    "source_query_index": 3,
                    "chart_type": "bar",
                    "x_column": "week",
                    "y_columns": "uploads",
                    "title": "Weekly Upload Volume",
                },
                "findings": [
                    {"severity": "high", "text": "Week 11 spike of +34.4% driven by bulk campaign — not organic growth."},
                    {"severity": "medium", "text": "Post-spike correction of -23.3% in Week 12 is expected mean-reversion."},
                ],
            },
        ],
        "conclusions": [
            "The content pipeline is operating at healthy capacity with 18.3% QoQ growth.",
            "Short-form video dominates production but long-form maintains a strong 24.4% share.",
            "Channel Gamma is the most efficient channel and a candidate for volume scaling.",
            "Channel Delta requires immediate attention — 50% conversion is significantly below peers.",
        ],
        "recommendations": [
            "Investigate Channel Delta's low conversion rate — conduct content quality audit and identify pipeline bottlenecks.",
            "Scale Channel Gamma's production volume, leveraging its high 80% conversion efficiency.",
            "Diversify asset formats by increasing carousel and story content to reduce short video over-reliance.",
            "Monitor Week 11-style bulk upload spikes to distinguish organic growth from one-time campaigns.",
            "Set quarterly targets of 2,000+ uploads/month to maintain the upward growth trajectory.",
        ],
        "metadata": {
            "generated_at": "2026-03-21 14:30",
            "caveats": [
                "Analysis covers Q1 2026 (January–March) only.",
                "Conversion rates exclude content still in review pipeline.",
                "Channel Delta data may include test uploads that skew metrics.",
            ],
        },
    }

    output_path = os.path.join(os.path.dirname(__file__), "outputs", "test_report_mock.html")
    save_report_html(mock_report, mock_query_results, output_path)
    print(f"Mock report saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test reports")
    parser.add_argument("--mock", action="store_true", default=True, help="Generate mock data report")
    args = parser.parse_args()

    if args.mock:
        path = test_with_mock_data()
        # Try to open in browser
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(path)}")
