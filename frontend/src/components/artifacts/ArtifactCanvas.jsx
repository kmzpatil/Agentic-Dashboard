import React, { useEffect, useMemo, useState } from 'react';
import { Bar, Line, Pie } from 'react-chartjs-2';
import { BarChart3, TrendingUp, PieChart as PieIcon, Table2, LayoutGrid, ChevronDown } from 'lucide-react';

const SERIES_COLORS = ['#ef4444', '#38bdf8', '#f59e0b', '#34d399', '#a855f7', '#3b82f6', '#ec4899', '#14b8a6'];

const TYPE_META = {
  bar:  { label: 'Bar Chart',  Icon: BarChart3 },
  line: { label: 'Line Chart', Icon: TrendingUp },
  pie:  { label: 'Pie Chart',  Icon: PieIcon },
};

function buildDatasetMap(datasets) {
  return Object.fromEntries((datasets || []).map((ds) => [ds.id, ds]));
}

function buildChartData(rows, xField, yFields, chartType) {
  if (!rows?.length || !xField || !yFields?.length) return null;
  const labels = rows.map((r) => String(r?.[xField] ?? ''));

  if (chartType === 'pie') {
    const yField = yFields[0];
    return {
      labels,
      datasets: [{
        label: yField,
        data: rows.map((r) => Number(r?.[yField] || 0)),
        backgroundColor: labels.map((_, i) => SERIES_COLORS[i % SERIES_COLORS.length]),
        borderColor: '#050505',
        borderWidth: 1,
      }],
    };
  }

  return {
    labels,
    datasets: yFields.map((field, i) => {
      const isForecast = field.startsWith('forecast_');
      const base = isForecast ? '#3b82f6' : SERIES_COLORS[i % SERIES_COLORS.length];
      return {
        label: isForecast ? 'AI Forecast' : field.replace(/_/g, ' '),
        data: rows.map((r) => Number(r?.[field] || 0)),
        backgroundColor: `${base}55`,
        borderColor: base,
        tension: 0.28,
        borderWidth: 2,
        fill: chartType === 'line' && !isForecast,
        borderDash: isForecast ? [5, 5] : [],
      };
    }),
  };
}

function ChartRenderer({ chartType, rows, xField, yFields }) {
  const data = useMemo(() => buildChartData(rows, xField, yFields, chartType), [rows, xField, yFields, chartType]);
  if (!data) return <div className="text-sm text-neutral-500">No chart data available.</div>;
  const Comp = chartType === 'pie' ? Pie : chartType === 'line' ? Line : Bar;
  return (
    <div className="h-[320px]">
      <Comp
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#d4d4d8' } } },
          scales: chartType === 'pie' ? {} : {
            x: { ticks: { color: '#737373' }, grid: { color: 'rgba(255,255,255,0.04)' } },
            y: { ticks: { color: '#737373' }, grid: { color: 'rgba(255,255,255,0.04)' } },
          },
        }}
      />
    </div>
  );
}

function SingleChartCard({ artifact, dataset }) {
  const rows = useMemo(() => (dataset?.rows || []).slice(0, artifact.spec?.maxRows || 24), [dataset, artifact]);
  const chartType = artifact.spec?.chartType || 'bar';
  const meta = TYPE_META[chartType] || TYPE_META.bar;

  return (
    <section className="rounded-3xl border border-neutral-800 bg-[#101010] overflow-hidden">
      <div className="flex items-center gap-3 border-b border-neutral-900 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-red-500/10 text-red-400">
          <meta.Icon size={15} />
        </div>
        <div>
          <div className="text-sm font-bold tracking-tight text-white">{artifact.title}</div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-500">
            {meta.label} · {Math.round((artifact.confidence || 0) * 100)}% confidence
          </div>
        </div>
      </div>
      <div className="p-5">
        <ChartRenderer
          chartType={chartType}
          rows={rows}
          xField={artifact.spec?.xField}
          yFields={artifact.spec?.yFields || []}
        />
      </div>
    </section>
  );
}

