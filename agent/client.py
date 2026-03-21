"""
client.py
---------
LLM client abstraction supporting Anthropic and Gemini providers.

Features:
  - Dual provider support (Anthropic Claude / Google Gemini)
  - Single Gemini client via GOOGLE_API_KEY (langchain-google-genai)
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

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

logger = logging.getLogger("frammer.client")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic").strip().lower()
DEFAULT_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# Single Gemini API key
_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip().strip('"')

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None


class LLMResponse:
    """Structured response from an LLM call."""
    def __init__(self, content: str, thinking: Optional[str] = None, raw: str = "", usage: Optional[dict] = None):
        self.content = content
        self.thinking = thinking
        self.raw = raw
        self.usage = usage or {}


class LLMClient:
    """
    Unified LLM client supporting Anthropic and Gemini providers.
    Provider is selected via AI_PROVIDER env var (default: anthropic).
    Single GOOGLE_API_KEY for Gemini via langchain-google-genai.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0,
        preserve_thinking: bool = False,
    ):
        self.provider = (provider or AI_PROVIDER).strip().lower()
        self.temperature = temperature
        self.preserve_thinking = preserve_thinking

        if self.provider == "gemini":
            self.model = model or DEFAULT_GEMINI_MODEL
            self._init_gemini()
        else:
            self.model = model or DEFAULT_ANTHROPIC_MODEL
            self._init_anthropic()

    def _init_gemini(self):
        if ChatGoogleGenerativeAI is None:
            raise ImportError("langchain-google-genai is not installed.")
        if not _GOOGLE_API_KEY:
            raise ValueError("No GOOGLE_API_KEY found in environment")
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=_GOOGLE_API_KEY,
            temperature=self.temperature,
            max_output_tokens=8192,
        )
        logger.info("Gemini client created: model=%s, temp=%.1f", self.model, self.temperature)

    def _init_anthropic(self):
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed.")
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            logger.warning("No ANTHROPIC_API_KEY found in environment!")
        self.llm = ChatAnthropic(
            model_name=self.model,
            temperature=self.temperature,
            api_key=api_key,
            max_tokens=4096,
        )

    # ── Factory helpers ──────────────────────────────────────────────────────

    @classmethod
    def fast(cls, provider: Optional[str] = None, model: Optional[str] = None) -> "LLMClient":
        """Deterministic routing / structured output mode."""
        return cls(provider=provider, model=model, temperature=0, preserve_thinking=False)

    @classmethod
    def thinking(cls, provider: Optional[str] = None, model: Optional[str] = None) -> "LLMClient":
        """Mode with reasoning trace preserved."""
        return cls(provider=provider, model=model, temperature=0, preserve_thinking=True)

    @classmethod
    def creative(cls, provider: Optional[str] = None, model: Optional[str] = None) -> "LLMClient":
        """Conversational / insight generation mode."""
        return cls(provider=provider, model=model, temperature=0.7, preserve_thinking=False)

    # ── Core invoke ──────────────────────────────────────────────────────────

    def invoke(self, prompt: str, *, label: str = "llm") -> LLMResponse:
        """
        Call the LLM with exponential backoff on 429 rate-limit errors.
        """
        max_attempts = 5
        start_time = time.time()

        for attempt in range(max_attempts):
            logger.info("[%s] Calling %s (model: %s, attempt %d)...", label, self.provider, self.model, attempt + 1)

            try:
                result = self.llm.invoke(prompt)
                duration = time.time() - start_time
                usage = getattr(result, "usage_metadata", {})

                logger.info(
                    "[%s] %s responded in %.2fs. Usage: %s",
                    label, self.provider, duration, json.dumps(usage) if usage else "N/A"
                )
                return self._parse(result.content, usage=usage)

            except Exception as exc:
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
                    "[%s] !!! LLM CALL FAILED !!!\n  Provider : %s\n  Model    : %s\n  Duration : %.2fs\n  Error    : %s",
                    label, self.provider, self.model, duration, exc,
                )
                raise

        raise RuntimeError(f"[{label}] Max LLM retries exceeded")

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _parse(self, raw, *, usage: Optional[dict] = None) -> LLMResponse:
        # Gemini returns content as a list of blocks; normalise to string
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
        return f"LLMClient(provider:{self.provider}, model:{self.model}, t={self.temperature}, {mode})"
