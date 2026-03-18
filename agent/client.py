"""
client.py
---------
LLM client abstraction using Anthropic Claude 3 Haiku.

Features:
  - Single API usage (Anthropic)
  - Exponential backoff retry on 429 rate-limit errors
  - Factory modes: fast(), thinking(), creative()
"""

import logging
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from logger_setup import setup_logging
setup_logging()
logger = logging.getLogger("frammer.client")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None


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
    ):
        self.model = model
        self.temperature = temperature
        self.preserve_thinking = preserve_thinking
        
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed.")
            
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            logger.warning("No ANTHROPIC_API_KEY found in environment!")
            
        self.llm = ChatAnthropic(
            model_name=self.model,
            temperature=self.temperature,
            api_key=api_key,
            max_tokens=4096,  # Prevent SQL/tool call truncation
        )

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

    # ── Core invoke ──────────────────────────────────────────────────────────

    def invoke(self, prompt: str, *, label: str = "llm") -> LLMResponse:
        """
        Call the LLM with exponential backoff on 429 rate-limit errors.
        """
        max_attempts = 5
        start_time = time.time()

        for attempt in range(max_attempts):
            logger.info("[%s] Calling Anthropic (model: %s, attempt %d)...", label, self.model, attempt + 1)

            try:
                result = self.llm.invoke(prompt)
                duration = time.time() - start_time
                usage = getattr(result, "usage_metadata", {})
                
                logger.info(
                    "[%s] Anthropic responded in %.2fs. Usage: %s",
                    label, duration, json.dumps(usage) if usage else "N/A"
                )
                return self._parse(result.content, label=label, usage=usage)

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
                    "[%s] !!! LLM CALL FAILED !!!\n  Model    : %s\n  Duration : %.2fs\n  Error    : %s",
                    label, self.model, duration, exc,
                )
                raise

        raise RuntimeError(f"[{label}] Max LLM retries exceeded")

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _parse(self, raw: str, *, label: str, usage: Optional[dict] = None) -> LLMResponse:
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
        return f"LLMClient(azure:{self._model}, t={self._temperature}, {mode})"
