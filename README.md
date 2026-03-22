# Frammer (gcdata)

Unified full-stack analytics platform with an AI-powered assistant, KPI engine, and PostgreSQL-backed APIs.

## Repository Structure

```
.
├── backend/            # FastAPI API server (Python)
│   ├── routes/         # 21 route modules (funnel, explorer, KPI, quality, etc.)
│   ├── queries/        # SQL query builders
│   ├── analytics/      # Analytics services (overview, trends, artifacts)
│   ├── kpi/            # Custom KPI DSL parser, compiler, and validator
│   ├── assistant/      # AI assistant service
│   ├── insights/       # Insights generation
│   ├── auth/           # JWT token handling
│   ├── middleware/      # Auth middleware and RBAC
│   ├── config/         # Environment and config resolution
│   ├── db/             # Connection pool, auth schema, seed scripts
│   ├── models/         # Pre-trained ML models (publish predictor)
│   └── main.py         # FastAPI app entry point
│
├── frontend/           # React + Vite UI
│   ├── src/
│   │   ├── features/   # Feature modules (funnel, overview, explorer, journey, quality, usage, wrapped, talk)
│   │   ├── components/ # Reusable UI (charts, layout, chat, insights, reports)
│   │   ├── hooks/      # Custom hooks (useApi, useVoiceInput)
│   │   └── lib/        # Utility libraries
│   ├── nginx.conf      # Nginx config for production
│   └── vite.config.js  # Vite dev server + API proxy
│
├── agent/              # AI agent services
│   ├── agent.py        # LangGraph orchestration engine
│   ├── mcp_server/     # FastMCP tool registry and modules
│   ├── tools/          # SQL query, schema, chart, KPI tools
│   ├── prompts/        # Agent prompt templates
│   └── templates/      # Report templates
│
├── database/           # PostgreSQL bootstrap and utilities
│   ├── bootstrap_postgres.py   # Schema and data loader
│   ├── local_postgres.py       # Local cluster manager
│   ├── migrations/             # SQL migrations
│   └── simulator/              # Data simulation engine
│
├── Orchestrator/       # Orchestration utilities
├── docker-compose.yml  # Full Docker stack (API + Web + DB)
├── Dockerfile.api      # Python/FastAPI container
├── Dockerfile.web      # Node build + Nginx container
├── requirements.txt    # Python dependencies
├── run.sh              # Local dev bootstrap script
├── .env.example        # Environment variable template
└── docker.md           # Docker deployment guide
```

## Prerequisites

| Requirement | Local Dev | Docker |
|---|---|---|
| Python | 3.10+ | - |
| Node.js | 18+ | - |
| PostgreSQL | 16+ (or use built-in local cluster) | - |
| Docker | - | 20.10+ |
| Docker Compose | - | v2 |

## Environment Setup

### 1. Create the env file

```bash
cp .env.example .env
```

### 2. Configure required variables

Open `.env` and set the following:

**Database:**
```env
PGHOST=127.0.0.1
PGPORT=55433
PGUSER=postgres
PGDATABASE=frammer_database
PGPASSWORD=<your-password>

# Docker aliases (must match the PG* values above)
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55433
POSTGRES_USER=postgres
POSTGRES_DB=frammer_database
POSTGRES_PASSWORD=<your-password>
```

**Auth:**
```env
JWT_SECRET=<a-strong-secret>
JWT_EXPIRES_IN=8h
```

**AI Provider (pick one):**
```env
# Option A: Anthropic
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your-key>
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Option B: Azure OpenAI
AI_PROVIDER=azure-openai
AZURE_OPENAI_ENDPOINT=<your-endpoint>
AZURE_OPENAI_API_KEY=<your-key>
AZURE_DEPLOYMENT=o4-mini
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Option C: Google
AI_PROVIDER=google
GOOGLE_API_KEY=<your-key>
```

**Frontend:**
```env
VITE_API_BASE_URL=http://localhost:4000/api
```

**Feature flags:**
```env
FEATURE_MCP_ENABLED=true
FEATURE_LABS_ENABLED=true
```

### 3. (Optional) Demo user seeds

The `.env.example` includes default credentials for demo users:
- `AUTH_WEBSITE_ADMIN_USERNAME` / `AUTH_WEBSITE_ADMIN_PASSWORD` — website admin
- `AUTH_CLIENT_ADMIN1_*` / `AUTH_CLIENT_ADMIN2_*` — client-scoped admins
- `AUTH_USER1_*` / `AUTH_USER2_*` — regular users

These are used by `seed_auth_users` to bootstrap login accounts.

---

## Quick Start (Docker)

Brings up PostgreSQL, the FastAPI backend, and the Nginx-served frontend.

```bash
# Build and start all services
docker compose up -d --build
```

The stack now bootstraps automatically:
- `db` runs `database/frammer_data.sql` on first volume initialization.
- `api` runs `database/docker_db_init.py` before Uvicorn startup.
- auth users are seeded automatically when needed.

Open the app:
- UI: http://localhost:8080
- API: http://localhost:4000/api

