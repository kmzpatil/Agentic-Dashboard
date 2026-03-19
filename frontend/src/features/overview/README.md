# Overview Feature

Primary mission-control dashboard surface for KPI monitoring, insights, alerts, and deep-dive visualizations.

## Files

- OverviewModule.jsx: main page component.
- KpiDetailsModal.jsx: KPI deep-dive modal with metric-specific charts.
- kpiDefinitions.js: KPI catalog, labels, formulas, significance text, and fallback chart structures.

## Main Module

Component: OverviewModule

Props:
- onNavigate: optional callback for cross-surface navigation (used by insights and alerts).

Data loading:
- GET /api/overview
- GET /api/insights?surface=mission-control

Uses shared useApi hook for both endpoints and renders skeleton/error states before dashboard content.

## KPI System

Core KPI cards are always shown:
- uploaded_count
- processed_count
- created_count
- published_count

Additional KPI workflow:
- Selection panel lists available advanced KPIs.
- Users can stage KPIs before promoting them to the dashboard.
- Promoted KPIs appear as removable cards.
- Clicking a KPI opens KpiDetailsModal for deeper analysis.

Definition source:
- kpiDefinitions.js exports KPI_DEFINITIONS with:
  - id/title
  - definition/formula/significance
  - getValue and getSubtitle formatters
  - trendData for cards
  - detailsData fallback structure for modal charts

## KPI Details Modal

Component: KpiDetailsModal

Props:
- kpi: selected KPI object or null.
- onClose: close handler.

Behavior:
- Fetches live KPI detail payload from GET /advanced-kpis/:kpiId using auth token.
- Merges API payload with local detailsData fallback structure.
- If API fails, modal still renders using local fallback data so layout remains usable.

Chart stack:
- Chart.js via react-chartjs-2 (Line, Bar, Pie, Scatter)
- chartjs-chart-matrix for matrix heatmaps
- chartjs-chart-treemap for treemap visuals

Modal rendering is KPI-specific, with chart layouts selected by KPI id.

## Other Sections In OverviewModule

- Output Types Summary
  - Tabbed output-type cards showing uploaded/created/published count and duration.

- Frammer AI Insights
  - Renders insight cards from insights endpoint.

- Top Performers
  - Displays best-performing dimension entities by conversion.

- Alerts
  - Actionable alert cards that navigate into funnel context with pre-filled breakdown filters.

## Formatting and Shared Dependencies

The overview feature uses:
- formatHours, formatNumber, formatPct from shared formatters.
- KpiCard, OverviewSkeleton, and InsightCard shared components.

## Contributor Notes

- Keep KPI_DEFINITIONS as the single source of truth for KPI metadata and fallback modal structure.
- When adding a KPI, update both:
  - kpiDefinitions.js entry
  - KpiDetailsModal switch-case chart renderer
- Preserve staged-to-active KPI flow in OverviewModule to avoid breaking add/remove behavior.
- If advanced KPI API schema changes, update merge logic in KpiDetailsModal first.
