#!/usr/bin/env bash
# run.sh — Start the full Frammer AI stack
#
# Services started:
#   1. Local PostgreSQL 18 cluster  (port 5433)
#   2. Auth users seeded            (idempotent — safe every run)
#   3. Python FastAPI agent          (port 8000)
#   4. Python FastAPI backend API    (port 4000)
#   5. Vite React dev server         (port 5173)
#
# Usage:
#   ./run.sh          — start everything (seeds auth users automatically)
#   ./run.sh --no-db  — skip postgres start (already running)
#   Ctrl-C            — graceful shutdown of all processes

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
CYN='\033[0;36m'; MAG='\033[0;35m'; BLD='\033[1m'; RST='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
AGENT_DIR="$ROOT_DIR/agent"
BACKEND_DIR="$ROOT_DIR/backend"
DATABASE_DIR="$ROOT_DIR/database"
LOG_DIR="$ROOT_DIR/.run_logs"

SKIP_DB=false
[[ "${1:-}" == "--no-db" ]] && SKIP_DB=true

mkdir -p "$LOG_DIR"

# ── PIDs we'll need to kill on exit ──────────────────────────────────────────
AGENT_PID=""; API_PID=""; VITE_PID=""

cleanup() {
  echo ""
  echo -e "${YLW}━━━ Shutting down Frammer AI stack ━━━${RST}"
  [[ -n "$VITE_PID"  ]] && kill "$VITE_PID"  2>/dev/null && echo -e "  ${MAG}▸ Vite stopped${RST}"
  [[ -n "$API_PID"   ]] && kill "$API_PID"   2>/dev/null && echo -e "  ${CYN}▸ FastAPI backend stopped${RST}"
  [[ -n "$AGENT_PID" ]] && kill "$AGENT_PID" 2>/dev/null && echo -e "  ${YLW}▸ Python agent stopped${RST}"
  echo -e "${GRN}✓ All services stopped.${RST}"
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${RED}${BLD}  ███████╗██████╗  █████╗ ███╗   ███╗███╗   ███╗███████╗██████╗ ${RST}"
echo -e "${RED}${BLD}  ██╔════╝██╔══██╗██╔══██╗████╗ ████║████╗ ████║██╔════╝██╔══██╗${RST}"
echo -e "${RED}${BLD}  █████╗  ██████╔╝███████║██╔████╔██║██╔████╔██║█████╗  ██████╔╝${RST}"
echo -e "${RED}${BLD}  ██╔══╝  ██╔══██╗██╔══██║██║╚██╔╝██║██║╚██╔╝██║██╔══╝  ██╔══██╗${RST}"
echo -e "${RED}${BLD}  ██║     ██║  ██║██║  ██║██║ ╚═╝ ██║██║ ╚═╝ ██║███████╗██║  ██║${RST}"
echo -e "${RED}${BLD}  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝${RST}"
echo -e "                 ${BLD}AI Nerve Centre — local dev stack${RST}"
echo ""

# ── 1. Preflight checks ───────────────────────────────────────────────────────
echo -e "${BLD}[1/4] Preflight checks${RST}"

fail() { echo -e "${RED}✗ $1${RST}"; exit 1; }

command -v node >/dev/null 2>&1 || fail "node not found. Install Node.js >= 18."
command -v npm  >/dev/null 2>&1 || fail "npm not found."

# Prefer miniconda/conda python (has all packages) over system python
PYTHON=""
for candidate in \
    "$HOME/miniconda3/bin/python3" \
    "$HOME/anaconda3/bin/python3" \
    "/opt/miniconda3/bin/python3" \
    "/opt/anaconda3/bin/python3" \
    "$(command -v python3 2>/dev/null)" \
    "$(command -v python  2>/dev/null)"; do
  if [[ -x "$candidate" ]] && "$candidate" -c "import uvicorn" 2>/dev/null; then
    PYTHON="$candidate"; break
  fi
done
[[ -z "$PYTHON" ]] && fail "No python with uvicorn found. Run: pip install -r agent/requirements.txt"

[[ -f "$FRONTEND_DIR/package.json" ]]      || fail "frontend/package.json not found."
[[ -f "$AGENT_DIR/api_server.py" ]]        || fail "agent/api_server.py not found."
[[ -f "$BACKEND_DIR/main.py" ]]            || fail "backend/main.py not found."
[[ -f "$DATABASE_DIR/local_postgres.py" ]] || fail "database/local_postgres.py not found."

echo -e "  ${GRN}✓ node $(node --version)  npm $(npm --version)  $("$PYTHON" --version)${RST}"

# ── 2. Node dependencies ──────────────────────────────────────────────────────
echo -e "${BLD}[2/4] Node dependencies${RST}"
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo -e "  ${YLW}▸ node_modules missing — running npm install…${RST}"
  (cd "$FRONTEND_DIR" && npm install --silent)
else
  echo -e "  ${GRN}✓ node_modules present${RST}"
fi

# ── 3. PostgreSQL ─────────────────────────────────────────────────────────────
echo -e "${BLD}[3/4] PostgreSQL — restore from frammer_data.sql if needed${RST}"
if $SKIP_DB; then
  echo -e "  ${CYN}▸ --no-db flag set, skipping postgres start${RST}"
else
  echo -e "  ${CYN}▸ Starting cluster…${RST}"
  (cd "$FRONTEND_DIR" && npm run db:start --silent) 2>&1 | sed 's/^/  /'
  echo -e "  ${GRN}✓ PostgreSQL ready${RST}"

  echo -e "  ${CYN}▸ Seeding auth users…${RST}"
  (cd "$FRONTEND_DIR" && npm run seed:auth --silent) 2>&1 | sed 's/^/  /' || true
  echo -e "  ${GRN}✓ Auth users seeded${RST}"
fi

# ── 4. Application services ───────────────────────────────────────────────────
echo -e "${BLD}[4/4] Starting application services${RST}"

# Clear any stale processes on target ports
for port in 8000 4000 5173; do
  pid=$(lsof -ti tcp:"$port" 2>/dev/null) && [[ -n "$pid" ]] && kill $pid 2>/dev/null && sleep 0.5 || true
done

# Python FastAPI agent — port 8000
# PYTHONPATH=agent/ lets uvicorn --reload find modules without --app-dir
echo -e "  ${YLW}▸ Python agent  → http://localhost:8000${RST}  (log: .run_logs/agent.log)"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$AGENT_DIR" \
  "$PYTHON" -m uvicorn api_server:app \
  --host 0.0.0.0 --port 8000 --log-level info \
  --reload --reload-dir "$AGENT_DIR" \
  > "$LOG_DIR/agent.log" 2>&1 &
AGENT_PID=$!

# FastAPI backend API — port 4000
echo -e "  ${CYN}▸ FastAPI backend → http://localhost:4000${RST}  (log: .run_logs/api.log)"
PYTHONDONTWRITEBYTECODE=1 \
  "$PYTHON" -m uvicorn backend.main:app \
  --host 0.0.0.0 --port 4000 --log-level info \
  --reload --reload-dir "$BACKEND_DIR" \
  > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!

# Vite dev server — port 5173
echo -e "  ${MAG}▸ Vite frontend  → http://localhost:5173${RST}  (log: .run_logs/vite.log)"
(cd "$FRONTEND_DIR" && npx vite > "$LOG_DIR/vite.log" 2>&1) &
VITE_PID=$!

# ── Wait for services to be ready ─────────────────────────────────────────────
echo ""
echo -e "${BLD}Waiting for services to come online…${RST}"

wait_for_port() {
  local label="$1" port="$2" max_wait=30 elapsed=0
  while ! nc -z 127.0.0.1 "$port" 2>/dev/null; do
    sleep 1; elapsed=$((elapsed + 1))
    if [[ $elapsed -ge $max_wait ]]; then
      echo -e "  ${RED}✗ $label (port $port) did not start in ${max_wait}s — check .run_logs/${RST}"
      return 0  # don't abort the script; let services keep running
    fi
  done
  echo -e "  ${GRN}✓ $label online (port $port)${RST}"
}

# Vite auto-increments if 5173 is busy — find whichever port it grabbed
wait_for_vite() {
  local max_wait=30 elapsed=0
  while [[ $elapsed -lt $max_wait ]]; do
    for port in 5173 5174 5175 5176 5177; do
      if nc -z 127.0.0.1 "$port" 2>/dev/null; then
        echo -e "  ${GRN}✓ Vite frontend online (port $port)${RST}"
        return 0
      fi
    done
    sleep 1; elapsed=$((elapsed + 1))
  done
  echo -e "  ${RED}✗ Vite frontend did not start in ${max_wait}s — check .run_logs/vite.log${RST}"
}

wait_for_port "FastAPI backend" 4000
wait_for_port "Python agent" 8000
wait_for_vite

# ── Ready ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
echo -e "${GRN}${BLD}  Frammer AI is running!  (PID $$)${RST}"
echo -e "${GRN}${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
echo ""
echo -e "  ${MAG}React UI     →  http://localhost:5173${RST}"
echo -e "  ${CYN}FastAPI API   →  http://localhost:4000/api/health${RST}"
echo -e "  ${YLW}Python agent →  http://localhost:8000/healthz${RST}"
echo ""
echo -e "  ${BLD}Stop:${RST}  Ctrl-C  ${BLD}or${RST}  kill $$"
echo -e "  ${BLD}Logs:${RST}  .run_logs/{agent,api,vite}.log"
echo ""
echo -e "${BLD}── Live logs ─────────────────────────────────────────${RST}"
echo ""

# ── Stream all three logs with coloured service prefixes ──────────────────────
tail -n 0 -F "$LOG_DIR/agent.log" 2>/dev/null \
  | sed "s/^/${YLW}[agent]${RST} /" &

tail -n 0 -F "$LOG_DIR/api.log" 2>/dev/null \
  | sed "s/^/${CYN}[api]  ${RST} /" &

tail -n 0 -F "$LOG_DIR/vite.log" 2>/dev/null \
  | sed "s/^/${MAG}[vite] ${RST} /" &

# Keep alive until Ctrl-C
wait $AGENT_PID $API_PID $VITE_PID 2>/dev/null
