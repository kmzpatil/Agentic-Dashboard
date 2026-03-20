"""
client.py
---------
LLM client abstraction using Anthropic Claude 3 Haiku.

Features:
  - Single API usage (Anthropic)
  - Exponential backoff retry on 429 rate-limit errors
  - Factory modes: fast(), thinking(), creative()
"""

import json
import logging
import os
import re
import time
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

try:
    from gemini_keys import get_next_gemini_key
except ImportError:
    def get_next_gemini_key(): return os.getenv("GOOGLE_API_KEY", "")

logger = logging.getLogger("frammer.client")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

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
    Unified LLM client backed by Anthropic Claude 3 Haiku.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0,
        preserve_thinking: bool = False,
        provider: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.preserve_thinking = preserve_thinking
        
        # Auto-detect provider if not specified
        if not provider:
            if "claude" in model.lower():
                provider = "anthropic"
            elif "gemini" in model.lower():
                provider = "google"
            else:
                provider = "anthropic" # Default
        
        self.provider = provider
            
        if provider == "anthropic":
            if ChatAnthropic is None:
                raise ImportError("langchain-anthropic is not installed.")
            api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            self.llm = ChatAnthropic(
                model_name=self.model,
                temperature=self.temperature,
                api_key=api_key,
                max_tokens=4096,
                max_retries=0, # Let LLMClient handle it
            )
        elif provider == "google":
            if ChatGoogleGenerativeAI is None:
                raise ImportError("langchain-google-genai is not installed.")
            
            # Using rotation list if possible
            api_key = get_next_gemini_key() or os.getenv("GOOGLE_API_KEY", "").strip()
            
            self.llm = ChatGoogleGenerativeAI(
                model=self.model,
                temperature=self.temperature,
                google_api_key=api_key,
                max_output_tokens=4096,
                max_retries=0, # Let LLMClient handle it
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    # ── Factory helpers ──────────────────────────────────────────────────────

    @classmethod
    def fast(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Deterministic routing / structured output mode."""
        return cls(model=model, temperature=0, preserve_thinking=False)

    @classmethod
    def thinking(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Conversational mode (Haiku does not really use reasoning tags, but keeping signature)."""
        return cls(model=model, temperature=0, preserve_thinking=True)

    @classmethod
    def creative(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Conversational / insight generation mode."""
        return cls(model=model, temperature=0.7, preserve_thinking=False)

    @classmethod
    def reporter(cls) -> "LLMClient":
        """Gemini Flash mode for the final report synthesis."""
        model = os.getenv("GEMINI_REPORT_MODEL", "gemini-3.1-flash-lite-preview")
        return cls(model=model, temperature=0, provider="google")

    # ── Core invoke ──────────────────────────────────────────────────────────

    def invoke(self, prompt: str, *, label: str = "llm") -> LLMResponse:
        """
        Call the LLM with exponential backoff on 429 rate-limit errors.
        """
        max_attempts = 20
        start_time = time.time()

        for attempt in range(max_attempts):
            logger.info("[%s] Calling %s (model: %s, attempt %d)...", label, self.provider.title(), self.model, attempt + 1)

            try:
                result = self.llm.invoke(prompt)
                duration = time.time() - start_time
                usage = getattr(result, "usage_metadata", {})
                
                logger.info(
                    "[%s] %s responded in %.2fs. Usage: %s",
                    label, self.provider.title(), duration, json.dumps(usage) if usage else "N/A"
                )
                return self._parse(result.content, label=label, usage=usage)

            except Exception as exc:
                if self._is_rate_limit(exc) and attempt < max_attempts - 1:
                    # Specific rotation for Google if we hit a wall
                    if self.provider == "google":
                        new_key = get_next_gemini_key()
                        logger.warning("[%s] !!! GEMINI RATE LIMIT !!! Rotating to new key and retrying...", label)
                        self.llm = ChatGoogleGenerativeAI(
                            model=self.model,
                            temperature=self.temperature,
                            google_api_key=new_key,
                            max_output_tokens=4096,
                            max_retries=0,
                        )
                        continue # Retry immediately with new key
                    
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

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _parse(self, raw: Any, *, label: str, usage: Optional[dict] = None) -> LLMResponse:
        if isinstance(raw, list):
            # Handle multimodal/list content parts
            raw = "".join(str(part.get("text", part) if isinstance(part, dict) else part) for part in raw)
        
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
        return any(kw in msg for kw in ("429", "rate limit", "too many requests", "rate_limit_exceeded"))

    def __repr__(self) -> str:
        mode = "thinking" if self.preserve_thinking else "fast"
        return f"LLMClient(model:{self.model}, t={self.temperature}, {mode})"
