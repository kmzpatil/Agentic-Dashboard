import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config.env import get_config
from backend.db.pool import close_pool, init_pool, query

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


if __name__ == "__main__":
    config = get_config()

    init_pool(config.db)
    try:
        query("SELECT 1")
    finally:
        close_pool()

    port = int(os.getenv("PORT", os.getenv("API_PORT", str(config.port))))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