function TableArtifact({ dataset, pageSize = 12 }) {
  const rows = dataset?.rows || [];
  const columns = dataset?.schema || [];
  if (!rows.length) return <div className="text-sm text-neutral-500">No rows returned.</div>;
  return (
    <div className="overflow-x-auto rounded-2xl border border-neutral-800">
      <table className="min-w-full text-sm">
        <thead className="bg-[#121212]">
          <tr>{columns.map((c) => <th key={c.key} className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500">{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, pageSize).map((row, ri) => (
            <tr key={ri} className="border-t border-neutral-900">
              {columns.map((c) => <td key={`${ri}-${c.key}`} className="px-4 py-3 text-neutral-300 whitespace-nowrap">{String(row?.[c.key] ?? '-')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KpiArtifact({ artifact }) {
  const items = artifact.spec?.items || [];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-neutral-800 bg-[#0D0D0D] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-500">{item.label}</div>
          <div className="mt-2 text-2xl font-black tracking-tight text-white">{item.value ?? '-'}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Multi-chart section with dropdown ────────────────────────────────────── */

function MultiChartViewer({ charts, datasetMap }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => { setSelectedIdx(0); setOpen(false); }, [charts]);

  const active = charts[selectedIdx] || charts[0];
  if (!active) return null;

  const dataset = active.dataset_id ? datasetMap[active.dataset_id] : null;
  const rows = (dataset?.rows || []).slice(0, active.spec?.maxRows || 24);
  const chartType = active.spec?.chartType || 'bar';
  const meta = TYPE_META[chartType] || TYPE_META.bar;

  return (
    <section className="rounded-3xl border border-neutral-800 bg-[#101010] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-neutral-900 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-red-500/10 text-red-400">
            <meta.Icon size={15} />
          </div>
          <div>
            <div className="text-sm font-bold tracking-tight text-white">{active.title}</div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-500">
              {meta.label} · {Math.round((active.confidence || 0) * 100)}% confidence
            </div>
          </div>
        </div>
        <div className="text-[11px] font-semibold text-neutral-600">
          {selectedIdx + 1} / {charts.length}
        </div>
      </div>

      {/* Dropdown */}
      <div className="relative border-b border-neutral-900/60 px-5 py-2.5">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between rounded-xl bg-[#0A0A0A] border border-neutral-800 px-3 py-2 text-[12px] font-semibold text-neutral-400 transition-colors hover:bg-[#141414] hover:text-neutral-200"
        >
          <div className="flex items-center gap-2 min-w-0">
            <meta.Icon size={12} className="text-red-400 shrink-0" />
            <span className="text-neutral-300 truncate">{active.title}</span>
          </div>
          <div className="flex items-center gap-1.5 shrink-0 ml-2">
            <span className="text-[10px] text-neutral-600">{charts.length} charts</span>
            <ChevronDown size={12} className={`text-neutral-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
          </div>
        </button>

        {open && (
          <div className="absolute left-5 right-5 z-20 mt-1 max-h-[240px] overflow-y-auto rounded-xl border border-neutral-700 bg-[#0C0C0C] py-1 shadow-2xl">
            {charts.map((chart, i) => {
              const ct = chart.spec?.chartType || 'bar';
              const m = TYPE_META[ct] || TYPE_META.bar;
              const isActive = i === selectedIdx;
              return (
                <button
                  key={chart.id}
                  onClick={() => { setSelectedIdx(i); setOpen(false); }}
                  className={`flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-[12px] transition-colors ${
                    isActive ? 'bg-[#1A1A1A] text-white' : 'text-neutral-400 hover:bg-[#141414] hover:text-neutral-200'
                  }`}
                >
                  <m.Icon size={13} className={isActive ? 'text-red-400' : 'text-neutral-600'} />
                  <span className="flex-1 truncate">{chart.title}</span>
                  <span className="shrink-0 rounded bg-neutral-800 px-1.5 py-0.5 text-[9px] font-bold uppercase text-neutral-500">
                    {ct}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="p-5">
        <ChartRenderer
          chartType={chartType}
          rows={rows}
          xField={active.spec?.xField}
          yFields={active.spec?.yFields || []}
        />
      </div>
    </section>
  );
}

/* ── Main ArtifactCanvas ──────────────────────────────────────────────────── */

export default function ArtifactCanvas({ artifacts = [], datasets = [] }) {
  const datasetMap = useMemo(() => buildDatasetMap(datasets), [datasets]);

  const chartArtifacts = useMemo(() => artifacts.filter((a) => a.kind === 'chart'), [artifacts]);
  const nonChartArtifacts = useMemo(() => artifacts.filter((a) => a.kind !== 'chart'), [artifacts]);

  if (!artifacts.length) {
    return (
      <div className="rounded-3xl border border-dashed border-neutral-800 bg-[#0B0B0B] p-6 text-sm text-neutral-500">
        No artifacts yet. Ask Copilot a question or open a trend view to populate this canvas.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Charts: dropdown when multiple, plain card when single */}
      {chartArtifacts.length > 1 ? (
        <MultiChartViewer charts={chartArtifacts} datasetMap={datasetMap} />
      ) : chartArtifacts.length === 1 ? (
        <SingleChartCard
          artifact={chartArtifacts[0]}
          dataset={chartArtifacts[0].dataset_id ? datasetMap[chartArtifacts[0].dataset_id] : null}
        />
      ) : null}

      {/* Non-chart artifacts */}
      {nonChartArtifacts.map((artifact) => {
        const dataset = artifact.dataset_id ? datasetMap[artifact.dataset_id] : null;
        const icon = artifact.kind === 'table' ? <Table2 size={15} /> : <LayoutGrid size={15} />;
        return (
          <section key={artifact.id} className="rounded-3xl border border-neutral-800 bg-[#101010] overflow-hidden">
            <div className="flex items-center gap-3 border-b border-neutral-900 px-5 py-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-red-500/10 text-red-400">{icon}</div>
              <div>
                <div className="text-sm font-bold tracking-tight text-white">{artifact.title}</div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-500">
                  {artifact.kind} · {Math.round((artifact.confidence || 0) * 100)}% confidence
                </div>
              </div>
            </div>
            <div className="p-5">
              {artifact.kind === 'table' && <TableArtifact dataset={dataset} pageSize={artifact.spec?.pageSize || 12} />}
              {artifact.kind === 'kpi-grid' && <KpiArtifact artifact={artifact} />}
            </div>
          </section>
        );
      })}
    </div>
  );
}
