"""
gemini_client.py
────────────────
Gemini LLM client used for report synthesis.
Uses google-genai SDK directly with a single GOOGLE_API_KEY.
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

_client = None


def _get_client():
    """Lazy-init the google-genai client."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=_GOOGLE_API_KEY)
    return _client


class _GeminiReportLLM:
    """
    Thin wrapper around google-genai that matches the interface agent.py
    expects: .invoke(prompt) returning an object with .content and .usage_metadata.
    """

    def __init__(self, model: str, temperature: float = 0.2, max_output_tokens: int = 16384):
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def invoke(self, prompt):
        from google.genai import types
        client = _get_client()
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        # Return an object matching what agent.py expects
        class _Response:
            pass

        resp = _Response()
        resp.content = response.text or ""
        resp.usage_metadata = {}
        if response.usage_metadata:
            resp.usage_metadata = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
        return resp


def get_gemini_llm():
    """
    Return a Gemini LLM for report synthesis.
    Uses google-genai SDK directly with GOOGLE_API_KEY.
    """
    if not _GOOGLE_API_KEY:
        logger.warning("No GOOGLE_API_KEY found in environment")
        return None

    model = os.getenv("GEMINI_REPORT_MODEL", "gemini-3-flash-preview").strip().strip('"')

    try:
        return _GeminiReportLLM(model=model, temperature=0.2, max_output_tokens=16384)
    except Exception as exc:
        logger.error("Failed to create Gemini report LLM: %s", exc)
        return None
