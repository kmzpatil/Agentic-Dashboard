"""
auth.py — Login and /me routes.
Port of backend_legacy/routes/auth.js.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..config import settings
from ..dependencies import AuthUser, get_db, require_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    clientName: str | None = None
    userId: int | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut


def _sign_token(payload: dict) -> str:
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expires_hours)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, conn: Connection = Depends(get_db)):
    username = req.username.strip()
    password = req.password

    if not username or not password:
        raise HTTPException(400, "username and password are required")

    row = conn.execute(
        text("""
            SELECT id, username, password_hash, role, client_name, user_id, is_active
            FROM app_users WHERE username = :u LIMIT 1
        """),
        {"u": username},
    ).mappings().first()

    if not row or not row["is_active"]:
        raise HTTPException(401, "Invalid username or password")

    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, "Invalid username or password")

    token = _sign_token({
        "sub":        str(row["id"]),
        "username":   row["username"],
        "role":       row["role"],
        "clientName": row["client_name"] or None,
        "userId":     row["user_id"] or None,
    })

    return LoginResponse(
        token=token,
        user=UserOut(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            clientName=row["client_name"] or None,
            userId=row["user_id"] or None,
        ),
    )


@router.get("/me")
def me(auth: AuthUser = Depends(require_auth), conn: Connection = Depends(get_db)):
    row = conn.execute(
        text("SELECT id, username, role, client_name, user_id, is_active FROM app_users WHERE id = :uid LIMIT 1"),
        {"uid": int(auth.auth_user_id)},
    ).mappings().first()

    if not row or not row["is_active"]:
        raise HTTPException(401, "Invalid session")

    return {
        "user": {
            "id":         row["id"],
            "username":   row["username"],
            "role":       row["role"],
            "clientName": row["client_name"] or None,
            "userId":     row["user_id"] or None,
        }
    }
