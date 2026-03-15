"""
Isolated simulator engine.

The simulator is intentionally disconnected from the analytics database. It keeps
its own in-process data store, log stream, and quality checks so Labs can run
without mutating KPI tables.
"""

from __future__ import annotations

import copy
import random
import string
import threading
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any


SIM_CLIENT = "Simulated Client"
SIM_PREFIX = "SIM"
SIM_HEADLINE_PREFIX = f"{SIM_PREFIX}:"

TARGET_TABLES = [
    "clients",
    "users",
    "channels",
    "raw_videos",
    "raw_video_channel",
    "created_assets",
    "published_posts",
    "post_distribution",
]

TABLE_COLUMNS: dict[str, list[dict[str, Any]]] = {
    "clients": [
        {"name": "Client_Name", "type": "text", "notnull": True, "pk": True},
    ],
    "users": [
        {"name": "User_ID", "type": "integer", "notnull": True, "pk": True},
        {"name": "User_Name", "type": "text", "notnull": False, "pk": False},
        {"name": "Team_Name", "type": "text", "notnull": False, "pk": False},
        {"name": "Client_Name", "type": "text", "notnull": False, "pk": False},
    ],
    "channels": [
        {"name": "Channel_Name", "type": "text", "notnull": True, "pk": True},
        {"name": "Client_Name", "type": "text", "notnull": False, "pk": False},
    ],
    "raw_videos": [
        {"name": "Video_ID", "type": "integer", "notnull": True, "pk": True},
        {"name": "User_ID", "type": "integer", "notnull": False, "pk": False},
        {"name": "Headline", "type": "text", "notnull": False, "pk": False},
        {"name": "Source_URL", "type": "text", "notnull": False, "pk": False},
        {"name": "Upload_Date", "type": "text", "notnull": False, "pk": False},
        {"name": "Input_Type", "type": "text", "notnull": False, "pk": False},
        {"name": "Language", "type": "text", "notnull": False, "pk": False},
        {"name": "Uploaded_Duration", "type": "integer", "notnull": False, "pk": False},
    ],
    "raw_video_channel": [
        {"name": "Video_ID", "type": "integer", "notnull": True, "pk": True},
        {"name": "Channel_Name", "type": "text", "notnull": True, "pk": True},
    ],
    "created_assets": [
        {"name": "Asset_ID", "type": "integer", "notnull": True, "pk": True},
        {"name": "Video_ID", "type": "integer", "notnull": False, "pk": False},
        {"name": "Output_Type", "type": "text", "notnull": False, "pk": False},
        {"name": "Create_Date", "type": "text", "notnull": False, "pk": False},
        {"name": "Created_Duration", "type": "integer", "notnull": False, "pk": False},
    ],
    "published_posts": [
        {"name": "Post_ID", "type": "integer", "notnull": True, "pk": True},
        {"name": "Asset_ID", "type": "integer", "notnull": False, "pk": False},
        {"name": "Publish_Date", "type": "text", "notnull": False, "pk": False},
        {"name": "Published_Duration", "type": "integer", "notnull": False, "pk": False},
    ],
    "post_distribution": [
        {"name": "Distribution_ID", "type": "integer", "notnull": True, "pk": True},
        {"name": "Post_ID", "type": "integer", "notnull": False, "pk": False},
        {"name": "Channel_Name", "type": "text", "notnull": False, "pk": False},
        {"name": "Published_Platform", "type": "text", "notnull": False, "pk": False},
        {"name": "Published_URL", "type": "text", "notnull": False, "pk": False},
    ],
}

