"""
Data Quality Engine - validates the Postgres database after each batch.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from psycopg2.pool import SimpleConnectionPool

from .data_logger import DataLogger

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Video_ID"],
    "users": ["User_ID"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Post_ID"],
    "channels": ["Channel_Name"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
}

PRIMARY_KEYS: dict[str, list[str]] = {
    "raw_videos": ["Video_ID"],
    "users": ["User_ID"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Post_ID"],
    "channels": ["Channel_Name"],
    "clients": ["Client_Name"],
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

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class QualityEngine:
    """Runs data-quality checks on the Postgres database."""

    def __init__(self, pool: SimpleConnectionPool, logger: DataLogger) -> None:
        self._pool = pool
        self._logger = logger

    def run_all_checks(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        issues += self._check_nulls()
        issues += self._check_duplicate_pks()
        issues += self._check_referential_integrity()
        issues += self._check_non_negative()
        issues += self._check_date_formats()

        tables = self._all_tables()
        table_scores: dict[str, dict[str, Any]] = {}
        for table in tables:
            table_issues = [i for i in issues if i["table"] == table]
            row_count = self._row_count(table)
            score = max(0.0, 1.0 - len(table_issues) / max(row_count, 1))
            table_scores[table] = {
                "row_count": row_count,
                "issue_count": len(table_issues),
                "score": round(score * 100, 1),
                "issues": table_issues,
            }

        total_issues = len(issues)
        total_rows = sum(s["row_count"] for s in table_scores.values())
        overall_score = max(0.0, 1.0 - total_issues / max(total_rows, 1))

        return {
            "overall_score": round(overall_score * 100, 1),
            "total_issues": total_issues,
            "total_rows": total_rows,
            "tables": table_scores,
        }

    def _check_nulls(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, cols in REQUIRED_COLUMNS.items():
            if not self._table_exists(table):
                continue
            pk_cols = PRIMARY_KEYS.get(table, [])
            pk_sql = ", ".join(f'"{c}"' for c in pk_cols) if pk_cols else ""
            for col in cols:
                select_cols = pk_sql or f'"{col}"'
                rows = self._fetchall(
                    f'SELECT {select_cols} FROM "{table}" WHERE "{col}" IS NULL'
                )
                for row in rows:
                    pk_values = _pk_dict(pk_cols, row) if pk_cols else {col: None}
                    issue = {
                        "table": table,
                        "check": "NULL_VIOLATION",
                        "column": col,
                        "pk": pk_values,
                        "message": f"Required column '{col}' is NULL in {table} {pk_values}",
                    }
                    issues.append(issue)
                    self._logger.log_quality_issue(table, issue["message"], issue)
        return issues

    def _check_duplicate_pks(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, pk_cols in PRIMARY_KEYS.items():
            if not self._table_exists(table):
                continue
            cols_sql = ", ".join(f'"{c}"' for c in pk_cols)
            rows = self._fetchall(
                f'SELECT {cols_sql}, COUNT(*) as cnt FROM "{table}" '
                f"GROUP BY {cols_sql} HAVING COUNT(*) > 1"
            )
            for row in rows:
                dup_vals = row[:-1]
                cnt = row[-1]
                issue = {
                    "table": table,
                    "check": "DUPLICATE_PK",
                    "columns": pk_cols,
                    "values": list(dup_vals),
                    "duplicate_count": cnt,
                    "message": f"Duplicate PK {dict(zip(pk_cols, dup_vals))} appears {cnt} times",
                }
                issues.append(issue)
                self._logger.log_quality_issue(table, issue["message"], issue)
        return issues

    def _check_referential_integrity(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for child_tbl, child_col, parent_tbl, parent_col in FOREIGN_KEYS:
            if not self._table_exists(child_tbl) or not self._table_exists(parent_tbl):
                continue
            pk_cols = PRIMARY_KEYS.get(child_tbl, [])
            pk_sql = ", ".join(f'c."{c}"' for c in pk_cols) if pk_cols else f'c."{child_col}"'
            rows = self._fetchall(
                f'SELECT {pk_sql}, c."{child_col}" FROM "{child_tbl}" c '
                f'LEFT JOIN "{parent_tbl}" p ON c."{child_col}" = p."{parent_col}" '
                f'WHERE p."{parent_col}" IS NULL AND c."{child_col}" IS NOT NULL'
            )
            for row in rows:
                pk_values = _pk_dict(pk_cols, row[:-1]) if pk_cols else {child_col: row[0]}
                orphan_value = row[-1]
                issue = {
                    "table": child_tbl,
                    "check": "FK_VIOLATION",
                    "column": child_col,
                    "value": orphan_value,
                    "references": f"{parent_tbl}.{parent_col}",
                    "pk": pk_values,
                    "message": (
                        f"Orphan FK: {child_tbl}.{child_col}={orphan_value} not in {parent_tbl}.{parent_col}"
                    ),
                }
                issues.append(issue)
                self._logger.log_quality_issue(child_tbl, issue["message"], issue)
        return issues

    def _check_non_negative(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, cols in NON_NEGATIVE_COLUMNS.items():
            if not self._table_exists(table):
                continue
            pk_cols = PRIMARY_KEYS.get(table, [])
            pk_sql = ", ".join(f'"{c}"' for c in pk_cols) if pk_cols else ""
            for col in cols:
                select_cols = f"{pk_sql}, \"{col}\"" if pk_sql else f'"{col}"'
                rows = self._fetchall(
                    f'SELECT {select_cols} FROM "{table}" WHERE "{col}" < 0'
                )
                for row in rows:
                    if pk_cols:
                        pk_values = _pk_dict(pk_cols, row[:-1])
                        value = row[-1]
                    else:
                        pk_values = {}
                        value = row[0]
                    issue = {
                        "table": table,
                        "check": "NEGATIVE_VALUE",
                        "column": col,
                        "value": value,
                        "pk": pk_values,
                        "message": f"Negative value {value} in {table}.{col} {pk_values}",
                    }
                    issues.append(issue)
                    self._logger.log_quality_issue(table, issue["message"], issue)
        return issues

    def _check_date_formats(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, cols in DATE_COLUMNS.items():
            if not self._table_exists(table):
                continue
            pk_cols = PRIMARY_KEYS.get(table, [])
            pk_sql = ", ".join(f'"{c}"' for c in pk_cols) if pk_cols else ""
            for col in cols:
                select_cols = f"{pk_sql}, \"{col}\"" if pk_sql else f'"{col}"'
                rows = self._fetchall(
                    f'SELECT {select_cols} FROM "{table}" WHERE "{col}" IS NOT NULL'
                )
                for row in rows:
                    if pk_cols:
                        pk_values = _pk_dict(pk_cols, row[:-1])
                        value = row[-1]
                    else:
                        pk_values = {}
                        value = row[0]
                    if not DATE_REGEX.match(str(value)):
                        issue = {
                            "table": table,
                            "check": "INVALID_DATE",
                            "column": col,
                            "value": value,
                            "pk": pk_values,
                            "message": (
                                f"Invalid date '{value}' in {table}.{col} {pk_values}, expected YYYY-MM-DD"
                            ),
                        }
                        issues.append(issue)
                        self._logger.log_quality_issue(table, issue["message"], issue)
        return issues

    def _table_exists(self, table: str) -> bool:
        rows = self._fetchall(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
        return bool(rows)

    def _all_tables(self) -> list[str]:
        rows = self._fetchall(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "AND table_name NOT LIKE %s",
            [r'\_%'],
        )
        return [r[0] for r in rows]

    def _row_count(self, table: str) -> int:
        rows = self._fetchall(f'SELECT COUNT(*) FROM "{table}"')
        return int(rows[0][0]) if rows else 0

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


def _pk_dict(columns: list[str], values: Iterable[Any]) -> dict[str, Any]:
    return dict(zip(columns, values))
