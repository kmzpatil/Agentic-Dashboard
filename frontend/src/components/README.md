# Frontend Components

Shared UI component library for the Frammer dashboard frontend.

This folder contains reusable building blocks used across feature modules (overview, funnel, usage, explorer, talk, labs). Components are grouped by domain so presentation concerns stay separate from feature orchestration.

## Structure

```text
components/
├── artifacts/
├── charts/
├── chat/
├── common/
├── insights/
└── layout/
```

## Folder Guide

### `artifacts/`
Assistant artifact rendering surface.

- Main component: `ArtifactCanvas`
- Renders artifact cards for:
  - charts
  - tables
  - KPI grids
- Consumes `artifacts` + `datasets` payloads from assistant responses.

Documentation:
- `artifacts/README.md`

### `charts/`
Lightweight XML-driven chart rendering.

- Main component: `XmlChartRenderer`
- Parses widget XML and renders KPI/bar/line/pie widgets.
- Useful for configurable chart payloads without writing dedicated JSX each time.

Documentation:
- `charts/README.md`

### `chat/`
Composable chat UI primitives.

- `ChatPanel`: side panel shell and API orchestration
- `ChatMessage`: user/assistant message rendering + markdown
- `ChatInput`: text/voice input and quick suggestions

Documentation:
- `chat/README.md`

### `common/`
Generic design-system-like primitives.

- `KpiCard`: reusable KPI tile with optional sparkline and actions
- `Skeleton` suite: loading states for sections and entire modules

Documentation:
- `common/README.md`

### `insights/`
Insight presentation components.

- `InsightCard`: severity-toned insight summary with confidence and CTA navigation

Documentation:
- `insights/README.md`

### `layout/`
High-level layout widgets used by dashboard shells.

- `FilterDock`: collapsible filter sidebar shell with static filter controls
- `PipelineRail`: compact pipeline stage strip using overview KPI totals

Note:
- `layout/` currently has no dedicated subfolder README; behavior is summarized here.

## Design and Composition Principles

- Keep feature-specific business logic in feature modules, not shared components.
- Keep shared components presentation-first and prop-driven.
- Prefer optional props and safe fallbacks over hard assumptions about payload shape.
- Maintain dark-theme consistency (`#050505` / `#111111` surfaces, neutral borders, accent highlights).
- Preserve role-aware behavior at call sites; shared components should stay generic unless explicitly role-bound.

## Data and Dependency Boundaries

- Components may consume shared utilities (`src/lib/*`) and hooks (`src/hooks/*`) when reused broadly.
- API requests should generally live in feature modules or container components.
- A few composite components (for example chat panel) include API wiring; if reused broadly, extract request logic to hooks/services.

## Typical Usage Pattern

1. Feature module owns page state and API data.
2. Feature passes prepared data/handlers into shared components.
3. Shared components render consistent UI and emit callbacks.
4. Feature module coordinates navigation, filtering, and persistence.

## Maintenance Checklist

When adding a new component folder under `components/`:

1. Add a local README in that folder describing contract and data shape.
2. Add the folder to this index.
3. Keep naming aligned with role:
   - `*Panel` for containers
   - `*Card` for content blocks
   - `*Rail/*Dock` for layout scaffolding
4. Document non-obvious payload assumptions and fallback behavior.

When changing existing shared components:

1. Verify downstream feature modules still pass compatible props.
2. Check loading/empty/error states remain graceful.
3. Ensure style changes preserve readability on dark backgrounds.
4. Update subfolder README and this index if scope changed.

## Related Paths

- Feature entry points: `src/features/*`
- Shared hooks: `src/hooks/*`
- Shared constants and formatters: `src/lib/*`
