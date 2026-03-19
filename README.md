# GCData — Frammer Analytics Dashboard

Unified stack: React dashboard, multi-agent AI copilot, FastAPI backend, PostgreSQL.

## Repository structure

```
gcdata/
├── frontend/          React + Vite + Tailwind UI (port 5173)
├── backend/           FastAPI API server (port 4000)
├── agent/             Multi-agent AI pipeline + legacy agent (port 4001)
│   ├── agents/        Router, SQL, Analytics, Visualization, Insight agents
│   ├── orchestrator/  Pipeline coordinator (fast path / deep path)
│   ├── tools/         Schema loader, SQL validator, DB tool, analysis helpers
│   ├── models/        Pydantic data models
│   ├── config/        Settings (env-driven)
│   └── tests/         Unit tests (pytest)
├── database/          Postgres bootstrap, migrations, simulator
├── Orchestrator/      Orchestration utilities
├── run.sh             Local dev launcher (Python + Node + Postgres)
└── docker-compose.yml Full Docker stack
```

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** (running locally or via Docker)
- An **Anthropic API key** (for the AI copilot)

## 1. Environment setup

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Key variables in `.env`:

| Variable | Example | Purpose |
|---|---|---|
| `PGHOST` | `127.0.0.1` | Postgres host |
| `PGPORT` | `5432` | Postgres port |
| `PGUSER` | `postgres` | Postgres user |
| `PGPASSWORD` | `your_password` | Postgres password |
| `PGDATABASE` | `frammer_database` | Database name |
| `DATABASE_URL` | `postgresql://postgres:your_password@127.0.0.1:5432/frammer_database` | Full DSN (used by the agent pipeline) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Anthropic API key |
| `JWT_SECRET` | `change-me` | Auth token secret |

**Important**: `DATABASE_URL` must match your `PG*` variables. The multi-agent
pipeline (asyncpg) reads `DATABASE_URL`; if it's not set, it builds one from
`PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`.

## 2. Install dependencies

### Option A: Using `run.sh` (recommended)

```bash
# Install everything (Python venv + Node modules) without starting servers:
./run.sh --install-only
```

### Option B: Manual

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Extra agent dependencies

The multi-agent pipeline needs these packages (already in `requirements.txt`):

```
sqlglot          — SQL validation
asyncpg          — async Postgres driver
pydantic-settings — env-driven config
anthropic        — Anthropic SDK
pytest-asyncio   — async test support
```

If you installed manually, confirm they're present:

```bash
pip install sqlglot asyncpg pydantic-settings anthropic pytest-asyncio
```

## 3. Database setup

### Ensure PostgreSQL is running

```bash
# Check if Postgres is reachable:
pg_isready -h 127.0.0.1 -p 5432

# If using the repo's local cluster manager:
python database/local_postgres.py start
```

### Bootstrap schema and seed data

```bash
# Load schema + demo data:
python database/bootstrap_postgres.py

# Seed auth users:
python -m backend.db.seed_auth_users
```

### Verify the database

```bash
psql -h 127.0.0.1 -U postgres -d frammer_database -c "\dt"
```

You should see tables like `clients`, `created_assets`, `channels`, `published_posts`, etc.

## 4. Running the stack

### Full stack (recommended)

```bash
./run.sh
```

This starts:
- **Backend** at `http://localhost:4000` (FastAPI + agent proxy)
- **Frontend** at `http://localhost:5173` (Vite dev server)

### Individual services

```bash
# Backend only:
./run.sh --backend-only

# Frontend only:
./run.sh --frontend-only

# Agent server standalone (optional, for debugging):
cd agent && python api_server.py
# → runs on port 4001
```

### Using Docker

```bash
docker compose up -d --build

# First time — seed the database:
docker compose run --rm api python /app/database/bootstrap_postgres.py
docker compose run --rm api python -m backend.db.seed_auth_users
```

- UI: `http://localhost:8080`
- API: `http://localhost:4000/api`

## 5. How the AI Copilot works

The copilot is a **two-speed multi-agent pipeline** inside `agent/`:

