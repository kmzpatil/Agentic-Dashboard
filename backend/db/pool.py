import re
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.config.env import DBConfig


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    row_count: int


_engine: Engine | None = None


def init_pool(db: DBConfig) -> None:
    global _engine
    if _engine is not None:
        return

    # When PGHOST is a Unix socket directory (starts with '/'), passing it in
    # the URL mangles the database name.  Use connect_args instead so psycopg2
    # receives host/port through its own keyword arguments.
    password_part = f":{db.password}" if db.password else ""
    is_socket = db.host.startswith("/")

    if is_socket:
        # URL has no host — psycopg2 gets it via connect_args
        url = f"postgresql+psycopg2://{db.user}{password_part}@/{db.database}"
        connect_args: dict = {"host": db.host, "port": db.port}
    else:
        url = f"postgresql+psycopg2://{db.user}{password_part}@{db.host}:{db.port}/{db.database}"
        connect_args = {}

    _engine = create_engine(
        url,
        connect_args=connect_args,
        pool_size=10,
        max_overflow=5,
        pool_pre_ping=True,
    )


def close_pool() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def _convert_postgres_placeholders(sql: str, params: Sequence[Any]) -> tuple[str, dict[str, Any]]:
    """Convert $1, $2 placeholders to SQLAlchemy named parameters :p1, :p2."""
    pattern = re.compile(r"\$(\d+)")
    matches = pattern.findall(sql)
    if not matches:
        return sql, {}

    # Replace $1 with :p1, $2 with :p2
    converted_sql = pattern.sub(r":p\1", sql)
    
    # Build a dict of params: {"p1": value, "p2": value, ...}
    converted_params = {}
    for pos_str in matches:
        pos = int(pos_str)
        converted_params[f"p{pos}"] = params[pos - 1]
    
    return converted_sql, converted_params


def query(sql: str, params: Sequence[Any] | None = None) -> QueryResult:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")

    safe_params = list(params or [])
    sql_to_run, params_to_run = _convert_postgres_placeholders(sql, safe_params)

    with _engine.connect() as connection:
        try:
            result = connection.execute(text(sql_to_run), params_to_run)
            
            # Fetch all rows if there's a result set (SELECT)
            if result.returns_rows:
                # RealDictCursor equivalent: list of dicts
                rows = [dict(row._mapping) for row in result.fetchall()]
            else:
                rows = []
                
            row_count = result.rowcount
            connection.commit()
            return QueryResult(rows=rows, row_count=row_count)
        except Exception:
            connection.rollback()
            raise
