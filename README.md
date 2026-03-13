# Frammer AI Dashboard

React + Vite frontend with a Node/Express API and PostgreSQL analytics backend.

## Current Status (March 2026)
- Frontend is modularized into feature modules: Overview, Usage & Trends, Funnel, Explorer.
- API is modularized by route domain under `backend/routes`.
- SQL/query logic is centralized under `backend/queries` (no large inline SQL blocks in route handlers).
- Config and DB wiring are separated into `backend/config` and `backend/db`.
- Basic runtime smoke checks are passing (`/api/health`, `/api/explorer/tables`).

## Tech Stack
- Frontend: React 19, Vite 5, Tailwind CSS
- Charts: Chart.js, react-chartjs-2, chartjs-chart-sankey
- Backend: Express 5, pg
- Database: PostgreSQL (`frammer_database`)

## Prerequisites
- Node.js 18+
- npm 9+
- PostgreSQL (local or remote)

## Setup
1. Create env file:

```bash
cp .env.example .env
```

2. Update `.env` values:
- `PORT` (or `API_PORT`): API port (default `4000`)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSWORD`: PostgreSQL connection
- `VITE_API_BASE_URL`: frontend-to-API base URL

3. Install dependencies:

```bash
npm install
```

## Run
Run frontend + API together:

```bash
npm run dev:full
```

Run separately:

```bash
npm run api
npm run dev
```

Default URLs:
- Frontend: `http://localhost:5173`
- API: `http://localhost:4000`

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

## Directory Structure
```text
.
├── app.js
├── app.jsx
├── server.js
├── backend
│   ├── app.js
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
- `PORT`: API port fallback
- `API_PORT`: optional API port alias
- `PGHOST`: PostgreSQL host or socket path
- `PGPORT`: PostgreSQL port
- `PGUSER`: PostgreSQL username
- `PGDATABASE`: PostgreSQL database name
- `PGPASSWORD`: PostgreSQL password
- `VITE_API_BASE_URL`: frontend API base URL

## Notes
- Keep `.env` local; commit `.env.example` only.

