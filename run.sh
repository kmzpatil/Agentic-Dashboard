#!/usr/bin/env bash
# run.sh — Start the Frammer AI stack
# Usage: ./run.sh [--no-db]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$ROOT_DIR/agent"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.run_logs"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
SKIP_DB=false
[[ "${1:-}" == "--no-db" ]] && SKIP_DB=true

mkdir -p "$LOG_DIR"

# ── Load .env so all child processes inherit env vars (e.g. GROQ_API_KEY) ────
[[ -f "$ROOT_DIR/.env" ]] && set -a && source "$ROOT_DIR/.env" && set +a

# ── Python interpreter / virtualenv bootstrap ─────────────────────────────────
VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON=""
for c in "$VENV_DIR/bin/python" "$VENV_DIR/Scripts/python.exe"; do
  [[ -x "$c" ]] && VENV_PYTHON="$c" && break
done

if [[ -z "$VENV_PYTHON" ]]; then
  BOOTSTRAP_PYTHON=""
  for c in "$(command -v python3 2>/dev/null)" "$(command -v python 2>/dev/null)" "$(command -v py 2>/dev/null)"; do
    [[ -n "$c" && -x "$c" ]] && BOOTSTRAP_PYTHON="$c" && break
  done

  [[ -z "$BOOTSTRAP_PYTHON" ]] && echo "ERROR: python not found" && exit 1

  echo "Creating virtual environment at .venv..."
  if [[ "$(basename "$BOOTSTRAP_PYTHON")" == "py" || "$(basename "$BOOTSTRAP_PYTHON")" == "py.exe" ]]; then
    "$BOOTSTRAP_PYTHON" -3 -m venv "$VENV_DIR"
  else
    "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
  fi

  for c in "$VENV_DIR/bin/python" "$VENV_DIR/Scripts/python.exe"; do
    [[ -x "$c" ]] && VENV_PYTHON="$c" && break
  done
fi

[[ -z "$VENV_PYTHON" ]] && echo "ERROR: could not locate virtualenv python" && exit 1
PYTHON="$VENV_PYTHON"

if [[ -f "$REQUIREMENTS_FILE" ]]; then
  echo "Installing Python dependencies from requirements.txt..."
  "$PYTHON" -m pip install --upgrade pip --quiet
  "$PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
else
  echo "WARN: requirements.txt not found at $REQUIREMENTS_FILE"
fi

# ── Node deps ─────────────────────────────────────────────────────────────────
[[ ! -d "$FRONTEND_DIR/node_modules" ]] && (cd "$FRONTEND_DIR" && npm install --silent)

# ── PostgreSQL ────────────────────────────────────────────────────────────────
if ! $SKIP_DB; then
  echo "Starting PostgreSQL..."
  if (cd "$FRONTEND_DIR" && npm run db:start --silent); then
    (cd "$FRONTEND_DIR" && npm run seed:auth --silent) || true
  else
    echo ""
    echo "WARN: Local PostgreSQL could not be started."
    echo "      Continuing without DB bootstrap (--no-db behavior)."
    echo "      If you need local DB bootstrap, install PostgreSQL binaries"
    echo "      (pg_ctl/initdb/psql/createdb) and set POSTGRES_BIN_DIR."
    echo ""
  fi
fi

# ── Clear stale processes on target ports ─────────────────────────────────────
# ── Clear stale processes on target ports ─────────────────────────────────────
OS_TYPE="$(uname -s)"

for port in 8000 4000 5173; do
  if [[ "$OS_TYPE" == MINGW* || "$OS_TYPE" == MSYS* || "$OS_TYPE" == CYGWIN* ]]; then
    # Windows (via Git Bash / MSYS2)
    # Find the PID listening on the target port
    WIN_PID=$(netstat -ano | grep "LISTENING" | grep ":$port " | awk '{print $5}' | head -n 1)
    if [[ -n "$WIN_PID" ]]; then
      # Use cmd.exe to run taskkill. 
      # The //C and //F are used to prevent Git Bash from mangling Windows paths/flags.
      cmd.exe //C "taskkill /F /PID $WIN_PID" >/dev/null 2>&1 || true
    fi
  else
    # Mac / Linux
    lsof -ti tcp:"$port" 2>/dev/null | xargs kill -9 2>/dev/null || true
  fi
done

# ── Cleanup on exit ───────────────────────────────────────────────────────────
AGENT_PID=""; API_PID=""; VITE_PID=""
cleanup() {
  echo "Shutting down..."
  [[ -n "$AGENT_PID" ]] && kill "$AGENT_PID" 2>/dev/null || true
  [[ -n "$API_PID"   ]] && kill "$API_PID"   2>/dev/null || true
  [[ -n "$VITE_PID"  ]] && kill "$VITE_PID"  2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Start services ────────────────────────────────────────────────────────────
echo "Starting services..."

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$AGENT_DIR" \
  "$PYTHON" -m uvicorn api_server:app \
  --host 0.0.0.0 --port 8000 --reload --reload-dir "$AGENT_DIR" \
  > "$LOG_DIR/agent.log" 2>&1 &
AGENT_PID=$!

PYTHONDONTWRITEBYTECODE=1 \
  "$PYTHON" -m uvicorn backend.main:app \
  --host 0.0.0.0 --port 4000 --reload --reload-dir "$BACKEND_DIR" \
  > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!

(cd "$FRONTEND_DIR" && npx vite > "$LOG_DIR/vite.log" 2>&1) &
VITE_PID=$!

echo ""
echo "  Agent   → http://localhost:8000"
echo "  Backend → http://localhost:4000"
echo "  UI      → http://localhost:5173"
echo ""
echo "Logs: .run_logs/  |  Ctrl-C to stop"
echo ""

# ── Stream logs ───────────────────────────────────────────────────────────────
tail -n 0 -F "$LOG_DIR/agent.log" 2>/dev/null | sed 's/^/[agent] /' &
tail -n 0 -F "$LOG_DIR/api.log"   2>/dev/null | sed 's/^/[api]   /' &
tail -n 0 -F "$LOG_DIR/vite.log"  2>/dev/null | sed 's/^/[vite]  /' &

wait $AGENT_PID $API_PID $VITE_PID 2>/dev/null