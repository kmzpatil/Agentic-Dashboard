"""
Simulator Engine - uses Postgres tables and generates realistic CRUD operations
with full logging and quality checks. Simulator data is isolated via SIM tags.
"""

from __future__ import annotations

import os
import random
import string
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from psycopg2.pool import SimpleConnectionPool

# Ensure env vars are available even when this module is imported before
# the caller has called load_dotenv (e.g. module-level instantiation in router.py)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from .data_logger import DataLogger
from .quality import QualityEngine

TABLES_DDL: list[tuple[str, str]] = [
    ("clients", ""),
    ("users", ""),
    ("channels", ""),
    ("raw_videos", ""),
    ("raw_video_channel", ""),
    ("created_assets", ""),
    ("published_posts", ""),
    ("post_distribution", ""),
]

TARGET_TABLES = [name for name, _ddl in TABLES_DDL]

SIM_CLIENT = "Simulated Client"
SIM_PREFIX = "SIM"
SIM_HEADLINE_PREFIX = f"{SIM_PREFIX}:"

FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank",
    "Ivy", "Jake", "Karen", "Leo", "Mona", "Nate", "Olivia", "Paul",
    "Quinn", "Rose", "Sam", "Tara", "Uma", "Vince", "Wendy", "Xander",
]
TEAM_NAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
CHANNEL_NAMES = [
    f"{SIM_PREFIX} Tech Digest",
    f"{SIM_PREFIX} Daily Bytes",
    f"{SIM_PREFIX} News Flash",
    f"{SIM_PREFIX} Sports Hub",
    f"{SIM_PREFIX} Culture Lens",
    f"{SIM_PREFIX} Market Watch",
    f"{SIM_PREFIX} Science Now",
    f"{SIM_PREFIX} Travel Tales",
]
LANGUAGES = ["English", "Hindi", "Spanish", "French", "German", "Japanese", "Korean", "Portuguese"]
INPUT_TYPES = ["Uploaded", "Created", "Live"]
OUTPUT_TYPES = ["Video", "Reel", "Short", "Story", "Post", "Article"]
PLATFORMS = ["Facebook", "Instagram", "LinkedIn", "YouTube", "X", "Threads"]
HEADLINES = [
    f"{SIM_HEADLINE_PREFIX} Major Tech Announcement",
    f"{SIM_HEADLINE_PREFIX} AI Is Changing Everything",
    f"{SIM_HEADLINE_PREFIX} Productivity Tips",
    f"{SIM_HEADLINE_PREFIX} The Future of Remote Work",
    f"{SIM_HEADLINE_PREFIX} Surprising Results",
    f"{SIM_HEADLINE_PREFIX} Industry Trends",
    f"{SIM_HEADLINE_PREFIX} Behind the Scenes",
    f"{SIM_HEADLINE_PREFIX} What You Need to Know",
]


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _pg_config() -> dict[str, Any]:
    host = _env("PGHOST", "POSTGRES_HOST")
    user = _env("PGUSER", "POSTGRES_USER")
    database = _env("PGDATABASE", "POSTGRES_DB")
    password = _env("PGPASSWORD", "POSTGRES_PASSWORD")
    port = int(_env("PGPORT", "POSTGRES_PORT") or "5432")

    if not host or not user or not database:
        raise RuntimeError(
            "Missing required database environment variables: PGHOST, PGPORT, PGUSER, PGDATABASE"
        )

    return {
        "host": host,
        "user": user,
        "password": password,
        "dbname": database,
        "port": port,
    }


def _random_date(start_year: int = 2024, end_year: int = 2026) -> str:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    day = start + timedelta(days=random.randint(0, delta))
    return day.isoformat()


def _random_url() -> str:
    slug = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"https://example.com/video/{slug}"


def _random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters, k=length))


class _IDCounter:
    def __init__(self, start: int = 1) -> None:
        self._val = start
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            value = self._val
            self._val += 1
            return value


