"""
report_formatter.py
-------------------
Pure utility module for report formatting and HTML rendering.
No agent loop, no LangChain tools — just formatting functions.

Used by the unified agent when mode="report":
  1. _get_gemini_llm() — Creates Gemini client for report formatting
  2. REPORT_FORMAT_PROMPT — Prompt template for structured report JSON
  3. render_report_html() — Renders report dict as self-contained A4 HTML
  4. save_report_html() — Convenience wrapper to write HTML to disk
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

logger = logging.getLogger("frammer.report_formatter")


# ── Gemini Client ────────────────────────────────────────────────────────────

try:
    from gemini_client import get_gemini_llm as _get_gemini_llm
except ImportError:
    from agent.gemini_client import get_gemini_llm as _get_gemini_llm


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


# ── HTML Helpers ─────────────────────────────────────────────────────────────

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


def md_to_html(text: str) -> str:
    """Convert basic markdown (bold, lists) to HTML."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
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


# ── HTML Report Renderer ────────────────────────────────────────────────────

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
                        for col in all_cols:
                            sample_val = chart_data[0].get(col, "")
                            if isinstance(sample_val, str) and not _is_numeric_str(sample_val):
                                x_col = col
                                break
                        if not x_col:
                            x_col = all_cols[0] if all_cols else ""
                    if not y_cols or not any(yc in all_cols for yc in y_cols):
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

                    chartjs_type = _map_chart_type(c_type)

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

  /* ── Charts ────────────────────────────────────────────────── */
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
  <button onclick="window.print()">Export PDF</button>
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


def save_report_html(report: Dict, query_results: List[Dict], output_path: str = "report_output.html") -> str:
    """Generate and save the report as an HTML file. Returns the file path."""
    html = render_report_html(report, query_results)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Report saved to %s", output_path)
    return output_path