```
User Query  +  mode (fast | deep | auto)
        │
        ▼
   Router Agent          ← Claude Haiku, <200ms
   (intent + complexity)
        │
   ┌────┴────┐
   ▼         ▼
FAST PATH  DEEP PATH
 (<2s)     (10-40s)
   │         │
SQL Agent  Analytics Agent (planner → parallel SQL → pandas)
   │         │
Viz Agent  Viz Agent (chart artifacts)
   │         │
Insight    Insight Agent
Agent        │
   │         ▼
   └──► Response with artifacts, datasets, insights
```

### Fast path
Single SQL query → chart artifact → one-sentence insight. Used for simple
lookups, aggregations, and rankings.

### Deep path
Multi-step plan → parallel SQL execution → pandas analysis (trend detection,
anomaly detection, growth rates) → multiple chart artifacts → detailed
narrative. Used for trends, analytics, and complex comparisons.

### Chart types

The pipeline auto-detects the best chart type and generates **artifacts**
that the frontend renders via `ArtifactCanvas.jsx` (Chart.js):

| Type | When used |
|---|---|
| **Bar** | Rankings, comparisons, category counts |
| **Line** | Time series, trends, growth over time |
| **Pie** | Proportions (max 8 slices) |
| **Area** | Cumulative trends |
| **Scatter** | Correlations, distributions |
| **Heatmap** | Cross-tabular / pivot data |
| **KPI cards** | Single-row results (e.g. total count) |

### Guardrails

- SQL is validated through a **6-layer SQLGlot pipeline** (syntax, tables,
  columns, DML blocking, LIMIT enforcement, SELECT * rejection)
- All queries are **read-only** — DROP/DELETE/UPDATE/INSERT are blocked
- Failed queries **self-repair** up to 3 attempts
- Schema is **introspected live** and refreshed every 10 minutes
- Results are **LRU-cached** (60s TTL)

## 6. Running tests

```bash
cd agent

# All agent tests (38 tests):
python -m pytest tests/ -v

# Individual test suites:
python -m pytest tests/test_validator.py -v    # SQL validation (19 tests)
python -m pytest tests/test_router.py -v       # Routing logic (6 tests)
python -m pytest tests/test_sql_agent.py -v    # SQL generation (8 tests)
python -m pytest tests/test_orchestrator.py -v # Pipeline E2E (5 tests)
```

### Stress test (requires live DB + Anthropic key)

```bash
cd ..  # back to project root
python test_queries.py
```

Runs 30 diverse queries through the pipeline and reports pass/fail.

## 7. Troubleshooting

### `password authentication failed for user "postgres"`

The multi-agent pipeline connects via `DATABASE_URL`. Make sure it matches
your actual Postgres credentials:

```bash
# Check what the agent will use:
grep DATABASE_URL .env

# It should be:
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/frammer_database
```

If `DATABASE_URL` is not set, it's built from `PGUSER` + `PGPASSWORD` + `PGHOST` +
`PGPORT` + `PGDATABASE`.

### `Orchestrator init failed (non-fatal)`

This means the multi-agent pipeline couldn't start, but the legacy agent is
still available. Common causes:

1. **Wrong DB credentials** — see above
2. **Postgres not running** — start it with `pg_isready` check
3. **Missing tables** — run `python database/bootstrap_postgres.py`
4. **Missing pip packages** — run `pip install sqlglot asyncpg pydantic-settings anthropic`

### `Request failed: 500`

Check the API log for the actual error:

```bash
# If using run.sh:
cat .run_logs/api.log | tail -30

# If running agent standalone:
# The error is printed directly to the terminal
```

### Frontend shows "No artifacts yet"

The copilot needs to return artifacts for the chart panel to open. Make sure:
1. The orchestrator started successfully (check for "Multi-agent orchestrator initialised" in logs)
2. Your Anthropic API key is valid
3. The database has data (run the seed commands)

### Port conflicts

```bash
# Kill processes on ports 4000/5173:
lsof -ti tcp:4000 | xargs kill -9
lsof -ti tcp:5173 | xargs kill -9
```

## 8. Useful run.sh flags

| Flag | Effect |
|---|---|
| `--install-only` | Install deps, don't start servers |
| `--reset-db` | Wipe and recreate the local Postgres cluster |
| `--seed-demo` | Bootstrap schema + seed demo data |
| `--backend-only` | Start only the FastAPI backend |
| `--frontend-only` | Start only the Vite dev server |
| `--prod-build` | Build the frontend production bundle |
