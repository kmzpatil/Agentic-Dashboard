# Charts Components

XML-driven lightweight chart rendering components.

## Main Component

- File: `XmlChartRenderer.jsx`
- Export: default React component `XmlChartRenderer`
- Purpose: render small dashboard-style widgets from XML config plus tabular data, without requiring chart-spec code per view.

## Component Contract

```jsx
<XmlChartRenderer xmlString={xmlString} data={data} />
```

### Props

- `xmlString` (`string`)
  - XML document containing one or more `<widget>` nodes.
- `data` (`Array | Object`)
  - Source rows used by widgets.
  - If array, used directly.
  - If object, component picks the first non-empty array value.

## Supported Widget Types

Widget type is selected via `type` attribute on `<widget>`.

- `kpi`
- `bar-chart`
- `line-chart`
- `pie-chart`

Unknown type fallback:
- defaults to `bar-chart` rendering path.

## XML Attribute Reference

### Common

- `title`: display title in widget header (optional)

### KPI Widget (`type="kpi"`)

- `metric`: field name to display from first data row
- `title`: card label

### Bar Chart Widget (`type="bar-chart"`)

- `x-field`: categorical label field
- `y-fields`: comma-separated numeric fields
- optional `title`

### Line Chart Widget (`type="line-chart"`)

- `x-field`: sequence/time label field
- `y-fields`: comma-separated numeric fields
- optional `title`

### Pie Chart Widget (`type="pie-chart"`)

- `name-field`: category label field
- `value-field`: numeric slice value field
- optional `title`

## XML Example

```xml
<dashboard>
  <widget type="kpi" title="Total Uploaded" metric="uploaded_count" />
  <widget type="bar-chart" title="Uploads by Channel" x-field="channel" y-fields="uploaded_count" />
  <widget type="line-chart" title="Trend" x-field="date" y-fields="uploaded_count,created_count" />
  <widget type="pie-chart" title="Output Mix" name-field="output_type" value-field="published_count" />
</dashboard>
```

## Data Expectations

- Input rows are plain objects where XML attributes map to object keys.
- Numeric chart values are coerced with `Number(...) || 0`.
- Bar/line widgets use up to first 20 rows in bar rendering loop.
- Pie widget uses up to first 8 slices.

## Internal Rendering Behavior

### Parsing

- XML is parsed with browser `DOMParser`.
- Invalid XML (parsererror) results in no widgets rendered.

### Dataset selection

- If `data` is an array: use as-is.
- If `data` is an object: choose first non-empty array value.
- If no usable rows: render empty-state cards per widget.

### Visual behavior by widget

- KPI: centered numeric metric card.
- Bar: custom div-based bars with mini legend for multiple y-fields.
- Line: SVG polyline renderer with per-series color.
- Pie: SVG arc slices with legend and percentages.

## Empty and Fallback States

- No widgets parsed: component returns `null`.
- Widget with missing required fields or no data: `EmptyChart` card.
- Empty chart message defaults to title or generic no-data text.

## Internal Helpers

- `parseXml(xmlString)`
- `getAttr(element, name, fallback)`
- `KpiWidget`
- `BarChartWidget`
- `LineChartWidget`
- `PieChartWidget`
- `EmptyChart`

## Contributor Notes

- Keep XML attribute names stable to avoid breaking backend/generated prompts that emit widget specs.
- If adding a widget type:
  - add dedicated widget component
  - add switch-case branch in `XmlChartRenderer`
  - document required XML attributes in this README
- Validate performance if increasing row/slice caps.
- Preserve graceful fallback behavior for malformed XML or partial data.
