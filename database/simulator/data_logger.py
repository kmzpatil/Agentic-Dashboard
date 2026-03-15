"""
Data Logger - tracks every database mutation and error in a dedicated log table.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from psycopg2.pool import SimpleConnectionPool

LOG_TABLE = "_simulation_log"

CREATE_LOG_SQL = f"""
CREATE TABLE IF NOT EXISTS {LOG_TABLE} (
    id            BIGSERIAL PRIMARY KEY,
    timestamp     TEXT    NOT NULL,
    operation     TEXT    NOT NULL,
    table_name    TEXT    NOT NULL,
    row_id        TEXT,
    old_values    TEXT,
    new_values    TEXT,
    status        TEXT    NOT NULL DEFAULT 'PENDING',
    error_message TEXT
)
"""


class DataLogger:
    """Append-only structured logger backed by the simulator's Postgres pool."""

    def __init__(self, pool: SimpleConnectionPool) -> None:
        self._pool = pool
        self._execute(CREATE_LOG_SQL, commit=True)

    def log_pending(
        self,
        operation: str,
        table_name: str,
        row_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
    ) -> int:
        row = self._fetchone(
            f"""
            INSERT INTO {LOG_TABLE}
                (timestamp, operation, table_name, row_id, old_values, new_values, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id
            """,
            (
                _now(),
                operation,
                table_name,
                row_id,
                _json(old_values),
                _json(new_values),
            ),
            commit=True,
        )
        return int(row[0]) if row else 0

    def mark_success(self, log_id: int) -> None:
        self._execute(
            f"UPDATE {LOG_TABLE} SET status = 'SUCCESS', timestamp = %s WHERE id = %s",
            (_now(), log_id),
            commit=True,
        )

    def mark_error(self, log_id: int, error_message: str) -> None:
        self._execute(
            f"UPDATE {LOG_TABLE} SET status = 'ERROR', error_message = %s, timestamp = %s WHERE id = %s",
            (error_message, _now(), log_id),
            commit=True,
        )

    def log_quality_issue(
        self,
        table_name: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> int:
        row = self._fetchone(
            f"""
            INSERT INTO {LOG_TABLE}
                (timestamp, operation, table_name, row_id, old_values, new_values, status, error_message)
            VALUES (%s, 'QUALITY_CHECK', %s, NULL, NULL, %s, 'QUALITY_ISSUE', %s)
            RETURNING id
            """,
            (_now(), table_name, _json(details), message),
            commit=True,
        )
        return int(row[0]) if row else 0

    def log_info(self, operation: str, table_name: str, message: str) -> int:
        row = self._fetchone(
            f"""
            INSERT INTO {LOG_TABLE}
                (timestamp, operation, table_name, status, error_message)
            VALUES (%s, %s, %s, 'INFO', %s)
            RETURNING id
            """,
            (_now(), operation, table_name, message),
            commit=True,
        )
        return int(row[0]) if row else 0

    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: str | None = None,
        table_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        query = f"SELECT * FROM {LOG_TABLE} WHERE 1=1"
        params: list[Any] = []
        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)
        if table_filter:
            query += " AND table_name = %s"
            params.append(table_filter)
        query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        params += [limit, offset]

        rows = self._fetchall(query, params)
        if not rows:
            return []
        columns = [
            "id",
            "timestamp",
            "operation",
            "table_name",
            "row_id",
            "old_values",
            "new_values",
            "status",
            "error_message",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def get_counts(self) -> dict[str, int]:
        rows = self._fetchall(
            f"SELECT status, COUNT(*) FROM {LOG_TABLE} GROUP BY status"
        )
        return {row[0]: int(row[1]) for row in rows}

    def get_timeseries_metrics(self, limit_points: int = 60) -> dict[str, Any]:
        rows = self._fetchall(
            f"""
            SELECT
                substr(timestamp, 1, 18) || '0' as bucket,
                SUM(CASE WHEN operation = 'INSERT' THEN 1 ELSE 0 END) as inserts,
                SUM(CASE WHEN operation = 'UPDATE' THEN 1 ELSE 0 END) as updates,
                SUM(CASE WHEN operation = 'DELETE' THEN 1 ELSE 0 END) as deletes
            FROM {LOG_TABLE}
            WHERE status = 'SUCCESS'
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT %s
            """,
            (limit_points,),
        )
        rows.reverse()

        return {
            "labels": [r[0] for r in rows],
            "inserts": [r[1] for r in rows],
            "updates": [r[2] for r in rows],
            "deletes": [r[3] for r in rows],
        }

    def clear(self) -> None:
        self._execute(f"DELETE FROM {LOG_TABLE}", commit=True)

    def _execute(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
        commit: bool = False,
    ) -> None:
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

    def _fetchone(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
        commit: bool = False,
    ) -> tuple[Any, ...] | None:
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or [])
                row = cursor.fetchone()
            if commit:
                conn.commit()
            return row
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def _fetchall(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[tuple[Any, ...]]:
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(obj: Any | None) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, default=str)
