# Database Simulator API

This simulator uses your Postgres database (configured via `PG*` or `POSTGRES_*` in `.env`) and writes only SIM-tagged rows so it does not touch real data.

## Behavior

- Simulator rows are isolated using:
  - `Client_Name = "Simulated Client"` for `clients`, `users`, `channels`
  - `Headline` prefixed with `"SIM:"` for `raw_videos`
- Related rows (`created_assets`, `published_posts`, `post_distribution`, `raw_video_channel`) are linked to those SIM rows.
- All simulator operations are logged to `_simulation_log`.

## Base URL

```
http://localhost:4000/api/simulator
```

## Endpoints

### GET /status
Returns simulator status, per-table SIM row counts, and log counts.

Example response:
```
{
  "running": true,
  "tables": {"clients": 1, "users": 10, "raw_videos": 20},
  "log_counts": {"SUCCESS": 120, "ERROR": 1},
  "settings": {"ops_per_batch": 5, "interval": 2.0}
}
```

### POST /start
Starts the simulator loop.

Query params:
- `ops_per_batch` (int, 1-50, default 5)
- `interval` (float, 0.5-30.0, default 2.0)

Example:
```
POST /start?ops_per_batch=8&interval=1.5
```

### POST /stop
Stops the simulator loop.

### POST /reset
Stops the loop, deletes SIM rows, clears `_simulation_log`, then reseeds SIM data.

### GET /tables
Returns table metadata and SIM row counts.

### GET /tables/{table_name}
Returns SIM rows for a given table.

Query params:
- `limit` (int, 1-500, default 50)
- `offset` (int, 0+, default 0)

### GET /logs
Returns log entries from `_simulation_log`.

Query params:
- `limit` (int, 1-1000, default 100)
- `offset` (int, 0+, default 0)
- `status` (string, optional)
- `table` (string, optional)

### GET /quality
Runs all quality checks and returns scores and issues.

### GET /metrics/timeseries
Returns counts of INSERT/UPDATE/DELETE operations over time.

## Notes

- The simulator does not create or drop your existing tables.
- If you change database credentials, restart the backend so the simulator reconnects.
