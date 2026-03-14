# Frammer AI Dashboard

React + Vite frontend with a Node/Express gateway, a Python agent service, and a PostgreSQL analytics backend.

## Current Status (March 2026)
- Frontend is modularized into feature modules: Overview, Usage & Trends, Funnel, Explorer.
- The public API is now a single Node gateway under `frontend/backend` for analytics, health, and agent proxying.
- The Python agent stays focused on chat/query/schema features and is reachable through the gateway.
- PostgreSQL config is normalized across `PG*`, `POSTGRES_*`, and PostgreSQL `DATABASE_URL` values.
- Basic runtime smoke checks are passing locally (`vite build`, Python compile, Node syntax checks).

## Tech Stack
- Frontend: React 19, Vite 5, Tailwind CSS
- Charts: Chart.js, react-chartjs-2, chartjs-chart-sankey
- Backend: Express 5, pg
- Database: PostgreSQL (`frammer_database`)

## Prerequisites
- Node.js 18+
- npm 9+
- PostgreSQL (local or remote)
- Python 3.10+

## Setup
1. Create env file in the repo root or inside `frontend/`:

```bash
cp .env.example .env
```

2. Update `.env` values:
- `PORT` (or `API_PORT`): Node gateway port (default `4000`)
- `POSTGRES_HOST` / `PGHOST`
- `POSTGRES_PORT` / `PGPORT`
- `POSTGRES_DB` / `PGDATABASE`
- `POSTGRES_USER` / `PGUSER`
- `POSTGRES_PASSWORD` / `PGPASSWORD`
- `POSTGRES_SSLMODE` / `PGSSLMODE`: `prefer`, `require`, etc.
- `AGENT_BASE_URL`: Python agent base URL (default `http://127.0.0.1:8000`)
- `VITE_API_BASE_URL`: frontend-to-gateway base URL

3. If Postgres does not already contain the Frammer schema/data, bootstrap it from the bundled SQLite snapshot:

```bash
npm run db:bootstrap
```

4. Install frontend dependencies:

```bash
npm install
```

5. Install Python dependencies for the agent service:

```bash
pip install -r ../agent/requirements.txt
```

## Run
Run frontend + gateway + agent together:

```bash
npm run dev:full
```

Run separately:

```bash
npm run api
npm run agent
npm run dev
```

Default URLs:
- Frontend: `http://localhost:5173`
- Gateway API: `http://localhost:4000`
- Agent service: `http://localhost:8000`

## Build
```bash
npm run build
npm run preview
```

## API Surface
- `GET /api/health`
- `GET /api/overview`
- `GET /api/usage-trends`
- `GET /api/funnel`
- `GET /api/funnel/video/:videoId`
- `GET /api/explorer/dimensions`
- `GET /api/explorer/multidim`
- `GET /api/explorer/tables`
- `GET /api/explorer/table/:tableName`
- `GET /api/explorer/chart`
- `POST /api/chat`
- `POST /api/query`
- `GET /api/agent/health`
- `GET /api/agent/tables`
- `GET /api/agent/schema/search`

## Directory Structure
```text
.
├── server.js
├── backend
│   ├── app.js
│   ├── agent
│   │   └── client.js
│   ├── config
│   │   └── env.js
│   ├── db
│   │   └── pool.js
│   ├── queries
│   │   ├── analyticsShared.js
│   │   ├── explorerQueries.js
│   │   ├── funnelQueries.js
│   │   └── overviewQueries.js
│   ├── routes
│   │   ├── agent.js
│   │   ├── api.js
│   │   ├── explorer.js
│   │   ├── funnel.js
│   │   ├── health.js
│   │   ├── overview.js
│   │   └── usageTrends.js
│   └── utils
└── src
    ├── main.jsx
    ├── index.css
    ├── AppShell.jsx
    ├── hooks
    │   └── useApi.js
    ├── components
    │   ├── common
    │   │   └── KpiCard.jsx
    │   └── layout
    │       ├── FilterDock.jsx
    │       └── PipelineRail.jsx
    ├── features
    │   ├── overview
    │   │   └── OverviewModule.jsx
    │   ├── usage
    │   │   └── UsageTrendsModule.jsx
    │   ├── funnel
    │   │   └── FunnelModule.jsx
    │   ├── explorer
    │   │   └── ExplorerModule.jsx
    │   └── shared
    │       └── ComingSoonModule.jsx
    └── lib
        ├── chartSetup.js
        ├── constants.js
        └── formatters.js
```

## Environment Variables
- `PORT`: gateway port fallback
- `API_PORT`: optional gateway port alias
- `POSTGRES_HOST` / `PGHOST`: PostgreSQL host or socket path
- `POSTGRES_PORT` / `PGPORT`: PostgreSQL port
- `POSTGRES_USER` / `PGUSER`: PostgreSQL username
- `POSTGRES_DB` / `PGDATABASE`: PostgreSQL database name
- `POSTGRES_PASSWORD` / `PGPASSWORD`: PostgreSQL password
- `POSTGRES_SSLMODE` / `PGSSLMODE`: PostgreSQL SSL mode
- `AGENT_BASE_URL`: Python agent base URL for proxying
- `VITE_API_BASE_URL`: frontend API base URL

## Notes
- Keep `.env` local; commit `.env.example` only.
- The Node gateway is the only API the frontend should talk to directly.
- The Postgres bootstrap script lives at [database/bootstrap_postgres.py](/Users/praty/Downloads/Projects/gc/gcdata/database/bootstrap_postgres.py).
