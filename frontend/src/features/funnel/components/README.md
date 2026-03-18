# Funnel Components

UI component layer for the Funnel feature.

This folder contains presentation and interaction components used by the funnel surface in `FunnelModule.jsx`. The components are intentionally split by analysis tab so each section can evolve independently while sharing a consistent filter context.

## Components at a Glance

### `FunnelFilterBar.jsx`
Role-aware filter and breakdown controller.

Responsibilities:
- Renders available `View by` options based on user role.
- Loads selectable filter options from `GET /api/funnel/filter-options`.
- Emits filter and breakdown updates to parent state.
- Displays active filter pills with per-filter clear + global reset.

Key props:
- `authUser`
- `breakdown`
- `filters`
- `onBreakdownChange(nextBreakdown)`
- `onFiltersChange(nextFilters)`

Role behavior:
- `website_admin`: can view/filter by client, user, team.
- `client_admin`: can view/filter by user, team (no client selector).
- `user`: limited view-by and no user/team selectors.

### `OverviewFlowTab.jsx`
Main funnel-flow storytelling panel.

Responsibilities:
- Shows view/filter context chips.
- Renders `PipelineStrip` summary metrics.
- Renders two Sankey charts:
  - stage flow (Upload -> Processed -> Created -> Published)
  - composition flow (breakdown source -> outcome -> platform)
- Supports source-limiting controls for composition chart (`Top N + Other` vs `Show all`).

Key props:
- `data`
- `breakdown`
- `filters`
- `groupedCompositionCount`
- `stageSankeyData`, `stageSankeyOptions`
- `compositionSankeyData`, `compositionSankeyOptions`
- `compositionChartRef`
- `handleCompositionClick`, `handleCompositionChartHover`
- `compositionSourceMode`, `onCompositionSourceModeChange`
- `compositionTopN`, `onCompositionTopNChange`
- `totalBreakdownSources`, `hiddenBreakdownSources`

### `PipelineStrip.jsx`
Compact KPI and stage-transition summary strip.

Responsibilities:
- Reads stage counts and KPI aggregates from `data`.
- Computes transition indicators and tone states (healthy/watch/risk).
- Displays pipeline progression and core KPI mini-cards.

Data expectations (fallback-aware):
- Stage values from `data.pipelineStrip` or `data.stageCounts`.
- KPI values from `data.kpis`.

### `ContentAnalysisTab.jsx`
Breakdown conversion analysis with role-specific detail.

Responsibilities:
- Displays active view/filter chips.
- Non-client view: bar chart for publish conversion by selected breakdown.
- Admin + client breakdown: detailed input-type x client heatmap with dynamic color scaling.
- Admin-only chart: publish conversion by client.

Key props:
- `authUser`
- `data`
- `breakdown`
- `filters`

### `ChannelEfficiencyTab.jsx`
Efficiency and waste diagnostics for channels and teams.

Responsibilities:
- Builds high-volume/low-yield segmentation using percentile thresholds.
- Highlights risk quadrant on scatter charts via custom Chart.js plugin.
- Shows ranked absolute waste lists for channels and teams.
- Visualizes publish lag distribution and team efficiency comparison.
- For admins, color-groups channel scatter points by client.

Key props:
- `authUser`
- `data`
- `breakdown`
- `filters`

Important internal behavior:
- Uses percentile cutoffs (`P70` volume, `P30` yield) to classify risk.
- Adds plugin-based radial overlay to emphasize high-cost quadrant.

### `DataExplorerTab.jsx`
Tabular breakdown + drilldown inspector for raw video journeys.

Responsibilities:
- Displays top-down breakdown table (uploaded/created/published/conversion).
- Shows per-video journey list with output mix.
- Admin/client_admin only: fetches detailed per-video journey from `GET /api/funnel/video/:videoId` (with active filter query).
- Resets selected video when breakdown or filters change.

Key props:
- `authUser`
- `data`
- `breakdown`
- `filters`

## Shared Patterns

- Common card shell style (`bg-[#111111]`, rounded border cards) appears across tabs.
- Context chips (`View by`, active filter count) are repeated for orientation.
- Chart rendering uses `react-chartjs-2` `Chart` component with local options per tab.
- Most formatting uses shared utilities from `src/lib/formatters`.

## Parent-Child Data Flow

1. Parent module resolves role, filter state, breakdown state, and API payloads.
2. `FunnelFilterBar` updates those states via callbacks.
3. Tab components consume the resolved `data + filters + breakdown + authUser`.
4. `DataExplorerTab` may perform an additional scoped fetch for selected video detail.

## Extending Safely

When adding a new funnel tab component:
- Keep role restrictions explicit and colocated with UI controls.
- Reuse shared context chips so users always know active view/filter state.
- Prefer derived data with `useMemo` for chart payload shaping.
- Define clear empty-state copy for unavailable role/filter combinations.
- Keep formatting consistent with shared formatters instead of ad-hoc conversions.

When adding new filters:
- Update options endpoint contract and filter bar selects together.
- Ensure filter query propagation is preserved for drilldowns (especially video inspector).
- Validate role gating so restricted filters are not shown to lower-privilege users.

## Quick Validation Checklist

- Switching `View by` updates all tab content without stale selections.
- Role changes hide/show the correct controls and admin-only charts.
- Reset and per-pill clear both produce expected filter state.
- Sankey charts render with both sparse and dense data.
- Video inspector fetch works only for `website_admin`/`client_admin`.
- Empty data states remain readable and non-breaking.
