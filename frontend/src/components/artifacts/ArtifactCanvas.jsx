import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Bar, Line, Pie, Doughnut, Scatter, Bubble, Radar, PolarArea } from 'react-chartjs-2';
import { Chart as ChartJS } from 'chart.js';
import { BoxPlotChart, ViolinChart } from '@sgratzl/chartjs-chart-boxplot';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import {
  BarChart3, Check, ChevronDown, Copy, Download, LineChart, PieChart, X,
  ScatterChart, Activity, Grid3x3, Target, TrendingUp, Layers,
  RotateCcw,
} from 'lucide-react';

// ── Colors ──────────────────────────────────────────────────────────────────
const SERIES_COLORS = [
  '#ef4444', '#38bdf8', '#f59e0b', '#34d399',
  '#a78bfa', '#fb923c', '#2dd4bf', '#f472b6',
  '#818cf8', '#fbbf24', '#4ade80', '#e879f9',
];
const PAGE_SIZE = 20;

// ── Chart component map ─────────────────────────────────────────────────────
const CHART_COMPONENTS = {
  bar: Bar, 'stacked-bar': Bar, 'horizontal-bar': Bar,
  line: Line, area: Line,
  pie: Pie, doughnut: Doughnut, 'polar-area': PolarArea,
  scatter: Scatter, bubble: Bubble,
  radar: Radar,
  box: BoxPlotChart, violin: ViolinChart,
};

// ── Chart type metadata ─────────────────────────────────────────────────────
const CHART_TYPE_META = {
  bar:              { label: 'Bar',         icon: BarChart3,    group: 'Comparison' },
  'stacked-bar':    { label: 'Stacked',     icon: Layers,       group: 'Comparison' },
  'horizontal-bar': { label: 'Horizontal',  icon: BarChart3,    group: 'Comparison' },
  line:             { label: 'Line',        icon: LineChart,    group: 'Trend' },
  area:             { label: 'Area',        icon: TrendingUp,   group: 'Trend' },
  pie:              { label: 'Pie',         icon: PieChart,     group: 'Proportion' },
  doughnut:         { label: 'Doughnut',    icon: PieChart,     group: 'Proportion' },
  'polar-area':     { label: 'Polar',       icon: Target,       group: 'Proportion' },
  scatter:          { label: 'Scatter',     icon: ScatterChart, group: 'Correlation' },
  bubble:           { label: 'Bubble',      icon: ScatterChart, group: 'Correlation' },
  radar:            { label: 'Radar',       icon: Activity,     group: 'Profile' },
  box:              { label: 'Box Plot',    icon: BarChart3,    group: 'Distribution' },
  violin:           { label: 'Violin',      icon: BarChart3,    group: 'Distribution' },
  heatmap:          { label: 'Heatmap',     icon: Grid3x3,      group: 'Advanced' },
  treemap:          { label: 'Treemap',     icon: Grid3x3,      group: 'Advanced' },
};

// ── SQL keywords for syntax highlighting ────────────────────────────────────
const SQL_KEYWORDS = new Set([
  'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL', 'LIKE', 'ILIKE',
  'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS', 'ON', 'AS',
  'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT', 'COUNT', 'SUM',
  'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
  'WITH', 'UNION', 'ALL', 'EXCEPT', 'INTERSECT', 'BETWEEN', 'EXISTS', 'OVER',
  'PARTITION', 'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'CAST', 'DATE', 'TIMESTAMP',
]);

function buildDatasetMap(datasets) {
  return Object.fromEntries((datasets || []).map(d => [d.id, d]));
}

// ── Smart chart type availability ───────────────────────────────────────────
function getAvailableTypes(dataset) {
  const cols = dataset?.schema || [];
  const rows = dataset?.rows || [];
  const numericCols = cols.filter(c => c.type === 'number').map(c => c.key);
  const dateishCols = cols.filter(c => {
    const k = c.key.toLowerCase();
    return c.type === 'date' || ['date', 'month', 'week', 'period', 'day'].some(t => k.includes(t));
  }).map(c => c.key);
  const dimCols = cols.filter(c => c.type !== 'number').map(c => c.key);

  const types = ['bar'];
  if (numericCols.length >= 2) types.push('stacked-bar');
  types.push('horizontal-bar');
  if (dateishCols.length > 0) types.push('line', 'area');
  else if (numericCols.length >= 1) types.push('line');
  if (rows.length <= 10 && numericCols.length >= 1) types.push('pie', 'doughnut', 'polar-area');
  if (numericCols.length >= 2) types.push('scatter');
  if (numericCols.length >= 3) types.push('bubble');
  if (numericCols.length >= 3 && rows.length <= 12) types.push('radar');
  // Box/violin: check for quartile-like columns
  const hasQuartiles = ['q1', 'median', 'q3'].every(q => numericCols.some(c => c.toLowerCase().includes(q)));
  if (hasQuartiles) types.push('box', 'violin');
  // Heatmap: need 2 dims + 1 numeric
  if (dimCols.length >= 2 && numericCols.length >= 1) types.push('heatmap');
  // Treemap: need 1 dim + 1 numeric
  if (dimCols.length >= 1 && numericCols.length >= 1) types.push('treemap');
  return types;
}

