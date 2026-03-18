# Shared Feature Modules

This folder contains reusable feature-level modules shared across navigation surfaces.

## Main Module

- File: `ComingSoonModule.jsx`
- Export: default React component `ComingSoonModule`
- Purpose: lightweight placeholder panel for routes/features that are intentionally not included in the current build scope.

## Component Contract

```jsx
<ComingSoonModule title="Explorer" />
```

### Props
- `title` (`string`): label shown as the placeholder heading.

## UI Behavior

- Renders a centered placeholder state with:
  - `Stethoscope` icon (from `lucide-react`)
  - title text
  - subtitle: `Not part of this build scope.`
- Uses neutral styling so it does not visually compete with active modules.

## When to Use

- Route exists in navigation but backend/frontend feature work is not ready.
- You need a consistent temporary state instead of blank content.
- Demo/staged environments where only a subset of modules is enabled.

## Contributor Notes

- Keep this module minimal and dependency-light.
- Avoid adding business logic or API calls in placeholders.
- If multiple placeholder types are needed, add new shared components instead of overloading this one with conditionals.
