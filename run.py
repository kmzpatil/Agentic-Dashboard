#!/usr/bin/env python3
"""
run.py — cross-platform bootstrap and run script for the Frammer stack.
Works on Windows (CMD, PowerShell), Linux, and macOS.

Usage:
    python run.py [options]

Options:
    --install-only   Install dependencies and exit
    --no-db          Skip database start
    --reset-db       Reset the local Postgres cluster
    --seed-demo      Seed demo/auth data
    --backend-only   Start backend only
    --frontend-only  Start frontend only
    --prod-build     Build frontend for production and exit
"""

from __future__ import annotations

import argparse
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
LOG_DIR = ROOT_DIR / ".run_logs"
VENV_DIR = ROOT_DIR / ".venv"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"

IS_WINDOWS = platform.system() == "Windows"


def find_system_python() -> str | None:
    """Find a usable Python interpreter on the system."""
    candidates = ["python3", "python", "py"]
    for name in candidates:
        try:
            result = subprocess.run(
                [name, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def get_venv_python() -> str | None:
    """Return the venv Python path if it exists."""
    candidates = [
        VENV_DIR / "Scripts" / "python.exe",  # Windows
        VENV_DIR / "bin" / "python",           # Unix
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return None


def create_venv(system_python: str) -> str:
    """Create the virtual environment and return the venv Python path."""
    print(f"Creating virtual environment at {VENV_DIR}")
    cmd = [system_python]
    # Windows py launcher needs -3 flag
    if Path(system_python).stem.lower() in ("py", "py.exe"):
        cmd.append("-3")
    cmd.extend(["-m", "venv", str(VENV_DIR)])
    subprocess.run(cmd, check=True)

    venv_python = get_venv_python()
    if not venv_python:
        print("ERROR: venv created but Python not found inside it")
        sys.exit(1)
    return venv_python


def install_python_deps(python: str) -> None:
    """Install Python dependencies via pip or uv."""
    print("Installing Python dependencies...")
    try:
        subprocess.run(
            [python, "-m", "pip", "--version"],
            capture_output=True, check=True,
        )
        subprocess.run(
            [python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
            check=True,
        )
        subprocess.run(
            [python, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to uv
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
            subprocess.run(
                ["uv", "pip", "install", "--python", python, "-r", str(REQUIREMENTS_FILE)],
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: pip is unavailable in the venv and uv is not installed.")
            print("Install pip in the venv or install uv, then retry.")
            sys.exit(1)


def install_frontend_deps() -> None:
    """Install frontend dependencies."""
    print("Installing frontend dependencies...")
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    subprocess.run([npm_cmd, "install", "--silent"], cwd=str(FRONTEND_DIR), check=True)


def load_dotenv() -> None:
    """Load .env file into environment if it exists."""
    env_file = ROOT_DIR / ".env"
    if not env_file.is_file():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                os.environ[key] = value


def kill_port(port: int) -> None:
    """Kill any process listening on the given port."""
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True,
            )
            for line in result.stdout.splitlines():
                if "LISTENING" in line and f":{port} " in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit():
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True,
                        )
                    break
        else:
            result = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"],
                capture_output=True, text=True,
            )
            pids = result.stdout.strip()
            if pids:
                for pid in pids.splitlines():
                    try:
                        os.kill(int(pid), 9)
                    except (ProcessLookupError, ValueError):
                        pass
    except FileNotFoundError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap and run the Frammer stack")
    parser.add_argument("--install-only", action="store_true", help="Install deps and exit")
    parser.add_argument("--no-db", action="store_true", help="Skip database start")
    parser.add_argument("--reset-db", action="store_true", help="Reset local Postgres cluster")
    parser.add_argument("--seed-demo", action="store_true", help="Seed demo data")
    parser.add_argument("--backend-only", action="store_true", help="Start backend only")
    parser.add_argument("--frontend-only", action="store_true", help="Start frontend only")
    parser.add_argument("--prod-build", action="store_true", help="Build frontend for production")
    args = parser.parse_args()

    if args.backend_only and args.frontend_only:
        print("ERROR: choose only one of --backend-only or --frontend-only")
        sys.exit(1)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv()

    # --- Python venv setup ---
    python = get_venv_python()
    if not python:
        system_python = find_system_python()
        if not system_python:
            print("ERROR: python not found on this system")
            sys.exit(1)
        python = create_venv(system_python)

    install_python_deps(python)
    install_frontend_deps()

    if args.install_only:
        print("Install complete.")
        return

    # --- Database ---
    if not args.no_db:
        if args.reset_db:
            print("Resetting local Postgres cluster...")
            subprocess.run([python, str(ROOT_DIR / "database" / "reset_local_postgres.py")], check=True)

        print("Starting local Postgres...")
        subprocess.run([python, str(ROOT_DIR / "database" / "local_postgres.py"), "start"], check=True)

        if args.reset_db or args.seed_demo:
            print("Bootstrapping demo data...")
            subprocess.run([python, str(ROOT_DIR / "database" / "bootstrap_postgres.py")], check=True)
            print("Seeding auth users...")
            subprocess.run([python, "-m", "backend.db.seed_auth_users"], cwd=str(ROOT_DIR), check=True)

    # --- Production build ---
    if args.prod_build:
        print("Building frontend production bundle...")
        npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), check=True)
        print("Build complete.")
        return

    # --- Kill stale processes on ports ---
    port = int(os.environ.get("PORT", "4000"))
    for p in [port, 5173]:
        kill_port(p)

    # --- Start services ---
    processes: list[subprocess.Popen] = []
    api_log = LOG_DIR / "api.log"
    vite_log = LOG_DIR / "vite.log"

    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"

    api_proc = None
    vite_proc = None

    if not args.frontend_only:
        print("Starting backend...")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        with open(api_log, "w") as log_f:
            api_proc = subprocess.Popen(
                [
                    python, "-m", "uvicorn", "backend.main:app",
                    "--host", "0.0.0.0",
                    "--port", str(port),
                    "--reload",
                    "--reload-dir", str(BACKEND_DIR),
                ],
                cwd=str(ROOT_DIR),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                env=env,
            )
        processes.append(api_proc)

    if not args.backend_only:
        print("Starting frontend...")
        with open(vite_log, "w") as log_f:
            vite_proc = subprocess.Popen(
                [npx_cmd, "vite", "--host", "0.0.0.0"],
                cwd=str(FRONTEND_DIR),
                stdout=log_f,
                stderr=subprocess.STDOUT,
            )
        processes.append(vite_proc)

    print()
    if api_proc:
        print(f"  Backend  -> http://localhost:{port}")
    if vite_proc:
        print(f"  UI       -> http://localhost:5173")
    print(f"  Logs     -> {LOG_DIR}")
    print()

    # --- Tail logs in background threads ---
    import threading

    def tail_log(path: Path, prefix: str) -> None:
        """Tail a log file and print lines with a prefix."""
        # Wait for file to have content
        for _ in range(50):
            if path.is_file() and path.stat().st_size > 0:
                break
            time.sleep(0.1)
        try:
            with open(path) as f:
                while True:
                    line = f.readline()
                    if line:
                        print(f"{prefix} {line}", end="", flush=True)
                    else:
                        # Check if all processes are still alive
                        if all(p.poll() is not None for p in processes):
                            break
                        time.sleep(0.1)
        except (OSError, KeyboardInterrupt):
            pass

    if api_proc:
        t = threading.Thread(target=tail_log, args=(api_log, "[api] "), daemon=True)
        t.start()
    if vite_proc:
        t = threading.Thread(target=tail_log, args=(vite_log, "[vite]"), daemon=True)
        t.start()

    # --- Wait for processes / handle shutdown ---
    def shutdown(*_: object) -> None:
        print("\nShutting down...")
        for proc in processes:
            try:
                proc.terminate()
            except OSError:
                pass
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            if all(p.poll() is not None for p in processes):
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
