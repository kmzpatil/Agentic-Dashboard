"""
client.py
---------
Single LLM client abstraction for the Frammer AI agent.

Wraps ChatGroq with:
  - Automatic 429 rate-limit retry with exponential backoff
  - Qwen3 <think>…</think> tag handling (strip or preserve)
  - Two factory modes: fast() and thinking()
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from langchain_groq import ChatGroq

logger = logging.getLogger("frammer.client")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

DEFAULT_MODEL = "qwen/qwen3-32b"


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""
    content: str                        # cleaned output (thinking tags stripped)
    thinking: Optional[str] = None      # raw thinking block when preserve_thinking=True
    raw: str = ""                       # unprocessed LLM output


class LLMClient:
    """
    Unified LLM client. All agent code should use this instead of
    instantiating ChatGroq directly.

    Parameters
    ----------
    model : str
        Groq model identifier.
    temperature : float
        Sampling temperature.
    preserve_thinking : bool
        If True, <think> blocks are extracted and returned in
        LLMResponse.thinking rather than discarded.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0,
        preserve_thinking: bool = False,
    ):
        self.llm = ChatGroq(model=model, temperature=temperature)
        self.preserve_thinking = preserve_thinking
        self._model = model
        self._temperature = temperature

    # ── Factory helpers ──────────────────────────────────────────────────────

    @classmethod
    def fast(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Deterministic, no-thinking mode for routing and structured output."""
        return cls(model=model, temperature=0, preserve_thinking=False)

    @classmethod
    def thinking(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Preserves the model's <think> reasoning for display in the UI."""
        return cls(model=model, temperature=0, preserve_thinking=True)

    @classmethod
    def creative(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Higher temperature for conversational / insight generation."""
        return cls(model=model, temperature=0.5, preserve_thinking=False)

    # ── Core invoke ──────────────────────────────────────────────────────────

    def invoke(self, prompt: str, *, label: str = "llm") -> LLMResponse:
        """
        Call the LLM with automatic retry on 429 rate-limit errors.

        Retries up to 4 times with exponential backoff (5, 10, 20, 40 s).
        """
        for attempt in range(5):
            try:
                result = self.llm.invoke(prompt)
                return self._parse(result.content, label=label)
            except Exception as exc:
                if self._is_rate_limit(exc) and attempt < 4:
                    wait = 5 * (2 ** attempt)
                    logger.warning(
                        "[%s] Groq 429 — backing off %ds (retry %d/4)",
                        label, wait, attempt + 1,
                    )
                    time.sleep(wait)
                    continue
                logger.error("[%s] LLM call failed: %s", label, exc)
                raise
        raise RuntimeError(f"[{label}] Max LLM retries exceeded")

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _parse(self, raw: str, *, label: str) -> LLMResponse:
        thinking = None
        match = _THINK_RE.search(raw)
        if match and self.preserve_thinking:
            thinking = match.group(1).strip()

        content = _THINK_RE.sub("", raw).strip()
        return LLMResponse(content=content, thinking=thinking, raw=raw)

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(kw in msg for kw in (
            "429", "rate limit", "too many requests", "rate_limit_exceeded",
        ))

    def __repr__(self) -> str:
        mode = "thinking" if self.preserve_thinking else "fast"
        return f"LLMClient({self._model}, t={self._temperature}, {mode})"
