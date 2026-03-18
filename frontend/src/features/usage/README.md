# Usage Feature

The usage feature renders historical usage trends, optional AI forecasting, anomaly overlays, and multi-dimensional breakdowns.

## Main Module

- File: `UsageTrendsModule.jsx`
- Export: default React component `UsageTrendsModule`
- Purpose: interactive analytics surface for pipeline activity over time.

## Component Contract

```jsx
<UsageTrendsModule
  authUser={authUser}
  routeState={routeState}
  onNavigate={onNavigate}
/>
```

### Props
- `authUser`: current authenticated user object. Role is used to scope certain filters.
- `routeState`: initial screen state (metric, granularity, forecasting mode).
- `onNavigate`: optional navigation callback for cross-surface actions.

## Data Sources

The module fetches data through `useApi` and `API_BASE`.

### Filter and validation endpoints
- `GET /api/usage-trends/v1/filters/options`
- `GET /api/usage-trends/v1/filters/date-range`
- `GET /api/usage-trends/v1/filters/validate`

### Metrics and trend endpoints
- `GET /api/usage-trends/v1/pipeline-metrics`
- `GET /api/trends`
- `GET /api/insights?surface=trends`

### Forecast endpoint
- `GET /api/usage-trends/v1/forecast/all-clients`

### Multi-dimensional endpoint
- `GET /api/usage-trends/v1/multi-dim`

## Key Behaviors

- Metric groups: counts, durations, rates, and advanced metrics.
- Granularity switch: day, week, month, quarter.
- Forecasting mode:
  - Supports configurable prediction horizon.
  - Accepts optional `cutoff_date` to pin forecast start.
  - Restricts prediction to compatible metric flow.
- Multi-dimensional analysis:
  - Dynamic analysis type selection.
  - Scoped client/user/date filters.
- Date range selection:
  - Dual-handle range slider based on backend min/max date window.
- Anomaly highlighting:
  - Uses trend anomaly payload to style chart points (drop/spike).
- Export:
  - CSV export for the plotted series.
  - PNG export from chart canvas.

## Local Utilities Inside Module

The file includes local helper UI/logic units:
- `FloatingDropdown`
- `GranularityPills`
- `CutoffDatePicker`
- `DateRangeSlider`
- date parsing/enumeration helpers
- filter query builder
- series shaping helpers for chart datasets

## Dependencies

- React hooks (`useState`, `useEffect`, `useMemo`, `useRef`)
- `react-chartjs-2` (`Line`)
- `lucide-react` icons
- shared frontend utilities:
  - `useApi`
  - `API_BASE`
  - `formatNumber`, `formatPct`
  - skeleton loaders from common components

## Notes for Contributors

- Keep API query parameter assembly centralized to avoid inconsistent filter behavior.
- Preserve stale-request guards to avoid race-condition UI updates.
- Any new metric should be reflected in:
  - metric option groups
  - formatting logic
  - backend metric support
- If adding forecast logic, validate compatibility with existing cutoff and prediction guards.
