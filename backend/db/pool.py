import re
from dataclasses import dataclass
from typing import Any, Sequence

from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

from backend.config.env import DBConfig


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    row_count: int


_pool: SimpleConnectionPool | None = None


def init_pool(db: DBConfig) -> None:
    global _pool
    if _pool is not None:
        return

    _pool = SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=db.host,
        port=db.port,
        user=db.user,
        dbname=db.database,
        password=db.password,
    )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def _convert_postgres_placeholders(sql: str, params: Sequence[Any]) -> tuple[str, list[Any]]:
    pattern = re.compile(r"\$(\d+)")
    matches = pattern.findall(sql)
    if not matches:
        return sql, list(params)

    converted_sql = pattern.sub("%s", sql)
    converted_params = [params[int(position) - 1] for position in matches]
    return converted_sql, converted_params


def query(sql: str, params: Sequence[Any] | None = None) -> QueryResult:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")

    safe_params = list(params or [])
    sql_to_run, params_to_run = _convert_postgres_placeholders(sql, safe_params)

    connection = _pool.getconn()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql_to_run, params_to_run)
            rows = cursor.fetchall() if cursor.description else []
            row_count = cursor.rowcount
            connection.commit()
            return QueryResult(rows=[dict(row) for row in rows], row_count=row_count)
    except Exception:
        connection.rollback()
        raise
    finally:
        _pool.putconn(connection)
