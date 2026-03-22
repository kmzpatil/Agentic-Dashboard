# Frammer Frontend

React + Vite dashboard UI for Frammer analytics. This frontend talks to the Python FastAPI backend (served from the repo-level `backend` package) and renders multiple analytics surfaces such as Overview, Funnel, Usage Trends, Explorer, Labs, and ATLAS.

## What Is In This Folder

- Vite app entrypoint and build config
- Frontend-only styling/config files (Tailwind, PostCSS)
- Modular feature surfaces under `src/features`
- Shared component library under `src/components`
- Shared hooks and helpers under `src/hooks` and `src/lib`

## Tech Stack

- React 19
- Vite 5
- Tailwind CSS
- Chart.js + react-chartjs-2
- chartjs-chart-sankey
- lucide-react
- react-markdown + remark-gfm

## Prerequisites

- Node.js 18+
- npm 9+
- Python 3.10+
- PostgreSQL (local or remote)

## Setup

1. Install frontend dependencies:

```bash
npm install
```

2. Create env file in `frontend/` (or repo root if you prefer shared env):

```bash
cp .env.example .env
```

3. Configure environment values (see Environment Variables section).

4. Ensure Python backend dependencies are installed from the repo root as needed.

## Run

### Frontend only

```bash
npm run dev
```

Frontend URL:
- `http://localhost:5173`

### API only (FastAPI backend from repo root package)

```bash
npm run api
```

API URL:
- `http://localhost:4000`

### Full local stack (DB start + API + Vite)

```bash
npm run dev:full
```

## Build and Preview

```bash
npm run build
npm run preview
```

## Useful Scripts

- `npm run dev`: start Vite dev server
- `npm run api`: start FastAPI app via uvicorn
- `npm run dev:full`: start DB helper + API + Vite concurrently
- `npm run db:start`: start local Postgres helper
- `npm run db:stop`: stop local Postgres helper
- `npm run db:status`: check local Postgres helper status
- `npm run db:bootstrap`: bootstrap Postgres from dataset
- `npm run seed:auth`: seed auth users

## Environment Variables

Core runtime variables used by frontend/backend integration:

- `VITE_API_BASE_URL`: frontend API base URL (for browser requests)
- `PORT` or `API_PORT`: API service port override (default `4000`)
- `POSTGRES_HOST` / `PGHOST`
- `POSTGRES_PORT` / `PGPORT`
- `POSTGRES_DB` / `PGDATABASE`
- `POSTGRES_USER` / `PGUSER`
- `POSTGRES_PASSWORD` / `PGPASSWORD`
- `POSTGRES_SSLMODE` / `PGSSLMODE`

## Source Layout

```text
src/
├── main.jsx
├── AppShell.jsx
├── index.css
├── components/
├── features/
├── hooks/
└── lib/
```

### Features

- `src/features/overview` — KPI cards, top performers, alerts
- `src/features/usage` — Time-series trends and anomaly detection
- `src/features/funnel` — Pipeline visualization (upload → create → publish)
- `src/features/explorer` — Multi-dimensional data analysis
- `src/features/journey` — User path and engagement tracking
- `src/features/quality` — Data quality metrics and issues
- `src/features/talk` — ATLAS — AI analytics chat
- `src/features/wrapped` — Period summary reports
- `src/features/shared` — Shared/placeholder components

### Shared Layers

- `src/components`: reusable UI components
- `src/hooks`: reusable hooks (`useApi`, `useVoiceInput`)
- `src/lib`: constants, chart registration, formatters

## Documentation Index

### Top-level shared docs

- `src/components/README.md`
- `src/hooks/README.md`
- `src/lib/README.md`

### Components docs

- `src/components/artifacts/README.md`
- `src/components/charts/README.md`
- `src/components/chat/README.md`
- `src/components/common/README.md`
- `src/components/insights/README.md`

### Feature docs

- `src/features/overview/README.md`
- `src/features/usage/README.md`
- `src/features/funnel/README.md`
- `src/features/funnel/components/README.md`
- `src/features/funnel/utils/README.md`
- `src/features/explorer/README.md`
- `src/features/talk/README.md`
- `src/features/shared/README.md`

## API Surface (Frontend-consumed)

Key routes consumed by this frontend include:

- `GET /api/health`
- `GET /api/overview`
- `GET /api/insights`
- `GET /api/usage-trends/*`
- `GET /api/funnel`
- `GET /api/funnel/filter-options`
- `GET /api/funnel/video/:videoId`
- `GET /api/explorer/*`
- `POST /api/chat`
- `GET /api/conversations`
- `GET /api/conversations/:id`
- `DELETE /api/conversations/:id`
- `GET /api/labs/simulator/*`
- `POST /api/labs/simulator/start|stop|reset`

## Notes

- Keep `.env` local and out of version control.
- Prefer adding docs near code (folder-level READMEs) and linking them here.
- If a feature contract changes, update both implementation and its README in the same change.
