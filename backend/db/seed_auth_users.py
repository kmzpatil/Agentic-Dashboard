import os
from pathlib import Path

import bcrypt
from dotenv import load_dotenv

from backend.config.env import get_config
from backend.db.pool import close_pool, init_pool, query


load_dotenv()


def ensure_auth_schema() -> None:
    exists = query("SELECT to_regclass('public.app_users') AS table_name")
    if exists.rows and exists.rows[0].get("table_name"):
        return

    schema_path = Path(__file__).with_name("auth_schema.sql")
    sql = schema_path.read_text(encoding="utf-8")
    query(sql)


def get_client_name() -> str:
    requested = os.getenv("AUTH_CLIENT_ADMIN_CLIENT_NAME")
    if requested:
        exists = query('SELECT 1 FROM clients WHERE "Client_Name" = $1 LIMIT 1', [requested])
        if exists.row_count == 0:
            raise RuntimeError(f"AUTH_CLIENT_ADMIN_CLIENT_NAME not found in clients table: {requested}")
        return requested

    result = query('SELECT "Client_Name" FROM clients ORDER BY "Client_Name" LIMIT 1')
    if result.row_count == 0:
        raise RuntimeError("No clients found. Seed the analytics dataset first.")

    row = result.rows[0]
    return row.get("Client_Name") or row.get("client_name")


def get_scoped_user(fallback_client_name: str) -> dict:
    requested_user_id = os.getenv("AUTH_USER_ID")
    if requested_user_id:
        try:
            requested = int(requested_user_id)
        except ValueError as exc:
            raise RuntimeError("AUTH_USER_ID must be an integer") from exc

        result = query(
            'SELECT "User_ID", "User_Name", "Client_Name" FROM users WHERE "User_ID" = $1 LIMIT 1',
            [requested],
        )
        if result.row_count == 0:
            raise RuntimeError(f"AUTH_USER_ID not found in users table: {requested}")
        return result.rows[0]

    result = query('SELECT "User_ID", "User_Name", "Client_Name" FROM users ORDER BY "User_ID" LIMIT 1')
    if result.row_count == 0:
        raise RuntimeError("No users found. Seed the analytics dataset first.")

    row = result.rows[0]
    return {
        **row,
        "Client_Name": row.get("Client_Name") or row.get("client_name") or fallback_client_name,
    }


def upsert_user(*, username: str, password_hash: str, role: str, client_name: str | None, user_id: int | None) -> None:
    query(
        '''
      INSERT INTO app_users (username, password_hash, role, client_name, user_id, is_active)
      VALUES ($1, $2, $3, $4, $5, TRUE)
      ON CONFLICT (username)
      DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        role = EXCLUDED.role,
        client_name = EXCLUDED.client_name,
        user_id = EXCLUDED.user_id,
        is_active = TRUE,
        updated_at = NOW()
    ''',
        [username, password_hash, role, client_name, user_id],
    )


def run() -> None:
    config = get_config()
    init_pool(config.db)

    try:
        ensure_auth_schema()

        client_name = get_client_name()
        scoped_user = get_scoped_user(client_name)

        website_admin_password = os.getenv("AUTH_WEBSITE_ADMIN_PASSWORD", "Admin@12345")
        client_admin_password = os.getenv("AUTH_CLIENT_ADMIN_PASSWORD", "Client@12345")
        user_password = os.getenv("AUTH_USER_PASSWORD", "User@12345")

        website_admin_hash = bcrypt.hashpw(website_admin_password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        client_admin_hash = bcrypt.hashpw(client_admin_password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        user_hash = bcrypt.hashpw(user_password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

        upsert_user(
            username=os.getenv("AUTH_WEBSITE_ADMIN_USERNAME", "website_admin"),
            password_hash=website_admin_hash,
            role="website_admin",
            client_name=None,
            user_id=None,
        )

        upsert_user(
            username=os.getenv("AUTH_CLIENT_ADMIN_USERNAME", "client_admin_client1"),
            password_hash=client_admin_hash,
            role="client_admin",
            client_name=client_name,
            user_id=None,
        )

        upsert_user(
            username=os.getenv("AUTH_USER_USERNAME", "user_local_1"),
            password_hash=user_hash,
            role="user",
            client_name=scoped_user.get("Client_Name") or scoped_user.get("client_name") or client_name,
            user_id=int(scoped_user.get("User_ID") or scoped_user.get("user_id")),
        )

        print("Auth users seeded successfully.")
        print(f"website_admin username: {os.getenv('AUTH_WEBSITE_ADMIN_USERNAME', 'website_admin')}")
        print(
            "client_admin username: "
            f"{os.getenv('AUTH_CLIENT_ADMIN_USERNAME', 'client_admin_client1')} (client: {client_name})"
        )
        print(
            "user username: "
            f"{os.getenv('AUTH_USER_USERNAME', 'user_local_1')} "
            f"(User_ID: {scoped_user.get('User_ID') or scoped_user.get('user_id')})"
        )
    finally:
        close_pool()


if __name__ == "__main__":
    run()
