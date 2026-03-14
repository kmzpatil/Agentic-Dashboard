import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


DEFAULT_EXPIRY = os.getenv("JWT_EXPIRES_IN", "8h")


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret and os.getenv("NODE_ENV") == "production":
        raise RuntimeError("Missing required JWT_SECRET environment variable")
    return secret or "local-dev-jwt-secret-change-me"


def _parse_expiry(expiry: str) -> timedelta:
    expiry = expiry.strip().lower()
    if expiry.endswith("h"):
        return timedelta(hours=int(expiry[:-1]))
    if expiry.endswith("m"):
        return timedelta(minutes=int(expiry[:-1]))
    if expiry.endswith("s"):
        return timedelta(seconds=int(expiry[:-1]))
    if expiry.endswith("d"):
        return timedelta(days=int(expiry[:-1]))
    return timedelta(seconds=int(expiry))


def sign_auth_token(payload: dict[str, Any]) -> str:
    claims = dict(payload)
    claims["exp"] = datetime.now(timezone.utc) + _parse_expiry(DEFAULT_EXPIRY)
    return jwt.encode(claims, _get_jwt_secret(), algorithm="HS256")


def verify_auth_token(token: str) -> dict[str, Any]:
    claims = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    return dict(claims)
