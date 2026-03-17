import React, { useMemo } from 'react';
import { Chart } from 'react-chartjs-2';

const C = {
  red: '#ef4444',
  grid: 'rgba(255,255,255,0.04)',
};

function redGrayPalette(count, alpha = 0.9) {
  if (!count || count <= 0) return [`rgba(239, 68, 68, ${alpha})`];
  if (count === 1) return [`rgba(239, 68, 68, ${alpha})`];

  const start = { r: 239, g: 68, b: 68 };
  const end = { r: 163, g: 163, b: 163 };

  return Array.from({ length: count }, (_, idx) => {
    const t = idx / (count - 1);
    const r = Math.round(start.r + (end.r - start.r) * t);
    const g = Math.round(start.g + (end.g - start.g) * t);
    const b = Math.round(start.b + (end.b - start.b) * t);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  });
}

const Card = ({ children, className = '' }) => (
  <div className={`bg-[#111111] rounded-xl border border-neutral-800 p-5 ${className}`}>{children}</div>
);

const CardTitle = ({ title, desc }) => (
  <div className="mb-4">
    <h3 className="text-[13px] font-semibold text-white">{title}</h3>
    {desc && <p className="mt-1 text-[11px] text-neutral-500 leading-relaxed">{desc}</p>}
  </div>
);

const barOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#a3a3a3', font: { size: 10 } }, grid: { display: false } },
    y: { ticks: { color: '#a3a3a3', font: { size: 10 } }, grid: { color: C.grid } },
  },
};

function heatCellStyle(value, minValue, maxValue) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  if (safe <= 0.0001) {
    return {
      backgroundColor: 'rgb(39, 28, 36)',
      borderColor: 'rgb(66, 45, 58)',
      color: '#f8fafc',
    };
  }

  const range = Math.max(maxValue - minValue, 1e-6);
  const t = Math.max(0, Math.min(1, (safe - minValue) / range));

  const red = { r: 166, g: 35, b: 64 };
  const green = { r: 44, g: 130, b: 88 };
  const baseR = Math.round(red.r + (green.r - red.r) * t);
  const baseG = Math.round(red.g + (green.g - red.g) * t);
  const baseB = Math.round(red.b + (green.b - red.b) * t);
  const bg = { r: 24, g: 24, b: 27 };
  const mix = 0.72;
  const r = Math.round(baseR * mix + bg.r * (1 - mix));
  const g = Math.round(baseG * mix + bg.g * (1 - mix));
  const b = Math.round(baseB * mix + bg.b * (1 - mix));
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  return {
    backgroundColor: `rgb(${r}, ${g}, ${b})`,
    borderColor: `rgb(${Math.max(r - 18, 0)}, ${Math.max(g - 18, 0)}, ${Math.max(b - 18, 0)})`,
    color: luminance > 0.6 ? '#111827' : '#f8fafc',
  };
}

function formatHeatPct(value) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  return `${safe.toFixed(safe >= 1 ? 2 : 2).replace(/\.00$/, '')}%`;
}