class SimulatorEngine:
    """
    Core simulation engine.

    - Uses the Postgres tables in the configured database
    - Seeds SIM-prefixed data
    - Runs a simulation loop executing random INSERT / UPDATE / DELETE operations
    - All operations are logged via DataLogger
    - Quality checks run after each batch
    """

    def __init__(self) -> None:
        self._pool = SimpleConnectionPool(minconn=1, maxconn=6, **_pg_config())
        self._logger = DataLogger(self._pool)
        self._quality = QualityEngine(self._pool, self._logger)

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._ops_per_batch = 5
        self._batch_interval = 2.0

        self._user_id = _IDCounter(self._max_id("users", "User_ID") + 1)
        self._video_id = _IDCounter(self._max_id("raw_videos", "Video_ID") + 1)
        self._asset_id = _IDCounter(self._max_id("created_assets", "Asset_ID") + 1)
        self._post_id = _IDCounter(self._max_id("published_posts", "Post_ID") + 1)

    def start(self, ops_per_batch: int = 5, interval: float = 2.0) -> None:
        with self._lock:
            self._ops_per_batch = ops_per_batch
            self._batch_interval = interval
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def reset(self) -> None:
        was_running = self._running
        self.stop()
        self._delete_simulator_rows()
        self._logger.clear()
        if was_running:
            self.start(self._ops_per_batch, self._batch_interval)

    def get_state(self) -> dict[str, Any]:
        tables = {table: self._count_sim_rows(table) for table in TARGET_TABLES}
        return {
            "running": self._running,
            "tables": tables,
            "log_counts": self._logger.get_counts(),
            "settings": {
                "ops_per_batch": self._ops_per_batch,
                "interval": self._batch_interval,
            },
        }

    def get_tables(self) -> list[dict[str, Any]]:
        result = []
        for table in TARGET_TABLES:
            if not self._table_exists(table):
                continue
            columns = self._get_columns(table)
            count = self._count_sim_rows(table)
            result.append({"name": table, "columns": columns, "row_count": count})
        return result

    def get_table_rows(self, table_name: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        if table_name not in TARGET_TABLES or not self._table_exists(table_name):
            return {"error": "Table not found", "rows": [], "columns": []}

        where_sql, params = self._sim_filter(table_name)
        sql = f'SELECT * FROM "{table_name}" {where_sql} ORDER BY 1 LIMIT %s OFFSET %s'
        rows = self._fetchall(sql, params + [limit, offset])
        columns = [c["name"] for c in self._get_columns(table_name)]
        records = [dict(zip(columns, row)) for row in rows]
        total = self._count_sim_rows(table_name)
        return {"columns": columns, "rows": records, "total": total}

    def get_logs(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self._logger.get_logs(**kwargs)

    def get_quality_report(self) -> dict[str, Any]:
        return self._quality.run_all_checks()

    def get_timeseries_metrics(self) -> dict[str, Any]:
        return self._logger.get_timeseries_metrics()

    def seed(self, count: int = 10) -> None:
        self._seed_clients()
        self._seed_users(count)
        self._seed_channels()
        self._seed_raw_videos(count * 2)
        self._seed_created_assets(count)
        self._seed_published_posts(count)

    @property
    def logger(self) -> DataLogger:
        return self._logger

    def _max_id(self, table: str, column: str) -> int:
        if not self._table_exists(table):
            return 0
        rows = self._fetchall(f'SELECT COALESCE(MAX("{column}"), 0) FROM "{table}"')
        return int(rows[0][0]) if rows else 0

    def _table_exists(self, table: str) -> bool:
        rows = self._fetchall(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
            [table],
        )
        return bool(rows)

    def _get_columns(self, table: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                CASE WHEN kcu.column_name IS NOT NULL THEN true ELSE false END AS is_pk
            FROM information_schema.columns c
            LEFT JOIN information_schema.table_constraints tc
              ON tc.table_schema = c.table_schema
             AND tc.table_name = c.table_name
             AND tc.constraint_type = 'PRIMARY KEY'
            LEFT JOIN information_schema.key_column_usage kcu
              ON kcu.table_schema = c.table_schema
             AND kcu.table_name = c.table_name
             AND kcu.constraint_name = tc.constraint_name
             AND kcu.column_name = c.column_name
            WHERE c.table_schema = 'public' AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            [table],
        )
        return [
            {
                "name": row[0],
                "type": row[1],
                "notnull": row[2] == "NO",
                "pk": bool(row[3]),
            }
            for row in rows
        ]

    def _sim_filter(self, table: str) -> tuple[str, list[Any]]:
        like_sim = f"{SIM_HEADLINE_PREFIX}%"
        if table == "clients":
            return "WHERE \"Client_Name\" = %s", [SIM_CLIENT]
        if table == "channels":
            return "WHERE \"Client_Name\" = %s", [SIM_CLIENT]
        if table == "users":
            return "WHERE \"Client_Name\" = %s", [SIM_CLIENT]
        if table == "raw_videos":
            return "WHERE \"Headline\" LIKE %s", [like_sim]
        if table == "raw_video_channel":
            return (
                "WHERE \"Video_ID\" IN (SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s)",
                [like_sim],
            )
        if table == "created_assets":
            return (
                "WHERE \"Video_ID\" IN (SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s)",
                [like_sim],
            )
        if table == "published_posts":
            return (
                "WHERE \"Asset_ID\" IN (SELECT \"Asset_ID\" FROM created_assets WHERE \"Video_ID\" IN "
                "(SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s))",
                [like_sim],
            )
        if table == "post_distribution":
            return (
                "WHERE \"Post_ID\" IN (SELECT \"Post_ID\" FROM published_posts WHERE \"Asset_ID\" IN "
                "(SELECT \"Asset_ID\" FROM created_assets WHERE \"Video_ID\" IN "
                "(SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s)))",
                [like_sim],
            )
        return "", []

    def _count_sim_rows(self, table: str) -> int:
        where_sql, params = self._sim_filter(table)
        rows = self._fetchall(f'SELECT COUNT(*) FROM "{table}" {where_sql}', params)
        return int(rows[0][0]) if rows else 0

    def _delete_simulator_rows(self) -> None:
        like_sim = f"{SIM_HEADLINE_PREFIX}%"
        statements = [
            (
                "DELETE FROM post_distribution WHERE \"Post_ID\" IN (SELECT \"Post_ID\" FROM published_posts "
                "WHERE \"Asset_ID\" IN (SELECT \"Asset_ID\" FROM created_assets WHERE \"Video_ID\" IN "
                "(SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s)))",
                [like_sim],
            ),
            (
                "DELETE FROM published_posts WHERE \"Asset_ID\" IN (SELECT \"Asset_ID\" FROM created_assets "
                "WHERE \"Video_ID\" IN (SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s))",
                [like_sim],
            ),
            (
                "DELETE FROM created_assets WHERE \"Video_ID\" IN (SELECT \"Video_ID\" FROM raw_videos "
                "WHERE \"Headline\" LIKE %s)",
                [like_sim],
            ),
            (
                "DELETE FROM raw_video_channel WHERE \"Video_ID\" IN (SELECT \"Video_ID\" FROM raw_videos "
                "WHERE \"Headline\" LIKE %s)",
                [like_sim],
            ),
            ("DELETE FROM raw_videos WHERE \"Headline\" LIKE %s", [like_sim]),
            ("DELETE FROM users WHERE \"Client_Name\" = %s", [SIM_CLIENT]),
            ("DELETE FROM channels WHERE \"Client_Name\" = %s", [SIM_CLIENT]),
            ("DELETE FROM clients WHERE \"Client_Name\" = %s", [SIM_CLIENT]),
        ]

        for sql, params in statements:
            self._execute(sql, params, commit=True)

    def _seed_clients(self) -> None:
        log_id = self._logger.log_pending(
            "INSERT", "clients", row_id=SIM_CLIENT, new_values={"Client_Name": SIM_CLIENT}
        )
        try:
            self._execute(
                'INSERT INTO clients ("Client_Name") VALUES (%s) ON CONFLICT DO NOTHING',
                [SIM_CLIENT],
                commit=True,
            )
            self._logger.mark_success(log_id)
        except Exception as exc:
            self._logger.mark_error(log_id, str(exc))

    def _seed_users(self, count: int) -> None:
        for _ in range(count):
            uid = self._user_id.next()
            row = {
                "User_ID": uid,
                "User_Name": f"{SIM_PREFIX} {random.choice(FIRST_NAMES)} {_random_string(4)}",
                "Team_Name": random.choice(TEAM_NAMES),
                "Client_Name": SIM_CLIENT,
            }
            log_id = self._logger.log_pending("INSERT", "users", row_id=str(uid), new_values=row)
            try:
                self._execute(
                    'INSERT INTO users ("User_ID", "User_Name", "Team_Name", "Client_Name") VALUES (%s,%s,%s,%s) '
                    "ON CONFLICT DO NOTHING",
                    [row["User_ID"], row["User_Name"], row["Team_Name"], row["Client_Name"]],
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

    def _seed_channels(self) -> None:
        for ch_name in CHANNEL_NAMES:
            row = {"Channel_Name": ch_name, "Client_Name": SIM_CLIENT}
            log_id = self._logger.log_pending("INSERT", "channels", row_id=ch_name, new_values=row)
            try:
                self._execute(
                    'INSERT INTO channels ("Channel_Name", "Client_Name") VALUES (%s,%s) ON CONFLICT DO NOTHING',
                    [row["Channel_Name"], row["Client_Name"]],
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

    def _seed_raw_videos(self, count: int) -> None:
        user_ids = self._fetchall(
            "SELECT \"User_ID\" FROM users WHERE \"Client_Name\" = %s",
            [SIM_CLIENT],
        )
        if not user_ids:
            return
        channel_names = self._fetchall(
            "SELECT \"Channel_Name\" FROM channels WHERE \"Client_Name\" = %s",
            [SIM_CLIENT],
        )

        for _ in range(count):
            vid = self._video_id.next()
            row = {
                "Video_ID": vid,
                "User_ID": random.choice(user_ids)[0],
                "Headline": random.choice(HEADLINES),
                "Source_URL": _random_url(),
                "Upload_Date": _random_date(),
                "Input_Type": random.choice(INPUT_TYPES),
                "Language": random.choice(LANGUAGES),
                "Uploaded_Duration": random.randint(10, 7200),
            }
            log_id = self._logger.log_pending("INSERT", "raw_videos", row_id=str(vid), new_values=row)
            try:
                self._execute(
                    'INSERT INTO raw_videos ("Video_ID", "User_ID", "Headline", "Source_URL", "Upload_Date", "Input_Type", '
                    '"Language", "Uploaded_Duration") VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    list(row.values()),
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

            if channel_names:
                channel = random.choice(channel_names)[0]
                link_row = {"Video_ID": vid, "Channel_Name": channel}
                link_id = self._logger.log_pending(
                    "INSERT",
                    "raw_video_channel",
                    row_id=f"{vid}-{channel}",
                    new_values=link_row,
                )
                try:
                    self._execute(
                        'INSERT INTO raw_video_channel ("Video_ID", "Channel_Name") VALUES (%s,%s) '
                        "ON CONFLICT DO NOTHING",
                        [vid, channel],
                        commit=True,
                    )
                    self._logger.mark_success(link_id)
                except Exception as exc:
                    self._logger.mark_error(link_id, str(exc))

    def _seed_created_assets(self, count: int) -> None:
        video_ids = self._fetchall(
            "SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s",
            [f"{SIM_HEADLINE_PREFIX}%"],
        )
        if not video_ids:
            return
        for _ in range(count):
            aid = self._asset_id.next()
            row = {
                "Asset_ID": aid,
                "Video_ID": random.choice(video_ids)[0],
                "Output_Type": random.choice(OUTPUT_TYPES),
                "Create_Date": _random_date(),
                "Created_Duration": random.randint(5, 3600),
            }
            log_id = self._logger.log_pending("INSERT", "created_assets", row_id=str(aid), new_values=row)
            try:
                self._execute(
                    'INSERT INTO created_assets ("Asset_ID", "Video_ID", "Output_Type", "Create_Date", "Created_Duration") '
                    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    list(row.values()),
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

    def _seed_published_posts(self, count: int) -> None:
        asset_ids = self._fetchall(
            "SELECT \"Asset_ID\" FROM created_assets WHERE \"Video_ID\" IN "
            "(SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s)",
            [f"{SIM_HEADLINE_PREFIX}%"],
        )
        if not asset_ids:
            return
        channel_names = self._fetchall(
            "SELECT \"Channel_Name\" FROM channels WHERE \"Client_Name\" = %s",
            [SIM_CLIENT],
        )
        for _ in range(count):
            pid = self._post_id.next()
            aid = random.choice(asset_ids)[0]
            row = {
                "Post_ID": pid,
                "Asset_ID": aid,
                "Publish_Date": _random_date(),
                "Published_Duration": random.randint(5, 1800),
            }
            log_id = self._logger.log_pending("INSERT", "published_posts", row_id=str(pid), new_values=row)
            try:
                self._execute(
                    'INSERT INTO published_posts ("Post_ID", "Asset_ID", "Publish_Date", "Published_Duration") '
                    "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    list(row.values()),
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

            if channel_names:
                platform = random.choice(PLATFORMS)
                dist_row = {
                    "Post_ID": pid,
                    "Channel_Name": random.choice(channel_names)[0],
                    "Published_Platform": platform,
                    "Published_URL": _random_url(),
                }
                dist_id = self._logger.log_pending(
                    "INSERT", "post_distribution", row_id=str(pid), new_values=dist_row
                )
                try:
                    self._execute(
                        'INSERT INTO post_distribution ("Post_ID", "Channel_Name", "Published_Platform", "Published_URL") '
                        "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        list(dist_row.values()),
                        commit=True,
                    )
                    self._logger.mark_success(dist_id)
                except Exception as exc:
                    self._logger.mark_error(dist_id, str(exc))

    def _loop(self) -> None:
        while self._running:
            try:
                self._run_batch()
            except Exception:
                pass
            time.sleep(self._batch_interval)

    def _run_batch(self) -> None:
        ops = [self._op_insert, self._op_update, self._op_delete]
        weights = [0.85, 0.14, 0.01]
        for _ in range(self._ops_per_batch):
            op = random.choices(ops, weights=weights, k=1)[0]
            try:
                op()
            except Exception:
                pass
        self._quality.run_all_checks()

    def _op_insert(self) -> None:
        table = random.choice(["raw_videos", "created_assets", "published_posts", "users"])
        if table == "users":
            self._seed_users(1)
        elif table == "raw_videos":
            self._seed_raw_videos(1)
        elif table == "created_assets":
            self._seed_created_assets(1)
        elif table == "published_posts":
            self._seed_published_posts(1)

    def _op_update(self) -> None:
        table = random.choice(["raw_videos", "created_assets", "users"])

        if table == "raw_videos":
            rows = self._fetchall(
                "SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s ORDER BY RANDOM() LIMIT 1",
                [f"{SIM_HEADLINE_PREFIX}%"],
            )
            if not rows:
                return
            vid = rows[0][0]
            new_headline = random.choice(HEADLINES) + " (Updated)"
            old = self._fetchall(
                "SELECT \"Headline\" FROM raw_videos WHERE \"Video_ID\" = %s",
                [vid],
            )
            old_val = old[0][0] if old else ""
            log_id = self._logger.log_pending(
                "UPDATE", table, str(vid), old_values={"Headline": old_val}, new_values={"Headline": new_headline}
            )
            try:
                self._execute(
                    'UPDATE raw_videos SET "Headline" = %s WHERE "Video_ID" = %s',
                    [new_headline, vid],
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

        elif table == "created_assets":
            rows = self._fetchall(
                "SELECT \"Asset_ID\" FROM created_assets WHERE \"Video_ID\" IN "
                "(SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s) "
                "ORDER BY RANDOM() LIMIT 1",
                [f"{SIM_HEADLINE_PREFIX}%"],
            )
            if not rows:
                return
            aid = rows[0][0]
            new_type = random.choice(OUTPUT_TYPES)
            old = self._fetchall(
                "SELECT \"Output_Type\" FROM created_assets WHERE \"Asset_ID\" = %s",
                [aid],
            )
            old_val = old[0][0] if old else ""
            log_id = self._logger.log_pending(
                "UPDATE", table, str(aid), old_values={"Output_Type": old_val}, new_values={"Output_Type": new_type}
            )
            try:
                self._execute(
                    'UPDATE created_assets SET "Output_Type" = %s WHERE "Asset_ID" = %s',
                    [new_type, aid],
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

        elif table == "users":
            rows = self._fetchall(
                "SELECT \"User_ID\" FROM users WHERE \"Client_Name\" = %s ORDER BY RANDOM() LIMIT 1",
                [SIM_CLIENT],
            )
            if not rows:
                return
            uid = rows[0][0]
            new_team = random.choice(TEAM_NAMES)
            old = self._fetchall(
                "SELECT \"Team_Name\" FROM users WHERE \"User_ID\" = %s",
                [uid],
            )
            old_val = old[0][0] if old else ""
            log_id = self._logger.log_pending(
                "UPDATE", table, str(uid), old_values={"Team_Name": old_val}, new_values={"Team_Name": new_team}
            )
            try:
                self._execute(
                    'UPDATE users SET "Team_Name" = %s WHERE "User_ID" = %s',
                    [new_team, uid],
                    commit=True,
                )
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

    def _op_delete(self) -> None:
        table = random.choice(["raw_videos", "created_assets"])

        if table == "raw_videos":
            rows = self._fetchall(
                "SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s ORDER BY RANDOM() LIMIT 1",
                [f"{SIM_HEADLINE_PREFIX}%"],
            )
            if not rows:
                return
            vid = rows[0][0]
            log_id = self._logger.log_pending("DELETE", table, str(vid))
            try:
                self._execute('DELETE FROM raw_videos WHERE "Video_ID" = %s', [vid], commit=True)
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

        elif table == "created_assets":
            rows = self._fetchall(
                "SELECT \"Asset_ID\" FROM created_assets WHERE \"Video_ID\" IN "
                "(SELECT \"Video_ID\" FROM raw_videos WHERE \"Headline\" LIKE %s) "
                "ORDER BY RANDOM() LIMIT 1",
                [f"{SIM_HEADLINE_PREFIX}%"],
            )
            if not rows:
                return
            aid = rows[0][0]
            log_id = self._logger.log_pending("DELETE", table, str(aid))
            try:
                self._execute('DELETE FROM created_assets WHERE "Asset_ID" = %s', [aid], commit=True)
                self._logger.mark_success(log_id)
            except Exception as exc:
                self._logger.mark_error(log_id, str(exc))

    def _execute(self, sql: str, params: Iterable[Any] | None = None, commit: bool = False) -> None:
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or [])
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def _fetchall(self, sql: str, params: Iterable[Any] | None = None) -> list[tuple[Any, ...]]:
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or [])
                return cursor.fetchall()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)
