"""
client.py
---------
Single LLM client abstraction for the Frammer AI agent.

Wraps AzureChatOpenAI (Azure OpenAI) with:
  - Automatic 429 rate-limit retry with exponential backoff
  - <think>…</think> tag handling (strip or preserve)
  - Two factory modes: fast() and thinking()

Note: o-series models (o1, o3, o4-mini, etc.) do not support the temperature
parameter — only the API default of 1 is accepted. Temperature is omitted for
these models automatically.
"""

import logging
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

logger = logging.getLogger("frammer.client")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

# Azure OpenAI deployment name (used as the "model" identifier)
DEFAULT_MODEL = os.getenv("AZURE_DEPLOYMENT", "o4-mini")

# o-series reasoning models do not accept a temperature parameter
_O_SERIES_PREFIXES = ("o1", "o3", "o4")


def _is_o_series(model: str) -> bool:
    return any(model.lower().startswith(p) for p in _O_SERIES_PREFIXES)


class LLMResponse:
    """Structured response from an LLM call."""

    def __init__(self, content: str, thinking: Optional[str] = None, raw: str = ""):
        self.content = content          # cleaned output (thinking tags stripped)
        self.thinking = thinking        # raw thinking block when preserve_thinking=True
        self.raw = raw                  # unprocessed LLM output


class LLMClient:
    """
    Unified LLM client backed by Azure OpenAI.  All agent code should use
    this instead of instantiating AzureChatOpenAI directly.

    Parameters
    ----------
    model : str
        Azure deployment name (overrides AZURE_DEPLOYMENT env var).
    temperature : float
        Sampling temperature (ignored for o-series reasoning models).
    preserve_thinking : bool
        If True, <think> blocks are extracted and returned in
        LLMResponse.thinking rather than discarded.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 1,
        preserve_thinking: bool = False,
    ):
        kwargs: dict = dict(
            azure_deployment=model,
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        )
        if not _is_o_series(model):
            kwargs["temperature"] = temperature

        self.llm = AzureChatOpenAI(**kwargs)
        self.preserve_thinking = preserve_thinking
        self._model = model
        self._temperature = temperature

    # ── Factory helpers ──────────────────────────────────────────────────────

    @classmethod
    def fast(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Deterministic mode for routing and structured output."""
        return cls(model=model, temperature=1, preserve_thinking=False)

    @classmethod
    def thinking(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Preserves the model's <think> reasoning for display in the UI."""
        return cls(model=model, temperature=1, preserve_thinking=True)

    @classmethod
    def creative(cls, model: str = DEFAULT_MODEL) -> "LLMClient":
        """Conversational / insight generation mode."""
        return cls(model=model, temperature=1, preserve_thinking=False)

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
                        "[%s] Azure OpenAI 429 — backing off %ds (retry %d/4)",
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
        return f"LLMClient(azure:{self._model}, t={self._temperature}, {mode})"
