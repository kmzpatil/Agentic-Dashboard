# Common Components

Shared, reusable UI primitives used across feature modules.

## Files

- `KpiCard.jsx`
- `Skeleton.jsx`

## `KpiCard.jsx`

Reusable KPI card with optional sparkline and optional add/remove affordances.

### Export

- default component: `KpiCard`

### Props

- `title`: KPI label text.
- `value`: primary metric value.
- `subtitle`: secondary context text.
- `trendData` (optional): numeric array for sparkline.
- `onRemove` (optional): renders remove button (`X`) in top-right.
- `onAdd` (optional): renders add button (`Plus`) in top-right.
- `onClick` (optional): makes entire card clickable.

### Behavior

- Registers required Chart.js line primitives locally.
- Sparkline color is trend-aware:
  - green when last value >= first value
  - red otherwise
- Sparkline uses gradient fill and no tooltips for compact dashboard display.
- Add/remove buttons stop event propagation so card click handlers do not trigger.

### Typical Usage

```jsx
<KpiCard
  title="PUBLISHED"
  value="12,340"
  subtitle="420 hrs"
  trendData={[20, 22, 25, 23, 28]}
  onClick={() => openDetails('published')}
/>
```

## `Skeleton.jsx`

Collection of loading placeholder components for module-level and section-level skeleton states.

### Base export

- `Skeleton`
  - Generic shimmer block component with custom className/style.

### Section-level exports

- `KpiSkeleton`
- `ChartSkeleton`
- `TableSkeleton`
- `SankeySkeleton`
- `SidebarSkeleton`
- `AnomalyListSkeleton`
- `MetricStripSkeleton`
- `MultiDimSkeleton`

### Page/module-level exports

- `OverviewSkeleton`
- `UsageTrendsSkeleton`
- `FunnelSkeleton`
- `ExplorerSkeleton`

### Behavior and styling notes

- Uses dark theme shimmer blocks (`animate-pulse`, neutral palette).
- Most skeletons are compositional: larger skeletons reuse smaller building blocks.
- Intended to preserve layout height and reduce content shift while data loads.

## Dependencies

`KpiCard`:
- `chart.js`
- `react-chartjs-2`
- `lucide-react`

`Skeleton` module:
- React only

## Cross-Feature Usage

These components are used by multiple feature modules, including:
- overview
- usage trends
- funnel
- explorer
- simulator and other dashboard surfaces that need KPI cards or loading placeholders

## Contributor Guidance

When extending `KpiCard`:
- Keep default card footprint stable to avoid layout regressions in KPI grids.
- Preserve `stopPropagation` behavior for icon buttons.
- Prefer non-interactive sparklines (tooltips off) for consistency with existing cards.

When adding new skeletons:
- Match existing neutral color + border language.
- Keep dimensions close to the loaded state component to minimize CLS.
- Reuse `Skeleton` building block rather than duplicating pulse styles.

## Known Caveat

`KpiSkeleton` currently uses a dynamic class token pattern:
- `md:grid-cols-${count}`

Depending on Tailwind configuration, dynamically constructed class names may not be generated unless safelisted. If responsive column behavior looks incorrect in production builds, replace with static class mapping or safelist those classes.