Stop:

```bash
docker compose down
```

### Docker Compose Services

| Service | Image | Port | Description |
|---|---|---|---|
| `api` | `python:3.12-slim` | `4000` | FastAPI backend with uvicorn |
| `web` | `node:20-alpine` → `nginx:1.27-alpine` | `8080` | Vite build served by Nginx |
| `db` | `postgres:16-alpine` | `5432` | PostgreSQL with persistent volume |

### Docker Notes

- The `db` service exposes port `5432` on the host. If your host already runs PostgreSQL on that port, stop it or change the port mapping in `docker-compose.yml`.
- The `api` container connects to the `db` service internally (`PGHOST=db`).
- The `web` container proxies `/api/*` and `/mcp/*` to the `api` container via Nginx.
- Database data is persisted in the `gcdata_db_data` Docker volume.
- If you changed bootstrap SQL or got an empty/partial initial import, recreate the volume once:

```bash
docker compose down -v
docker compose up -d --build
```

- To use an external PostgreSQL instead of the container, remove the `db` service and update `PGHOST` / `POSTGRES_HOST` in `.env`.

---

## Quick Start (Local Dev)

Uses a local Python venv, Node, and a local PostgreSQL cluster managed by the repo scripts.

```bash
./run.sh
```

`run.sh` is the recommended entrypoint and delegates to `run.py` (cross-platform runner).

This will:
1. Create a Python virtual environment (`.venv/`)
2. Install Python and Node dependencies
3. Start a local PostgreSQL cluster
4. Launch the FastAPI backend (port 4000) and Vite dev server (port 5173)

Open the app:
- UI: http://localhost:5173
- API: http://localhost:4000/api
- Logs: `.run_logs/`

### run.sh Flags

| Flag | Description |
|---|---|
| `--install-only` | Install dependencies and exit (no servers started) |
| `--no-db` | Skip starting the local PostgreSQL cluster |
| `--reset-db` | Reset and re-bootstrap the local database |
| `--seed-demo` | Bootstrap demo data and seed auth users |
| `--backend-only` | Start only the FastAPI backend |
| `--frontend-only` | Start only the Vite dev server |
| `--prod-build` | Build the frontend production bundle and exit |

---

## Environment Variables Reference

### App / Runtime

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Environment mode |
| `PORT` | `4000` | Backend API port |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:4000` | Allowed CORS origins (comma-separated) |
| `FEATURE_MCP_ENABLED` | `true` | Enable MCP server mount |
| `FEATURE_LABS_ENABLED` | `true` | Enable labs/experimental features |

### Database

| Variable | Default | Description |
|---|---|---|
| `PGHOST` | `127.0.0.1` | PostgreSQL host |
| `PGPORT` | `55433` | PostgreSQL port |
| `PGUSER` | `postgres` | PostgreSQL user |
| `PGDATABASE` | `frammer_database` | Database name |
| `PGPASSWORD` | - | Database password |
| `PGSSLMODE` | `prefer` | SSL mode |

Docker aliases: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD`

### Local Postgres Cluster

| Variable | Default | Description |
|---|---|---|
| `LOCAL_POSTGRES_HOST` | `127.0.0.1` | Local cluster host |
| `LOCAL_POSTGRES_PORT` | `55433` | Local cluster port |
| `LOCAL_POSTGRES_USER` | `postgres` | Local cluster user |
| `LOCAL_POSTGRES_DB` | `frammer_database` | Local cluster database |

### Simulator

| Variable | Default | Description |
|---|---|---|
| `SIMULATOR_PGHOST` | `127.0.0.1` | Simulator DB host |
| `SIMULATOR_PGPORT` | `5432` | Simulator DB port |
| `SIMULATOR_PGUSER` | `postgres` | Simulator DB user |
| `SIMULATOR_PGDATABASE` | `frammer_database` | Simulator DB name |
| `SIMULATOR_PGPASSWORD` | - | Simulator DB password |

### AI / Provider

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | - | Google AI API key |

### Auth / JWT

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `change-me` | JWT signing secret |
| `JWT_EXPIRES_IN` | `8h` | Token expiration |

### Frontend

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:4000/api` | API base URL (only `VITE_*` vars are bundled) |

### MCP

| Variable | Default | Description |
|---|---|---|
| `MCP_SERVER_NAME` | `frammer-mcp` | MCP server name |
| `DATABASE_SCHEMA` | `public` | Database schema |

---

## Troubleshooting

- **API returns DB errors** — Run the bootstrap and seed commands to load schema and data.
- **Web UI cannot reach the API** — Verify `VITE_API_BASE_URL` in `.env`. For Docker, rebuild the web image after changing it.
- **Port 5432 conflict** — Stop your system PostgreSQL or change the port mapping in `docker-compose.yml`.
- **Port 4000/5173 in use** — `run.sh` auto-kills stale processes on those ports. For Docker, check with `docker ps`.
- **Local Postgres won't start** — Check `database/local_postgres.py status` and logs. Try `./run.sh --reset-db`.
