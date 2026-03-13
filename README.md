# Frammer AI Dashboard

React + Vite frontend with a Node/Express API and PostgreSQL analytics backend.

## Current Status (March 2026)
- Frontend is modularized into feature modules: Overview, Usage & Trends, Funnel, Explorer.
- API is modularized by route domain under `backend/routes`.
- SQL/query logic is centralized under `backend/queries` (no large inline SQL blocks in route handlers).
- Config and DB wiring are separated into `backend/config` and `backend/db`.
- Local username/password auth with self-issued JWT is integrated.
- Role-based data access is enforced:
    - `website_admin`: all clients/users
    - `client_admin`: scoped to one client
    - `user`: scoped to one user

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
- `JWT_SECRET`, `JWT_EXPIRES_IN`: JWT settings
- `VITE_API_BASE_URL`: frontend-to-API base URL

3. Install dependencies:

```bash
npm install
```

4. Initialize auth schema and seed local users:

```bash
npm run seed:auth
```

If your DB user cannot create tables in `public`, run once as `postgres` and then seed again:

```bash
sudo -u postgres psql -d frammer_database -f backend/db/auth_schema.sql
sudo -u postgres psql -d frammer_database -c "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app_users TO <your_pg_user>;"
sudo -u postgres psql -d frammer_database -c "GRANT USAGE, SELECT ON SEQUENCE app_users_id_seq TO <your_pg_user>;"
npm run seed:auth
```

Default seeded users (override via `.env`):
- `website_admin` / `Admin@12345`
- `client_admin_client1` / `Client@12345`
- `user_local_1` / `User@12345`

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
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/overview`
- `GET /api/usage-trends`
- `GET /api/funnel`
- `GET /api/funnel/video/:videoId`
- `GET /api/explorer/dimensions`
- `GET /api/explorer/multidim`
- `GET /api/explorer/tables`
- `GET /api/explorer/table/:tableName`
- `GET /api/explorer/chart`

Notes:
- All `/api/*` analytics routes require `Authorization: Bearer <token>`.
- `/api/explorer/tables`, `/api/explorer/table/:tableName`, and `/api/explorer/chart` are restricted to `website_admin`.

## Directory Structure
```text
.
├── app.js
├── app.jsx
├── server.js
├── backend
│   ├── app.js
│   ├── auth
│   │   └── jwt.js
│   ├── config
│   │   └── env.js
│   ├── db
│   │   ├── auth_schema.sql
│   │   ├── pool.js
│   │   └── seedAuthUsers.js
│   ├── middleware
│   │   └── auth.js
│   ├── queries
│   │   ├── analyticsShared.js
│   │   ├── explorerQueries.js
│   │   ├── funnelQueries.js
│   │   └── overviewQueries.js
│   ├── routes
│   │   ├── api.js
│   │   ├── auth.js
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
- `JWT_SECRET`: signing secret used for local JWT issue/verify
- `JWT_EXPIRES_IN`: token validity duration (example: `8h`)
- `AUTH_WEBSITE_ADMIN_USERNAME`, `AUTH_WEBSITE_ADMIN_PASSWORD`: seeded website admin credentials
- `AUTH_CLIENT_ADMIN_USERNAME`, `AUTH_CLIENT_ADMIN_PASSWORD`, `AUTH_CLIENT_ADMIN_CLIENT_NAME`: seeded client admin credentials and mapped client
- `AUTH_USER_USERNAME`, `AUTH_USER_PASSWORD`, `AUTH_USER_ID`: seeded user credentials and mapped user
- `VITE_API_BASE_URL`: frontend API base URL

## Notes
- Keep `.env` local; commit `.env.example` only.

