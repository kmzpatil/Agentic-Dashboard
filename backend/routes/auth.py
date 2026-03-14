import bcrypt
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth.jwt import sign_auth_token
from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth


router = APIRouter()


class LoginInput(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginInput):
    username = str(payload.username or "").strip()
    password = str(payload.password or "")

    if not username or not password:
        return JSONResponse(status_code=400, content={"error": "username and password are required"})

    try:
        user_result = query(
            '''
          SELECT id, username, password_hash, role, client_name, user_id, is_active
          FROM app_users
          WHERE username = $1
          LIMIT 1
        ''',
            [username],
        )

        if user_result.row_count == 0 or not user_result.rows[0].get("is_active"):
            return JSONResponse(status_code=401, content={"error": "Invalid username or password"})

        auth_user = user_result.rows[0]
        is_valid = bcrypt.checkpw(password.encode("utf-8"), auth_user["password_hash"].encode("utf-8"))
        if not is_valid:
            return JSONResponse(status_code=401, content={"error": "Invalid username or password"})

        token = sign_auth_token(
            {
                "sub": str(auth_user["id"]),
                "username": auth_user["username"],
                "role": auth_user["role"],
                "clientName": auth_user.get("client_name") or None,
                "userId": auth_user.get("user_id") or None,
            }
        )

        return {
            "token": token,
            "user": {
                "id": auth_user["id"],
                "username": auth_user["username"],
                "role": auth_user["role"],
                "clientName": auth_user.get("client_name") or None,
                "userId": auth_user.get("user_id") or None,
            },
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@router.get("/me")
def me(auth: AuthContext = Depends(require_auth)):
    try:
        me_result = query(
            '''
          SELECT id, username, role, client_name, user_id, is_active
          FROM app_users
          WHERE id = $1
          LIMIT 1
        ''',
            [auth.auth_user_id],
        )

        if me_result.row_count == 0 or not me_result.rows[0].get("is_active"):
            return JSONResponse(status_code=401, content={"error": "Invalid session"})

        row = me_result.rows[0]
        return {
            "user": {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "clientName": row.get("client_name") or None,
                "userId": row.get("user_id") or None,
            }
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
