"""
Manage a self-contained local PostgreSQL instance for the Frammer app.

The cluster lives inside `database/.local_postgres`, uses a Unix socket inside
that directory, and defaults to port 5433 to avoid colliding with any system
Postgres instance.

Usage:
    python database/local_postgres.py start
    python database/local_postgres.py stop
    python database/local_postgres.py status
    python database/local_postgres.py env
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LOCAL_DIR = ROOT_DIR / "database" / ".local_postgres"
DATA_DIR = LOCAL_DIR / "data"
SOCKET_DIR = LOCAL_DIR / "socket"
LOG_FILE = LOCAL_DIR / "postgres.log"
BIN_DIR = Path(os.getenv("POSTGRES_BIN_DIR", "/opt/homebrew/opt/postgres/bin"))

PG_CTL = BIN_DIR / "pg_ctl"
INITDB = BIN_DIR / "initdb"
PSQL = BIN_DIR / "psql"
CREATEDB = BIN_DIR / "createdb"

PG_PORT = int(os.getenv("LOCAL_POSTGRES_PORT", "5433"))
PG_USER = os.getenv("LOCAL_POSTGRES_USER") or os.getenv("USER") or "postgres"
PG_DATABASE = os.getenv("LOCAL_POSTGRES_DB", "frammer_database")
SERVER_CONFIG = [
    "-c",
    "shared_memory_type=mmap",
    "-c",
    "dynamic_shared_memory_type=posix",
]


def run(cmd: list[str], check: bool = True, capture_output: bool = False, env: dict[str, str] | None = None):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture_output,
        env=env,
    )


def ensure_binaries() -> None:
    missing = [path.name for path in (PG_CTL, INITDB, PSQL, CREATEDB) if not path.exists()]
    if missing:
        raise RuntimeError(
            f"Missing PostgreSQL binaries: {', '.join(missing)}. Set POSTGRES_BIN_DIR if Homebrew is elsewhere.",
        )


def ensure_directories() -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    SOCKET_DIR.mkdir(parents=True, exist_ok=True)


def cluster_initialized() -> bool:
    return (DATA_DIR / "PG_VERSION").exists()


def init_cluster() -> None:
    if cluster_initialized():
        return

    ensure_directories()
    run(
        [
            str(INITDB),
            "-D",
            str(DATA_DIR),
            "-U",
            PG_USER,
            "-A",
            "trust",
            "--encoding=UTF8",
            "-c",
            "shared_memory_type=mmap",
            "-c",
            "dynamic_shared_memory_type=posix",
        ]
    )


def pg_ctl_status() -> subprocess.CompletedProcess[str]:
    return run(
        [str(PG_CTL), "-D", str(DATA_DIR), "status"],
        check=False,
        capture_output=True,
    )


def is_running() -> bool:
    status = pg_ctl_status()
    return status.returncode == 0


def start_cluster() -> None:
    init_cluster()

    if is_running():
        return

    ensure_directories()
    run(
        [
            str(PG_CTL),
            "-D",
            str(DATA_DIR),
            "-l",
            str(LOG_FILE),
            "-o",
            f"-k {SOCKET_DIR} -p {PG_PORT} {' '.join(SERVER_CONFIG)}",
            "-w",
            "start",
        ]
    )


def stop_cluster() -> None:
    if not cluster_initialized():
        return

    if not is_running():
        return

    run([str(PG_CTL), "-D", str(DATA_DIR), "-w", "stop"])


def psql_cmd(database: str, sql: str) -> list[str]:
    return [
        str(PSQL),
        "-h",
        str(SOCKET_DIR),
        "-p",
        str(PG_PORT),
        "-U",
        PG_USER,
        "-d",
        database,
        "-Atqc",
        sql,
    ]


def database_exists() -> bool:
    result = run(
        psql_cmd("postgres", f"SELECT 1 FROM pg_database WHERE datname = '{PG_DATABASE}'"),
        check=False,
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "1"


def ensure_database() -> None:
    if database_exists():
        return

    run(
        [
            str(CREATEDB),
            "-h",
            str(SOCKET_DIR),
            "-p",
            str(PG_PORT),
            "-U",
            PG_USER,
            PG_DATABASE,
        ]
    )


def public_table_count() -> int:
    result = run(
        psql_cmd(
            PG_DATABASE,
            "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'",
        ),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return 0

    try:
        return int(result.stdout.strip() or "0")
    except ValueError:
        return 0


def bootstrap_if_needed(force: bool = False) -> None:
    if not force and public_table_count() > 0:
        return

    # Prefer the native pg_dump (frammer_data.sql) — includes all tables + auth users.
    # Fall back to the old SQLite bootstrap only if the dump is missing.
    pg_dump_path = ROOT_DIR / "database" / "frammer_data.sql"
    if pg_dump_path.exists():
        print(f"Restoring from {pg_dump_path.name}…")
        run(
            [
                str(PSQL),
                "-h", str(SOCKET_DIR),
                "-p", str(PG_PORT),
                "-U", PG_USER,
                "-d", PG_DATABASE,
                "-f", str(pg_dump_path),
            ],
            check=False,  # owner/ACL lines may error on a fresh cluster — that's fine
        )
        print("Restore complete.")
        return

    # Legacy fallback: SQLite → Postgres migration
    print("frammer_data.sql not found — falling back to SQLite bootstrap…")
    env = os.environ.copy()
    env.update(
        {
            "POSTGRES_HOST": str(SOCKET_DIR),
            "POSTGRES_PORT": str(PG_PORT),
            "POSTGRES_DB": PG_DATABASE,
            "POSTGRES_USER": PG_USER,
            "POSTGRES_PASSWORD": "",
            "POSTGRES_SSLMODE": "disable",
        }
    )
    run([sys.executable, str(ROOT_DIR / "database" / "bootstrap_postgres.py")], env=env)


def print_env() -> None:
    print(f"POSTGRES_HOST={SOCKET_DIR}")
    print(f"POSTGRES_PORT={PG_PORT}")
    print(f"POSTGRES_DB={PG_DATABASE}")
    print(f"POSTGRES_USER={PG_USER}")
    print("POSTGRES_PASSWORD=")
    print("POSTGRES_SSLMODE=disable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local Postgres for Frammer.")
    parser.add_argument("command", choices=("start", "stop", "status", "env"))
    parser.add_argument("--force-bootstrap", action="store_true", help="Re-import the SQLite snapshot even if tables already exist.")
    args = parser.parse_args()

    ensure_binaries()

    if args.command == "start":
        start_cluster()
        ensure_database()
        bootstrap_if_needed(force=args.force_bootstrap)
        print_env()
        print(f"LOG_FILE={LOG_FILE}")
        return

    if args.command == "stop":
        stop_cluster()
        return

    if args.command == "status":
        status = pg_ctl_status()
        print(status.stdout.strip() or status.stderr.strip() or ("running" if status.returncode == 0 else "stopped"))
        print_env()
        return

    print_env()


if __name__ == "__main__":
    main()
