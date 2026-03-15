#!/usr/bin/env bash
# run.sh — bootstrap and run the unified Frammer stack

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.run_logs"
VENV_DIR="$ROOT_DIR/.venv"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"

INSTALL_ONLY=false
SKIP_DB=false
RESET_DB=false
SEED_DEMO=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
PROD_BUILD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-only) INSTALL_ONLY=true ;;
    --no-db) SKIP_DB=true ;;
    --reset-db) RESET_DB=true ;;
    --seed-demo) SEED_DEMO=true ;;
    --backend-only) BACKEND_ONLY=true ;;
    --frontend-only) FRONTEND_ONLY=true ;;
    --prod-build) PROD_BUILD=true ;;
    *)
      echo "Unknown flag: $1"
      exit 1
      ;;
  esac
  shift
done

if $BACKEND_ONLY && $FRONTEND_ONLY; then
  echo "ERROR: choose only one of --backend-only or --frontend-only"
  exit 1
fi

mkdir -p "$LOG_DIR"

[[ -f "$ROOT_DIR/.env" ]] && set -a && source "$ROOT_DIR/.env" && set +a

bootstrap_python() {
  for candidate in "$(command -v python3 2>/dev/null)" "$(command -v python 2>/dev/null)" "$(command -v py 2>/dev/null)"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

resolve_venv_python() {
  for candidate in "$VENV_DIR/bin/python" "$VENV_DIR/Scripts/python.exe"; do
    [[ -x "$candidate" ]] && echo "$candidate" && return 0
  done
  return 1
}

VENV_PYTHON="$(resolve_venv_python || true)"
if [[ -z "$VENV_PYTHON" ]]; then
  BOOTSTRAP_PYTHON="$(bootstrap_python || true)"
  [[ -z "$BOOTSTRAP_PYTHON" ]] && echo "ERROR: python not found" && exit 1

  echo "Creating virtual environment at $VENV_DIR"
  if [[ "$(basename "$BOOTSTRAP_PYTHON")" == "py" || "$(basename "$BOOTSTRAP_PYTHON")" == "py.exe" ]]; then
    "$BOOTSTRAP_PYTHON" -3 -m venv "$VENV_DIR"
  else
    "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
  fi
  VENV_PYTHON="$(resolve_venv_python)"
fi

PYTHON="$VENV_PYTHON"

echo "Installing Python dependencies..."
"$PYTHON" -m pip install --upgrade pip --quiet
"$PYTHON" -m pip install -r "$REQUIREMENTS_FILE"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install --silent)
fi

if $INSTALL_ONLY; then
  echo "Install complete."
  exit 0
fi

if ! $SKIP_DB; then
  if $RESET_DB; then
    echo "Resetting local Postgres cluster..."
    "$PYTHON" "$ROOT_DIR/database/reset_local_postgres.py"
  fi

  echo "Starting local Postgres..."
  "$PYTHON" "$ROOT_DIR/database/local_postgres.py" start

  if $RESET_DB || $SEED_DEMO; then
    echo "Bootstrapping demo data..."
    "$PYTHON" "$ROOT_DIR/database/bootstrap_postgres.py"
    echo "Seeding auth users..."
    "$PYTHON" -m backend.db.seed_auth_users
  fi
fi

if $PROD_BUILD; then
  echo "Building frontend production bundle..."
  (cd "$FRONTEND_DIR" && npm run build)
  echo "Build complete."
  exit 0
fi

OS_TYPE="$(uname -s)"
for port in 4000 5173; do
  if [[ "$OS_TYPE" == MINGW* || "$OS_TYPE" == MSYS* || "$OS_TYPE" == CYGWIN* ]]; then
    WIN_PID=$(netstat -ano | grep "LISTENING" | grep ":$port " | awk '{print $5}' | head -n 1)
    [[ -n "$WIN_PID" ]] && cmd.exe //C "taskkill /F /PID $WIN_PID" >/dev/null 2>&1 || true
  else
    lsof -ti tcp:"$port" 2>/dev/null | xargs kill -9 2>/dev/null || true
  fi
done

API_PID=""
VITE_PID=""
cleanup() {
  echo "Shutting down..."
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$VITE_PID" ]] && kill "$VITE_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

if ! $FRONTEND_ONLY; then
  echo "Starting backend..."
  PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-4000}" \
    --reload \
    --reload-dir "$BACKEND_DIR" \
    > "$LOG_DIR/api.log" 2>&1 &
  API_PID=$!
fi

if ! $BACKEND_ONLY; then
  echo "Starting frontend..."
  (cd "$FRONTEND_DIR" && npx vite --host 0.0.0.0 > "$LOG_DIR/vite.log" 2>&1) &
  VITE_PID=$!
fi

echo ""
[[ -n "$API_PID"  ]] && echo "  Backend → http://localhost:${PORT:-4000}"
[[ -n "$VITE_PID" ]] && echo "  UI      → http://localhost:5173"
echo "  Logs    → $LOG_DIR"
echo ""

[[ -n "$API_PID" ]] && tail -n 0 -F "$LOG_DIR/api.log" 2>/dev/null | sed 's/^/[api]   /' &
[[ -n "$VITE_PID" ]] && tail -n 0 -F "$LOG_DIR/vite.log" 2>/dev/null | sed 's/^/[vite]  /' &

wait $API_PID $VITE_PID 2>/dev/null
