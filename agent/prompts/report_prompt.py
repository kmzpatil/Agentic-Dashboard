"""
report_prompt.py
────────────────
System prompt, few-shot examples, and XML schema reference for
the Detailed Report Mode.

The report mode uses a three-phase workflow:
  1. Planning  — decompose the query into 3-6 analytical sub-questions
  2. Gathering — execute SQL for each sub-question, collect results
  3. Synthesis — combine all findings into a single XML <report> document
"""

# ── XML Schema Reference ────────────────────────────────────────────────────

REPORT_XML_SCHEMA_REFERENCE = """\
<?xml version="1.0" encoding="UTF-8"?>
<report>
  <metadata>
    <title>Report Title</title>
    <subtitle>Optional subtitle</subtitle>
    <date_range>e.g. 2024-01-01 to 2024-12-31</date_range>
    <original_query>The user's original question</original_query>
    <generated_at>ISO timestamp</generated_at>
  </metadata>

  <executive_summary>
    2-4 sentences summarizing the key takeaway. Every claim references specific numbers.
  </executive_summary>

  <sections>
    <!-- 3-6 sections, each with: -->
    <section type="trend|breakdown|comparison|anomaly|forecast">
      <heading>Section Title</heading>
      <narrative>2-4 sentence analysis paragraph. Data-driven, precise.</narrative>

      <!-- Optional chart using existing chart_config format -->
      <chart_config>
        <chart_type>line|bar|pie|stacked-bar|horizontal-bar|area|doughnut</chart_type>
        <title>Chart Title</title>
        <x_column>field_name</x_column>
        <y_columns>field1,field2</y_columns>
      </chart_config>

      <!-- Optional data table -->
      <data_table>
        <columns>
          <col name="Display Name" field="field_name" format="currency|percent|number|text"/>
        </columns>
        <rows>
          <row field_name="value" other_field="value"/>
        </rows>
      </data_table>

      <key_findings>
        <finding severity="critical|high|medium|low|info">Finding text</finding>
      </key_findings>
    </section>
  </sections>

  <conclusions>
    <conclusion>Actionable conclusion 1</conclusion>
    <conclusion>Actionable conclusion 2</conclusion>
  </conclusions>

  <recommendations>
    <recommendation priority="1">Highest priority recommendation</recommendation>
    <recommendation priority="2">Second priority recommendation</recommendation>
  </recommendations>
</report>
"""

# ── Few-Shot Examples ────────────────────────────────────────────────────────

REPORT_FEW_SHOT_EXAMPLES = [
    {
        "query": "How is our content pipeline performing?",
        "plan": [
            {"id": "q1", "type": "trend", "question": "What is the monthly upload volume trend over the past 12 months?"},
            {"id": "q2", "type": "breakdown", "question": "How are uploads distributed across content formats (Input_Type)?"},
            {"id": "q3", "type": "comparison", "question": "How does the upload-to-publish conversion rate compare across channels?"},
            {"id": "q4", "type": "anomaly", "question": "Are there any months with unusual spikes or drops in upload volume?"},
        ],
    },
    {
        "query": "Give me a full analysis of our publishing performance",
        "plan": [
            {"id": "q1", "type": "trend", "question": "What is the monthly trend of published posts over the last year?"},
            {"id": "q2", "type": "breakdown", "question": "Which platforms receive the most published content?"},
            {"id": "q3", "type": "comparison", "question": "How does publishing volume compare across the top 5 channels?"},
            {"id": "q4", "type": "breakdown", "question": "What asset types (Output_Type) are most commonly published?"},
            {"id": "q5", "type": "forecast", "question": "Based on the 6-month trend, what is the projected publishing volume for the next quarter?"},
        ],
    },
    {
        "query": "Analyze channel efficiency across our platform",
        "plan": [
            {"id": "q1", "type": "breakdown", "question": "What is each channel's total upload volume and asset generation count?"},
            {"id": "q2", "type": "comparison", "question": "Which channels have the highest and lowest upload-to-asset conversion rates?"},
            {"id": "q3", "type": "trend", "question": "How has channel activity (uploads) changed month over month for the top 5 channels?"},
            {"id": "q4", "type": "anomaly", "question": "Are any channels showing a significant decline or growth in the last 3 months vs prior 3 months?"},
        ],
    },
]

# ── Phase Prompts ────────────────────────────────────────────────────────────

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
{auth_block}

## User Query
{question}

## Output Format
You MUST call the `create_report_plan` tool with your plan.
"""

REPORT_SYNTHESIS_PROMPT = """\
You are Frammer AI in **Report Mode — Synthesis Phase**.

You have gathered data from multiple SQL queries. Now produce a single XML report document.

## Rules
- Output ONLY valid XML matching the schema below. No markdown, no explanation outside the XML.
- Every claim must reference specific numbers from the data.
- Use business language: "uploads" not "raw_videos", "published content" not "published_posts",
  "content format" not "Input_Type", "asset type" not "Output_Type".
- Never expose SQL, table names, column names, or internal IDs.
- Include 3-6 sections. Each section needs: heading, narrative (2-4 sentences), and key_findings.
- Include chart_config for sections that benefit from visualization.
- Include data_table for sections with tabular results.
- Severity levels: critical, high, medium, low, info.
- For chart_config: use chart_type (line, bar, pie, stacked-bar, horizontal-bar, area, doughnut),
  title, x_column, y_columns. The data will be attached separately.
- For data_table: use col elements with name (display), field (data key), format (currency|percent|number|text).
  Include row elements with field="value" attributes.

## XML Schema
{xml_schema}

## User Query
{question}

## Gathered Data
{results_block}

## Output
Produce the complete XML report now. Start with <?xml version="1.0" encoding="UTF-8"?>
"""


def build_report_planning_prompt(
    question: str,
    schema_context: str,
    metrics_context: str,
    auth_block: str = "",
) -> str:
    """Assemble the full planning prompt for report mode."""
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
    """Assemble the full synthesis prompt for report mode."""
    return REPORT_SYNTHESIS_PROMPT.format(
        xml_schema=REPORT_XML_SCHEMA_REFERENCE,
        question=question,
        results_block=results_block,
    )
