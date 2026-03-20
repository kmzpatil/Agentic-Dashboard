import os

# Read from .env string
_env_keys = os.getenv("GEMINI_KEYS", "")
GEMINI_KEYS = [k.strip() for k in _env_keys.split(",") if k.strip()]

_current_key_index = 0

def get_next_gemini_key():
    global _current_key_index
    if not GEMINI_KEYS:
        return os.getenv("GOOGLE_API_KEY", "")
        
    key = GEMINI_KEYS[_current_key_index]
    _current_key_index = (_current_key_index + 1) % len(GEMINI_KEYS)
    return key
