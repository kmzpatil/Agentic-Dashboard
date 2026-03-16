# Frammer (gcdata)

Unified stack for analytics dashboard, AI agent, and PostgreSQL-backed APIs.

## What is in this repo
- `backend/`: FastAPI API server (mounted under `/api`).
- `agent/`: Agent services and tools (MCP, analytics helpers).
- `database/`: Postgres bootstrap, simulator, and local cluster utilities.
- `frontend/`: React + Vite UI and Nginx build output.
- `Orchestrator/`: Orchestration utilities.
- `run.sh`: Local dev bootstrap (Python + Node + Postgres).
- `docker-compose.yml`: Full Docker stack (API + Web + Postgres).

## Prerequisites
- Docker 20.10+ and Docker Compose v2
- For local (non-docker) run: Python 3.10+ and Node.js 18+

## Environment setup
1. Create a local env file:

```bash
cp .env.example .env
```

2. Fill required values in `.env`:
- `POSTGRES_PASSWORD` (required for Docker DB)
- `PGPASSWORD` (should match `POSTGRES_PASSWORD`)
- `JWT_SECRET`
- `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` (if using AI provider)

Notes:
- For Docker, the API container will connect to the `db` service internally.
- For local dev with `run.sh`, `PGHOST` and `PGPORT` should match your local Postgres.

## Quick start (Docker)
This brings up Postgres, API, and the web UI.

```bash
docker compose up -d --build
```

Seed the database (first time only):

```bash
docker compose run --rm api python /app/database/bootstrap_postgres.py
docker compose run --rm api python -m backend.db.seed_auth_users
```

Open:
- UI: http://localhost:8080
- API: http://localhost:4000/api

Stop:

```bash
docker compose down
```

## Quick start (Local dev)
This uses local Python, Node, and a local Postgres cluster managed by the repo scripts.

```bash
./run.sh
```

Useful flags:
- `./run.sh --install-only`
- `./run.sh --reset-db`
- `./run.sh --seed-demo`
- `./run.sh --backend-only`
- `./run.sh --frontend-only`

Open:
- UI: http://localhost:5173
- API: http://localhost:4000/api

## Docker compose notes
- The `db` service exposes port `5432` on your host.
- If you already have Postgres on `5432`, stop it or change the port mapping in compose.
- To run against an external Postgres instead of the container, update compose to remove `db` and set `PGHOST`/`POSTGRES_HOST` accordingly.

## Troubleshooting
- If the API starts but returns DB errors, run the bootstrap commands above to load schema/data.
- If the web UI cannot reach the API, verify `VITE_API_BASE_URL` in `.env` and rebuild the web image.
