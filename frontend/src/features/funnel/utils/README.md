# Funnel Utils

Utility functions for shaping Funnel data into Chart.js Sankey-friendly structures.

## File

- `funnelFlow.js`

This module centralizes all non-UI flow transformations used by the Funnel feature. Its main goals are:
- normalize link payloads from mixed sources
- group tiny edges to reduce Sankey noise
- generate breakdown -> outcome links with optional top-N source limiting
- provide consistent Sankey chart options and tooltip math

## Exports

### Constants

- `SMALL_FLOW_SHARE` (default `0.018`)
  - Minimum share threshold used by `groupSmallLinks`.
  - Links below this share may be grouped into `Other` depending on edge type.

- `MAX_BREAKDOWN_SOURCES` (default `10`)
  - Default top-N source cap used by `buildBreakdownOutcomeLinks`.

### `normalizeSankeyLinks(links = [])`

Normalizes and validates incoming links.

Input shape (per item):
- `from`
- `to`
- `flow`
- optional `edgeType`

Behavior:
- coerces values to `{ from: string, to: string, flow: number, edgeType }`
- removes invalid links (`from`/`to` missing, or `flow <= 0`)
- applies deterministic sort:
  - non-`Other` sources first
  - higher flow first
  - then lexical tie-breakers

Returns:
- sorted, clean links array

### `groupSmallLinks(links = [], minShare = SMALL_FLOW_SHARE)`

Reduces Sankey clutter by folding small links into `from -> Other` buckets.

Behavior:
- computes global `threshold = totalFlow * minShare`
- preserves semantically important edges even when small:
  - `client_to_*`
  - `*_to_published`
  - `*_to_not_published`
  - `published_to_platform`
- groups only eligible low-flow links into `Other`
- keeps deterministic sort order

Returns:
- grouped links array

### `buildBreakdownOutcomeLinks(rows, breakdown, maxSources, aggregateRemainderAsOther, publishedPlatformTailLinks)`

Builds composition Sankey links from aggregated breakdown rows.

Expected `rows` fields:
- `label` (source label)
- `created_count`
- `published_count`

Derived values:
- `notPublished = max(created_count - published_count, 0)`

Core behavior:
- sorts sources by `created_count` descending
- keeps top `maxSources`
- emits links:
  - `<source> -> Published`
  - `<source> -> Not Published`
- optional remainder aggregation:
  - `Other -> Published`
  - `Other -> Not Published`

Platform tail behavior:
- accepts optional `publishedPlatformTailLinks`
- keeps only `Published -> <platform>` links
- rescales tail flows to match computed `Published` inflow to prevent Sankey mismatch

Returns:
- finalized composition links array

### `buildFromTotals(links = [])`

Computes total outgoing flow per `from` node.

Returns:
- object map `{ [fromNode]: totalFlow }`

Used primarily for tooltip denominator math.

### `makeSankeyOptions(fromTotals = {}, extras = {})`

Returns shared Chart.js Sankey options with consistent styling and tooltips.

Tooltip behavior:
- title: `from -> to`
- body: absolute flow + percentage share of source node

Example label format:
- `1,240 flow (62.5% of Channel A)`

`extras` can override/extend default chart options.

## Typical Integration Flow

1. Build or fetch raw links.
2. Normalize links with `normalizeSankeyLinks`.
3. Optionally reduce noise using `groupSmallLinks`.
4. Compute `fromTotals` with `buildFromTotals`.
5. Build options with `makeSankeyOptions(fromTotals, extras)`.
6. Feed links + options into `react-chartjs-2` Sankey chart.

For composition mode (breakdown -> outcome -> platform):
1. Build source outcome links via `buildBreakdownOutcomeLinks`.
2. Optionally pass platform tail links for `Published -> platform` continuation.
3. Use returned links directly in chart dataset.

## Data Contracts and Assumptions

- Flow values are numeric and non-negative.
- `Published` and `Not Published` are reserved outcome nodes.
- `Other` is reserved for grouped minor source categories.
- `buildBreakdownOutcomeLinks` expects already-aggregated rows (not raw event-level data).

## Contributor Notes

- Keep all flow math here, not in JSX components.
- Preserve deterministic sorting to avoid chart jitter between renders.
- If introducing new edge types, update grouping preservation logic in `groupSmallLinks` deliberately.
- If node names change (for example `Published` label), update all reserved-node filters in one pass.
- Maintain scaling logic for platform tails so Sankey totals remain visually and mathematically coherent.