// ── Build chart data ────────────────────────────────────────────────────────
function buildChartData(chartType, artifact, dataset) {
  if (!artifact || !dataset) return null;
  const spec = artifact.spec || {};
  const rows = (dataset.rows || []).slice(0, spec.maxRows || 50);
  const xField = spec.xField;
  const yFields = spec.yFields || [];
  const labels = rows.map(row => String(row?.[xField] ?? ''));
  const sizeField = spec.sizeField;
  const groupField = spec.groupField;

  // Proportion charts
  if (['pie', 'doughnut', 'polar-area'].includes(chartType)) {
    const yField = yFields[0];
    return {
      labels,
      datasets: [{
        label: yField,
        data: rows.map(row => Number(row?.[yField] || 0)),
        backgroundColor: labels.map((_, i) => SERIES_COLORS[i % SERIES_COLORS.length]),
        borderColor: '#0a0a0a',
        borderWidth: 2,
        hoverBorderColor: '#fff',
        hoverBorderWidth: 2,
      }],
    };
  }

  // Scatter
  if (chartType === 'scatter') {
    const yField = yFields[0];
    if (groupField) {
      const groups = [...new Set(rows.map(r => String(r[groupField] || 'Other')))];
      return {
        datasets: groups.map((group, i) => ({
          label: group,
          data: rows.filter(r => String(r[groupField]) === group).map(r => ({
            x: Number(r[xField] || 0),
            y: Number(r[yField] || 0),
          })),
          backgroundColor: `${SERIES_COLORS[i % SERIES_COLORS.length]}88`,
          borderColor: SERIES_COLORS[i % SERIES_COLORS.length],
          borderWidth: 1.5,
          pointRadius: 5,
          pointHoverRadius: 8,
        })),
      };
    }
    return {
      datasets: [{
        label: `${xField} vs ${yField}`,
        data: rows.map(r => ({ x: Number(r[xField] || 0), y: Number(r[yField] || 0) })),
        backgroundColor: `${SERIES_COLORS[0]}88`,
        borderColor: SERIES_COLORS[0],
        borderWidth: 1.5,
        pointRadius: 5,
        pointHoverRadius: 8,
      }],
    };
  }

  // Bubble
  if (chartType === 'bubble') {
    const yField = yFields[0];
    const sizeValues = rows.map(r => Number(r[sizeField] || 1));
    const maxSize = Math.max(...sizeValues, 1);
    return {
      datasets: [{
        label: `${xField} vs ${yField}`,
        data: rows.map(r => ({
          x: Number(r[xField] || 0),
          y: Number(r[yField] || 0),
          r: Math.max(3, (Number(r[sizeField] || 1) / maxSize) * 20),
        })),
        backgroundColor: `${SERIES_COLORS[0]}66`,
        borderColor: SERIES_COLORS[0],
        borderWidth: 1.5,
        hoverBorderWidth: 2,
      }],
    };
  }

  // Radar
  if (chartType === 'radar') {
    // Labels are the metric names (yFields), each row is an entity
    return {
      labels: yFields.map(f => f.replace(/_/g, ' ')),
      datasets: rows.map((row, i) => ({
        label: String(row[xField] || `Entity ${i + 1}`),
        data: yFields.map(f => Number(row[f] || 0)),
        backgroundColor: `${SERIES_COLORS[i % SERIES_COLORS.length]}22`,
        borderColor: SERIES_COLORS[i % SERIES_COLORS.length],
        borderWidth: 2,
        pointBackgroundColor: SERIES_COLORS[i % SERIES_COLORS.length],
        pointRadius: 4,
        pointHoverRadius: 6,
      })),
    };
  }

  // Box plot / Violin
  if (['box', 'violin'].includes(chartType)) {
    const numCols = (dataset.schema || []).filter(c => c.type === 'number').map(c => c.key);
    const minCol = numCols.find(c => c.toLowerCase().includes('min')) || numCols[0];
    const q1Col = numCols.find(c => c.toLowerCase().includes('q1'));
    const medCol = numCols.find(c => c.toLowerCase().includes('median'));
    const q3Col = numCols.find(c => c.toLowerCase().includes('q3'));
    const maxCol = numCols.find(c => c.toLowerCase().includes('max')) || numCols[numCols.length - 1];

    if (!q1Col || !medCol || !q3Col) return null;

    return {
      labels,
      datasets: [{
        label: 'Distribution',
        data: rows.map(r => ({
          min: Number(r[minCol] || 0),
          q1: Number(r[q1Col] || 0),
          median: Number(r[medCol] || 0),
          q3: Number(r[q3Col] || 0),
          max: Number(r[maxCol] || 0),
        })),
        backgroundColor: `${SERIES_COLORS[0]}44`,
        borderColor: SERIES_COLORS[0],
        borderWidth: 2,
        outlierColor: '#ef4444',
        medianColor: '#fafafa',
      }],
    };
  }

  // Heatmap
  if (chartType === 'heatmap') {
    const dimCols = (dataset.schema || []).filter(c => c.type !== 'number').map(c => c.key);
    const numCols = (dataset.schema || []).filter(c => c.type === 'number').map(c => c.key);
    const xDim = dimCols[0] || xField;
    const yDim = dimCols[1] || dimCols[0];
    const valField = numCols[0];
    const values = rows.map(r => Number(r[valField] || 0));
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    const range = maxV - minV || 1;

    return {
      datasets: [{
        label: valField,
        data: rows.map(r => ({
          x: String(r[xDim] || ''),
          y: String(r[yDim] || ''),
          v: Number(r[valField] || 0),
        })),
        backgroundColor: (ctx) => {
          const v = ctx.raw?.v ?? 0;
          const norm = (v - minV) / range;
          const hue = Math.round((1 - norm) * 240); // Blue (cold) to Red (hot)
          return `hsl(${hue}, 80%, 45%)`;
        },
        borderColor: '#0a0a0a',
        borderWidth: 2,
        width: ({ chart }) => (chart.chartArea?.width || 300) / (new Set(rows.map(r => r[xDim])).size || 1) - 2,
        height: ({ chart }) => (chart.chartArea?.height || 200) / (new Set(rows.map(r => r[yDim])).size || 1) - 2,
      }],
    };
  }

  // Treemap
  if (chartType === 'treemap') {
    const dimCols = (dataset.schema || []).filter(c => c.type !== 'number').map(c => c.key);
    const numCols = (dataset.schema || []).filter(c => c.type === 'number').map(c => c.key);
    const labelField = dimCols[0] || xField;
    const valField = numCols[0];
    const groupKey = dimCols[1];

    return {
      datasets: [{
        tree: rows.map(r => ({
          label: String(r[labelField] || ''),
          value: Number(r[valField] || 0),
          group: groupKey ? String(r[groupKey] || '') : undefined,
        })),
        key: 'value',
        groups: groupKey ? ['group', 'label'] : ['label'],
        backgroundColor: (ctx) => {
          const i = ctx.dataIndex || 0;
          return `${SERIES_COLORS[i % SERIES_COLORS.length]}cc`;
        },
        borderColor: '#0a0a0a',
        borderWidth: 2,
        spacing: 1,
        labels: {
          display: true,
          color: '#fafafa',
          font: { size: 11, weight: '600' },
          formatter: (ctx) => ctx.raw?._data?.label || '',
        },
      }],
    };
  }

  // Default: bar, stacked-bar, horizontal-bar, line, area
  return {
    labels,
    datasets: yFields.map((field, i) => {
      const isForecast = field.startsWith('forecast_');
      const baseColor = isForecast ? '#3b82f6' : SERIES_COLORS[i % SERIES_COLORS.length];
      const isArea = chartType === 'area';
      const isStacked = chartType === 'stacked-bar';
      return {
        label: isForecast ? 'AI Forecast' : field.replace(/_/g, ' '),
        data: rows.map(row => Number(row?.[field] || 0)),
        backgroundColor: isArea ? `${baseColor}33` : `${baseColor}88`,
        borderColor: baseColor,
        tension: ['line', 'area'].includes(chartType) ? 0.35 : 0,
        borderWidth: 2,
        fill: isArea ? 'origin' : false,
        borderDash: isForecast ? [5, 5] : [],
        pointRadius: ['line', 'area'].includes(chartType) ? 3 : 0,
        pointHoverRadius: ['line', 'area'].includes(chartType) ? 6 : 0,
        pointBackgroundColor: baseColor,
        ...(isStacked ? { stack: 'stack0' } : {}),
      };
    }),
  };
}

