"""
logger_setup.py
---------------
Shared colored logging setup for the ATLAS agent stack.

Color scheme:
  INFO     → Cyan            (normal operations)
  WARNING  → Yellow          (rate limits, soft errors)
  ERROR    → Red bold        (failures)
  DEBUG    → Dark grey
  Key logs → Custom colored sections using special logger names:
    frammer.client2     → Magenta (LLM calls)
    frammer.agent.groq  → varied (see FammerFormatter)
"""

import logging
import os

# ANSI escape codes
_RESET       = "\033[0m"
_BOLD        = "\033[1m"

_BLACK       = "\033[30m"
_RED         = "\033[31m"
_GREEN       = "\033[32m"
_YELLOW      = "\033[33m"
_BLUE        = "\033[34m"
_MAGENTA     = "\033[35m"
_CYAN        = "\033[36m"
_WHITE       = "\033[37m"

_BRIGHT_RED      = "\033[91m"
_BRIGHT_GREEN    = "\033[92m"
_BRIGHT_YELLOW   = "\033[93m"
_BRIGHT_BLUE     = "\033[94m"
_BRIGHT_MAGENTA  = "\033[95m"
_BRIGHT_CYAN     = "\033[96m"
_BRIGHT_WHITE    = "\033[97m"

_DIM = "\033[2m"

# Colors per log level
_LEVEL_COLORS = {
    "DEBUG":    _DIM + _WHITE,
    "INFO":     _CYAN,
    "WARNING":  _BOLD + _YELLOW,
    "ERROR":    _BOLD + _BRIGHT_RED,
    "CRITICAL": _BOLD + _RED,
}

# Colors for specific logger names
_LOGGER_COLORS = {
    "frammer.client2":     _MAGENTA,
    "frammer.agent.groq":  _BRIGHT_CYAN,
    "frammer.conversations": _DIM + _WHITE,
    "httpx":               _DIM + _WHITE,
    "groq":                _DIM + _WHITE,
    "uvicorn":             _DIM + _WHITE,
    "fastapi":             _DIM + _WHITE,
}

# Prefix highlights for specific message patterns
_PREFIX_HIGHLIGHTS = {
    "Key Rotation":         _BRIGHT_GREEN,
    "LOOP ITER":            _BRIGHT_CYAN,
    "TOOL CALL":            _BRIGHT_YELLOW,
    "LOOP FINAL ANSWER":    _BRIGHT_GREEN,
    "LOOP ERROR":           _BRIGHT_RED,
    "Planner: Done":        _BRIGHT_MAGENTA,
    "Planner: Generating":  _MAGENTA,
    "AGENT DONE":           _BOLD + _BRIGHT_GREEN,
    "RATE LIMIT":           _BOLD + _BRIGHT_YELLOW,
    "LLM CALL FAILED":      _BOLD + _BRIGHT_RED,
    "Intent →":             _BRIGHT_BLUE,
    "=== ReAct":            _BOLD + _CYAN,
}


class FrammerColorFormatter(logging.Formatter):
    """
    Colorizes log output based on level and logger name.
    Specific message patterns get their own highlight colors.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Base level color
        level_color = _LEVEL_COLORS.get(record.levelname, _RESET)
        # Logger color override
        logger_color = _LEVEL_COLORS.get(record.levelname, _RESET)
        for name_prefix, color in _LOGGER_COLORS.items():
            if record.name.startswith(name_prefix):
                logger_color = color
                break

        # Timestamp
        ts = self.formatTime(record, "%H:%M:%S")
        timestamp = f"{_DIM}{ts}{_RESET}"

        # Level badge
        level = f"{level_color}[{record.levelname[:4]}]{_RESET}"

        # Logger name (shortened)
        short_name = record.name.replace("frammer.", "")
        logger_name = f"{logger_color}{short_name}{_RESET}"

        # Message — check for keyword highlights
        msg = record.getMessage()
        for keyword, kw_color in _PREFIX_HIGHLIGHTS.items():
            if keyword in msg:
                # Highlight the keyword inline
                msg = msg.replace(keyword, f"{kw_color}{keyword}{_RESET}")
                break

        # Exception
        exc_text = ""
        if record.exc_info:
            exc_text = "\n" + self.formatException(record.exc_info)

        return f"{timestamp} {level} {logger_name}: {msg}{exc_text}"


def setup_logging(level: int = logging.INFO) -> None:
    """
    Call once at startup to configure colored logging for the entire ATLAS stack.
    Silences noisy third-party loggers to WARNING.

    Idempotent: checks root handler types to avoid duplicate setup even when
    this module is imported under multiple names (e.g. 'logger_setup' vs 'agent.logger_setup').
    """
    root = logging.getLogger()

    # Guard: if root already has our formatter, skip setup entirely
    for h in root.handlers:
        if isinstance(h.formatter, FrammerColorFormatter):
            return

    root.setLevel(level)

    # Remove existing handlers to prevent duplication
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(FrammerColorFormatter())
    root.addHandler(handler)

    # Silence noisy libs
    for noisy in ("httpx", "httpcore", "groq._base_client", "openai", "google.genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Keep our loggers at INFO
    for name in ("frammer", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).setLevel(logging.INFO)
