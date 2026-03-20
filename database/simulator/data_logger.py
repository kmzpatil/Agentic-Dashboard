"""
Data Logger - tracks every database mutation and error in a dedicated log table.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

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
    """Append-only structured logger backed by the simulator's Postgres engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
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
            VALUES (:ts, :op, :tbl, :rid, :old, :new, 'PENDING')
            RETURNING id
            """,
            {
                "ts": _now(),
                "op": operation,
                "tbl": table_name,
                "rid": row_id,
                "old": _json(old_values),
                "new": _json(new_values),
            },
            commit=True,
        )
        return int(row[0]) if row else 0

    def mark_success(self, log_id: int) -> None:
        self._execute(
            f"UPDATE {LOG_TABLE} SET status = 'SUCCESS', timestamp = :ts WHERE id = :id",
            {"ts": _now(), "id": log_id},
            commit=True,
        )

    def mark_error(self, log_id: int, error_message: str) -> None:
        self._execute(
            f"UPDATE {LOG_TABLE} SET status = 'ERROR', error_message = :err, timestamp = :ts WHERE id = :id",
            {"err": error_message, "ts": _now(), "id": log_id},
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
            VALUES (:ts, 'QUALITY_CHECK', :tbl, NULL, NULL, :details, 'QUALITY_ISSUE', :err)
            RETURNING id
            """,
            {"ts": _now(), "tbl": table_name, "details": _json(details), "err": message},
            commit=True,
        )
        return int(row[0]) if row else 0

    def log_info(self, operation: str, table_name: str, message: str) -> int:
        row = self._fetchone(
            f"""
            INSERT INTO {LOG_TABLE}
                (timestamp, operation, table_name, status, error_message)
            VALUES (:ts, :op, :tbl, 'INFO', :msg)
            RETURNING id
            """,
            {"ts": _now(), "op": operation, "tbl": table_name, "msg": message},
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
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status_filter:
            query += " AND status = :status"
            params["status"] = status_filter
        if table_filter:
            query += " AND table_name = :table"
            params["table"] = table_filter
        query += " ORDER BY id DESC LIMIT :limit OFFSET :offset"

        rows = self._fetchall(query, params)
        if not rows:
            return []
        
        # SQLAlchemy rows can be converted to dicts via _mapping
        return [dict(row._mapping) for row in rows]

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
            LIMIT :lim
            """,
            {"lim": limit_points},
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
        params: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> None:
        with self._engine.connect() as conn:
            try:
                conn.execute(text(sql), params or {})
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise

    def _fetchone(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> Any | None:
        with self._engine.connect() as conn:
            try:
                result = conn.execute(text(sql), params or {})
                row = result.fetchone()
                if commit:
                    conn.commit()
                return row
            except Exception:
                conn.rollback()
                raise

    def _fetchall(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        with self._engine.connect() as conn:
            try:
                result = conn.execute(text(sql), params or {})
                return result.fetchall()
            except Exception:
                # No commit needed for fetchall usually, but rollback if inside transaction
                conn.rollback()
                raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(obj: Any | None) -> str | None:
    if obj is None:
        return None
    return json.dumps(obj, default=str)
