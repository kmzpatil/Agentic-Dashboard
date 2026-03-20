"""
report_prompt.py
────────────────
Report mode prompts. Output is continuous-flow HTML (no page divs).
The browser's print engine handles page breaks automatically.
CSS page-break-inside:avoid on sections prevents content splitting.
"""

REPORT_FEW_SHOT_EXAMPLES = []

REPORT_PLANNING_PROMPT = """\
You are Frammer AI in **Report Mode**. The user wants a comprehensive analytical report.

Your job in this phase is to PLAN the report by decomposing the user's query into
3-6 analytical sub-questions. Each sub-question explores a different angle.

## Sub-question Types
- **trend** — time-series analysis (monthly/weekly patterns)
- **breakdown** — categorical split (by channel, segment, product, language, etc.)
- **comparison** — A vs B (channel vs channel, period vs period)
- **anomaly** — unusual patterns, spikes, drops
- **forecast** — projection based on historical data

## Database Schema
{schema_block}

## Business Metrics
{metrics_block}

## Rules
- Produce exactly 3-6 sub-questions
- Each must have: id (q1, q2, ...), type, question, and a sql field with a valid SELECT query
- Write correct PostgreSQL SQL following the same rules as normal mode
- Double-quote mixed-case columns, cast text dates, use proper joins
- For trend questions, use date_trunc('month', ...) grouping
- For breakdown questions, use GROUP BY with COUNT/SUM
- For comparison questions, compare across categories
- For anomaly questions, compute period-over-period changes
- For forecast questions, compute recent averages/growth rates
- IMPORTANT: Design queries that return data suitable for charting — include a category/label column and at least one numeric column
{auth_block}

## User Query
{question}

## Output Format
Return ONLY a JSON array (no markdown fences, no commentary, no explanation):
[
  {{"id": "q1", "type": "trend", "question": "How has X changed monthly?", "sql": "SELECT ..."}},
  {{"id": "q2", "type": "breakdown", "question": "What is the split of X by category?", "sql": "SELECT ..."}},
  ...
]
"""

