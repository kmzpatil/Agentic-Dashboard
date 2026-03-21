"""
client.py
---------
LLM client wrapping the native Google GenAI Python SDK.

Features:
  - Single Gemini provider via GOOGLE_API_KEY
  - Sync and async invocation (simple prompts + tool-calling)
  - Exponential backoff retry on 429 rate-limit errors
  - Factory modes: fast(), thinking(), creative()
"""

import json
import logging
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

logger = logging.getLogger("frammer.client")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip().strip('"')


class LLMResponse:
    """Structured response from an LLM call."""
    def __init__(self, content: str, thinking: Optional[str] = None, raw: str = "", usage: Optional[dict] = None):
        self.content = content
        self.thinking = thinking
        self.raw = raw
        self.usage = usage or {}


class LLMClient:
    """
    LLM client using the native Google GenAI SDK.
    Single GOOGLE_API_KEY for Gemini — no LangChain, no Anthropic.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0,
        preserve_thinking: bool = False,
    ):
        self.model = model or DEFAULT_GEMINI_MODEL
        self.temperature = temperature
        self.preserve_thinking = preserve_thinking

        if not _GOOGLE_API_KEY:
            raise ValueError("No GOOGLE_API_KEY found in environment")

        self._client = genai.Client(api_key=_GOOGLE_API_KEY)
        logger.info("Gemini client created: model=%s, temp=%.1f", self.model, self.temperature)

    # ── Factory helpers ──────────────────────────────────────────────────────

    @classmethod
    def fast(cls, model: Optional[str] = None) -> "LLMClient":
        """Deterministic routing / structured output mode."""
        return cls(model=model, temperature=0, preserve_thinking=False)

    @classmethod
    def thinking(cls, model: Optional[str] = None) -> "LLMClient":
        """Mode with reasoning trace preserved."""
        return cls(model=model, temperature=0, preserve_thinking=True)

    @classmethod
    def creative(cls, model: Optional[str] = None) -> "LLMClient":
        """Conversational / insight generation mode."""
        return cls(model=model, temperature=0.7, preserve_thinking=False)

    # ── Sync invoke (simple string prompt, no tools) ─────────────────────────

    def invoke(self, prompt: str, *, label: str = "llm") -> LLMResponse:
        """
        Call the LLM synchronously with exponential backoff on 429 errors.
        Used by memory.py for compaction and title generation.
        """
        max_attempts = 5
        start_time = time.time()

        for attempt in range(max_attempts):
            logger.info("[%s] Calling Gemini (model: %s, attempt %d)...", label, self.model, attempt + 1)

            try:
                result = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        max_output_tokens=8192,
                    ),
                )
                duration = time.time() - start_time
                usage = {}
                if result.usage_metadata:
                    usage = {
                        "input_tokens": getattr(result.usage_metadata, "prompt_token_count", 0),
                        "output_tokens": getattr(result.usage_metadata, "candidates_token_count", 0),
                    }

                logger.info(
                    "[%s] Gemini responded in %.2fs. Usage: %s",
                    label, duration, json.dumps(usage) if usage else "N/A"
                )
                return self._parse(result.text or "", usage=usage)

            except Exception as exc:
                exc_msg = str(exc)
                exc_lower = exc_msg.lower()

                if "free_tier" in exc_lower or "freetier" in exc_lower:
                    logger.error(
                        "[%s] FREE TIER QUOTA HIT — your GOOGLE_API_KEY is on the free tier "
                        "(limit: 20 requests/day). Enable billing at https://ai.dev/rate-limit",
                        label,
                    )
                    raise RuntimeError(
                        f"Gemini free-tier quota exceeded. Your API key is being treated as "
                        f"free tier (20 req/day). Verify billing at "
                        f"https://aistudio.google.com/apikey"
                    ) from exc

                if self._is_rate_limit(exc) and attempt < max_attempts - 1:
                    wait = 5 * (2 ** attempt)
                    logger.warning(
                        "[%s] !!! RATE LIMIT (429) !!! Retrying in %ds (Attempt %d/%d).",
                        label, wait, attempt + 1, max_attempts - 1,
                    )
                    time.sleep(wait)
                    continue

                duration = time.time() - start_time
                logger.error(
                    "[%s] !!! LLM CALL FAILED !!!\n  Model    : %s\n  Duration : %.2fs\n  Error    : %s",
                    label, self.model, duration, exc,
                )
                raise

        raise RuntimeError(f"[{label}] Max LLM retries exceeded")

    # ── Async invoke (simple string prompt, no tools) ────────────────────────

    async def ainvoke(self, prompt: str, *, label: str = "llm"):
        """
        Call the LLM asynchronously. Returns the raw genai response.
        Used by _force_synthesize, _synthesize_report, conversational fast-path.
        """
        return await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=8192,
            ),
        )

    # ── Async invoke with tools (for ReAct loop) ────────────────────────────

    async def ainvoke_with_tools(self, contents, config: types.GenerateContentConfig):
        """
        Call the LLM asynchronously with tool definitions.
        Returns the raw genai response for the agent loop to parse.
        """
        return await self._client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _parse(self, raw, *, usage: Optional[dict] = None) -> LLMResponse:
        if isinstance(raw, list):
            raw = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw
            ).strip()
        if not isinstance(raw, str):
            raw = str(raw)
        thinking = None
        match = _THINK_RE.search(raw)
        if match and self.preserve_thinking:
            thinking = match.group(1).strip()
        content = _THINK_RE.sub("", raw).strip()
        return LLMResponse(content=content, thinking=thinking, raw=raw, usage=usage)

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(kw in msg for kw in ("429", "rate limit", "too many requests", "rate_limit_exceeded", "resource_exhausted"))

    def __repr__(self) -> str:
        mode = "thinking" if self.preserve_thinking else "fast"
        return f"LLMClient(model:{self.model}, t={self.temperature}, {mode})"
