"""
report_agent.py
---------------
Report generation agent for Frammer AI.

Two-phase pipeline:
  1. RESEARCH: Reuses the ReAct loop agent (Anthropic Haiku) to gather data.
  2. FORMAT:   One-shot Gemini Flash Lite call to produce structured report JSON.

The output is a structured report dict that the frontend renders as paginated
A4 HTML and exports to PDF via window.print() + CSS @page rules.
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv

_AGENT_DIR = Path(__file__).resolve().parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.append(str(_AGENT_DIR))

load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

logger = logging.getLogger("frammer.report")

# Import from existing agent
try:
    from agent import (
        AgentResult, ChartResult, MAX_ITERATIONS,
        _llm_client, _schema_cache, _extract_response,
        _build_auth_block, _build_system_prompt, _build_messages,
        _load_schema_and_metrics, _execute_query_batch,
        _summarize_query_results, _generate_charts_from_specs,
        execute_queries, answer,
    )
    from client import LLMClient
except ImportError:
    from agent.agent import (
        AgentResult, ChartResult, MAX_ITERATIONS,
        _llm_client, _schema_cache, _extract_response,
        _build_auth_block, _build_system_prompt, _build_messages,
        _load_schema_and_metrics, _execute_query_batch,
        _summarize_query_results, _generate_charts_from_specs,
        execute_queries, answer,
    )
    from agent.client import LLMClient

from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


# ── Gemini Client ────────────────────────────────────────────────────────────

GEMINI_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.0-flash-lite")
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]


def _get_gemini_llm():
    """Create a Gemini LLM instance for report formatting."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = GEMINI_KEYS[0] if GEMINI_KEYS else ""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0.3,
        google_api_key=api_key,
        max_output_tokens=8192,
    )


# ── Report Format Prompt ────────────────────────────────────────────────────

REPORT_FORMAT_PROMPT = """\
You are a report formatting agent for Frammer AI, a media production analytics platform.
Given analysis results, produce a structured JSON report.

## Output Format
Return ONLY a valid JSON object (no markdown fences, no extra text) with this structure:
{{
  "title": "Clear, business-focused report title",
  "executive_summary": "3-4 sentence overview of key findings. Bold key numbers with **double asterisks**.",
  "sections": [
    {{
      "title": "Section heading",
      "content": "Markdown narrative (2-4 paragraphs). **Bold** key numbers. Business language only. Tell a story, don't just list numbers.",
      "chart": {{
        "source_query_index": 0,
        "chart_type": "bar",
        "x_column": "column_name",
        "y_columns": "col1,col2",
        "title": "Chart title"
      }},
      "table": {{
        "source_query_index": 0,
        "max_rows": 10,
        "title": "Table title"
      }}
    }}
  ],
  "recommendations": [
    "Specific, actionable recommendation 1",
    "Specific, actionable recommendation 2"
  ],
  "metadata": {{
    "generated_at": "{timestamp}",
    "caveats": ["Any limitations or assumptions about the data"]
  }}
}}

## Rules
- Business language ONLY. NEVER expose SQL, table names (raw_videos, created_assets, etc.), column names, or internal IDs.
- Translate technical terms: uploads (not raw_videos), generated content/assets (not created_assets), published content (not published_posts), content format (not Input_Type), asset type (not Output_Type).
- Each section should tell a coherent story — don't just dump numbers.
- Include a "chart" object in a section ONLY when the data clearly supports a visualization.
- The "chart.source_query_index" is the 0-based index of the query in the results list.
- Include a "table" object for detailed breakdowns (top-N lists, comparisons).
- Keep executive summary to 3-4 sentences max.
- Recommendations should be actionable, specific, and derived from the data.
- Include 3-5 sections for a comprehensive report.
- If a section doesn't need a chart or table, omit those fields entirely.

## User Question / Report Topic
{question}

## Analysis Data
{results_context}
"""


# ── HTML Report Generator ────────────────────────────────────────────────────

