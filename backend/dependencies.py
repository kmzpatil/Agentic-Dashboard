"""
dependencies.py
---------------
FastAPI dependencies: database sessions, JWT auth, RBAC.
"""

from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from .config import settings

# ── Database engine (connection pool) ────────────────────────────────────────

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=5,
        )
    return _engine


def get_db():
    """Yield a raw DB connection from the pool, auto-returned on exit."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn


# ── Auth types ───────────────────────────────────────────────────────────────

VALID_ROLES = {"website_admin", "client_admin", "user"}


@dataclass
class AuthUser:
    auth_user_id: str
    username: str
    role: str
    client_name: Optional[str] = None
    user_id: Optional[int] = None


# ── JWT verification ────────────────────────────────────────────────────────


def _verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token")


def require_auth(request: Request) -> AuthUser:
    """FastAPI dependency that extracts and validates the JWT Bearer token."""
    auth_header = request.headers.get("authorization", "")
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Authentication required")

    claims = _verify_token(parts[1])

    role = claims.get("role", "")
    if role not in VALID_ROLES:
        raise HTTPException(401, "Invalid token role")

    if role == "client_admin" and not claims.get("clientName"):
        raise HTTPException(401, "Invalid token scope for client admin")

    if role == "user" and not claims.get("userId"):
        raise HTTPException(401, "Invalid token scope for user role")

    return AuthUser(
        auth_user_id=str(claims.get("sub", "")),
        username=claims.get("username", ""),
        role=role,
        client_name=claims.get("clientName"),
        user_id=int(claims["userId"]) if claims.get("userId") else None,
    )


def require_admin(auth: AuthUser = Depends(require_auth)) -> AuthUser:
    if auth.role != "website_admin":
        raise HTTPException(403, "Forbidden")
    return auth
