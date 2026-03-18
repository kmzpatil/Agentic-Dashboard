# Insights Components

Reusable UI for rendering actionable AI insight cards.

## Main Component

- File: `InsightCard.jsx`
- Export: default component `InsightCard`
- Purpose: display an insight summary with severity tone, confidence score, evidence tags, and a call-to-action navigation button.

## Component Contract

```jsx
<InsightCard insight={insight} onNavigate={onNavigate} />
```

### Props

- `insight` (`object`, required)
  - insight payload rendered by the card.
- `onNavigate` (`function`, optional)
  - callback invoked when CTA button is clicked.

## Expected `insight` Shape

```json
{
  "severity": "critical",
  "confidence": 0.92,
  "title": "High drop in publish conversion",
  "summary": "Conversion declined 12% week-over-week in Channel A.",
  "evidence": ["WoW: -12%", "Channel: A", "Input: Webinar"],
  "cta": {
    "label": "Investigate in Funnel",
    "target": "funnel",
    "filter_state": {
      "view": "funnel",
      "breakdown": "channel",
      "channel": "A"
    }
  }
}
```

## Severity Styling

Severity tokens map to badge styles/icons via internal `SEVERITY_STYLES`:

- `critical`
  - red badge
  - `AlertTriangle` icon
- `warning`
  - amber badge
  - `Sparkles` icon
- `info`
  - sky badge
  - `Sparkles` icon

Fallback behavior:
- unknown severity defaults to `info` style.

## Rendering Behavior

- Displays severity badge and confidence percentage in card header.
- Renders title + summary body copy.
- Renders evidence chips only when `insight.evidence` has entries.
- CTA button label defaults to `Open` when absent.

Confidence display:
- `Math.round((insight.confidence || 0) * 100)`

## CTA Navigation Behavior

On button click:

1. If `insight.cta.filter_state` exists, passes it to `onNavigate`.
2. Otherwise passes `{ view: insight.cta.target }`.
3. If `onNavigate` is missing, click is a safe no-op due to optional chaining.

## Dependencies

- React
- `lucide-react` icons (`ArrowRight`, `AlertTriangle`, `Sparkles`)

## Usage Notes

- Keep `summary` concise; the card is optimized for scan-first dashboards.
- Prefer deterministic `evidence` strings (already human-readable).
- For cross-surface deep links, include full `cta.filter_state` so receiving modules can hydrate directly.

## Contributor Guidance

- Add new severities by extending `SEVERITY_STYLES` and preserving fallback behavior.
- Keep CTA logic centralized in the card click handler to avoid duplicated navigation branching in parent modules.
- Maintain confidence in normalized range `[0, 1]` before passing into this component.
