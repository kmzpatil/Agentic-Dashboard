# Funnel Feature

Interactive pipeline analysis surface for understanding where volume turns into published output and where waste accumulates.

This feature combines:
- role-aware filtering
- Sankey flow visualization
- efficiency diagnostics
- content conversion analysis
- drilldown-level journey inspection

## Entry Point

- File: `FunnelModule.jsx`
- Export: default React component `FunnelModule`

## Component Contract

```jsx
<FunnelModule
  authUser={authUser}
  routeState={routeState}
  onNavigate={onNavigate}
/>
```

### Props

- `authUser`: authenticated user object (role-aware behavior).
- `routeState`: initial route context (`breakdown` and funnel filter keys).
- `onNavigate`: callback used to persist/propagate navigation state when filters or zoom actions change.

## Folder Structure

```text
funnel/
├── FunnelModule.jsx
├── components/
│   ├── ChannelEfficiencyTab.jsx
│   ├── ContentAnalysisTab.jsx
│   ├── DataExplorerTab.jsx
│   ├── FunnelFilterBar.jsx
│   ├── OverviewFlowTab.jsx
│   ├── PipelineStrip.jsx
│   └── README.md
└── utils/
    ├── funnelFlow.js
    └── README.md
```

## Primary Responsibilities in `FunnelModule`

- Owns canonical state for:
  - `breakdown`
  - `filters`
  - active analysis tab
  - composition source mode (`top` vs `all`)
  - composition top-N cap
- Synchronizes local state with incoming `routeState`.
- Builds funnel query string and fetches data with `useApi`.
- Shapes Sankey datasets/options via utility helpers.
- Handles composition-chart click-to-zoom behavior.
- Routes view rendering across tab components.

## Analysis Tabs

Tab IDs in module:
- `overview` -> Pipeline & Flow
- `channel` -> Channel Efficiency
- `content` -> Content Analysis
- `explorer` -> Data Explorer

Tab implementation details are documented in:
- `components/README.md`

## Data Fetching

`FunnelModule` main query:
- `GET /api/funnel?breakdown=<...>&<filters...>`

Child component queries:
- `FunnelFilterBar`: `GET /api/funnel/filter-options`
- `DataExplorerTab` (admin/client_admin drilldown): `GET /api/funnel/video/:videoId`

## Filter and Breakdown Model

Supported filter keys:
- `client`
- `input_type`
- `language`
- `channel`
- `user`
- `team`

Behavior notes:
- `routeState` can pre-populate breakdown and any filter key.
- Switching breakdown may clear the same-dimension filter to prevent conflicting context.
- Filter state is propagated through `onNavigate` so parent routing can stay in sync.

## Sankey Flow Pipeline

Flow processing is abstracted in `utils/funnelFlow.js` and includes:
- link normalization
- small-link grouping into `Other`
- breakdown outcome link construction
- source-total calculations for tooltip percentages
- shared Sankey chart option generation

For full utility contracts and assumptions, see:
- `utils/README.md`

## Composition Source Controls

Overview flow supports two composition modes:
- `Top N + Other`: keeps strongest sources and aggregates the rest.
- `Show all`: renders all available breakdown sources.

Default top-N values are dimension-specific via `BREAKDOWN_SOURCES_LIMITS` in `FunnelModule.jsx`.

## Role-Aware Behavior (High-Level)

- Breakdown options and filters are role-gated in filter bar.
- Explorer drilldown detail fetch is restricted to `website_admin` and `client_admin`.
- Client-level visibility and payload masking rules are enforced server-side; UI should not assume unrestricted data.

## Integration Notes

- Uses shared `useApi`, `API_BASE`, and formatter helpers from `src/lib`.
- Uses Chart.js Sankey through tab components and utility-generated options.
- Uses skeleton state from shared components during loading.

## Contributor Workflow

When adding/changing funnel behavior:

1. Update orchestration in `FunnelModule.jsx` only for cross-tab concerns.
2. Keep chart/data transformation logic in `utils/funnelFlow.js`.
3. Keep presentation-specific behavior inside tab components.
4. Preserve role-gating in both UI controls and backend payload logic.
5. Validate that `onNavigate` state remains stable after filter/breakdown/zoom changes.

## Quick QA Checklist

- Route-initialized filters appear correctly on first render.
- Changing `View by` updates data and visual context chips.
- Top-N composition mode and Show-all mode both render correctly.
- Composition click-to-zoom updates filters as expected.
- Role-restricted controls and drilldowns are hidden/unavailable for non-privileged roles.
- Empty-data and API-error states remain clear and non-breaking.

## Related Docs

- `components/README.md`
- `utils/README.md`