// ── Build chart options ─────────────────────────────────────────────────────
function buildChartOptions(chartType) {
  const darkGrid = 'rgba(255,255,255,0.04)';
  const tickColor = '#737373';

  // Shared tooltip style
  const tooltipConfig = {
    enabled: true,
    backgroundColor: 'rgba(9, 9, 11, 0.96)',
    borderColor: 'rgba(63, 63, 70, 0.5)',
    borderWidth: 1,
    titleColor: '#fafafa',
    titleFont: { size: 13, weight: '700' },
    bodyColor: '#d4d4d8',
    bodyFont: { size: 12 },
    padding: { top: 10, bottom: 10, left: 14, right: 14 },
    cornerRadius: 10,
    displayColors: true,
    boxWidth: 8,
    boxHeight: 8,
    boxPadding: 6,
    usePointStyle: true,
    callbacks: {
      label: (ctx) => {
        const val = ctx.parsed?.y ?? ctx.parsed ?? ctx.raw?.v ?? ctx.raw?.value ?? 0;
        const formatted = typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : val;
        return ` ${ctx.dataset.label || ''}: ${formatted}`;
      },
    },
  };

  // Shared legend
  const legendConfig = {
    labels: {
      color: '#d4d4d8',
      usePointStyle: true,
      pointStyle: 'circle',
      padding: 16,
      font: { size: 11, weight: '600' },
    },
  };

  // Shared scales for cartesian charts
  const cartesianScales = {
    x: { ticks: { color: tickColor, font: { size: 10 } }, grid: { color: darkGrid }, border: { color: darkGrid } },
    y: { ticks: { color: tickColor, font: { size: 10 } }, grid: { color: darkGrid }, border: { color: darkGrid } },
  };

  // Zoom config
  const zoomConfig = {
    pan: { enabled: true, mode: 'x', modifierKey: null },
    zoom: {
      wheel: { enabled: true, speed: 0.05 },
      pinch: { enabled: true },
      mode: 'x',
    },
  };

  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 600, easing: 'easeOutQuart' },
    interaction: { mode: 'nearest', intersect: false },
    plugins: { legend: legendConfig, tooltip: tooltipConfig, zoom: zoomConfig, datalabels: { display: false } },
    scales: cartesianScales,
  };

  // Per-type overrides
  switch (chartType) {
    case 'stacked-bar':
      return {
        ...base,
        scales: {
          x: { ...cartesianScales.x, stacked: true },
          y: { ...cartesianScales.y, stacked: true },
        },
      };

    case 'horizontal-bar':
      return { ...base, indexAxis: 'y' };

    case 'area':
      return {
        ...base,
        scales: {
          x: cartesianScales.x,
          y: { ...cartesianScales.y, stacked: true },
        },
      };

    case 'pie':
    case 'doughnut':
    case 'polar-area':
      return {
        ...base,
        scales: {},
        plugins: {
          ...base.plugins,
          zoom: { zoom: { wheel: { enabled: false } }, pan: { enabled: false } },
          datalabels: {
            display: true,
            color: '#fff',
            font: { weight: 'bold', size: 11 },
            formatter: (value, ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((value / total) * 100).toFixed(1);
              return Number(pct) > 4 ? `${pct}%` : '';
            },
          },
        },
      };

    case 'scatter':
      return {
        ...base,
        plugins: {
          ...base.plugins,
          zoom: { ...zoomConfig, zoom: { ...zoomConfig.zoom, mode: 'xy' } },
          tooltip: {
            ...tooltipConfig,
            callbacks: {
              label: (ctx) => {
                const x = ctx.raw?.x?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '';
                const y = ctx.raw?.y?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '';
                return ` ${ctx.dataset.label}: (${x}, ${y})`;
              },
            },
          },
        },
      };

    case 'bubble':
      return {
        ...base,
        plugins: {
          ...base.plugins,
          zoom: { ...zoomConfig, zoom: { ...zoomConfig.zoom, mode: 'xy' } },
          tooltip: {
            ...tooltipConfig,
            callbacks: {
              label: (ctx) => {
                const x = ctx.raw?.x?.toLocaleString() ?? '';
                const y = ctx.raw?.y?.toLocaleString() ?? '';
                const r = ctx.raw?.r?.toFixed(1) ?? '';
                return ` ${ctx.dataset.label}: (${x}, ${y}) size: ${r}`;
              },
            },
          },
        },
      };

    case 'radar':
      return {
        ...base,
        scales: {
          r: {
            suggestedMin: 0,
            grid: { color: darkGrid },
            angleLines: { color: darkGrid },
            pointLabels: { color: '#a1a1aa', font: { size: 11, weight: '500' } },
            ticks: { color: tickColor, backdropColor: 'transparent', font: { size: 9 } },
          },
        },
        plugins: {
          ...base.plugins,
          zoom: { zoom: { wheel: { enabled: false } }, pan: { enabled: false } },
        },
      };

    case 'box':
    case 'violin':
      return {
        ...base,
        plugins: {
          ...base.plugins,
          zoom: { zoom: { wheel: { enabled: false } }, pan: { enabled: false } },
          tooltip: {
            ...tooltipConfig,
            callbacks: {
              label: (ctx) => {
                const d = ctx.raw || {};
                return [
                  ` Max: ${Number(d.max).toLocaleString()}`,
                  ` Q3: ${Number(d.q3).toLocaleString()}`,
                  ` Median: ${Number(d.median).toLocaleString()}`,
                  ` Q1: ${Number(d.q1).toLocaleString()}`,
                  ` Min: ${Number(d.min).toLocaleString()}`,
                ];
              },
            },
          },
        },
      };

    case 'heatmap':
      return {
        ...base,
        scales: {
          x: { type: 'category', ticks: { color: tickColor, font: { size: 10 } }, grid: { display: false } },
          y: { type: 'category', ticks: { color: tickColor, font: { size: 10 } }, grid: { display: false } },
        },
        plugins: {
          ...base.plugins,
          legend: { display: false },
          zoom: { zoom: { wheel: { enabled: false } }, pan: { enabled: false } },
          tooltip: {
            ...tooltipConfig,
            callbacks: {
              title: () => '',
              label: (ctx) => ` ${ctx.raw.x} x ${ctx.raw.y}: ${Number(ctx.raw.v).toLocaleString()}`,
            },
          },
        },
      };

    case 'treemap':
      return {
        ...base,
        scales: {},
        plugins: {
          ...base.plugins,
          legend: { display: false },
          zoom: { zoom: { wheel: { enabled: false } }, pan: { enabled: false } },
          tooltip: {
            ...tooltipConfig,
            callbacks: {
              title: () => '',
              label: (ctx) => {
                const raw = ctx.raw?._data || {};
                return ` ${raw.label || ''}: ${Number(raw.value || 0).toLocaleString()}`;
              },
            },
          },
        },
      };

    default: // bar, line
      return base;
  }
}

