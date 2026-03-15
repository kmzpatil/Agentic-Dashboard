import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    database: str
    password: str | None


@dataclass(frozen=True)
class AppConfig:
    port: int
    db: DBConfig


def get_config() -> AppConfig:
    port = int(os.getenv("PORT", os.getenv("API_PORT", "4000")))

    host = os.getenv("PGHOST")
    port_raw = os.getenv("PGPORT")
    user = os.getenv("PGUSER")
    database = os.getenv("PGDATABASE")
    password = os.getenv("PGPASSWORD") or None

    if not host or not port_raw or not user or not database:
        raise RuntimeError(
            "Missing required database environment variables: PGHOST, PGPORT, PGUSER, PGDATABASE"
        )

    db = DBConfig(
        host=host,
        port=int(port_raw),
        user=user,
        database=database,
        password=password,
    )

    return AppConfig(port=port, db=db)
