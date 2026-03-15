from dataclasses import dataclass
from typing import Callable, Iterable

from fastapi import Header, HTTPException, status

from backend.auth.jwt import verify_auth_token


VALID_ROLES = {"website_admin", "client_admin", "user"}


@dataclass(frozen=True)
class AuthContext:
    auth_user_id: str
    username: str
    role: str
    client_name: str | None
    user_id: int | None


def extract_bearer_token(authorization_header: str | None = None) -> str | None:
    if not authorization_header:
        return None

    parts = authorization_header.split(" ", 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer" or not token:
        return None

    return token


def require_auth(authorization: str | None = Header(default=None)) -> AuthContext:
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        claims = verify_auth_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    role = claims.get("role")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role")

    if role == "client_admin" and not claims.get("clientName"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token scope for client admin",
        )

    if role == "user" and not claims.get("userId"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token scope for user role",
        )

    return AuthContext(
        auth_user_id=str(claims.get("sub")),
        username=str(claims.get("username")),
        role=str(role),
        client_name=claims.get("clientName"),
        user_id=int(claims["userId"]) if claims.get("userId") else None,
    )


def require_roles(roles: Iterable[str]) -> Callable[[AuthContext], AuthContext]:
    role_set = set(roles)

    def dependency(auth: AuthContext) -> AuthContext:
        if auth.role not in role_set:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return auth

    return dependency
