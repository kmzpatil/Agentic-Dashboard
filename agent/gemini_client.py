"""
gemini_client.py
────────────────
Shared Gemini LLM client for report formatting and synthesis.
Used by both report_agent.py and report_formatter.py.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env")
load_dotenv(_AGENT_DIR.parent / ".env")
load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.0-flash-lite")
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]


def get_gemini_llm(max_output_tokens=8192, temperature=0.3):
    """Create a Gemini LLM instance for report formatting."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = GEMINI_KEYS[0] if GEMINI_KEYS else ""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=temperature,
        google_api_key=api_key,
        max_output_tokens=max_output_tokens,
    )
