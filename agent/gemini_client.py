"""
gemini_client.py
────────────────
Gemini LLM client used exclusively for report synthesis.
Pre-builds a pool of clients (one per API key) and picks randomly each call.
"""

import logging
import os
import random

from dotenv import load_dotenv
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env", override=True)
load_dotenv(_AGENT_DIR.parent / ".env", override=True)
load_dotenv(override=True)

logger = logging.getLogger("frammer.gemini_client")

# Parse keys once at module level
_GEMINI_KEYS = [
    k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()
]

# Lazy-built pool of report LLM clients
_report_pool = []


def _build_report_pool():
    """Build one ChatGoogleGenerativeAI client per API key."""
    global _report_pool
    if _report_pool:
        return

    model = os.getenv("GEMINI_REPORT_MODEL", "gemini-3.1-flash-lite-preview").strip().strip('"')

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        logger.error("langchain-google-genai not installed")
        return

    for key in _GEMINI_KEYS:
        try:
            _report_pool.append(ChatGoogleGenerativeAI(
                model=model,
                google_api_key=key,
                temperature=0.2,
                max_output_tokens=16384,
            ))
        except Exception as exc:
            logger.warning("Failed to create Gemini client for key ...%s: %s", key[-4:], exc)

    if _report_pool:
        logger.info("Gemini report pool created: model=%s, %d clients", model, len(_report_pool))
    else:
        logger.warning("No Gemini report clients could be created")


def get_gemini_llm():
    """
    Return a random Gemini LLM from the pre-built pool.
    Each call picks a different client to spread rate-limit load.
    """
    # Support explicit GOOGLE_API_KEY as single-key override
    api_key = os.getenv("GOOGLE_API_KEY", "").strip().strip('"')
    if api_key:
        model = os.getenv("GEMINI_REPORT_MODEL", "gemini-3.1-flash-lite-preview").strip().strip('"')
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.2,
                max_output_tokens=16384,
            )
        except Exception as exc:
            logger.error("Failed to create Gemini LLM with GOOGLE_API_KEY: %s", exc)
            return None

    _build_report_pool()
    if not _report_pool:
        return None

    client = random.choice(_report_pool)
    logger.info("Gemini report: picked random client from pool of %d", len(_report_pool))
    return client
