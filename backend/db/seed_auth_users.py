import os
import re
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


def table_exists(table_name: str) -> bool:
    exists = query("SELECT to_regclass($1) AS table_name", [f"public.{table_name}"])
    if not exists.rows:
        return False
    return bool(exists.rows[0].get("table_name"))


def table_has_rows(table_name: str) -> bool:
    result = query(f'SELECT 1 FROM "{table_name}" LIMIT 1')
    return result.row_count > 0


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


def get_scoped_user(fallback_client_name: str, requested_user_id: int | None = None) -> dict:
    if requested_user_id:
        result = query(
            'SELECT "User_ID", "User_Name", "Client_Name" FROM users WHERE "User_ID" = $1 LIMIT 1',
            [requested_user_id],
        )
        if result.row_count == 0:
            raise RuntimeError(f"AUTH_USER_ID not found in users table: {requested_user_id}")
        return result.rows[0]

    result = query('SELECT "User_ID", "User_Name", "Client_Name" FROM users ORDER BY "User_ID" LIMIT 1')
    if result.row_count == 0:
        raise RuntimeError("No users found. Seed the analytics dataset first.")

    row = result.rows[0]
    return {
        **row,
        "Client_Name": row.get("Client_Name") or row.get("client_name") or fallback_client_name,
    }


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def _env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def iter_client_admin_configs(default_client_name: str) -> list[dict]:
    indexed: list[dict] = []
    seen_indexes = sorted(
        {
            match.group(1)
            for key in os.environ
            if (match := re.fullmatch(r"AUTH_CLIENT_ADMIN(\d+)_USERNAME", key))
        },
        key=int,
    )

    for index in seen_indexes:
        username = os.getenv(f"AUTH_CLIENT_ADMIN{index}_USERNAME")
        password = os.getenv(f"AUTH_CLIENT_ADMIN{index}_PASSWORD")
        client_name = os.getenv(f"AUTH_CLIENT_ADMIN{index}_CLIENT")
        if not username or not password or not client_name:
            raise RuntimeError(
                f"AUTH_CLIENT_ADMIN{index}_USERNAME, AUTH_CLIENT_ADMIN{index}_PASSWORD, and "
                f"AUTH_CLIENT_ADMIN{index}_CLIENT must all be set together",
            )
        exists = query('SELECT 1 FROM clients WHERE "Client_Name" = $1 LIMIT 1', [client_name])
        if exists.row_count == 0:
            raise RuntimeError(f"Configured client admin client not found: {client_name}")
        indexed.append(
            {
                "username": username,
                "password": password,
                "client_name": client_name,
            }
        )

    if indexed:
        return indexed

    return [
        {
            "username": os.getenv("AUTH_CLIENT_ADMIN_USERNAME", "client_admin_client1"),
            "password": os.getenv("AUTH_CLIENT_ADMIN_PASSWORD", "Client@12345"),
            "client_name": default_client_name,
        }
    ]


def iter_user_configs(default_client_name: str) -> list[dict]:
    indexed: list[dict] = []
    seen_indexes = sorted(
        {
            match.group(1)
            for key in os.environ
            if (match := re.fullmatch(r"AUTH_USER(\d+)_USERNAME", key))
        },
        key=int,
    )

    for index in seen_indexes:
        username = os.getenv(f"AUTH_USER{index}_USERNAME")
        password = os.getenv(f"AUTH_USER{index}_PASSWORD")
        user_id = _env_int(f"AUTH_USER{index}_ID")
        client_name = os.getenv(f"AUTH_USER{index}_CLIENT")
        if not username or not password or user_id is None:
            raise RuntimeError(
                f"AUTH_USER{index}_USERNAME, AUTH_USER{index}_PASSWORD, and AUTH_USER{index}_ID "
                "must all be set together",
            )
        scoped_user = get_scoped_user(client_name or default_client_name, requested_user_id=user_id)
        indexed.append(
            {
                "username": username,
                "password": password,
                "client_name": client_name or scoped_user.get("Client_Name") or scoped_user.get("client_name") or default_client_name,
                "user_id": int(scoped_user.get("User_ID") or scoped_user.get("user_id")),
            }
        )

    if indexed:
        return indexed

    requested_user_id = _env_int("AUTH_USER_ID")
    scoped_user = get_scoped_user(default_client_name, requested_user_id=requested_user_id)
    return [
        {
            "username": os.getenv("AUTH_USER_USERNAME", "user_local_1"),
            "password": os.getenv("AUTH_USER_PASSWORD", "User@12345"),
            "client_name": scoped_user.get("Client_Name") or scoped_user.get("client_name") or default_client_name,
            "user_id": int(scoped_user.get("User_ID") or scoped_user.get("user_id")),
        }
    ]


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

        upsert_user(
            username=os.getenv("AUTH_WEBSITE_ADMIN_USERNAME", "website_admin"),
            password_hash=_hash_password(os.getenv("AUTH_WEBSITE_ADMIN_PASSWORD", "Admin@12345")),
            role="website_admin",
            client_name=None,
            user_id=None,
        )

        has_clients = table_exists("clients") and table_has_rows("clients")
        has_users = table_exists("users") and table_has_rows("users")
        if not has_clients or not has_users:
            print(
                "Analytics client/user data not available yet. "
                "Seeded website_admin only."
            )
            print(f"website_admin username: {os.getenv('AUTH_WEBSITE_ADMIN_USERNAME', 'website_admin')}")
            return

        client_name = get_client_name()

        client_admin_configs = iter_client_admin_configs(client_name)
        for config_item in client_admin_configs:
            upsert_user(
                username=config_item["username"],
                password_hash=_hash_password(config_item["password"]),
                role="client_admin",
                client_name=config_item["client_name"],
                user_id=None,
            )

        user_configs = iter_user_configs(client_name)
        for config_item in user_configs:
            upsert_user(
                username=config_item["username"],
                password_hash=_hash_password(config_item["password"]),
                role="user",
                client_name=config_item["client_name"],
                user_id=config_item["user_id"],
            )

        print("Auth users seeded successfully.")
        print(f"website_admin username: {os.getenv('AUTH_WEBSITE_ADMIN_USERNAME', 'website_admin')}")
        for config_item in client_admin_configs:
            print(
                "client_admin username: "
                f"{config_item['username']} (client: {config_item['client_name']})"
            )
        for config_item in user_configs:
            print(
                "user username: "
                f"{config_item['username']} (User_ID: {config_item['user_id']})"
            )
    finally:
        close_pool()


if __name__ == "__main__":
    run()
