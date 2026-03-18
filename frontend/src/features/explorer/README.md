# Explorer Feature

Flexible analysis workspace for slicing metrics by multiple dimensions and, for admins, directly inspecting raw tables.

## Main Module

- File: `ExplorerModule.jsx`
- Export: default React component `ExplorerModule`
- Purpose: provide two exploration surfaces in one module:
  - Multi-dimensional analytics (chart + derived table)
  - Raw table explorer (website_admin only)

## Component Contract

```jsx
<ExplorerModule authUser={authUser} />
```

### Props

- `authUser`: authenticated user object used for role-gating raw explorer access.

## View Modes

`ExplorerModule` manages two tabs:

- `multi`: Multi-Dim Analysis
  - Available to all roles.
  - Uses dimension/measure/time controls.
  - Renders chart and analysis table from aggregated query output.

- `raw`: Raw Table Explorer
  - Only available when `authUser.role === website_admin`.
  - Enables table selection, row limits, per-column filtering, and sorting.

## Data Endpoints

### Structural and filter metadata

- `GET /api/explorer/dimensions`
- `GET /api/explorer/channels`
- `GET /api/explorer/tables` (website_admin only)

### Multi-dimensional analysis

- `GET /api/explorer/multidim`

Query parameters assembled by module include:
- `dim1`
- `dim2`
- `measure`
- `timeGrain`
- `dateField`
- `channels`
- optional: `dim1Value`, `startDate`, `endDate`

### Raw table inspection

- `GET /api/explorer/table/:tableName?limit=:rowLimit` (website_admin only)

## Core State Model

Primary state domains:
- Analysis configuration: `dim1`, `dim2`, `measure`, `timeGrain`, `dateField`, `isTimeAnalysisOn`
- Channel filter: searchable multiselect with `all` sentinel
- Dim2 value filter: searchable multiselect with preselection behavior
- Date range: `startDate`, `endDate` + dual slider synchronization
- View routing: `viewTab` (`multi` or `raw`)
- Raw explorer controls: `tableName`, `rowLimit`, `columnFilters`, `sortConfig`
- Dimension table sorting: `dimTableSort`

## Multi-Dim Analysis Behavior

- Supports stacked grouped charting by `dim1` and optional `dim2`.
- Switches chart type by mode:
  - no time grain: bar chart from matrix rows
  - time analysis: line chart from time-series rows
- Provides deterministic color mapping per legend value.
- Applies frontend dim2 filtering to both charts and summary table.
- Auto-preselects first four dim2 values once fresh dim2 data arrives.

### Time Analysis Toggle

- When enabled:
  - forces effective `timeGrain` away from `none` (defaults to `day`)
  - surfaces date field selector (`upload_date`, `create_date`, `publish_date`)
- When disabled:
  - effective time grain returns to `none`
  - measure-focused matrix mode is emphasized

## Date Filtering UX

Date filters are dual-input plus slider:
- From date input
- To date input
- Dual range slider synced to both inputs

Constraints:
- Global slider bounds are fixed in module
- Slider ensures minimum one-day separation between handles

## Raw Table Explorer Behavior

Admin raw table view supports:
- Dynamic table selection (with `app_users` excluded from default table list)
- Row limit controls (`10`, `50`, `100`, `120`, `500`)
- Column-level filters:
  - text contains
  - numeric min/max
  - date start/end
  - searchable multiselect for high-cardinality categorical columns
- Tri-state sorting (`asc`, `desc`, `default`) with type-aware comparisons
  - numeric
  - date
  - string fallback

Filtering and sorting pipeline:
1. Fetch table rows
2. Apply column filters
3. Apply selected sort config
4. Render sorted/filtered result set

## Rendering Structure

In multi mode, layout consists of:
- Control bar
- Visual analysis chart panel
- Metrics sidebar
- Dimension analysis data table

In raw mode, layout consists of:
- Raw control bar
- Large scrollable data grid with sticky headers and filter row

## Shared Dependencies

- `useApi` hook for all API calls
- `API_BASE` shared constant
- `formatNumber` formatter
- `react-chartjs-2` (`Bar`, `Line`)
- `lucide-react` icons

## Contributor Notes

- Keep URL construction logic explicit and centralized before passing into `useApi`.
- Preserve role guards for raw explorer endpoints and UI controls.
- Maintain sentinel semantics (`all`) for multiselect filters.
- Reuse existing type-aware sort approach when adding new sortable columns.
- If introducing new dimensions/measures server-side, ensure dropdown defaults and collision handling remain valid.

## Testing and Validation Checklist

- Non-admin users cannot access raw table view.
- Channel and dim2 multiselects correctly support `all` and search filtering.
- Time analysis toggle updates chart mode and effective time grain as expected.
- Date inputs and slider remain synchronized.
- Multi-dim chart and analysis table stay consistent under dim2 filtering.
- Raw filters and sorting can be reset cleanly.
- Table switch clears stale raw filters/sort state.