// ── Chart Type Selector ─────────────────────────────────────────────────────
function ChartTypeSelector({ current, available, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const currentMeta = CHART_TYPE_META[current] || CHART_TYPE_META.bar;
  const CurrentIcon = currentMeta.icon;

  // Group available types
  const groups = {};
  available.forEach(t => {
    const meta = CHART_TYPE_META[t];
    if (!meta) return;
    if (!groups[meta.group]) groups[meta.group] = [];
    groups[meta.group].push({ type: t, ...meta });
  });

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 rounded-xl bg-[#0A0A0A] border border-neutral-800 px-3 py-2 text-[12px] font-semibold text-neutral-300 transition-colors hover:bg-[#111] hover:border-neutral-700"
      >
        <CurrentIcon size={13} />
        {currentMeta.label}
        <ChevronDown size={11} className={`text-neutral-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 z-50 w-[220px] rounded-xl border border-neutral-800 bg-[#0D0D0D] shadow-2xl overflow-hidden">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <div className="px-3 pt-2.5 pb-1 text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                {group}
              </div>
              {items.map(({ type, label, icon: Icon }) => (
                <button
                  key={type}
                  onClick={() => { onChange(type); setOpen(false); }}
                  className={`flex w-full items-center gap-2.5 px-3 py-2 text-[12px] transition-colors ${
                    type === current
                      ? 'bg-[#1A1A1A] text-white font-semibold'
                      : 'text-neutral-400 hover:bg-[#111] hover:text-neutral-200'
                  }`}
                >
                  <Icon size={12} className="shrink-0" />
                  {label}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Chart Summary Strip ─────────────────────────────────────────────────────
function ChartSummaryStrip({ dataset }) {
  const stats = useMemo(() => {
    const rows = dataset?.rows || [];
    const numCols = (dataset?.schema || []).filter(c => c.type === 'number').map(c => c.key);
    if (!rows.length || !numCols.length) return null;
    const col = numCols[0];
    const values = rows.map(r => Number(r[col] || 0)).filter(v => !isNaN(v));
    if (!values.length) return null;
    return {
      count: rows.length,
      max: Math.max(...values),
      min: Math.min(...values),
      avg: values.reduce((a, b) => a + b, 0) / values.length,
      col,
    };
  }, [dataset]);

  if (!stats) return null;

  const fmt = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 1 });

  return (
    <div className="flex items-center gap-4 px-1 py-1.5 text-[11px] text-neutral-600 shrink-0">
      <span>{stats.count} data points</span>
      <span className="text-neutral-800">·</span>
      <span>Max: <span className="text-neutral-400">{fmt(stats.max)}</span></span>
      <span className="text-neutral-800">·</span>
      <span>Min: <span className="text-neutral-400">{fmt(stats.min)}</span></span>
      <span className="text-neutral-800">·</span>
      <span>Avg: <span className="text-neutral-400">{fmt(stats.avg)}</span></span>
    </div>
  );
}

// ── Chart Error Boundary ─────────────────────────────────────────────────────
class ChartErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error('[ChartErrorBoundary]', error, info?.componentStack);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-neutral-500">
          <span className="text-sm">Chart rendering failed. Try a different chart type.</span>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex items-center gap-1.5 rounded-lg bg-[#1A1A1A] border border-neutral-800 px-3 py-1.5 text-[12px] font-semibold text-neutral-400 hover:bg-[#222] hover:text-neutral-200"
          >
            <RotateCcw size={11} /> Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Canvas Chart (for heatmap/treemap) ──────────────────────────────────────
function CanvasChart({ type, data, options }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    if (chartRef.current) chartRef.current.destroy();
    if (!canvasRef.current) return;
    try {
      chartRef.current = new ChartJS(canvasRef.current, { type, data, options });
    } catch (e) {
      console.error('[CanvasChart]', e);
      setError(e);
    }
    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, [type, data, options]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-neutral-500">
        Chart rendering failed. Try a different chart type.
      </div>
    );
  }

  return <canvas ref={canvasRef} />;
}

// ── Visualize Tab ───────────────────────────────────────────────────────────
function VisualizeTab({ artifact, dataset }) {
  const chartRef = useRef(null);
  const defaultType = artifact?.spec?.chartType || 'bar';
  const [chartType, setChartType] = useState(defaultType);

  useEffect(() => { setChartType(artifact?.spec?.chartType || 'bar'); }, [artifact?.spec?.chartType]);

  const available = useMemo(() => getAvailableTypes(dataset), [dataset]);
  const data = useMemo(() => buildChartData(chartType, artifact, dataset), [chartType, artifact, dataset]);
  const options = useMemo(() => buildChartOptions(chartType), [chartType]);

  const ChartComponent = CHART_COMPONENTS[chartType];
  const isCanvasChart = ['heatmap', 'treemap'].includes(chartType);
  const needsDatalabels = ['pie', 'doughnut', 'polar-area'].includes(chartType);
  const plugins = needsDatalabels ? [ChartDataLabels] : [];

  const handleResetZoom = () => chartRef.current?.resetZoom?.();

  if (!data) return (
    <div className="flex-1 flex items-center justify-center text-sm text-neutral-500">
      No chart data available.
    </div>
  );

  return (
    <div className="flex flex-col h-full gap-2 p-5">
      <div className="flex items-center justify-between shrink-0">
        <ChartTypeSelector current={chartType} available={available} onChange={setChartType} />
        <button
          onClick={handleResetZoom}
          className="flex items-center gap-1.5 rounded-lg bg-[#0A0A0A] border border-neutral-800 px-2.5 py-1.5 text-[11px] font-semibold text-neutral-500 transition-colors hover:bg-[#111] hover:text-neutral-300 hover:border-neutral-700"
        >
          <RotateCcw size={11} />
          Reset Zoom
        </button>
      </div>

      <div className="flex-1 min-h-0 relative" style={{ minHeight: 300 }}>
        <ChartErrorBoundary key={chartType}>
          {isCanvasChart ? (
            <CanvasChart type={chartType === 'heatmap' ? 'matrix' : chartType} data={data} options={options} />
          ) : ChartComponent ? (
            <ChartComponent ref={chartRef} data={data} options={options} plugins={plugins} />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-neutral-500">
              Unsupported chart type: {chartType}
            </div>
          )}
        </ChartErrorBoundary>
      </div>

      <ChartSummaryStrip dataset={dataset} />
    </div>
  );
}

// ── Data Tab ────────────────────────────────────────────────────────────────
function DataTab({ dataset }) {
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const rows = dataset?.rows || [];
  const columns = dataset?.schema || [];

  const sorted = useMemo(() => {
    if (!sortKey) return rows;
    return [...rows].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageRows = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
    setPage(0);
  };

  const exportCSV = () => {
    const header = columns.map(c => c.label).join(',');
    const body = rows.map(row =>
      columns.map(c => {
        const v = row[c.key] ?? '';
        return typeof v === 'string' && v.includes(',') ? `"${v}"` : v;
      }).join(',')
    ).join('\n');
    const blob = new Blob([`${header}\n${body}`], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dataset?.title || 'data'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!rows.length) return (
    <div className="flex-1 flex items-center justify-center text-sm text-neutral-500">No data available.</div>
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-800/60 shrink-0">
        <span className="text-[12px] text-neutral-500">
          {rows.length} rows{sortKey ? ` · sorted by ${sortKey} ${sortDir}` : ''}
        </span>
        <button
          onClick={exportCSV}
          className="flex items-center gap-1.5 rounded-lg bg-[#1A1A1A] px-3 py-1.5 text-[12px] font-semibold text-neutral-400 transition-colors hover:bg-[#222] hover:text-neutral-200"
        >
          <Download size={12} /> Export CSV
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="sticky top-0 z-10 bg-[#0F0F0F]">
            <tr>
              {columns.map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer select-none px-4 py-3 text-left text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500 hover:text-neutral-300"
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {sortKey === col.key && (
                      <ChevronDown size={11} className={`transition-transform ${sortDir === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, i) => (
              <tr key={i} className="border-t border-neutral-900 hover:bg-[#0D0D0D]">
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-3 text-neutral-300 whitespace-nowrap">
                    {String(row?.[col.key] ?? '-')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-neutral-800/60 px-4 py-2.5 shrink-0">
          <span className="text-[12px] text-neutral-500">Page {page + 1} of {totalPages}</span>
          <div className="flex gap-2">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="rounded-lg bg-[#1A1A1A] px-3 py-1.5 text-[12px] font-semibold text-neutral-400 disabled:opacity-30 hover:bg-[#222] hover:text-neutral-200">Previous</button>
            <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} className="rounded-lg bg-[#1A1A1A] px-3 py-1.5 text-[12px] font-semibold text-neutral-400 disabled:opacity-30 hover:bg-[#222] hover:text-neutral-200">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Query Tab ───────────────────────────────────────────────────────────────
function highlightSQL(sql) {
  const tokenRegex = /'[^']*'|"[^"]*"|--[^\n]*|\b\w+\b|[^\w\s]/g;
  const tokens = [];
  let match;
  let lastIndex = 0;
  while ((match = tokenRegex.exec(sql)) !== null) {
    if (match.index > lastIndex) tokens.push({ type: 'space', text: sql.slice(lastIndex, match.index) });
    const text = match[0];
    if (text.startsWith("'")) tokens.push({ type: 'string', text });
    else if (text.startsWith('"')) tokens.push({ type: 'identifier', text });
    else if (text.startsWith('--')) tokens.push({ type: 'comment', text });
    else if (/^\d+(\.\d+)?$/.test(text)) tokens.push({ type: 'number', text });
    else if (SQL_KEYWORDS.has(text.toUpperCase())) tokens.push({ type: 'keyword', text });
    else tokens.push({ type: 'plain', text });
    lastIndex = match.index + text.length;
  }
  if (lastIndex < sql.length) tokens.push({ type: 'space', text: sql.slice(lastIndex) });
  return tokens;
}

function QueryTab({ sql }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(sql).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
  };

  if (!sql) return (
    <div className="flex-1 flex items-center justify-center text-sm text-neutral-500">No SQL available for this query.</div>
  );

  const tokens = highlightSQL(sql);
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-800/60 shrink-0">
        <span className="text-[12px] text-neutral-500 uppercase tracking-[0.18em] font-bold">Generated SQL</span>
        <button onClick={handleCopy} className="flex items-center gap-1.5 rounded-lg bg-[#1A1A1A] px-3 py-1.5 text-[12px] font-semibold text-neutral-400 transition-colors hover:bg-[#222] hover:text-neutral-200">
          {copied ? <><Check size={12} className="text-emerald-400" /> Copied!</> : <><Copy size={12} /> Copy</>}
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre className="text-[13px] leading-[1.8] font-mono whitespace-pre-wrap">
          {tokens.map((token, i) => {
            if (token.type === 'keyword') return <span key={i} className="text-sky-400 font-semibold">{token.text}</span>;
            if (token.type === 'string') return <span key={i} className="text-amber-300">{token.text}</span>;
            if (token.type === 'number') return <span key={i} className="text-emerald-400">{token.text}</span>;
            if (token.type === 'comment') return <span key={i} className="text-neutral-600 italic">{token.text}</span>;
            if (token.type === 'identifier') return <span key={i} className="text-violet-300">{token.text}</span>;
            return <span key={i} className="text-neutral-300">{token.text}</span>;
          })}
        </pre>
      </div>
    </div>
  );
}

// ── Main ArtifactCanvas ─────────────────────────────────────────────────────
export default function ArtifactCanvas({ artifacts = [], datasets = [], sql = '', onClose }) {
  const datasetMap = useMemo(() => buildDatasetMap(datasets), [datasets]);
  const chartArtifacts = useMemo(() => artifacts.filter(a => a.kind === 'chart'), [artifacts]);
  const tableArtifact = artifacts.find(a => a.kind === 'table');
  const hasCharts = chartArtifacts.length > 0;

  const [activeTab, setActiveTab] = useState(hasCharts ? 'visualize' : 'data');
  const [activeChartIndex, setActiveChartIndex] = useState(0);

  const activeChart = chartArtifacts[activeChartIndex] || chartArtifacts[0] || null;
  const panelTitle = activeChart?.title || tableArtifact?.title || 'Analysis';

  useEffect(() => {
    if (!hasCharts && activeTab === 'visualize') setActiveTab('data');
  }, [hasCharts]);

  useEffect(() => { setActiveChartIndex(0); }, [chartArtifacts.length]);

  const tabs = [
    ...(hasCharts ? [{ id: 'visualize', label: 'Visualize' }] : []),
    { id: 'data', label: 'Data' },
    { id: 'query', label: 'Query' },
  ];

  const chartDataset = activeChart?.dataset_id ? datasetMap[activeChart.dataset_id] : null;
  const tableDataset = tableArtifact?.dataset_id ? datasetMap[tableArtifact.dataset_id] : null;
  const primaryDataset = chartDataset || tableDataset || datasets[0] || null;

  return (
    <div className="flex flex-col h-full bg-[#0B0B0B]">
      <div className="flex items-center justify-between border-b border-neutral-800/50 px-5 py-3.5 shrink-0">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-neutral-600">Data Workbench</div>
          <div className="mt-0.5 text-[13px] font-semibold text-neutral-300 truncate max-w-[260px]">{panelTitle}</div>
        </div>
        {onClose && (
          <button onClick={onClose} className="flex h-7 w-7 items-center justify-center rounded-lg text-neutral-600 transition-colors hover:bg-[#1A1A1A] hover:text-neutral-300">
            <X size={15} />
          </button>
        )}
      </div>

      <div className="flex items-center gap-1 border-b border-neutral-800/50 px-4 shrink-0">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2.5 text-[12px] font-semibold transition-colors border-b-2 -mb-px ${
              activeTab === tab.id ? 'border-red-500 text-white' : 'border-transparent text-neutral-500 hover:text-neutral-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'visualize' && activeChart && (
          <div className="flex flex-col h-full">
            {chartArtifacts.length > 1 && (
              <div className="flex items-center gap-1.5 px-4 pt-3 pb-1 shrink-0 overflow-x-auto">
                {chartArtifacts.map((chart, i) => (
                  <button
                    key={chart.id}
                    onClick={() => setActiveChartIndex(i)}
                    className={`shrink-0 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition-colors ${
                      i === activeChartIndex ? 'bg-[#1E1E1E] text-white' : 'text-neutral-500 hover:bg-[#151515] hover:text-neutral-300'
                    }`}
                  >
                    {chart.title || `Chart ${i + 1}`}
                  </button>
                ))}
              </div>
            )}
            <div className="flex-1 min-h-0">
              <VisualizeTab artifact={activeChart} dataset={chartDataset} />
            </div>
          </div>
        )}
        {activeTab === 'data' && <DataTab dataset={primaryDataset} />}
        {activeTab === 'query' && <QueryTab sql={sql} />}
      </div>
    </div>
  );
}
