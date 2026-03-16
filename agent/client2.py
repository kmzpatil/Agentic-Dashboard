"""
client2.py
----------
Enhanced LLM client abstraction with multi-provider support and Groq key rotation.

Features:
  - Azure OpenAI and Groq support via AI_PROVIDER env var
  - Random rotation across GROQ_API_KEY_1..GROQ_API_KEY_15 on every call
  - Exponential backoff retry on 429 rate-limit errors
  - <think>…</think> tag stripping/preserving
  - Factory modes: fast(), thinking(), creative()
"""

import logging
import os
import random
import re
import time
from typing import Optional

from dotenv import load_dotenv

# Load agent/.env first (highest priority), then root .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from logger_setup import setup_logging
setup_logging()
logger = logging.getLogger("frammer.client2")

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

# ── Provider defaults ────────────────────────────────────────────────────────

AI_PROVIDER = os.getenv("AI_PROVIDER", "azure-openai").lower()

_O_SERIES_PREFIXES = ("o1", "o3", "o4")

def _is_o_series(model: str) -> bool:
    return any(model.lower().startswith(p) for p in _O_SERIES_PREFIXES)

def _get_default_model(provider: str) -> str:
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    return os.getenv("AZURE_DEPLOYMENT", "o4-mini")


# ── Groq API key pool ────────────────────────────────────────────────────────

def _load_groq_keys() -> list[str]:
    """
    Load all Groq API keys from env.
    Looks for: GROQ_API_KEY, GROQ_API_KEY_1 ... GROQ_API_KEY_15
    Returns a list of all non-empty keys found.
    """
    keys = []
    # Primary key (no suffix)
    base = os.getenv("GROQ_API_KEY", "").strip()
    if base:
        keys.append(base)
    # Numbered keys
    for i in range(1, 16):
        k = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    return keys

_GROQ_KEY_POOL: list[str] = _load_groq_keys()

if _GROQ_KEY_POOL:
    logger.info("Groq key pool loaded: %d key(s) available.", len(_GROQ_KEY_POOL))
else:
    logger.warning("No Groq API keys found. Set GROQ_API_KEY or GROQ_API_KEY_1..15 in agent/.env")


def _pick_groq_key() -> str:
    """Pick a random API key from the pool."""
    if not _GROQ_KEY_POOL:
        raise ValueError("GROQ_API_KEY pool is empty. Add at least one key to agent/.env")
    key = random.choice(_GROQ_KEY_POOL)
    idx = _GROQ_KEY_POOL.index(key) + 1
    logger.info("Key Rotation: Using key #%d from pool of %d.", idx, len(_GROQ_KEY_POOL))
    return key


# ── Response dataclass ───────────────────────────────────────────────────────

class LLMResponse:
    """Structured response from an LLM call."""
    def __init__(self, content: str, thinking: Optional[str] = None, raw: str = ""):
        self.content = content
        self.thinking = thinking
        self.raw = raw


# ── LLM Client ───────────────────────────────────────────────────────────────

try:
    from langchain_openai import AzureChatOpenAI
except ImportError:
    AzureChatOpenAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None


class LLMClient:
    """
    Unified LLM client supporting Azure OpenAI and Groq.
    For Groq, randomly rotates across available API keys on every call.
    """

    def __init__(
        self,
        provider: str = AI_PROVIDER,
        model: Optional[str] = None,
        temperature: float = 1,
        preserve_thinking: bool = False,
    ):
        self.provider = provider
        self.model = model or _get_default_model(provider)
        self.temperature = temperature
        self.preserve_thinking = preserve_thinking
        self._init_llm()

    def _init_llm(self, api_key: Optional[str] = None):
        """Initialise or re-initialise the underlying LLM (used for key rotation)."""
        if self.provider == "groq":
            if ChatGroq is None:
                raise ImportError("langchain-groq is not installed.")
            key = api_key or _pick_groq_key()
            self.llm = ChatGroq(
                model_name=self.model,
                temperature=self.temperature,
                groq_api_key=key,
                max_tokens=8192,  # Prevent SQL/tool call truncation
            )
        else:
            if AzureChatOpenAI is None:
                raise ImportError("langchain-openai is not installed.")
            kwargs: dict = dict(
                azure_deployment=self.model,
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
            )
            if not _is_o_series(self.model):
                kwargs["temperature"] = self.temperature
            self.llm = AzureChatOpenAI(**kwargs)

    # ── Factory helpers ──────────────────────────────────────────────────────

    @classmethod
    def fast(cls, provider: str = AI_PROVIDER, model: Optional[str] = None) -> "LLMClient":
        """Deterministic routing / structured output mode."""
        return cls(provider=provider, model=model, temperature=0, preserve_thinking=False)

    @classmethod
    def thinking(cls, provider: str = AI_PROVIDER, model: Optional[str] = None) -> "LLMClient":
        """Preserves <think> reasoning blocks."""
        return cls(provider=provider, model=model, temperature=0, preserve_thinking=True)

    @classmethod
    def creative(cls, provider: str = AI_PROVIDER, model: Optional[str] = None) -> "LLMClient":
        """Conversational / insight generation mode."""
        return cls(provider=provider, model=model, temperature=0.7, preserve_thinking=False)

    # ── Core invoke ──────────────────────────────────────────────────────────

    def invoke(self, prompt: str, *, label: str = "llm") -> LLMResponse:
        """
        Call the LLM. On Groq, rotates to a new random key on every call.
        Retries up to 4 times with exponential backoff on 429 rate-limit errors.
        """
        max_attempts = 5
        start_time = time.time()

        for attempt in range(max_attempts):
            # Rotate Groq key on every attempt
            if self.provider == "groq":
                self._init_llm()
            
            logger.info("[%s] Calling %s (model: %s, attempt %d)...", label, self.provider.upper(), self.model, attempt + 1)

            try:
                result = self.llm.invoke(prompt)
                duration = time.time() - start_time
                logger.info("[%s] %s responded in %.2fs.", label, self.provider.upper(), duration)
                return self._parse(result.content, label=label)

            except Exception as exc:
                if self._is_rate_limit(exc) and attempt < max_attempts - 1:
                    wait = 5 * (2 ** attempt)
                    logger.warning(
                        "[%s] !!! RATE LIMIT (429) !!! Provider: %s — Retrying in %ds (Attempt %d/%d).",
                        label, self.provider.upper(), wait, attempt + 1, max_attempts - 1,
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
        return any(kw in msg for kw in ("429", "rate limit", "too many requests", "rate_limit_exceeded"))

    def __repr__(self) -> str:
        mode = "thinking" if self.preserve_thinking else "fast"
        return f"LLMClient({self.provider}:{self.model}, {mode})"
