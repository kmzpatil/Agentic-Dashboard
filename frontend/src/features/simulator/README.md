# Simulator Feature

Operational panel for controlling and monitoring an isolated data simulator environment.

## Main Module

- File: `SimulatorModule.jsx`
- Export: default React component `SimulatorModule`
- Purpose: run simulator actions, monitor table/log activity, and track data quality in near real-time.

## High-Level Behavior

- Polls simulator endpoints every 5 seconds.
- Shows KPI summary cards for run state, table count, log volume, and quality score.
- Provides action controls to start, stop, and reset simulator execution.
- Displays table row counts and recent simulator logs.

## Data Sources

The module calls these endpoints under `API_BASE`:

### Status and telemetry
- `GET /api/labs/simulator/status`
- `GET /api/labs/simulator/tables`
- `GET /api/labs/simulator/logs?limit=20`
- `GET /api/labs/simulator/quality`

### Actions
- `POST /api/labs/simulator/start?ops_per_batch=<n>&interval=<seconds>`
- `POST /api/labs/simulator/stop`
- `POST /api/labs/simulator/reset`

## State Model

Core state managed by the module:
- `status`: simulator runtime metadata and log counters.
- `tables`: list of simulator tables and row counts.
- `logs`: recent operation log entries.
- `quality`: quality report payload (`overall_score`, issue counts).
- `loading`: request/action in-progress flag.
- `error`: top-level user-facing error message.
- `opsPerBatch`: configurable operation batch size used by start action.
- `intervalSeconds`: configurable interval used by start action.

## Control Panel

- `Ops per batch`: numeric input for generated operations per cycle.
- `Interval (sec)`: numeric input for simulator cadence.
- Action buttons:
  - `Start`: starts simulator with selected parameters.
  - `Stop`: stops active simulator loop.
  - `Reset`: resets simulator state/data.

## Rendering Notes

- Uses shared `KpiCard` for top metrics.
- Uses `Intl.NumberFormat` for readable counts.
- Auto-refresh timer is cleaned up on unmount.
- Initial control defaults are synced from `status.settings` only once after first successful load.

## Error Handling

- Any failed fetch/action updates a single error banner.
- UI remains interactive after failures to allow retry.
- Manual Refresh button triggers immediate reload of all sections.

## Contributor Notes

- Keep all simulator fetches grouped in `loadAll` to maintain synchronized snapshots.
- If action API contracts change, update `runAction` URL construction first.
- Preserve one-time default sync behavior (`syncedDefaults`) so user-entered values are not overwritten on every poll.