PRIMARY_KEYS: dict[str, list[str]] = {
    "clients": ["Client_Name"],
    "users": ["User_ID"],
    "channels": ["Channel_Name"],
    "raw_videos": ["Video_ID"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Distribution_ID"],
}

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Video_ID"],
    "users": ["User_ID"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Distribution_ID"],
    "channels": ["Channel_Name"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
}

FOREIGN_KEYS: list[tuple[str, str, str, str]] = [
    ("raw_videos", "User_ID", "users", "User_ID"),
    ("created_assets", "Video_ID", "raw_videos", "Video_ID"),
    ("published_posts", "Asset_ID", "created_assets", "Asset_ID"),
    ("post_distribution", "Post_ID", "published_posts", "Post_ID"),
    ("raw_video_channel", "Video_ID", "raw_videos", "Video_ID"),
    ("raw_video_channel", "Channel_Name", "channels", "Channel_Name"),
]

NON_NEGATIVE_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Uploaded_Duration"],
    "created_assets": ["Created_Duration"],
    "published_posts": ["Published_Duration"],
}

DATE_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Upload_Date"],
    "created_assets": ["Create_Date"],
    "published_posts": ["Publish_Date"],
}

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {table: [] for table in TARGET_TABLES}
        self._logs: list[dict[str, Any]] = []
        self._log_id = _IDCounter(1)
        self._distribution_id = _IDCounter(1)
        self._user_id = _IDCounter(1)
        self._video_id = _IDCounter(1)
        self._asset_id = _IDCounter(1)
        self._post_id = _IDCounter(1)

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._ops_per_batch = 5
        self._batch_interval = 2.0

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
        self._tables = {table: [] for table in TARGET_TABLES}
        self._logs = []
        self._distribution_id = _IDCounter(1)
        self._user_id = _IDCounter(1)
        self._video_id = _IDCounter(1)
        self._asset_id = _IDCounter(1)
        self._post_id = _IDCounter(1)
        if was_running:
            self.start(self._ops_per_batch, self._batch_interval)

    def get_state(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "tables": {table: len(rows) for table, rows in self._tables.items()},
            "log_counts": dict(Counter(log["status"] for log in self._logs)),
            "settings": {
                "ops_per_batch": self._ops_per_batch,
                "interval": self._batch_interval,
            },
        }

    def get_tables(self) -> list[dict[str, Any]]:
        return [
            {
                "name": table,
                "columns": copy.deepcopy(TABLE_COLUMNS[table]),
                "row_count": len(self._tables[table]),
            }
            for table in TARGET_TABLES
        ]

    def get_table_rows(self, table_name: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        if table_name not in self._tables:
            return {"error": "Table not found", "rows": [], "columns": []}
        rows = self._tables[table_name][offset: offset + limit]
        columns = [column["name"] for column in TABLE_COLUMNS[table_name]]
        return {"columns": columns, "rows": copy.deepcopy(rows), "total": len(self._tables[table_name])}

    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: str | None = None,
        table_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = list(reversed(self._logs))
        if status_filter:
            rows = [row for row in rows if row["status"] == status_filter]
        if table_filter:
            rows = [row for row in rows if row["table_name"] == table_filter]
        return copy.deepcopy(rows[offset: offset + limit])

    def get_quality_report(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        issues += self._check_nulls()
        issues += self._check_duplicate_pks()
        issues += self._check_referential_integrity()
        issues += self._check_non_negative()
        issues += self._check_date_formats()

        tables: dict[str, dict[str, Any]] = {}
        total_rows = 0
        for table_name in TARGET_TABLES:
            row_count = len(self._tables[table_name])
            total_rows += row_count
            table_issues = [issue for issue in issues if issue["table"] == table_name]
            score = 100.0 if row_count == 0 else max(0.0, 100.0 - (len(table_issues) / row_count) * 100)
            tables[table_name] = {
                "row_count": row_count,
                "issue_count": len(table_issues),
                "score": round(score, 1),
                "issues": table_issues,
            }

        overall_score = 100.0 if total_rows == 0 else max(0.0, 100.0 - (len(issues) / total_rows) * 100)
        return {
            "overall_score": round(overall_score, 1),
            "total_issues": len(issues),
            "total_rows": total_rows,
            "tables": tables,
        }

    def get_timeseries_metrics(self) -> dict[str, Any]:
        buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"INSERT": 0, "UPDATE": 0, "DELETE": 0})
        for log in self._logs:
            if log["status"] != "SUCCESS":
                continue
            bucket = log["timestamp"][:16]
            if log["operation"] in {"INSERT", "UPDATE", "DELETE"}:
                buckets[bucket][log["operation"]] += 1

        labels = sorted(buckets.keys())[-60:]
        return {
            "labels": labels,
            "inserts": [buckets[label]["INSERT"] for label in labels],
            "updates": [buckets[label]["UPDATE"] for label in labels],
            "deletes": [buckets[label]["DELETE"] for label in labels],
        }

    def seed(self, count: int = 10) -> None:
        self._seed_clients()
        self._seed_users(count)
        self._seed_channels()
        self._seed_raw_videos(count * 2)
        self._seed_created_assets(count)
        self._seed_published_posts(count)

    def _pk_tuple(self, table: str, row: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(row.get(column) for column in PRIMARY_KEYS[table])

    def _insert_row(self, table: str, row: dict[str, Any], *, operation: str = "INSERT") -> bool:
        if any(self._pk_tuple(table, existing) == self._pk_tuple(table, row) for existing in self._tables[table]):
            return False
        log_id = self._log_pending(operation, table, row_id=self._row_id(table, row), new_values=row)
        self._tables[table].append(copy.deepcopy(row))
        self._mark_success(log_id)
        return True

    def _log_pending(
        self,
        operation: str,
        table_name: str,
        *,
        row_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
    ) -> int:
        log_id = self._log_id.next()
        self._logs.append(
            {
                "id": log_id,
                "timestamp": _now(),
                "operation": operation,
                "table_name": table_name,
                "row_id": row_id,
                "old_values": copy.deepcopy(old_values),
                "new_values": copy.deepcopy(new_values),
                "status": "PENDING",
                "error_message": None,
            }
        )
        return log_id

    def _mark_success(self, log_id: int) -> None:
        for log in self._logs:
            if log["id"] == log_id:
                log["status"] = "SUCCESS"
                log["timestamp"] = _now()
                return

    def _mark_error(self, log_id: int, message: str) -> None:
        for log in self._logs:
            if log["id"] == log_id:
                log["status"] = "ERROR"
                log["error_message"] = message
                log["timestamp"] = _now()
                return

    def _row_id(self, table: str, row: dict[str, Any]) -> str:
        return "|".join(str(row.get(column, "")) for column in PRIMARY_KEYS[table])

    def _seed_clients(self) -> None:
        self._insert_row("clients", {"Client_Name": SIM_CLIENT})

    def _seed_users(self, count: int) -> None:
        for _ in range(count):
            self._insert_row(
                "users",
                {
                    "User_ID": self._user_id.next(),
                    "User_Name": f"{SIM_PREFIX} {random.choice(FIRST_NAMES)} {_random_string(4)}",
                    "Team_Name": random.choice(TEAM_NAMES),
                    "Client_Name": SIM_CLIENT,
                },
            )

    def _seed_channels(self) -> None:
        for channel_name in CHANNEL_NAMES:
            self._insert_row(
                "channels",
                {
                    "Channel_Name": channel_name,
                    "Client_Name": SIM_CLIENT,
                },
            )

    def _seed_raw_videos(self, count: int) -> None:
        user_ids = [row["User_ID"] for row in self._tables["users"]]
        channel_names = [row["Channel_Name"] for row in self._tables["channels"]]
        if not user_ids:
            return
        for _ in range(count):
            video_id = self._video_id.next()
            self._insert_row(
                "raw_videos",
                {
                    "Video_ID": video_id,
                    "User_ID": random.choice(user_ids),
                    "Headline": random.choice(HEADLINES),
                    "Source_URL": _random_url(),
                    "Upload_Date": _random_date(),
                    "Input_Type": random.choice(INPUT_TYPES),
                    "Language": random.choice(LANGUAGES),
                    "Uploaded_Duration": random.randint(10, 7200),
                },
            )
            if channel_names:
                self._insert_row(
                    "raw_video_channel",
                    {
                        "Video_ID": video_id,
                        "Channel_Name": random.choice(channel_names),
                    },
                )

    def _seed_created_assets(self, count: int) -> None:
        video_ids = [row["Video_ID"] for row in self._tables["raw_videos"]]
        if not video_ids:
            return
        for _ in range(count):
            self._insert_row(
                "created_assets",
                {
                    "Asset_ID": self._asset_id.next(),
                    "Video_ID": random.choice(video_ids),
                    "Output_Type": random.choice(OUTPUT_TYPES),
                    "Create_Date": _random_date(),
                    "Created_Duration": random.randint(5, 3600),
                },
            )

    def _seed_published_posts(self, count: int) -> None:
        asset_ids = [row["Asset_ID"] for row in self._tables["created_assets"]]
        channel_names = [row["Channel_Name"] for row in self._tables["channels"]]
        if not asset_ids:
            return
        for _ in range(count):
            post_id = self._post_id.next()
            self._insert_row(
                "published_posts",
                {
                    "Post_ID": post_id,
                    "Asset_ID": random.choice(asset_ids),
                    "Publish_Date": _random_date(),
                    "Published_Duration": random.randint(5, 1800),
                },
            )
            if channel_names:
                self._insert_row(
                    "post_distribution",
                    {
                        "Distribution_ID": self._distribution_id.next(),
                        "Post_ID": post_id,
                        "Channel_Name": random.choice(channel_names),
                        "Published_Platform": random.choice(PLATFORMS),
                        "Published_URL": _random_url(),
                    },
                )

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
            random.choices(ops, weights=weights, k=1)[0]()

    def _op_insert(self) -> None:
        table = random.choice(["raw_videos", "created_assets", "published_posts", "users"])
        if table == "users":
            self._seed_users(1)
        elif table == "raw_videos":
            self._seed_raw_videos(1)
        elif table == "created_assets":
            self._seed_created_assets(1)
        else:
            self._seed_published_posts(1)

    def _op_update(self) -> None:
        table = random.choice(["raw_videos", "created_assets", "users"])
        rows = self._tables[table]
        if not rows:
            return
        row = random.choice(rows)

        if table == "raw_videos":
            old_values = {"Headline": row["Headline"]}
            row["Headline"] = f"{random.choice(HEADLINES)} (Updated)"
            new_values = {"Headline": row["Headline"]}
        elif table == "created_assets":
            old_values = {"Output_Type": row["Output_Type"]}
            row["Output_Type"] = random.choice(OUTPUT_TYPES)
            new_values = {"Output_Type": row["Output_Type"]}
        else:
            old_values = {"Team_Name": row["Team_Name"]}
            row["Team_Name"] = random.choice(TEAM_NAMES)
            new_values = {"Team_Name": row["Team_Name"]}

        log_id = self._log_pending("UPDATE", table, row_id=self._row_id(table, row), old_values=old_values, new_values=new_values)
        self._mark_success(log_id)

    def _op_delete(self) -> None:
        table = random.choice(["raw_videos", "created_assets"])
        if not self._tables[table]:
            return

        row = random.choice(self._tables[table])
        log_id = self._log_pending("DELETE", table, row_id=self._row_id(table, row))

        if table == "raw_videos":
            video_id = row["Video_ID"]
            asset_ids = [asset["Asset_ID"] for asset in self._tables["created_assets"] if asset["Video_ID"] == video_id]
            post_ids = [post["Post_ID"] for post in self._tables["published_posts"] if post["Asset_ID"] in asset_ids]
            self._tables["post_distribution"] = [item for item in self._tables["post_distribution"] if item["Post_ID"] not in post_ids]
            self._tables["published_posts"] = [item for item in self._tables["published_posts"] if item["Post_ID"] not in post_ids]
            self._tables["created_assets"] = [item for item in self._tables["created_assets"] if item["Asset_ID"] not in asset_ids]
            self._tables["raw_video_channel"] = [item for item in self._tables["raw_video_channel"] if item["Video_ID"] != video_id]
            self._tables["raw_videos"] = [item for item in self._tables["raw_videos"] if item["Video_ID"] != video_id]
        else:
            asset_id = row["Asset_ID"]
            post_ids = [post["Post_ID"] for post in self._tables["published_posts"] if post["Asset_ID"] == asset_id]
            self._tables["post_distribution"] = [item for item in self._tables["post_distribution"] if item["Post_ID"] not in post_ids]
            self._tables["published_posts"] = [item for item in self._tables["published_posts"] if item["Post_ID"] not in post_ids]
            self._tables["created_assets"] = [item for item in self._tables["created_assets"] if item["Asset_ID"] != asset_id]

        self._mark_success(log_id)

    def _check_nulls(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, required_columns in REQUIRED_COLUMNS.items():
            for row in self._tables[table]:
                for column in required_columns:
                    if row.get(column) is None:
                        issues.append(
                            {
                                "table": table,
                                "check": "NULL_VIOLATION",
                                "column": column,
                                "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                                "message": f"Required column '{column}' is NULL",
                            }
                        )
        return issues

    def _check_duplicate_pks(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, pk_columns in PRIMARY_KEYS.items():
            counts = Counter(tuple(row.get(column) for column in pk_columns) for row in self._tables[table])
            for values, count in counts.items():
                if count <= 1:
                    continue
                issues.append(
                    {
                        "table": table,
                        "check": "DUPLICATE_PK",
                        "columns": pk_columns,
                        "values": list(values),
                        "duplicate_count": count,
                        "message": f"Duplicate PK detected for {table}",
                    }
                )
        return issues

    def _check_referential_integrity(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for child_table, child_column, parent_table, parent_column in FOREIGN_KEYS:
            parent_values = {row.get(parent_column) for row in self._tables[parent_table]}
            for row in self._tables[child_table]:
                value = row.get(child_column)
                if value is None or value in parent_values:
                    continue
                issues.append(
                    {
                        "table": child_table,
                        "check": "FK_VIOLATION",
                        "column": child_column,
                        "value": value,
                        "references": f"{parent_table}.{parent_column}",
                        "pk": {key: row.get(key) for key in PRIMARY_KEYS[child_table]},
                        "message": f"Orphan FK: {child_table}.{child_column}={value}",
                    }
                )
        return issues

    def _check_non_negative(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in NON_NEGATIVE_COLUMNS.items():
            for row in self._tables[table]:
                for column in columns:
                    value = row.get(column)
                    if value is not None and value < 0:
                        issues.append(
                            {
                                "table": table,
                                "check": "NEGATIVE_VALUE",
                                "column": column,
                                "value": value,
                                "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                                "message": f"Negative value in {table}.{column}",
                            }
                        )
        return issues

    def _check_date_formats(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in DATE_COLUMNS.items():
            for row in self._tables[table]:
                for column in columns:
                    value = row.get(column)
                    if value is None:
                        continue
                    try:
                        datetime.strptime(str(value), "%Y-%m-%d")
                    except ValueError:
                        issues.append(
                            {
                                "table": table,
                                "check": "INVALID_DATE",
                                "column": column,
                                "value": value,
                                "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                                "message": f"Invalid date in {table}.{column}",
                            }
                        )
        return issues