def _is_numeric_str(val) -> bool:
    """Check if a string value looks numeric."""
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        cleaned = val.replace("%", "").replace(",", "").replace("$", "").strip()
        try:
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False
    return False


def _is_numeric_column(data: List[Dict], col: str) -> bool:
    """Check if a column is predominantly numeric."""
    numeric_count = sum(1 for row in data[:10] if _is_numeric_str(row.get(col, "")))
    return numeric_count > len(data[:10]) * 0.5


def _parse_numeric(val) -> float:
    """Parse a value into a float, stripping % and , characters."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace("%", "").replace(",", "").replace("$", "").strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _map_chart_type(report_type: str) -> str:
    """Map report chart type names to Chart.js type strings."""
    mapping = {
        "bar": "bar",
        "stacked-bar": "bar",
        "horizontal-bar": "bar",
        "line": "line",
        "area": "line",
        "pie": "pie",
        "doughnut": "doughnut",
        "polar-area": "polarArea",
        "scatter": "scatter",
        "bubble": "bubble",
        "radar": "radar",
    }
    return mapping.get(report_type, "bar")


def render_report_html(
    report: Dict,
    query_results: Optional[List[Dict]] = None,
) -> str:
    """
    Render a structured report dict as a self-contained A4-paginated HTML file.
    This HTML can be opened in a browser and printed to PDF via Ctrl+P / Cmd+P.
    """
    title = report.get("title", "Frammer AI Report")
    summary = report.get("executive_summary", "")
    sections = report.get("sections", [])
    recommendations = report.get("recommendations", [])
    metadata = report.get("metadata", {})

    # Convert markdown bold (**text**) to HTML <strong>
    def md_to_html(text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Convert markdown lists
        lines = text.split('\n')
        result = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                result.append(f'<li>{md_to_html(stripped[2:])}</li>')
            else:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                if stripped:
                    result.append(f'<p>{stripped}</p>')
        if in_list:
            result.append('</ul>')
        return '\n'.join(result)

    # Build sections HTML and collect chart init data
    sections_html = ""
    chart_inits = []  # JS chart initialization data
    chart_counter = 0

    for i, section in enumerate(sections):
        s_title = section.get("title", f"Section {i + 1}")
        s_content = md_to_html(section.get("content", ""))

        # Table rendering
        table_html = ""
        table_spec = section.get("table")
        if table_spec and query_results:
            idx = table_spec.get("source_query_index", 0)
            max_rows = table_spec.get("max_rows", 10)
            t_title = table_spec.get("title", "")
            if idx < len(query_results) and query_results[idx].get("status") == "success":
                data = query_results[idx].get("data", [])[:max_rows]
                if data:
                    cols = list(data[0].keys())
                    header = ''.join(f'<th>{c.replace("_", " ").title()}</th>' for c in cols)
                    rows = ''.join(
                        '<tr>' + ''.join(f'<td>{row.get(c, "")}</td>' for c in cols) + '</tr>'
                        for row in data
                    )
                    table_html = f"""
                    <div class="report-table avoid-break">
                        {f'<div class="table-title">{t_title}</div>' if t_title else ''}
                        <table>
                            <thead><tr>{header}</tr></thead>
                            <tbody>{rows}</tbody>
                        </table>
                    </div>"""

        # Real chart rendering via Chart.js
        chart_html = ""
        chart_spec = section.get("chart")
        if chart_spec and query_results:
            idx = chart_spec.get("source_query_index", 0)
            if idx < len(query_results) and query_results[idx].get("status") == "success":
                chart_data = query_results[idx].get("data", [])
                if chart_data:
                    canvas_id = f"chart_{chart_counter}"
                    chart_counter += 1
                    c_title = chart_spec.get("title", "Chart")
                    c_type = chart_spec.get("chart_type", "bar")
                    x_col = chart_spec.get("x_column", "")
                    y_cols_raw = chart_spec.get("y_columns", "")
                    y_cols = [c.strip() for c in y_cols_raw.split(",") if c.strip()] if isinstance(y_cols_raw, str) else y_cols_raw

                    # Auto-detect x and y columns if not specified or invalid
                    all_cols = list(chart_data[0].keys()) if chart_data else []
                    if not x_col or x_col not in all_cols:
                        # Pick first non-numeric column as x, or first column
                        for col in all_cols:
                            sample_val = chart_data[0].get(col, "")
                            if isinstance(sample_val, str) and not _is_numeric_str(sample_val):
                                x_col = col
                                break
                        if not x_col:
                            x_col = all_cols[0] if all_cols else ""
                    if not y_cols or not any(yc in all_cols for yc in y_cols):
                        # Pick all numeric columns (excluding x) as y
                        y_cols = [c for c in all_cols if c != x_col and _is_numeric_column(chart_data, c)]
                        if not y_cols:
                            y_cols = [c for c in all_cols if c != x_col][:2]

                    # Build chart init config
                    labels = [str(row.get(x_col, "")) for row in chart_data]
                    datasets_js = []
                    colors = [
                        "rgba(37, 99, 235, 0.85)", "rgba(220, 38, 38, 0.85)",
                        "rgba(22, 163, 74, 0.85)", "rgba(234, 88, 12, 0.85)",
                        "rgba(124, 58, 237, 0.85)", "rgba(14, 165, 233, 0.85)",
                    ]
                    border_colors = [
                        "rgba(37, 99, 235, 1)", "rgba(220, 38, 38, 1)",
                        "rgba(22, 163, 74, 1)", "rgba(234, 88, 12, 1)",
                        "rgba(124, 58, 237, 1)", "rgba(14, 165, 233, 1)",
                    ]

                    for yi, yc in enumerate(y_cols):
                        values = []
                        for row in chart_data:
                            v = row.get(yc, 0)
                            values.append(_parse_numeric(v))
                        datasets_js.append({
                            "label": yc.replace("_", " ").title(),
                            "data": values,
                            "backgroundColor": colors[yi % len(colors)],
                            "borderColor": border_colors[yi % len(border_colors)],
                            "borderWidth": 2,
                            "borderRadius": 4,
                            "fill": c_type == "area",
                        })

                    # Map chart type to Chart.js type
                    chartjs_type = _map_chart_type(c_type)
                    indexAxis = '"y"' if c_type == "horizontal-bar" else '"x"'

                    chart_inits.append({
                        "id": canvas_id,
                        "type": chartjs_type,
                        "labels": labels,
                        "datasets": datasets_js,
                        "title": c_title,
                        "indexAxis": "y" if c_type == "horizontal-bar" else "x",
                        "is_pie": chartjs_type in ("pie", "doughnut", "polarArea"),
                    })

                    chart_html = f"""
                    <div class="report-chart avoid-break">
                        <div class="chart-title">{c_title}</div>
                        <div class="chart-canvas-wrapper">
                            <canvas id="{canvas_id}"></canvas>
                        </div>
                    </div>"""
            else:
                # Query index out of range — show placeholder
                c_title = chart_spec.get("title", "Chart")
                chart_html = f"""
                <div class="report-chart-placeholder avoid-break">
                    <div class="chart-label">{c_title}</div>
                    <div class="chart-type">Data unavailable</div>
                </div>"""

        sections_html += f"""
        <div class="report-section avoid-break">
            <h3>{s_title}</h3>
            <div class="section-content">{s_content}</div>
            {chart_html}
            {table_html}
        </div>"""

    # Recommendations HTML
    recs_html = ""
    if recommendations:
        items = ''.join(f'<li>{r}</li>' for r in recommendations)
        recs_html = f"""
        <div class="report-section avoid-break">
            <h3>Recommendations</h3>
            <ol class="recommendations">{items}</ol>
        </div>"""

    # Metadata / footer
    generated_at = metadata.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    caveats = metadata.get("caveats", [])
    caveats_html = ''.join(f'<li>{c}</li>' for c in caveats) if caveats else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  /* ── Reset & Base ─────────────────────────────────────────── */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a2e;
    background: #f0f0f5;
  }}

  /* ── Print / @page ────────────────────────────────────────── */
  @page {{
    size: A4;
    margin: 18mm 15mm 22mm 15mm;
  }}

  @page :first {{
    margin-top: 12mm;
  }}

  @media print {{
    body {{ background: white; }}
    .no-print {{ display: none !important; }}
    .report-pages {{ box-shadow: none; padding: 0; max-width: none; }}
    .report-page-break {{ page-break-after: always; }}
  }}

  /* ── Page break control ───────────────────────────────────── */
  .avoid-break {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  /* ── Toolbar (screen only) ────────────────────────────────── */
  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: #1a1a2e;
    color: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    font-size: 13px;
  }}

  .toolbar button {{
    background: #2563eb;
    color: white;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }}

  .toolbar button:hover {{ background: #1d4ed8; }}

  /* ── A4 Container ─────────────────────────────────────────── */
  .report-pages {{
    max-width: 210mm;
    margin: 24px auto;
    padding: 20mm 18mm;
    background: white;
    box-shadow: 0 2px 20px rgba(0, 0, 0, 0.08);
    min-height: 297mm;
  }}

  /* ── Letterhead ───────────────────────────────────────────── */
  .letterhead {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2.5px solid #2563eb;
    padding-bottom: 14px;
    margin-bottom: 28px;
  }}

  .letterhead-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .letterhead-logo {{
    width: 32px;
    height: 32px;
    background: #2563eb;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 800;
    font-size: 16px;
  }}

  .letterhead h1 {{
    font-size: 18pt;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.5px;
  }}

  .letterhead-meta {{
    text-align: right;
    font-size: 9pt;
    color: #6b7280;
    line-height: 1.5;
  }}

  /* ── Report Title ─────────────────────────────────────────── */
  .report-title {{
    font-size: 20pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 6px;
    letter-spacing: -0.3px;
    line-height: 1.3;
  }}

  .report-subtitle {{
    font-size: 10pt;
    color: #6b7280;
    margin-bottom: 24px;
    font-style: italic;
  }}

  /* ── Executive Summary ────────────────────────────────────── */
  .executive-summary {{
    background: #f8fafc;
    border-left: 4px solid #2563eb;
    padding: 16px 20px;
    margin-bottom: 32px;
    border-radius: 0 8px 8px 0;
  }}

  .executive-summary h2 {{
    font-size: 10pt;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #2563eb;
    margin-bottom: 8px;
    font-weight: 700;
  }}

  .executive-summary p {{
    font-size: 10.5pt;
    line-height: 1.7;
    color: #374151;
    margin-bottom: 6px;
  }}

  .executive-summary p:last-child {{ margin-bottom: 0; }}

  /* ── Sections ─────────────────────────────────────────────── */
  .report-section {{
    margin-bottom: 28px;
  }}

  .report-section h3 {{
    font-size: 13pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e5e7eb;
  }}

  .section-content p {{
    margin-bottom: 10px;
    line-height: 1.7;
    color: #374151;
  }}

  .section-content p:last-child {{ margin-bottom: 0; }}

  .section-content strong {{ color: #1a1a2e; font-weight: 600; }}

  .section-content ul {{
    margin: 8px 0 12px 20px;
    color: #374151;
  }}

  .section-content ul li {{
    margin-bottom: 4px;
    line-height: 1.6;
  }}

  /* ── Tables ───────────────────────────────────────────────── */
  .report-table {{
    margin: 16px 0;
  }}

  .table-title {{
    font-size: 9.5pt;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
  }}

  thead {{
    background: #f8fafc;
  }}

  th {{
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    color: #374151;
    border-bottom: 2px solid #e5e7eb;
    white-space: nowrap;
  }}

  td {{
    padding: 7px 12px;
    border-bottom: 1px solid #f3f4f6;
    color: #4b5563;
  }}

  tr:last-child td {{ border-bottom: none; }}

  tbody tr:hover {{ background: #fafbfc; }}

  /* ── Chart Placeholder ────────────────────────────────────── */
  .report-chart-placeholder {{
    margin: 16px 0;
    padding: 32px 20px;
    background: #f8fafc;
    border: 1.5px dashed #d1d5db;
    border-radius: 10px;
    text-align: center;
  }}

  .report-chart {{
    margin: 16px 0;
    padding: 16px;
    background: #fafbfc;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
  }}

  .chart-title {{
    font-size: 9.5pt;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 10px;
  }}

  .chart-canvas-wrapper {{
    position: relative;
    width: 100%;
    max-height: 280px;
  }}

  .chart-canvas-wrapper canvas {{
    max-height: 280px;
  }}

  /* Placeholder for unavailable charts */
  .report-chart-placeholder {{
    margin: 16px 0;
    padding: 24px 20px;
    background: #f8fafc;
    border: 1.5px dashed #d1d5db;
    border-radius: 10px;
    text-align: center;
  }}

  .chart-label {{ font-size: 10pt; font-weight: 600; color: #374151; }}
  .chart-type {{ font-size: 8.5pt; color: #9ca3af; margin-top: 2px; }}

  /* ── Recommendations ──────────────────────────────────────── */
  .recommendations {{
    margin: 0;
    padding: 0;
    list-style: none;
    counter-reset: rec;
  }}

  .recommendations li {{
    counter-increment: rec;
    padding: 10px 14px 10px 44px;
    position: relative;
    margin-bottom: 8px;
    background: #f0fdf4;
    border-radius: 8px;
    border: 1px solid #bbf7d0;
    color: #166534;
    line-height: 1.6;
  }}

  .recommendations li::before {{
    content: counter(rec);
    position: absolute;
    left: 12px;
    top: 10px;
    width: 22px;
    height: 22px;
    background: #22c55e;
    color: white;
    border-radius: 50%;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  /* ── Footer ───────────────────────────────────────────────── */
  .report-footer {{
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #e5e7eb;
    font-size: 8.5pt;
    color: #9ca3af;
  }}

  .report-footer .generated {{ margin-bottom: 6px; }}

  .caveats {{
    margin-top: 8px;
    padding: 10px 14px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 6px;
    font-size: 8.5pt;
    color: #92400e;
  }}

  .caveats ul {{ margin: 4px 0 0 16px; }}
  .caveats li {{ margin-bottom: 2px; }}
</style>
</head>
<body>

<!-- Toolbar (hidden when printing) -->
<div class="toolbar no-print">
  <span>Frammer AI Report — Preview</span>
  <button onclick="window.print()">⬇ Export PDF</button>
</div>

<!-- A4 Report Content -->
<div class="report-pages">

  <!-- Letterhead -->
  <div class="letterhead avoid-break">
    <div class="letterhead-brand">
      <div class="letterhead-logo">F</div>
      <h1>Frammer AI</h1>
    </div>
    <div class="letterhead-meta">
      Analytics Report<br>
      {generated_at}
    </div>
  </div>

  <!-- Title -->
  <div class="report-title">{title}</div>
  <div class="report-subtitle">Auto-generated analytics report</div>

  <!-- Executive Summary -->
  <div class="executive-summary avoid-break">
    <h2>Executive Summary</h2>
    {md_to_html(summary)}
  </div>

  <!-- Sections -->
  {sections_html}

  <!-- Recommendations -->
  {recs_html}

  <!-- Footer -->
  <div class="report-footer avoid-break">
    <div class="generated">Generated by Frammer AI on {generated_at}</div>
    {f'<div class="caveats"><strong>Note:</strong><ul>{caveats_html}</ul></div>' if caveats_html else ''}
  </div>

</div>

<!-- Chart.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>

<script>
// Initialize all charts
document.addEventListener('DOMContentLoaded', function() {{
  const chartConfigs = {json.dumps(chart_inits, default=str)};

  chartConfigs.forEach(function(cfg) {{
    const ctx = document.getElementById(cfg.id);
    if (!ctx) return;

    const isPie = cfg.is_pie;
    const options = {{
      responsive: true,
      maintainAspectRatio: true,
      indexAxis: cfg.indexAxis || 'x',
      plugins: {{
        legend: {{
          display: cfg.datasets.length > 1 || isPie,
          position: isPie ? 'right' : 'top',
          labels: {{ font: {{ size: 10, family: "'Inter', sans-serif" }}, padding: 12 }}
        }},
        title: {{ display: false }},
        tooltip: {{
          backgroundColor: 'rgba(26, 26, 46, 0.92)',
          titleFont: {{ size: 11 }},
          bodyFont: {{ size: 11 }},
          padding: 10,
          cornerRadius: 6,
        }}
      }},
      scales: isPie ? {{}} : {{
        x: {{
          grid: {{ display: false }},
          ticks: {{ font: {{ size: 9 }}, maxRotation: 45 }}
        }},
        y: {{
          beginAtZero: true,
          grid: {{ color: 'rgba(0,0,0,0.05)' }},
          ticks: {{ font: {{ size: 9 }} }}
        }}
      }},
      animation: {{ duration: 0 }}  // Instant render for print
    }};

    // Pie/doughnut need backgroundColor as array
    if (isPie && cfg.datasets.length > 0) {{
      const colors = [
        'rgba(37, 99, 235, 0.85)', 'rgba(220, 38, 38, 0.85)',
        'rgba(22, 163, 74, 0.85)', 'rgba(234, 88, 12, 0.85)',
        'rgba(124, 58, 237, 0.85)', 'rgba(14, 165, 233, 0.85)',
        'rgba(245, 158, 11, 0.85)', 'rgba(236, 72, 153, 0.85)',
      ];
      cfg.datasets[0].backgroundColor = cfg.labels.map(function(_, i) {{
        return colors[i % colors.length];
      }});
      cfg.datasets[0].borderWidth = 2;
      cfg.datasets[0].borderColor = 'white';
    }}

    new Chart(ctx, {{
      type: cfg.type,
      data: {{
        labels: cfg.labels,
        datasets: cfg.datasets
      }},
      options: options
    }});
  }});
}});
</script>

</body>
</html>"""


