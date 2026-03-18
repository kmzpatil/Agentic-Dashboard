# Labs Feature

Experimental workspace for non-core analytics surfaces.

## Main Module

- File: `LabsModule.jsx`
- Export: default React component `LabsModule`
- Purpose: lightweight shell that introduces the Labs context and hosts experimental tools.

## Structure

`LabsModule` renders two major parts:

1. Labs hero/header section
- Visual label: Frammer Labs
- Messaging that this area is for scenario testing and experimentation
- Badge: Experimental Surface

2. Embedded simulator surface
- Renders `SimulatorModule` from `../simulator/SimulatorModule`
- Reuses the full simulator control and monitoring experience inside Labs

## Behavior Notes

- No direct API calls are made in `LabsModule` itself.
- Data operations are delegated to `SimulatorModule`.
- The module acts as a presentation and composition layer for experimental workflows.

## Dependencies

- `lucide-react` icons: `FlaskConical`, `Sparkles`
- `SimulatorModule` from the simulator feature

## Contributor Notes

- Keep this file focused on Labs framing and composition.
- Add new experimental panels here by composing dedicated feature modules, rather than embedding heavy logic directly in this shell.
- If Labs grows into multiple tools, consider splitting into tabs/sections while preserving simulator as a standalone module.
