# Artifact Components

Rendering layer for assistant-generated analysis artifacts.

## Main Component

- File: `ArtifactCanvas.jsx`
- Export: default React component `ArtifactCanvas`
- Purpose: render structured assistant outputs (charts, tables, KPI grids) in a consistent, card-based canvas.

## Component Contract

```jsx
<ArtifactCanvas artifacts={artifacts} datasets={datasets} />
```

### Props

- `artifacts` (`Array`, default `[]`)
  - Artifact descriptors with metadata, kind, and rendering spec.
- `datasets` (`Array`, default `[]`)
  - Dataset payloads keyed by `id`, referenced by artifacts using `dataset_id`.

## Supported Artifact Kinds

### `chart`

Renderer: internal `ChartArtifact`

Uses:
- `react-chartjs-2` (`Bar`, `Line`, `Pie`)

Expected fields:
- `artifact.kind = chart`
- `artifact.dataset_id`
- `artifact.spec.chartType` (`bar`, `line`, `pie`)
- `artifact.spec.xField`
- `artifact.spec.yFields` (array)
- optional `artifact.spec.maxRows`

Behavior:
- builds chart data via `chartDataFromArtifact`
- slices dataset rows to `maxRows` (default 24)
- supports forecast-series styling for y-fields prefixed with `forecast_`

### `table`

Renderer: internal `TableArtifact`

Expected fields:
- `artifact.kind = table`
- `artifact.dataset_id`
- optional `artifact.spec.pageSize`

Dataset requirements:
- `dataset.schema` (array of `{ key, label }`)
- `dataset.rows` (array of objects)

Behavior:
- renders bordered table with sticky-like header styling
- displays first `pageSize` rows (default 12)

### `kpi-grid`

Renderer: internal `KpiArtifact`

Expected fields:
- `artifact.kind = kpi-grid`
- `artifact.spec.items` (array of `{ label, value }`)

Behavior:
- renders KPI cards in responsive grid layout

## Artifact Header Metadata

Each artifact card header shows:
- icon by kind (`chart`, `table`, `kpi-grid`)
- title (`artifact.title`)
- subtitle with `artifact.kind` and confidence percentage

Confidence formatting:
- `Math.round((artifact.confidence || 0) * 100)`

## Internal Helpers

Defined in `ArtifactCanvas.jsx`:

- `buildDatasetMap(datasets)`
  - Converts dataset array to id-keyed lookup map.

- `chartDataFromArtifact(artifact, dataset)`
  - Converts artifact spec + dataset rows into Chart.js-ready structure.

- `ChartArtifact`
- `TableArtifact`
- `KpiArtifact`
  - Specialized renderers for each artifact kind.

## Empty States

Canvas-level empty state:
- shown when `artifacts.length === 0`
- message prompts user to ask Copilot/open trend views

Renderer-level empty states:
- chart: `No chart data available.`
- table: `No rows returned for this artifact.`

## Data Contract Examples

### Chart artifact example

```json
{
  "id": "artifact_1",
  "kind": "chart",
  "title": "Uploaded Trend",
  "confidence": 0.92,
  "dataset_id": "dataset_trend",
  "spec": {
    "chartType": "line",
    "xField": "Date",
    "yFields": ["uploaded_count", "forecast_uploaded_count"],
    "maxRows": 30
  }
}
```

### Dataset example

```json
{
  "id": "dataset_trend",
  "schema": [
    { "key": "Date", "label": "Date" },
    { "key": "uploaded_count", "label": "Uploaded" }
  ],
  "rows": [
    { "Date": "2026-03-01", "uploaded_count": 120 },
    { "Date": "2026-03-02", "uploaded_count": 133 }
  ]
}
```

## Extension Guidance

When adding a new artifact kind:

1. Add icon mapping in `ArtifactCanvas` header section.
2. Add kind-specific renderer branch in artifact body.
3. Define/validate required `artifact.spec` fields.
4. Add empty/error fallback to avoid hard crashes on partial payloads.
5. Keep data shaping pure and colocated (similar to `chartDataFromArtifact`).

When extending chart behavior:
- Keep dataset row slicing in one place.
- Preserve forecast visual differentiation for AI-predicted series.
- Ensure pie mode always uses exactly one Y field.

## Dependencies

- React (`useMemo`)
- `react-chartjs-2`
- `lucide-react`

## Where It Is Used

This component is used by conversational analytics surfaces to display assistant-produced artifacts and datasets (for example, the talk module artifact side panel).
