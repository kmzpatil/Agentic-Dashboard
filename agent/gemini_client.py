"""
gemini_client.py
────────────────
Gemini LLM client used exclusively for report synthesis.
"""

import logging
import os

from dotenv import load_dotenv
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env", override=True)
load_dotenv(_AGENT_DIR.parent / ".env", override=True)
load_dotenv(override=True)

logger = logging.getLogger("frammer.gemini_client")


def get_gemini_llm():
    """
    Create a fresh Gemini LLM instance every time.
    No caching — avoids stale model name issues.
    """
    # Support both GOOGLE_API_KEY and GEMINI_KEYS (comma-separated, use first)
    api_key = os.getenv("GOOGLE_API_KEY", "").strip().strip('"')
    if not api_key:
        gemini_keys = os.getenv("GEMINI_KEYS", "").strip()
        if gemini_keys:
            api_key = gemini_keys.split(",")[0].strip()
    if not api_key:
        logger.warning("GOOGLE_API_KEY / GEMINI_KEYS not set — Gemini unavailable")
        return None

    model = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-flash").strip().strip('"')

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=16384,
        )
        logger.info("Gemini LLM created: model=%s", model)
        return llm

    except ImportError:
        logger.error("langchain-google-genai not installed")
        return None
    except Exception as exc:
        logger.error("Failed to create Gemini LLM: %s", exc)
        return None
