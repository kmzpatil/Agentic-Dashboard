"""
config.py
---------
Centralized configuration for the FastAPI backend.
Reads from .env at the project root and frontend/.env.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "frontend" / ".env")


def _first(*keys: str) -> str | None:
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return None


@dataclass
class Settings:
    # Database
    db_host: str = ""
    db_port: int = 5433
    db_name: str = "frammer_database"
    db_user: str = ""
    db_password: str = ""
    db_sslmode: str = "disable"
    database_url: str = ""

    # JWT
    jwt_secret: str = "frammer-local-dev-secret-change-me"
    jwt_expires_hours: int = 8

    # Agent
    agent_base_url: str = "http://127.0.0.1:8000"
    agent_timeout_s: int = 90

    # Server
    port: int = 4000


def load_settings() -> Settings:
    s = Settings()

    s.jwt_secret = os.getenv("JWT_SECRET", s.jwt_secret)
    expires_in = os.getenv("JWT_EXPIRES_IN", "8h")
    s.jwt_expires_hours = int(expires_in.replace("h", "")) if "h" in expires_in else 8

    s.agent_base_url = os.getenv("AGENT_BASE_URL", s.agent_base_url)
    s.agent_timeout_s = int(os.getenv("AGENT_TIMEOUT_MS", "90000")) // 1000
    s.port = int(_first("PORT", "API_PORT") or "4000")

    conn_str = _first("POSTGRES_URL", "PGDATABASE_URL")
    if conn_str:
        s.database_url = conn_str
    else:
        s.db_host = _first("PGHOST", "POSTGRES_HOST") or ""
        s.db_user = _first("PGUSER", "POSTGRES_USER") or ""
        s.db_name = _first("PGDATABASE", "POSTGRES_DB") or "frammer_database"
        s.db_password = _first("PGPASSWORD", "POSTGRES_PASSWORD") or ""
        s.db_port = int(_first("PGPORT", "POSTGRES_PORT") or "5433")
        s.db_sslmode = _first("PGSSLMODE", "POSTGRES_SSLMODE", "DB_SSLMODE") or "disable"

        db_url = _first("DATABASE_URL")
        if db_url and db_url.startswith("postgres"):
            s.database_url = db_url
        elif s.db_host and s.db_user and s.db_name:
            host_part = s.db_host
            query = ""
            if s.db_host.startswith("/"):
                query = f"?host={s.db_host}&sslmode={s.db_sslmode}"
                host_part = "localhost"
            else:
                query = f"?sslmode={s.db_sslmode}"

            pw = f":{s.db_password}" if s.db_password else ""
            s.database_url = f"postgresql+psycopg2://{s.db_user}{pw}@{host_part}:{s.db_port}/{s.db_name}{query}"

    return s


settings = load_settings()
