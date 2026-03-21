"""
gemini_client.py
────────────────
Gemini LLM client used for report synthesis.
Uses langchain-google-genai with a single GOOGLE_API_KEY.
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

_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip().strip('"')


def get_gemini_llm():
    """
    Return a ChatGoogleGenerativeAI instance for report synthesis.
    Uses the single GOOGLE_API_KEY from environment.
    """
    if not _GOOGLE_API_KEY:
        logger.warning("No GOOGLE_API_KEY found in environment")
        return None

    model = os.getenv("GEMINI_REPORT_MODEL", "gemini-3-flash-preview").strip().strip('"')

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=_GOOGLE_API_KEY,
            temperature=0.2,
            max_output_tokens=16384,
        )
    except ImportError:
        logger.error("langchain-google-genai not installed")
        return None
    except Exception as exc:
        logger.error("Failed to create Gemini LLM: %s", exc)
        return None
