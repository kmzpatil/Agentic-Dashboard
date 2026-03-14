"""
Bootstrap the Frammer PostgreSQL database from the bundled SQLite snapshot.

This script prefers the already-materialized `frammer_database.sqlite` file, but
can also rebuild a temporary SQLite database from `frammer_database.sql` if
needed. Target PostgreSQL credentials are resolved from `PG*`, `POSTGRES_*`, or
an explicit PostgreSQL `DATABASE_URL` / `POSTGRES_URL`.

Usage:
    python database/bootstrap_postgres.py
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT_DIR / "database"
DEFAULT_SQLITE_PATH = DATABASE_DIR / "frammer_database.sqlite"
DEFAULT_SQL_PATH = DATABASE_DIR / "frammer_database.sql"

load_dotenv(ROOT_DIR / ".env")
load_dotenv()


SQLITE_TO_POSTGRES = {
    "TEXT": "TEXT",
    "INTEGER": "BIGINT",
    "REAL": "DOUBLE PRECISION",
    "NUMERIC": "NUMERIC",
    "BLOB": "BYTEA",
    "": "TEXT",
}

INDEXES = (
    ("idx_raw_videos_video_id", "raw_videos", ["Video_ID"]),
    ("idx_raw_videos_user_id", "raw_videos", ["User_ID"]),
    ("idx_raw_videos_upload_date", "raw_videos", ["Upload_Date"]),
    ("idx_raw_video_channel_video_id", "raw_video_channel", ["Video_ID"]),
    ("idx_raw_video_channel_channel_name", "raw_video_channel", ["Channel_Name"]),
    ("idx_users_user_id", "users", ["User_ID"]),
    ("idx_users_client_name", "users", ["Client_Name"]),
    ("idx_created_assets_asset_id", "created_assets", ["Asset_ID"]),
    ("idx_created_assets_video_id", "created_assets", ["Video_ID"]),
    ("idx_created_assets_create_date", "created_assets", ["Create_Date"]),
    ("idx_created_assets_output_type", "created_assets", ["Output_Type"]),
    ("idx_published_posts_post_id", "published_posts", ["Post_ID"]),
    ("idx_published_posts_asset_id", "published_posts", ["Asset_ID"]),
    ("idx_published_posts_publish_date", "published_posts", ["Publish_Date"]),
    ("idx_post_distribution_post_id", "post_distribution", ["Post_ID"]),
    ("idx_post_distribution_channel_name", "post_distribution", ["Channel_Name"]),
    ("idx_channels_channel_name", "channels", ["Channel_Name"]),
)


def env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue

        normalized = value.strip()
        if normalized:
            return normalized

    return None


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def sqlite_type_to_postgres(declared_type: str) -> str:
    return SQLITE_TO_POSTGRES.get((declared_type or "").upper().strip(), "TEXT")


def resolve_postgres_connection():
    for env_name in ("POSTGRES_URL", "PGDATABASE_URL", "DATABASE_URL"):
        value = env_value(env_name)
        if value and value.startswith("postgres"):
            return psycopg2.connect(value)

    host = env_value("PGHOST", "POSTGRES_HOST")
    user = env_value("PGUSER", "POSTGRES_USER")
    database = env_value("PGDATABASE", "POSTGRES_DB")
    password = env_value("PGPASSWORD", "POSTGRES_PASSWORD")
    port = int(env_value("PGPORT", "POSTGRES_PORT") or "5432")
    sslmode = env_value("PGSSLMODE", "POSTGRES_SSLMODE", "DB_SSLMODE") or "prefer"

    if not host or not user or not database:
        raise RuntimeError(
            "Missing PostgreSQL credentials. Set PG* vars, POSTGRES_* vars, or POSTGRES_URL.",
        )

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        sslmode=sslmode,
    )


def ensure_sqlite_source() -> tuple[Path, tempfile.TemporaryDirectory | None]:
    if DEFAULT_SQLITE_PATH.exists():
        return DEFAULT_SQLITE_PATH, None

    if not DEFAULT_SQL_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {DEFAULT_SQLITE_PATH} or {DEFAULT_SQL_PATH} to bootstrap from.",
        )

    temp_dir = tempfile.TemporaryDirectory(prefix="frammer-bootstrap-")
    sqlite_path = Path(temp_dir.name) / "frammer_database.sqlite"
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.executescript(DEFAULT_SQL_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()

    return sqlite_path, temp_dir


def list_tables(sqlite_conn: sqlite3.Connection) -> list[str]:
    rows = sqlite_conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def fetch_table_info(sqlite_conn: sqlite3.Connection, table_name: str):
    return sqlite_conn.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall()


def recreate_table(pg_conn, table_name: str, columns) -> None:
    quoted_table = quote_ident(table_name)
    column_defs = []
    primary_keys = []

    for _, column_name, column_type, not_null, default_value, primary_key in columns:
        column_sql = [
            quote_ident(column_name),
            sqlite_type_to_postgres(column_type),
        ]
        if not_null:
            column_sql.append("NOT NULL")
        if default_value is not None:
            column_sql.append(f"DEFAULT {default_value}")
        column_defs.append(" ".join(column_sql))
        if primary_key:
            primary_keys.append(quote_ident(column_name))

    if primary_keys:
        column_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")

    ddl = f"CREATE TABLE {quoted_table} ({', '.join(column_defs)})"

    with pg_conn.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {quoted_table} CASCADE")
        cursor.execute(ddl)


def copy_table_rows(sqlite_conn: sqlite3.Connection, pg_conn, table_name: str) -> int:
    quoted_table = quote_ident(table_name)
    rows = sqlite_conn.execute(f"SELECT * FROM {quoted_table}").fetchall()
    if not rows:
        return 0

    column_names = [description[0] for description in sqlite_conn.execute(f"SELECT * FROM {quoted_table} LIMIT 1").description]
    quoted_columns = ", ".join(quote_ident(name) for name in column_names)
    insert_sql = f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES %s"

    with pg_conn.cursor() as cursor:
        execute_values(cursor, insert_sql, rows, page_size=1000)

    return len(rows)


def create_indexes(pg_conn) -> None:
    with pg_conn.cursor() as cursor:
        for index_name, table_name, columns in INDEXES:
            columns_sql = ", ".join(quote_ident(column) for column in columns)
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {quote_ident(index_name)} "
                f"ON {quote_ident(table_name)} ({columns_sql})"
            )


def main() -> None:
    sqlite_path, temp_dir = ensure_sqlite_source()
    print(f"SQLite source: {sqlite_path}")

    sqlite_conn = None
    pg_conn = None

    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row

        pg_conn = resolve_postgres_connection()
        pg_conn.autocommit = False

        tables = list_tables(sqlite_conn)
        print(f"Found {len(tables)} table(s): {', '.join(tables)}")

        for table_name in tables:
            columns = fetch_table_info(sqlite_conn, table_name)
            recreate_table(pg_conn, table_name, columns)
            row_count = copy_table_rows(sqlite_conn, pg_conn, table_name)
            pg_conn.commit()
            print(f"Loaded {table_name}: {row_count} row(s)")

        create_indexes(pg_conn)
        pg_conn.commit()
        print("Bootstrap complete. Indexes created.")
    finally:
        if sqlite_conn is not None:
            sqlite_conn.close()
        if pg_conn is not None:
            pg_conn.close()
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    main()
