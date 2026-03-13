# Frammer AI Dashboard (Frontend + API)

This repository contains:
- A React + Vite + Tailwind dashboard UI
- A Node/Express API server
- PostgreSQL-backed analytics endpoints for Overview, Usage & Trends, Funnel, and Explorer

## 1) Prerequisites
- Node.js 18+
- npm 9+
- PostgreSQL running locally

## 2) Environment Setup
Create your local env file from the example:

```bash
cp .env.example .env
```

Edit `.env` values as needed:
- `PORT`: API server port
- `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSWORD`: DB connection
- `VITE_API_BASE_URL`: frontend URL to backend API

## 3) Install Dependencies
```bash
npm install
```

## 4) Database Notes
This app expects the `frammer_database` schema loaded in PostgreSQL.

Quick connectivity check:
```bash
psql -h /run/postgresql -p 5433 -U manish -d frammer_database -c "SELECT 1;"
```

If your PostgreSQL uses different host/port/user, update `.env` accordingly.

## 5) Run the App
Run API + frontend together:
```bash
npm run dev:full
```

Or separately:

API:
```bash
npm run api
```

Frontend:
```bash
npm run dev
```

Frontend default URL:
- `http://localhost:5173`

API default URL:
- `http://localhost:4000`

## 6) Build for Production
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## 7) Project Structure
- `app.jsx`: Main dashboard UI (Overview, Usage & Trends, Funnel, Explorer)
- `server.js`: Express API + analytics SQL endpoints
- `src/`: Frontend entry + global styles
- `tailwind.config.js`, `postcss.config.js`, `vite.config.js`: build/style tooling

## 8) Environment Variables Reference
- `PORT`: API port
- `PGHOST`: PostgreSQL host or socket path
- `PGPORT`: PostgreSQL port
- `PGUSER`: PostgreSQL username
- `PGDATABASE`: PostgreSQL database name
- `PGPASSWORD`: PostgreSQL password (optional when peer/local auth is enabled)
- `VITE_API_BASE_URL`: Base URL used by frontend to call API

## 9) Git Hygiene
Local secrets are ignored by git:
- `.env`
- `.env.local`

Commit the template only:
- `.env.example`

