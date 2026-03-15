"""Reset the self-contained local PostgreSQL cluster used for demos."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.local_postgres import LOCAL_DIR, stop_cluster


def main() -> None:
    try:
        stop_cluster()
    except Exception:
        pass

    if LOCAL_DIR.exists():
        shutil.rmtree(LOCAL_DIR)
    print(f"Removed local Postgres cluster at {LOCAL_DIR}")


if __name__ == "__main__":
    main()
