#!/usr/bin/env bash
# run.sh — Start the Frammer AI stack
# Usage: ./run.sh [--no-db]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$ROOT_DIR/agent"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.run_logs"
SKIP_DB=false
[[ "${1:-}" == "--no-db" ]] && SKIP_DB=true

mkdir -p "$LOG_DIR"

# ── Load .env so all child processes inherit env vars (e.g. GROQ_API_KEY) ────
[[ -f "$ROOT_DIR/.env" ]] && set -a && source "$ROOT_DIR/.env" && set +a

# ── Python interpreter (prefer local venv) ────────────────────────────────────
PYTHON=""
for c in "$ROOT_DIR/.venv/bin/python" "$(command -v python3 2>/dev/null)" "$(command -v python 2>/dev/null)"; do
  [[ -x "$c" ]] && PYTHON="$c" && break
done
[[ -z "$PYTHON" ]] && echo "ERROR: python not found" && exit 1

# ── Node deps ─────────────────────────────────────────────────────────────────
[[ ! -d "$FRONTEND_DIR/node_modules" ]] && (cd "$FRONTEND_DIR" && npm install --silent)

# ── PostgreSQL ────────────────────────────────────────────────────────────────
if ! $SKIP_DB; then
  echo "Starting PostgreSQL..."
  (cd "$FRONTEND_DIR" && npm run db:start --silent)
  (cd "$FRONTEND_DIR" && npm run seed:auth --silent) || true
fi

# ── Clear stale processes on target ports ─────────────────────────────────────
for port in 8000 4000 5173; do
  lsof -ti tcp:"$port" 2>/dev/null | xargs kill -9 2>/dev/null || true
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