# ── Report Agent: Research + Format Pipeline ─────────────────────────────────

async def run_report_agent(
    question: str,
    auth: Optional[Any] = None,
    working_memory: str = "",
    history: Optional[List[Dict]] = None,
) -> AgentResult:
    """
    Run the report agent pipeline:
      1. Research: ReAct loop gathers data (same as normal agent)
      2. Format: Gemini Flash Lite formats into structured report
      3. Return: AgentResult with report dict
    """
    logger.info("=== REPORT AGENT START ===")
    overall_start = time.time()
    actions_log: List[str] = []

    try:
        # Phase 1: Research (reuse the ReAct loop)
        schema, metrics = _load_schema_and_metrics()
        agent_llm = _llm_client.llm.bind_tools([execute_queries, answer])

        all_query_results: List[Dict] = []
        all_full_data: List[Dict] = []
        last_sql = ""

        for iteration in range(MAX_ITERATIONS):
            system = _build_system_prompt(schema, metrics, auth, working_memory, all_query_results)
            # Override the prompt to emphasize thorough data gathering for reports
            system = system.replace(
                "You may iterate up to",
                "You are gathering data for a comprehensive report. Be thorough — query for multiple angles. You may iterate up to"
            )
            messages = _build_messages(system, question, history)

            logger.info("=== REPORT RESEARCH ITERATION %d ===", iteration + 1)
            actions_log.append(f"Researching (round {iteration + 1})...")
            resp = await asyncio.to_thread(agent_llm.invoke, messages)

            tool_calls = getattr(resp, "tool_calls", [])
            if not tool_calls:
                # Conversational — shouldn't happen in report mode, but handle it
                return AgentResult(
                    intent="conversational",
                    response=_extract_response(resp.content),
                    actions=actions_log,
                    mode="report",
                )

            tc = tool_calls[0]
            tool_name = tc.get("name", "")
            args = tc.get("args", {})

            if tool_name == "execute_queries":
                queries = args.get("queries", [])
                reasoning = args.get("reasoning", "")
                actions_log.append(f"Executing {len(queries)} queries — {reasoning[:80]}")

                batch_results = await _execute_query_batch(queries, auth=auth)
                for result in batch_results:
                    all_query_results.append(result)
                    all_full_data.append(result)
                    if result.get("status") == "success":
                        last_sql = result.get("sql", "")
                        actions_log.append(f"SQL OK — {result.get('row_count', 0)} rows ({result.get('description', '')})")
                    else:
                        actions_log.append(f"SQL Error — {result.get('error', '')[:60]}")
                continue

            elif tool_name == "answer":
                # Agent decided it has enough data — move to formatting
                break

        # Phase 2: Format with Gemini
        actions_log.append("Formatting report with Gemini...")
        logger.info("=== REPORT FORMATTING (Gemini) ===")

        results_context = _summarize_query_results(all_query_results)
        format_prompt = REPORT_FORMAT_PROMPT.format(
            question=question,
            results_context=results_context,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        gemini_llm = _get_gemini_llm()
        fmt_resp = await asyncio.to_thread(gemini_llm.invoke, format_prompt)

        # Extract text content — Gemini may return a list of content blocks
        raw_content = ""
        if hasattr(fmt_resp, 'content'):
            content = fmt_resp.content
            if isinstance(content, list):
                # Multi-part response: join text parts
                raw_content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            elif isinstance(content, str):
                raw_content = content
            else:
                raw_content = str(content)
        else:
            raw_content = str(fmt_resp)

        # Strip markdown fences if present
        raw_content = re.sub(r'^```(?:json)?\s*\n?', '', raw_content.strip(), flags=re.IGNORECASE)
        raw_content = re.sub(r'\n?```\s*$', '', raw_content).strip()

        try:
            report_json = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logger.error("Gemini returned invalid JSON: %s", e)
            report_json = {
                "title": "Analysis Report",
                "executive_summary": raw_content[:500],
                "sections": [],
                "recommendations": [],
                "metadata": {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "caveats": ["Report formatting failed — showing raw summary"]},
            }

        # Generate charts for sections that reference them
        for section in report_json.get("sections", []):
            if section.get("chart"):
                chart_specs = [section["chart"]]
                charts = await _generate_charts_from_specs(chart_specs, all_full_data)
                if charts:
                    section["chart_xml"] = charts[0].chart_xml
                    section["chart_data"] = charts[0].data_records

        actions_log.append("Report formatted successfully")

        total_time = time.time() - overall_start
        logger.info("=== REPORT AGENT COMPLETE (%.2fs) ===", total_time)

        # Attach query results to report so HTML renderer can build charts/tables
        report_json["_query_results"] = all_query_results

        # Log chart specs for debugging
        for si, section in enumerate(report_json.get("sections", [])):
            has_chart = "chart" in section and section["chart"]
            has_table = "table" in section and section["table"]
            logger.info("Section %d [%s]: chart=%s table=%s", si, section.get("title", "?"), has_chart, has_table)

        return AgentResult(
            intent="report",
            mode="report",
            response=report_json.get("executive_summary", ""),
            report=report_json,
            actions=actions_log,
            sql=last_sql,
        )

    except Exception as exc:
        logger.error("!!! Report Agent Error: %s !!!", exc, exc_info=True)
        return AgentResult(
            intent="report",
            mode="report",
            response=f"Report generation failed: {exc}",
            error=str(exc),
            actions=actions_log,
        )


# ── Convenience: Generate HTML file from report ─────────────────────────────

def save_report_html(report: Dict, query_results: List[Dict], output_path: str = "report_output.html") -> str:
    """Generate and save the report as an HTML file. Returns the file path."""
    html = render_report_html(report, query_results)
    path = Path(output_path)
    path.write_text(html, encoding="utf-8")
    logger.info("Report saved to %s", path.resolve())
    return str(path.resolve())
