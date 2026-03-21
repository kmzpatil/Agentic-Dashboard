"""
client.py
---------
LLM client abstraction supporting Anthropic and Gemini providers.

Gemini uses the google-genai SDK directly (single GOOGLE_API_KEY).
A langchain-compatible wrapper is exposed via .langchain_llm for
agent.py's tool-calling loop (bind_tools).

Features:
  - Dual provider support (Anthropic Claude / Google Gemini)
  - Single Gemini client via google-genai SDK
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

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


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

    Gemini calls go through google-genai SDK directly.
    For langchain tool-calling compatibility (bind_tools), use .langchain_llm.
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
        if genai is None:
            raise ImportError("google-genai is not installed.")
        if not _GOOGLE_API_KEY:
            raise ValueError("No GOOGLE_API_KEY found in environment")
        self._genai_client = genai.Client(api_key=_GOOGLE_API_KEY)
        self._langchain_llm = None  # lazy
        logger.info("Gemini client created: model=%s, temp=%.1f", self.model, self.temperature)

    def _init_anthropic(self):
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed.")
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            logger.warning("No ANTHROPIC_API_KEY found in environment!")
        self._anthropic_llm = ChatAnthropic(
            model_name=self.model,
            temperature=self.temperature,
            api_key=api_key,
            max_tokens=4096,
        )

    @property
    def llm(self):
        """
        Return a langchain-compatible LLM object.
        For Gemini: lazily creates a ChatGoogleGenerativeAI wrapper.
        For Anthropic: returns the ChatAnthropic instance.
        Used by agent.py for bind_tools() and direct .invoke() calls.
        """
        if self.provider == "gemini":
            if self._langchain_llm is None:
                if ChatGoogleGenerativeAI is None:
                    raise ImportError("langchain-google-genai is not installed.")
                self._langchain_llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=_GOOGLE_API_KEY,
                    temperature=self.temperature,
                    max_output_tokens=8192,
                )
            return self._langchain_llm
        return self._anthropic_llm

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
        Gemini calls use google-genai SDK directly.
        """
        max_attempts = 5
        start_time = time.time()

        for attempt in range(max_attempts):
            logger.info("[%s] Calling %s (model: %s, attempt %d)...", label, self.provider, self.model, attempt + 1)

            try:
                if self.provider == "gemini":
                    result = self._invoke_gemini(prompt)
                else:
                    result = self._invoke_anthropic(prompt)

                duration = time.time() - start_time
                logger.info(
                    "[%s] %s responded in %.2fs. Usage: %s",
                    label, self.provider, duration,
                    json.dumps(result.usage) if result.usage else "N/A",
                )
                return result

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

    def _invoke_gemini(self, prompt: str) -> LLMResponse:
        """Call Gemini via google-genai SDK."""
        config = genai_types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=8192,
        )
        response = self._genai_client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        usage = {}
        if response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
        return self._parse(response.text or "", usage=usage)

    def _invoke_anthropic(self, prompt: str) -> LLMResponse:
        """Call Anthropic via langchain."""
        result = self._anthropic_llm.invoke(prompt)
        usage = getattr(result, "usage_metadata", {})
        return self._parse(result.content, usage=usage)

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
        return f"LLMClient(provider:{self.provider}, model:{self.model}, t={self.temperature}, {mode})"
