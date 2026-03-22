"""
parser.py
---------
Converts user input (formula or natural language) into a KPI DSL JSON.

DSL JSON schema:
{
  "type": "single_metric" | "formula",
  "metric": "<metric_name>",          # only for single_metric
  "formula": "<arithmetic_expr>",     # only for formula
  "operands": ["metric1", "metric2"], # metrics used in the formula
  "time_granularity": "day" | "week" | "month",
  "filters": []
}

Formula mode:
  - Parses a user-supplied arithmetic expression referencing known metric names
  - Detects which metric atoms are used
  - Returns DSL with type="single_metric" if only one atom and no arithmetic,
    or type="formula" if multiple atoms / arithmetic is involved

Natural-language mode:
  - Calls Claude (Anthropic) to convert the NL description → DSL JSON
  - LLM is ONLY used here at creation time; execution is always deterministic
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from backend.kpi.validator import FORMULA_ATOMS, SINGLE_METRICS, ALL_KNOWN_METRICS

logger = logging.getLogger("frammer.kpi.parser")

# Arithmetic operators and parentheses
_ARITHMETIC_CHARS = set("+-*/() \t\n\r")

# Tokenizer: splits a formula into metric-name tokens and non-metric tokens
_METRIC_RE = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in sorted(ALL_KNOWN_METRICS, key=len, reverse=True)) + r")\b"
)

_NL_SYSTEM_PROMPT = """\
You are a KPI formula assistant for a video content analytics platform. You are part of ATLAS, the AI analytics engine.
Convert the user's natural language description into a JSON DSL. Respond with ONLY valid JSON, no explanations.

--- DATABASE SCHEMA ---
The platform tracks a 3-stage video pipeline:

Stage 1 – Uploaded (Raw_Video table)
  Raw_Video: Video_ID (PK), User_ID (FK→User), Headline, Source_URL, Upload_Date,
             Input_Type, Language, Uploaded_Duration (total runtime in seconds)
  Raw_Video_Channel: Video_ID (FK), Channel_Name (FK)  ← many-to-many junction

Stage 2 – Created (Created_Asset table)
  Created_Asset: Asset_ID (PK), Video_ID (FK→Raw_Video), Output_Type, Create_Date,
                 Created_Duration (total runtime in seconds)

Stage 3 – Published (Published_Post + Post_Distribution tables)
  Published_Post:    Post_ID (PK), Asset_ID (FK→Created_Asset), Publish_Date,
                     Published_Duration (total runtime in seconds)
  Post_Distribution: Post_ID (FK), Channel_Name (FK), Published_Platform, Published_URL

Supporting tables:
  User:    User_ID (PK), User_Name, Team_Name, Client_Name (FK→Client)
  Channel: Channel_Name (PK), Client_Name (FK→Client)
  Client:  Client_Name (PK)

--- METRIC ATOMS (composable in arithmetic formulas) ---
- uploaded_count       : COUNT of Raw_Video rows (how many raw videos were uploaded)
- created_count        : COUNT of Created_Asset rows (how many clip assets were edited/created)
- published_count      : COUNT of Published_Post rows (how many posts went live)
- uploaded_duration    : SUM of Raw_Video.Uploaded_Duration in seconds (total raw footage length)
- created_duration     : SUM of Created_Asset.Created_Duration in seconds (total edited clip length)
- published_duration   : SUM of Published_Post.Published_Duration in seconds (total published content length)

Mapping natural language to atoms:
  "raw videos / footage uploaded / source content"  → uploaded_count / uploaded_duration
  "clips / edited assets / created content"         → created_count / created_duration
  "published posts / live posts / published content"→ published_count / published_duration
  "hours" or "duration"                             → *_duration atoms
  "number / count / how many"                       → *_count atoms

--- PRE-BUILT SINGLE METRICS (use as-is, do NOT combine in formulas) ---
- publish_conversion_rate  : published_count / created_count * 100  (% of clips that get published)
- creation_rate            : created_count / uploaded_count * 100   (% of uploads that become clips)
- processing_efficiency    : published_duration / created_duration * 100 (% of created duration that goes live)
- waste_index              : avg created duration minus avg published duration (content trimmed away)