export default function ContentAnalysisTab({ authUser, data, breakdown = 'channel', filters }) {
  const isAdmin = authUser?.role === 'website_admin';
  const breakdownRows = data?.breakdown || [];
  const showClientHeatmap = isAdmin && breakdown === 'client';
  const viewLabel = breakdown.replace('_', ' ');
  const heatmapRows = data?.inputTypeClientHeatmap || [];
  const activeFilters = Object.entries(filters || {}).filter(([, v]) => v);
  const heatRange = useMemo(() => {
    const allValues = heatmapRows.flatMap((row) => (
      (row.clients || [])
        .map((cell) => Number(cell.conversion_pct))
        .filter((num) => Number.isFinite(num))
    ));
    const values = allValues.filter((num) => num > 0);
    if (!values.length) return { min: 0, max: 1 };
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [heatmapRows]);

  const outputTypeSurvivalData = useMemo(() => {
    return {
      labels: breakdownRows.map((r) => r.label),
      datasets: [{
        label: 'Conversion %',
        data: breakdownRows.map((r) => Number(r.conversion || 0)),
        backgroundColor: redGrayPalette(breakdownRows.length, 0.9),
        borderRadius: 4,
      }],
    };
  }, [breakdownRows]);

  const publishByClientData = useMemo(() => {
    const rows = data?.publishByClient || [];
    return {
      labels: rows.map((r) => r.client_name),
      datasets: [{
        label: 'Conversion %',
        data: rows.map((r) => Number(r.conversion_pct || 0)),
        backgroundColor: redGrayPalette(rows.length, 0.72),
        borderRadius: 5, barPercentage: 0.58,
      }],
    };
  }, [data?.publishByClient]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center rounded-full border border-neutral-700/80 bg-neutral-900/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          View by: {viewLabel}
        </span>
        {activeFilters.length > 0 && (
          <span className="inline-flex items-center rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-[10px] font-semibold text-violet-300">
            {activeFilters.length} filter{activeFilters.length > 1 ? 's' : ''} active
          </span>
        )}
      </div>

      {/* Input type × client heatmap — client view (admins only) */}
      {showClientHeatmap ? (
        <Card>
          <CardTitle
            title="Input type × client — publish conversion heatmap"
            desc="Extra detail for client view. Metric is published ÷ created."
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] border-separate border-spacing-y-1 text-sm">
              <thead>
                <tr className="text-neutral-500">
                  <th className="sticky left-0 z-20 bg-[#111111] py-2 text-left pr-4 text-[10.5px] font-medium">Input type</th>
                  {(data?.heatmapClients || []).map((client) => (
                    <th key={client} className="py-2 text-center text-[10.5px] font-medium">{client}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapRows.map((row) => (
                  <tr key={row.input_type}>
                    <td className="sticky left-0 z-10 bg-[#111111] py-2 pr-4 text-neutral-200 text-[12px] font-medium max-w-[230px] truncate" title={row.input_type}>
                      {row.input_type}
                    </td>
                    {(row.clients || []).map((cell, i) => {
                      const conversion = Number(cell.conversion_pct);
                      const safeConversion = Number.isFinite(conversion) ? conversion : 0;
                      const cellStyle = heatCellStyle(safeConversion, heatRange.min, heatRange.max);
                      return (
                        <td
                          key={i}
                          className="rounded-md border px-4 py-2 text-center font-semibold text-[11.5px] font-mono min-w-[120px]"
                          style={cellStyle}
                          title={`Created: ${cell.assets_created || 0}, Published: ${cell.posts_published || 0}`}
                        >
                          {formatHeatPct(safeConversion)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center gap-3 text-[10.5px] text-neutral-500">
            <span>Lower conversion</span>
            <div className="h-2 w-28 rounded-full bg-gradient-to-r from-[#7a233f] to-[#2d6f55] border border-neutral-700/70" />
            <span>Higher conversion</span>
          </div>
        </Card>
      ) : (
        <Card>
          <CardTitle
            title={`${breakdown.replace('_', ' ')} — publish conversion`}
            desc="Conversion rate (%) by the current View by categories."
          />
          <div className="h-[220px]">
            <Chart type="bar" data={outputTypeSurvivalData} options={barOptions} />
          </div>
        </Card>
      )}

      {/* Publish by client — admins only */}
      {isAdmin && publishByClientData.labels.length > 0 && (
        <Card>
          <CardTitle
            title="Publish conversion by client"
            desc="Published ÷ created by client for the current filter context."
          />
          <div className="h-[220px]">
            <Chart type="bar" data={publishByClientData} options={{
              ...barOptions,
              scales: {
                ...barOptions.scales,
                y: { ...barOptions.scales.y, ticks: { ...barOptions.scales.y.ticks, callback: (v) => `${v}%` }, title: { display: true, text: 'Conversion rate (%)', color: '#a3a3a3', font: { size: 10 } } },
              },
            }} />
          </div>
        </Card>
      )}
    </div>
  );
}
