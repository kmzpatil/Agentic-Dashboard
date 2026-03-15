import React, { useMemo } from 'react';
import { Bar, Line, Pie } from 'react-chartjs-2';
import { BarChart3, Table2, LayoutGrid } from 'lucide-react';

const SERIES_COLORS = ['#ef4444', '#38bdf8', '#f59e0b', '#34d399'];

function buildDatasetMap(datasets) {
  return Object.fromEntries((datasets || []).map((dataset) => [dataset.id, dataset]));
}

function chartDataFromArtifact(artifact, dataset) {
  if (!artifact || !dataset) return null;
  const rows = (dataset.rows || []).slice(0, artifact.spec?.maxRows || 24);
  const xField = artifact.spec?.xField;
  const yFields = artifact.spec?.yFields || [];
  const labels = rows.map((row) => String(row?.[xField] ?? ''));

  if (artifact.spec?.chartType === 'pie') {
    const yField = yFields[0];
    return {
      labels,
      datasets: [
        {
          label: yField,
          data: rows.map((row) => Number(row?.[yField] || 0)),
          backgroundColor: labels.map((_, index) => SERIES_COLORS[index % SERIES_COLORS.length]),
          borderColor: '#050505',
          borderWidth: 1,
        },
      ],
    };
  }

  return {
    labels,
    datasets: yFields.map((field, index) => ({
      label: field.replace(/_/g, ' '),
      data: rows.map((row) => Number(row?.[field] || 0)),
      backgroundColor: `${SERIES_COLORS[index % SERIES_COLORS.length]}55`,
      borderColor: SERIES_COLORS[index % SERIES_COLORS.length],
      tension: 0.28,
      borderWidth: 2,
      fill: artifact.spec?.chartType === 'line',
    })),
  };
}

function ChartArtifact({ artifact, dataset }) {
  const data = useMemo(() => chartDataFromArtifact(artifact, dataset), [artifact, dataset]);

  if (!data) {
    return <div className="text-sm text-neutral-500">No chart data available.</div>;
  }

  const ChartComponent = artifact.spec?.chartType === 'pie'
    ? Pie
    : artifact.spec?.chartType === 'line'
      ? Line
      : Bar;

  return (
    <div className="h-[320px]">
      <ChartComponent
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#d4d4d8' },
            },
          },
          scales: artifact.spec?.chartType === 'pie'
            ? {}
            : {
              x: { ticks: { color: '#737373' }, grid: { color: 'rgba(255,255,255,0.04)' } },
              y: { ticks: { color: '#737373' }, grid: { color: 'rgba(255,255,255,0.04)' } },
            },
        }}
      />
    </div>
  );
}

function TableArtifact({ dataset, pageSize = 12 }) {
  const rows = dataset?.rows || [];
  const columns = dataset?.schema || [];

  if (!rows.length) {
    return <div className="text-sm text-neutral-500">No rows returned for this artifact.</div>;
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-neutral-800">
      <table className="min-w-full text-sm">
        <thead className="bg-[#121212]">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, pageSize).map((row, rowIndex) => (
            <tr key={`${dataset.id}-${rowIndex}`} className="border-t border-neutral-900">
              {columns.map((column) => (
                <td key={`${rowIndex}-${column.key}`} className="px-4 py-3 text-neutral-300 whitespace-nowrap">
                  {String(row?.[column.key] ?? '-')}
                </td>
              ))}
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

export default function ArtifactCanvas({ artifacts = [], datasets = [] }) {
  const datasetMap = useMemo(() => buildDatasetMap(datasets), [datasets]);

  if (!artifacts.length) {
    return (
      <div className="rounded-3xl border border-dashed border-neutral-800 bg-[#0B0B0B] p-6 text-sm text-neutral-500">
        No artifacts yet. Ask Copilot a question or open a trend view to populate this canvas.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {artifacts.map((artifact) => {
        const dataset = artifact.dataset_id ? datasetMap[artifact.dataset_id] : null;
        const icon = artifact.kind === 'table'
          ? <Table2 size={15} />
          : artifact.kind === 'kpi-grid'
            ? <LayoutGrid size={15} />
            : <BarChart3 size={15} />;

        return (
          <section key={artifact.id} className="rounded-3xl border border-neutral-800 bg-[#101010] overflow-hidden">
            <div className="flex items-center justify-between gap-3 border-b border-neutral-900 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-red-500/10 text-red-400">
                  {icon}
                </div>
                <div>
                  <div className="text-sm font-bold tracking-tight text-white">{artifact.title}</div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-500">
                    {artifact.kind} · {Math.round((artifact.confidence || 0) * 100)}% confidence
                  </div>
                </div>
              </div>
            </div>
            <div className="p-5">
              {artifact.kind === 'chart' && <ChartArtifact artifact={artifact} dataset={dataset} />}
              {artifact.kind === 'table' && <TableArtifact dataset={dataset} pageSize={artifact.spec?.pageSize || 12} />}
              {artifact.kind === 'kpi-grid' && <KpiArtifact artifact={artifact} />}
            </div>
          </section>
        );
      })}
    </div>
  );
}
