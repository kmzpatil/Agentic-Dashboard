#!/usr/bin/env python3
"""Ensure Docker Postgres has the target application database before API startup."""

from __future__ import annotations

import os
import subprocess
import sys
import time

import psycopg2
from psycopg2 import sql


REQUIRED_TABLES = {
    "raw_videos",
    "created_assets",
    "published_posts",
    "users",
    "app_users",
    "conversations",
}


def ensure_minimal_analytics_schema(app_connect_args: dict) -> None:
    """Create a minimal analytics schema so API queries do not fail on empty DBs."""
    ddl_statements = [
        '''
        CREATE TABLE IF NOT EXISTS clients (
            "Client_Name" TEXT PRIMARY KEY
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS users (
            "User_ID" BIGINT PRIMARY KEY,
            "User_Name" TEXT,
            "Client_Name" TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS channels (
            "Channel_Name" TEXT PRIMARY KEY,
            "Client_Name" TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS raw_videos (
            "Video_ID" TEXT PRIMARY KEY,
            "User_ID" BIGINT,
            "Input_Type" TEXT,
            "Language" TEXT,
            "Upload_Date" TEXT,
            "Uploaded_Duration" DOUBLE PRECISION
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS raw_video_channel (
            "Video_ID" TEXT,
            "Channel_Name" TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS created_assets (
            "Asset_ID" TEXT PRIMARY KEY,
            "Video_ID" TEXT,
            "Created_Duration" DOUBLE PRECISION,
            "Create_Date" TEXT,
            "Output_Type" TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS published_posts (
            "Post_ID" TEXT PRIMARY KEY,
            "Asset_ID" TEXT,
            "Published_Duration" DOUBLE PRECISION,
            "Publish_Date" TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS post_distribution (
            "Post_ID" TEXT,
            "Channel_Name" TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id VARCHAR(64) PRIMARY KEY,
            user_id BIGINT,
            title TEXT,
            metadata_json TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id BIGSERIAL PRIMARY KEY,
            conversation_id VARCHAR(64) NOT NULL,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        ''',
    ]

    with psycopg2.connect(**app_connect_args) as conn:
        with conn.cursor() as cur:
            for stmt in ddl_statements:
                cur.execute(stmt)
            # Queries use to_date(text, 'YYYY-MM-DD'), so keep date-like columns as text.
            cur.execute(
                'ALTER TABLE raw_videos ALTER COLUMN "Upload_Date" TYPE TEXT USING "Upload_Date"::text'
            )
            cur.execute(
                'ALTER TABLE created_assets ALTER COLUMN "Create_Date" TYPE TEXT USING "Create_Date"::text'
            )
            cur.execute(
                'ALTER TABLE published_posts ALTER COLUMN "Publish_Date" TYPE TEXT USING "Publish_Date"::text'
            )
        conn.commit()


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def main() -> None:
    host = _first_env("PGHOST", "POSTGRES_HOST", default="db")
    port = int(_first_env("PGPORT", "POSTGRES_PORT", default="5432"))
    user = _first_env("PGUSER", "POSTGRES_USER", default="postgres")
    password = _first_env("PGPASSWORD", "POSTGRES_PASSWORD", default="")
    target_db = _first_env("PGDATABASE", "POSTGRES_DB", default="frammer_database")

    # Connect to maintenance DB first so we can create target DB if needed.
    connect_args = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": "postgres",
    }

    for attempt in range(1, 31):
        try:
            conn = psycopg2.connect(**connect_args)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(target_db)))
                    print(f"Created database: {target_db}")
                else:
                    print(f"Database exists: {target_db}")
            conn.close()
            break
        except psycopg2.OperationalError as exc:
            if attempt == 30:
                raise
            print(f"Waiting for database ({attempt}/30): {exc}")
            time.sleep(2)

    app_connect_args = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": target_db,
    }
    with psycopg2.connect(**app_connect_args) as app_conn:
        with app_conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            existing_tables = {row[0] for row in cur.fetchall()}

    missing_tables = REQUIRED_TABLES - existing_tables
    if not missing_tables:
        print("Bootstrap not required: core tables already exist.")
        return

    print(f"Missing tables detected: {', '.join(sorted(missing_tables))}")
    sqlite_file = "/app/database/frammer_database.sqlite"
    sql_file = "/app/database/frammer_database.sql"
    if not os.path.isfile(sqlite_file) and not os.path.isfile(sql_file):
        print(
            "Bootstrap files not found in container "
            "(/app/database/frammer_database.sqlite or /app/database/frammer_database.sql)."
        )
        print("Creating minimal analytics schema and seeding auth schema/users.")
        ensure_minimal_analytics_schema(app_connect_args)
        subprocess.run([sys.executable, "-m", "backend.db.seed_auth_users"], check=True)
        return

    print("Running bootstrap_postgres.py...")
    subprocess.run([sys.executable, "/app/database/bootstrap_postgres.py"], check=True)
    print("Running seed_auth_users...")
    subprocess.run([sys.executable, "-m", "backend.db.seed_auth_users"], check=True)
    print("Bootstrap and auth seeding complete.")


if __name__ == "__main__":
    main()