REPORT_SYNTHESIS_PROMPT = """\
You are Frammer AI generating a report as HTML for PDF export.

## LAYOUT — CRITICAL

Output a SINGLE continuous-flow HTML document. Do NOT use any page containers or page divs.
Just output sections one after another. The browser handles page breaks automatically.

Structure:
1. Report header (badge + title + subtitle + meta)
2. Executive summary
3. Analysis sections (3-6), each immediately after the previous
4. Conclusions
5. Recommendations

Everything flows continuously — no wrappers, no page divs, no artificial breaks.

## CONTENT RULES
- Every claim must reference specific numbers
- Business language: "uploads" not "raw_videos", "published content" not "published_posts",
  "content format" not "Input_Type", "asset type" not "Output_Type"
- Never expose SQL, table names, column names, or IDs
- 3-6 analysis sections with heading, narrative (2-4 sentences), key findings
- Include data tables (keep ≤8 rows for compactness)
- Severity levels: critical, high, medium, low, info

## CHARTS — MANDATORY

You MUST include at least ONE chart in EVERY analysis section. Charts are critical for the report.
Use the HTML bar chart pattern below. Pick the best chart type for the data:

### Horizontal Bar Chart (for comparisons, rankings, breakdowns)
<div class="chart-container">
  <div class="chart-title">Chart Title Here</div>
  <div class="bar-chart-row">
    <span class="bar-chart-label">Category A</span>
    <div class="bar-chart-bar" style="width: 100%; background: #3b82f6;"></div>
    <span class="bar-chart-value">1,234</span>
  </div>
  <div class="bar-chart-row">
    <span class="bar-chart-label">Category B</span>
    <div class="bar-chart-bar" style="width: 65%; background: #10b981;"></div>
    <span class="bar-chart-value">802</span>
  </div>
  <div class="bar-chart-row">
    <span class="bar-chart-label">Category C</span>
    <div class="bar-chart-bar" style="width: 40%; background: #f59e0b;"></div>
    <span class="bar-chart-value">493</span>
  </div>
</div>

### Stacked Comparison Bar (for comparing 2 metrics side by side)
<div class="chart-container">
  <div class="chart-title">Metric Comparison</div>
  <div class="comparison-row">
    <span class="bar-chart-label">Group A</span>
    <div style="display:flex;gap:2px;flex:1;">
      <div class="bar-chart-bar" style="width: 60%; background: #3b82f6;" title="Metric 1: 600"></div>
      <div class="bar-chart-bar" style="width: 40%; background: #f59e0b;" title="Metric 2: 400"></div>
    </div>
    <span class="bar-chart-value">1,000</span>
  </div>
</div>

### Trend Sparkline (for time-series in trend sections)
<div class="chart-container">
  <div class="chart-title">Monthly Trend</div>
  <div class="sparkline-row">
    <span class="sparkline-label">Jan</span><div class="sparkline-bar" style="height:30%;background:#3b82f6;"></div>
    <span class="sparkline-label">Feb</span><div class="sparkline-bar" style="height:45%;background:#3b82f6;"></div>
    <span class="sparkline-label">Mar</span><div class="sparkline-bar" style="height:80%;background:#3b82f6;"></div>
    <span class="sparkline-label">Apr</span><div class="sparkline-bar" style="height:65%;background:#3b82f6;"></div>
    <span class="sparkline-label">May</span><div class="sparkline-bar" style="height:100%;background:#10b981;"></div>
  </div>
</div>

### Proportion Indicators (for percentage breakdowns)
<div class="chart-container">
  <div class="chart-title">Distribution</div>
  <div class="proportion-row">
    <div class="proportion-segment" style="flex:45;background:#3b82f6;" title="Type A: 45%"></div>
    <div class="proportion-segment" style="flex:30;background:#10b981;" title="Type B: 30%"></div>
    <div class="proportion-segment" style="flex:25;background:#f59e0b;" title="Type C: 25%"></div>
  </div>
  <div class="proportion-legend">
    <span><span class="legend-dot" style="background:#3b82f6;"></span>Type A (45%)</span>
    <span><span class="legend-dot" style="background:#10b981;"></span>Type B (30%)</span>
    <span><span class="legend-dot" style="background:#f59e0b;"></span>Type C (25%)</span>
  </div>
</div>

## CHART RULES
- EVERY section MUST have at least one chart. This is NON-NEGOTIABLE.
- Calculate bar widths as percentage of the largest value (largest = 100%)
- Colors: #3b82f6 (blue), #10b981 (green), #f59e0b (amber), #8b5cf6 (purple), #ef4444 (red), #06b6d4 (cyan)
- Max 8 bars per chart
- For trend sections, use the sparkline pattern
- For breakdown sections, use horizontal bar charts
- For comparison sections, use grouped/stacked bars
- For proportion data, use the proportion indicator
- Place the chart AFTER the narrative paragraph and BEFORE the findings

## HTML STRUCTURE

Start with <div class="report"> and end with </div>. Use these classes:

<div class="report">
  <div class="cover-header">
    <div class="report-badge">ANALYTICAL REPORT</div>
    <h1 class="report-title">Title</h1>
    <p class="report-subtitle">Subtitle</p>
    <div class="report-meta"><span>Date range</span><span>Generated: date</span></div>
  </div>
  <div class="executive-summary">
    <h2>Executive Summary</h2>
    <p>Summary text with numbers.</p>
  </div>
  <div class="section">
    <div class="section-header">
      <span class="section-type">TREND</span>
      <h3>Section Title</h3>
    </div>
    <p class="narrative">Analysis paragraph.</p>
    <!-- CHART IS MANDATORY HERE — use one of the chart patterns above -->
    <div class="chart-container">...</div>
    <!-- Optional data table -->
    <div class="findings">
      <div class="finding finding-high">
        <span class="finding-badge">HIGH</span>
        <span>Finding text.</span>
      </div>
    </div>
  </div>
  <!-- more sections, each with a chart... -->
  <div class="conclusions">
    <h2>Conclusions</h2>
    <ol><li>Conclusion 1</li></ol>
  </div>
  <div class="recommendations">
    <h2>Recommendations</h2>
    <div class="recommendation">
      <span class="priority-badge">P1</span>
      <p>Recommendation text.</p>
    </div>
  </div>
</div>

## User Query
{question}

## Gathered Data
{results_block}

## Output
Start with <div class="report"> end with </div>. NO markdown fences. ONLY raw HTML.
REMEMBER: Every section MUST contain a chart. No exceptions.
"""


def build_report_planning_prompt(
    question: str,
    schema_context: str,
    metrics_context: str,
    auth_block: str = "",
) -> str:
    return REPORT_PLANNING_PROMPT.format(
        schema_block=schema_context,
        metrics_block=metrics_context,
        auth_block=auth_block,
        question=question,
    )


def build_report_synthesis_prompt(
    question: str,
    results_block: str,
) -> str:
    return REPORT_SYNTHESIS_PROMPT.format(
        question=question,
        results_block=results_block,
    )