--- OUTPUT FORMAT (choose ONE type) ---

Single metric (one of the 10 known metrics used standalone):
{"type": "single_metric", "metric": "<metric_name>", "time_granularity": "month", "filters": []}

Formula (arithmetic expression using metric atoms):
{"type": "formula", "formula": "<expr using atom names>", "operands": ["atom1", "atom2"], "time_granularity": "month", "filters": []}

--- RULES ---
- Use "month" as time_granularity unless the user explicitly says day or week
- filters is always []
- For ratios/rates, prefer pre-built single metrics when they exactly match
- For custom arithmetic, build a formula using atom names only (not table/column names)
- The formula field must be a valid arithmetic expression using only atom names and operators +-*/()
- operands must list every atom name that appears in the formula
- NEVER output SQL, table names, column names, or anything other than the JSON structure above
- If the request cannot be mapped to available metrics, pick the closest match and output valid JSON
"""


def parse_formula_mode(expression: str, time_granularity: str = "month") -> dict[str, Any]:
    """
    Parse a formula expression into a DSL JSON.

    Supports:
      - A single known metric name  → type="single_metric"
      - Arithmetic combining metric atoms → type="formula"
    """
    expr = expression.strip()

    # Direct single-metric shorthand
    if expr in ALL_KNOWN_METRICS:
        return {
            "type": "single_metric",
            "metric": expr,
            "time_granularity": time_granularity,
            "filters": [],
        }

    # Detect metric atoms present in the formula
    found = _detect_operands(expr)
    if not found:
        raise ValueError(
            f"No known metric names found in expression '{expr}'. "
            f"Supported atoms: {sorted(FORMULA_ATOMS)}. "
            f"Single metrics: {sorted(SINGLE_METRICS)}."
        )

    # If only one atom and no arithmetic operators → treat as single_metric
    if len(found) == 1 and not _has_arithmetic(expr, list(found)[0]):
        metric = list(found)[0]
        return {
            "type": "single_metric",
            "metric": metric,
            "time_granularity": time_granularity,
            "filters": [],
        }

    # Check that all found atoms are formula-composable
    non_composable = found - FORMULA_ATOMS
    if non_composable:
        raise ValueError(
            f"Metrics {sorted(non_composable)} cannot be combined in a formula. "
            "They are pre-built derived metrics. Use them as standalone 'single_metric' KPIs."
        )

    return {
        "type": "formula",
        "formula": expr,
        "operands": sorted(found),
        "time_granularity": time_granularity,
        "filters": [],
    }


def parse_nl_mode(expression: str, time_granularity: str = "month") -> dict[str, Any]:
    """
    Convert a natural language KPI description to DSL JSON using the LLM.
    LLM is called ONLY here (creation time), never at execution time.
    """
    prompt = (
        f"{_NL_SYSTEM_PROMPT}\n\n"
        f"User request: \"{expression}\"\n"
        f"Preferred time_granularity: \"{time_granularity}\"\n"
        "Output JSON:"
    )

    raw = _call_llm(prompt)
    return _extract_json(raw)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_operands(expr: str) -> set[str]:
    """Return the set of known metric atom names found in the expression."""
    return set(_METRIC_RE.findall(expr))


def _has_arithmetic(expr: str, metric: str) -> bool:
    """True if the expression is more than just the bare metric name."""
    stripped = expr.replace(metric, "").strip()
    return bool(stripped)


def _call_llm(prompt: str) -> str:
    """
    Call the Gemini API to convert NL → DSL JSON.
    Raises ValueError if the API key is missing or the call fails.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip().strip('"')
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. "
            "Natural-language KPI creation requires a valid Google API key."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=512,
            ),
        )
        return response.text or ""

    except Exception as exc:
        logger.error("LLM call for NL KPI parsing failed: %s", exc)
        raise ValueError(f"LLM call failed: {exc}") from exc


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from the LLM response text."""
    # Try direct parse
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response: {text[:200]}")
