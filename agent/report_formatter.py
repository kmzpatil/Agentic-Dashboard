"""
report_formatter.py
-------------------
Pure rendering module for deterministic HTML report generation.
Takes a structured JSON report dict + actual query results →
produces a self-contained A4-ready HTML document with Chart.js.

No LLM calls, no agent logic — just formatting functions.

Used by the unified agent when mode="report":
  1. render_report_html(report, query_results) — Renders report dict as self-contained A4 HTML
  2. save_report_html(report, query_results, path) — Convenience wrapper to write HTML to disk
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("frammer.report_formatter")


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
    title = report.get("title", "ATLAS Report")
    summary = report.get("executive_summary", "")
    sections = report.get("sections", [])
    recommendations = report.get("recommendations", [])
    if isinstance(recommendations, str):
        recommendations = [recommendations]
    metadata = report.get("metadata", {})
    conclusions = report.get("conclusions", [])
    if isinstance(conclusions, str):
        conclusions = [conclusions]

    generated_at = metadata.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    caveats = metadata.get("caveats", [])
    if isinstance(caveats, str):
        caveats = [caveats]

    # Build sections HTML and collect chart init data
    sections_html = ""
    chart_inits = []  # JS chart initialization data
    chart_counter = 0

    for i, section in enumerate(sections):
        s_title = section.get("title", f"Section {i + 1}")
        s_type = section.get("type", "").upper()
        s_content = md_to_html(section.get("content", ""))

        # Section type badge
        type_badge = f'<span class="section-type">{s_type}</span>' if s_type else ''

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
        <table class="data-table">
          <thead><tr>{header}</tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

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
        <div class="chart-container">
          <div class="chart-title">{c_title}</div>
          <div class="chart-canvas-wrapper">
            <canvas id="{canvas_id}"></canvas>
          </div>
        </div>"""

        # Findings
        findings_html = ""
        findings = section.get("findings", [])
        if findings:
            items = []
            for f in findings:
                sev = f.get("severity", "info").lower()
                text = f.get("text", str(f) if isinstance(f, str) else "")
                if isinstance(f, str):
                    text = f
                    sev = "info"
                items.append(
                    f'<div class="finding finding-{sev}">'
                    f'<span class="finding-badge">{sev.upper()}</span>'
                    f'<span>{text}</span></div>'
                )
            findings_html = f'<div class="findings">{"".join(items)}</div>'

        sections_html += f"""
      <div class="section">
        <div class="section-header">
          {type_badge}
          <h3>{s_title}</h3>
        </div>
        <p class="narrative">{s_content}</p>
        {chart_html}
        {table_html}
        {findings_html}
      </div>"""

    # Conclusions HTML
    conclusions_html = ""
    if conclusions:
        items = ''.join(f'<li>{c}</li>' for c in conclusions)
        conclusions_html = f"""
      <div class="conclusions">
        <h2>Conclusions</h2>
        <ol>{items}</ol>
      </div>"""

    # Recommendations HTML
    recs_html = ""
    if recommendations:
        items = []
        for idx, r in enumerate(recommendations):
            items.append(
                f'<div class="recommendation">'
                f'<span class="priority-badge">P{idx + 1}</span>'
                f'<p>{r}</p></div>'
            )
        recs_html = f"""
      <div class="recommendations">
        <h2>Recommendations</h2>
        {"".join(items)}
      </div>"""

    # Caveats footer
    caveats_html = ""
    if caveats:
        caveats_items = ''.join(f'<li>{c}</li>' for c in caveats)
        caveats_html = f"""
      <div class="caveats">
        <strong>Note:</strong>
        <ul>{caveats_items}</ul>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  /* ── Reset & Base ── */
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #1a1a1a; background: #fff;
    font-size: 16px; line-height: 1.6;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    margin: 0; padding: 0;
  }}
  @page {{ size: A4; margin: 18mm 16mm 16mm 16mm; }}

  /* ── Page header / letterhead ── */
  .report-page-header {{
    display: flex; align-items: center; gap: 10px;
    padding: 0 0 8px 0;
    border-bottom: 2px solid #ef4444;
    background: #fff;
    height: 36px;
  }}
  @media screen {{
    .report-page-header {{
      position: sticky; top: 0; z-index: 50;
      padding: 8px 16px;
    }}
  }}
  @media print {{
    /* Don't use position:fixed — it overlaps content on page breaks.
       The header shows once at the top; the @page top margin keeps
       subsequent pages clear. */
    .report-page-header {{
      position: static;
    }}
  }}
  .report-page-header .logo {{ font-size: 18px; font-weight: 800; color: #ef4444; letter-spacing: -0.02em; }}
  .report-page-header .divider {{ width: 1px; height: 16px; background: #d1d5db; }}
  .report-page-header .label {{ font-size: 11px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: #9ca3af; }}

  /* ── Report content ── */
  .report {{ padding: 24px 48px 48px 48px; max-width: 900px; margin: 0 auto; }}
  .report::after {{ content: ''; display: block; height: 10px; }}

  /* ── Page break control ── */
  .avoid-break {{ page-break-inside: avoid; break-inside: avoid; }}

  /* ── Cover ── */
  .cover-header {{ padding: 12px 0 16px 0; margin-bottom: 10px; }}
  .report-badge {{
    display: inline-block; font-size: 11px; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: #dc2626; background: #fef2f2;
    padding: 4px 12px; border-radius: 8px; margin-bottom: 10px;
  }}
  .report-title {{ font-size: 32px; font-weight: 800; color: #111; margin: 0 0 6px 0; line-height: 1.2; }}
  .report-subtitle {{ font-size: 18px; color: #6b7280; margin: 0 0 10px 0; }}
  .report-meta {{ display: flex; gap: 18px; font-size: 14px; color: #9ca3af; }}

  /* ── Executive Summary ── */
  .executive-summary {{
    background: #f0f7ff; border: 1px solid #dbeafe;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;
    page-break-inside: avoid;
  }}
  .executive-summary h2 {{
    font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.14em; color: #2563eb; margin: 0 0 10px 0;
  }}
  .executive-summary p {{ font-size: 16px; color: #374151; margin: 0 0 8px 0; line-height: 1.6; }}
  .executive-summary p:last-child {{ margin-bottom: 0; }}

  /* ── Sections ── */
  .section {{
    margin-bottom: 14px; padding-bottom: 10px;
    border-bottom: 1px solid #e5e7eb;
  }}
  .section:last-of-type {{ border-bottom: none; }}
  .section-header {{
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 8px; padding-bottom: 6px;
    border-bottom: 2px solid #e5e7eb;
    page-break-inside: avoid; page-break-after: avoid;
  }}
  .section-type {{
    font-size: 10px; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #6b7280; background: #f3f4f6;
    padding: 3px 10px; border-radius: 4px;
  }}
  .section-header h3 {{ font-size: 22px; font-weight: 700; color: #111827; margin: 0; }}
  .narrative {{ font-size: 15px; color: #374151; margin: 0 0 10px 0; line-height: 1.65; }}
  .narrative p {{ margin: 0 0 10px 0; }}
  .narrative p:last-child {{ margin-bottom: 0; }}
  .narrative strong {{ color: #111; font-weight: 600; }}
  .narrative ul {{ margin: 6px 0 10px 20px; }}
  .narrative li {{ margin-bottom: 4px; }}

  /* ── Tables ── */
  .data-table {{
    width: 100%; border-collapse: collapse; font-size: 14px;
    margin: 14px 0; page-break-inside: avoid;
  }}
  .data-table thead {{ background: #f9fafb; }}
  .data-table th {{
    text-align: left; padding: 8px 12px; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #6b7280; border-bottom: 2px solid #d1d5db;
  }}
  .data-table td {{
    padding: 8px 12px; color: #374151;
    border-bottom: 1px solid #f3f4f6;
    font-variant-numeric: tabular-nums;
  }}

  /* ── Charts (Chart.js canvas) ── */
  .chart-container {{
    margin: 10px 0; padding: 12px 14px;
    background: #fafbfc; border: 1px solid #f0f0f0; border-radius: 8px;
    page-break-inside: avoid;
    overflow: hidden;
  }}
  .chart-title {{ font-size: 14px; font-weight: 700; color: #374151; margin-bottom: 8px; }}
  .chart-canvas-wrapper {{
    position: relative; width: 100%; height: 280px;
  }}
  .chart-canvas-wrapper canvas {{
    position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important;
  }}

  /* ── Findings ── */
  .findings {{ display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }}
  .finding {{
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 10px; border-radius: 6px; font-size: 14px;
    page-break-inside: avoid;
  }}
  .finding-badge {{
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    padding: 2px 8px; border-radius: 3px; white-space: nowrap;
    flex-shrink: 0; margin-top: 2px;
  }}
  .finding-critical {{ background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }}
  .finding-critical .finding-badge {{ background: #fee2e2; color: #dc2626; }}
  .finding-high {{ background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; }}
  .finding-high .finding-badge {{ background: #ffedd5; color: #ea580c; }}
  .finding-medium {{ background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }}
  .finding-medium .finding-badge {{ background: #fef3c7; color: #d97706; }}
  .finding-low {{ background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }}
  .finding-low .finding-badge {{ background: #dbeafe; color: #2563eb; }}
  .finding-info {{ background: #f9fafb; border: 1px solid #e5e7eb; color: #374151; }}
  .finding-info .finding-badge {{ background: #f3f4f6; color: #6b7280; }}

  /* ── Conclusions ── */
  .conclusions, .recommendations {{ margin-bottom: 14px; page-break-inside: avoid; }}
  .conclusions h2, .recommendations h2 {{
    font-size: 20px; font-weight: 700;
    color: #111827; margin: 0 0 12px 0;
    padding-bottom: 8px; border-bottom: 2px solid #e5e7eb;
  }}
  .conclusions ol {{ margin: 0; padding-left: 20px; }}
  .conclusions li {{ font-size: 15px; color: #374151; margin-bottom: 8px; line-height: 1.6; }}

  /* ── Recommendations ── */
  .recommendation {{
    display: flex; align-items: flex-start; gap: 12px;
    padding: 12px 16px; background: #f9fafb; border: 1px solid #e5e7eb;
    border-radius: 8px; margin-bottom: 8px; page-break-inside: avoid;
  }}
  .priority-badge {{
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 6px;
    background: #fef3c7; color: #b45309;
    font-size: 12px; font-weight: 700; flex-shrink: 0;
  }}
  .recommendation p {{ font-size: 15px; color: #374151; margin: 0; line-height: 1.6; }}

  /* ── Caveats ── */
  .caveats {{
    margin-top: 20px; padding: 14px 18px;
    background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 6px; font-size: 13px; color: #92400e;
  }}
  .caveats ul {{ margin: 6px 0 0 18px; }}
  .caveats li {{ margin-bottom: 4px; }}

  /* ── Screen-only toolbar ── */
  @media screen {{
    .screen-toolbar {{
      position: sticky; top: 0; z-index: 100;
      background: #111; color: white;
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 24px; font-size: 15px;
    }}
    .screen-toolbar button {{
      background: #ef4444; color: white; border: none;
      padding: 8px 20px; border-radius: 6px;
      font-size: 14px; font-weight: 600; cursor: pointer;
    }}
    .screen-toolbar button:hover {{ background: #dc2626; }}
  }}
  @media print {{
    .screen-toolbar {{ display: none !important; }}
  }}
</style>
</head>
<body>

<!-- Screen-only toolbar -->
<div class="screen-toolbar">
  <span>ATLAS — Report Preview</span>
</div>

<!-- Fixed header (repeats on every printed page) -->
<div class="report-page-header">
  <span class="logo">ATLAS</span>
  <span class="divider"></span>
  <span class="label">Analytics Report</span>
</div>

<!-- Report content -->
<div class="report">

  <!-- Cover -->
  <div class="cover-header">
    <div class="report-badge">ANALYTICAL REPORT</div>
    <h1 class="report-title">{title}</h1>
    <p class="report-subtitle">Auto-generated analytics report</p>
    <div class="report-meta">
      <span>Generated: {generated_at}</span>
    </div>
  </div>

  <!-- Executive Summary -->
  <div class="executive-summary">
    <h2>Executive Summary</h2>
    {md_to_html(summary)}
  </div>

  <!-- Analysis Sections -->
  {sections_html}

  <!-- Conclusions -->
  {conclusions_html}

  <!-- Recommendations -->
  {recs_html}

  <!-- Caveats -->
  {caveats_html}

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
      maintainAspectRatio: false,
      indexAxis: cfg.indexAxis || 'x',
      plugins: {{
        legend: {{
          display: cfg.datasets.length > 1 || isPie,
          position: isPie ? 'right' : 'top',
          labels: {{ font: {{ size: 13, family: "-apple-system, 'Segoe UI', Roboto, sans-serif" }}, padding: 12 }}
        }},
        title: {{ display: false }},
        tooltip: {{
          backgroundColor: 'rgba(17, 17, 17, 0.92)',
          titleFont: {{ size: 13 }},
          bodyFont: {{ size: 13 }},
          padding: 10,
          cornerRadius: 4,
        }}
      }},
      scales: isPie ? {{}} : {{
        x: {{
          grid: {{ display: false }},
          ticks: {{ font: {{ size: 12 }}, maxRotation: 45 }}
        }},
        y: {{
          beginAtZero: true,
          grid: {{ color: 'rgba(0,0,0,0.04)' }},
          ticks: {{ font: {{ size: 12 }} }}
        }}
      }},
      animation: {{ duration: 0 }}
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
      data: {{ labels: cfg.labels, datasets: cfg.datasets }},
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
