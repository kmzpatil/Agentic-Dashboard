# src

Application source root for the Frammer frontend.

This folder contains the app bootstrap, global styling, top-level shell, feature modules, and shared component/hook/lib layers.

## Entry Flow

1. `main.jsx` mounts `AppShell` into `#root`.
2. `AppShell.jsx`:
   - restores auth session
   - manages route state from URL query params
   - loads service health
   - renders top navigation and selected feature module
3. Feature modules under `features/` render screen-specific analytics UIs.

## Core Files

- `main.jsx`
  - React root bootstrap (`ReactDOM.createRoot`)
  - StrictMode wrapper

- `AppShell.jsx`
  - authentication/login/logout flow
  - URL query-state navigation (`view`, breakdown/filter params)
  - health pills for DB/AI/MCP status
  - top-level view switching:
    - Mission Control
    - Trends
    - Funnel
    - Explorer
    - Copilot
    - Labs

- `index.css`
  - Tailwind directives
  - global dark-theme base styles
  - root sizing and scrollbar/selection behavior

## High-Level Directory Map

```text
src/
├── AppShell.jsx
├── main.jsx
├── index.css
├── components/
├── features/
├── hooks/
└── lib/
```

## Layer Responsibilities

### `features/`
Feature-level modules and subdomains.

Current modules:
- `overview`
- `usage`
- `funnel`
- `explorer`
- `talk`
- `labs`
- `simulator`
- `shared`

### `components/`
Reusable UI components shared by multiple features.

Includes:
- chat components
- insight cards
- artifact renderers
- chart renderers
- common KPI/skeleton primitives
- layout widgets

### `hooks/`
Shared hooks for network and browser API behavior.

- `useApi`
- `useVoiceInput`

### `lib/`
Shared constants and utility helpers.

- Chart.js registration setup
- API constants / custom CSS tokens
- formatting utilities

## Route + State Model (from `AppShell`)

- Route state is query-string driven.
- `navigate(nextState)` merges/removes query params and updates current view.
- Feature modules receive route state and callback navigation for deep-linking.

This enables direct URLs for pre-filtered feature views.

## Documentation Index

### Shared layers

- `components/README.md`
- `hooks/README.md`
- `lib/README.md`

### Features

- `features/overview/README.md`
- `features/usage/README.md`
- `features/funnel/README.md`
- `features/funnel/components/README.md`
- `features/funnel/utils/README.md`
- `features/explorer/README.md`
- `features/talk/README.md`
- `features/labs/README.md`
- `features/simulator/README.md`
- `features/shared/README.md`

### Components subfolders

- `components/artifacts/README.md`
- `components/charts/README.md`
- `components/chat/README.md`
- `components/common/README.md`
- `components/insights/README.md`

## Contributor Notes

- Keep domain logic in features and shared rendering in components.
- Keep all cross-feature helper logic in hooks/lib.
- If adding a new feature folder, include a local README and add it to this index.
- If route/query behavior changes, update both `AppShell.jsx` and affected feature docs.
