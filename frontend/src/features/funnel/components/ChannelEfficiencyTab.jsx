import React, { useMemo } from 'react';
import { Chart } from 'react-chartjs-2';

const C = {
  c1: '#8b5cf6', c2: '#60a5fa', c3: '#34d399', c4: '#f97316',
  red: '#ef4444', amber: '#f59e0b', green: '#22c55e',
  grid: 'rgba(255,255,255,0.04)',
};

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

const CLIENT_COLORS = [C.c1, C.c2, C.c3, C.c4, '#ec4899', '#22c55e', '#f59e0b', '#a3a3a3'];
const HIGH_VOLUME_PERCENTILE = 0.70;
const LOW_YIELD_PERCENTILE = 0.30;
const HIGH_VOLUME_LABEL = `P${Math.round(HIGH_VOLUME_PERCENTILE * 100)}`;
const LOW_YIELD_LABEL = `P${Math.round(LOW_YIELD_PERCENTILE * 100)}`;

const riskQuadrantPlugin = {
  id: 'riskQuadrant',
  beforeDatasetsDraw(chart, _args, pluginOptions) {
    if (!pluginOptions?.enabled) return;
    const { chartArea, scales, ctx } = chart;
    if (!chartArea || !scales?.x || !scales?.y) return;

    const xCutoff = Number(pluginOptions.xCutoff || 0);
    const yCutoff = Number(pluginOptions.yCutoff || 0);
    const xStart = scales.x.getPixelForValue(xCutoff);
    const yStart = scales.y.getPixelForValue(yCutoff);

    const left = Math.max(chartArea.left, Math.min(chartArea.right, xStart));
    const top = Math.max(chartArea.top, Math.min(chartArea.bottom, yStart));
    const width = chartArea.right - left;
    const height = chartArea.bottom - top;

    if (width <= 0 || height <= 0) return;

    const centerX = chartArea.right;
    const centerY = chartArea.bottom;
    const radiusX = Math.max(width * 1.05, 1);
    const radiusY = Math.max(height * 1.05, 1);
    const yScale = radiusY / radiusX;

    ctx.save();
    ctx.beginPath();
    ctx.rect(left, top, width, height);
    ctx.clip();

    ctx.translate(centerX, centerY);
    ctx.scale(1, yScale);
    const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, radiusX);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.34)');
    gradient.addColorStop(0.38, 'rgba(239, 68, 68, 0.20)');
    gradient.addColorStop(0.72, 'rgba(239, 68, 68, 0.09)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, radiusX, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  },
};

function percentile(values = [], p = 0.5) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const position = Math.max(0, Math.min(sorted.length - 1, (sorted.length - 1) * p));
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  const weight = position - lower;
  return sorted[lower] + (sorted[upper] - sorted[lower]) * weight;
}

function pointKey(clientName, channelName) {
  return `${clientName || 'Unknown'}::${channelName || 'Unknown'}`;
}

export default function ChannelEfficiencyTab({ authUser, data, breakdown, filters }) {
  const isAdmin = authUser?.role === 'website_admin';
  const viewLabel = (breakdown || 'channel').replace('_', ' ');
  const activeFilters = Object.entries(filters || {}).filter(([, v]) => v);
  const rows = data?.channelEfficiency || [];
  const teamRows = data?.teamVolumeYield || [];

  const segregation = useMemo(() => {
    if (!rows.length) {
      return { volumeThreshold: 0, yieldThreshold: 0, xMin: 0, xMax: 1, riskKeys: new Set(), riskCount: 0 };
    }

    const volumes = rows.map((row) => Number(row.videos_assigned || 0));
    const yields = rows.map((row) => Number(row.yield_pct || 0));
    const volumeThreshold = percentile(volumes, HIGH_VOLUME_PERCENTILE);
    const yieldThreshold = percentile(yields, LOW_YIELD_PERCENTILE);
    const xMin = Math.max(0, Math.min(...volumes) * 0.92);
    const xMax = Math.max(...volumes) * 1.08;

    const riskKeys = new Set(
      rows
        .filter((row) => Number(row.videos_assigned || 0) >= volumeThreshold && Number(row.yield_pct || 0) <= yieldThreshold)
        .map((row) => pointKey(row.client_name, row.channel_name)),
    );

    return { volumeThreshold, yieldThreshold, xMin, xMax, riskKeys, riskCount: riskKeys.size };
  }, [rows]);

  const clientLegend = useMemo(
    () => Array.from(new Set(rows.map((row) => row.client_name || 'Unknown'))),
    [rows],
  );

  const teamSegregation = useMemo(() => {
    if (!teamRows.length) {
      return { volumeThreshold: 0, yieldThreshold: 0, riskKeys: new Set(), riskCount: 0 };
    }

    const volumes = teamRows.map((row) => Number(row.videos_assigned || 0));
    const yields = teamRows.map((row) => Number(row.yield_pct || 0));
    const volumeThreshold = percentile(volumes, HIGH_VOLUME_PERCENTILE);
    const yieldThreshold = percentile(yields, LOW_YIELD_PERCENTILE);

    const riskKeys = new Set(
      teamRows
        .filter((row) => Number(row.videos_assigned || 0) >= volumeThreshold && Number(row.yield_pct || 0) <= yieldThreshold)
        .map((row) => row.team_name || 'Unknown'),
    );

    return { volumeThreshold, yieldThreshold, riskKeys, riskCount: riskKeys.size };
  }, [teamRows]);

  const channelEfficiencyScatterData = useMemo(() => {
    if (isAdmin) {
      // Colour-code by client
      const grouped = rows.reduce((acc, row) => {
        const client = row.client_name || 'Unknown';
        if (!acc[client]) acc[client] = [];
        acc[client].push({
          x: Number(row.videos_assigned || 0),
          y: Number(row.yield_pct || 0),
          channel_name: row.channel_name,
          client_name: client,
          risk: segregation.riskKeys.has(pointKey(client, row.channel_name)),
        });
        return acc;
      }, {});
      const clientNames = Object.keys(grouped);
      return {
        datasets: [
          ...clientNames.map((client, idx) => ({
            label: client,
            data: grouped[client],
            backgroundColor: CLIENT_COLORS[idx % CLIENT_COLORS.length],
            pointRadius: (ctx) => (ctx.raw?.risk ? 6 : 4),
            pointBorderWidth: (ctx) => (ctx.raw?.risk ? 2 : 0),
            pointBorderColor: (ctx) => (ctx.raw?.risk ? 'rgba(239, 68, 68, 0.96)' : 'transparent'),
            pointHoverRadius: (ctx) => (ctx.raw?.risk ? 7 : 5),
          })),
        ],
      };
    }

    // Non-admin: single colour, no client grouping
    return {
      datasets: [
        {
          label: 'Channels',
          data: rows.map((row) => ({
            x: Number(row.videos_assigned || 0),
            y: Number(row.yield_pct || 0),
            channel_name: row.channel_name,
            client_name: row.client_name || 'Unknown',
            risk: segregation.riskKeys.has(pointKey(row.client_name, row.channel_name)),
          })),
          backgroundColor: C.c2,
          pointRadius: (ctx) => (ctx.raw?.risk ? 6 : 4),
          pointBorderWidth: (ctx) => (ctx.raw?.risk ? 2 : 0),
          pointBorderColor: (ctx) => (ctx.raw?.risk ? 'rgba(239, 68, 68, 0.96)' : 'transparent'),
          pointHoverRadius: (ctx) => (ctx.raw?.risk ? 7 : 5),
        },
      ],
    };
  }, [isAdmin, rows, segregation]);

  const scatterOptions = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: {
        display: isAdmin,
        labels: { color: '#d4d4d4' },
      },
      riskQuadrant: {
        enabled: rows.length > 0,
        xCutoff: segregation.volumeThreshold,
        yCutoff: segregation.yieldThreshold,
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.raw?.channel_name || ''}: ${ctx.raw.x} videos, ${ctx.raw.y}% yield${ctx.raw?.risk ? ' [high volume + low yield]' : ''}`,
        },
      },
    },
    scales: {
      x: { title: { display: true, text: 'Videos assigned', color: '#a3a3a3', font: { size: 10 } }, ticks: { color: '#a3a3a3', font: { size: 10 } }, grid: { color: C.grid } },
      y: {
        min: 0,
        max: 100,
        title: { display: true, text: 'Yield %', color: '#a3a3a3', font: { size: 10 } },
        ticks: { color: '#a3a3a3', font: { size: 10 }, callback: (v) => `${v}%` },
        grid: { color: C.grid },
      },
    },
  };

  const teamScatterData = useMemo(() => ({
    datasets: [
      {
        label: 'Teams',
        data: teamRows.map((row) => ({
          x: Number(row.videos_assigned || 0),
          y: Number(row.yield_pct || 0),
          team_name: row.team_name || 'Unknown',
          risk: teamSegregation.riskKeys.has(row.team_name || 'Unknown'),
        })),
        backgroundColor: C.c3,
        pointRadius: (ctx) => (ctx.raw?.risk ? 6 : 4),
        pointBorderWidth: (ctx) => (ctx.raw?.risk ? 2 : 0),
        pointBorderColor: (ctx) => (ctx.raw?.risk ? 'rgba(239, 68, 68, 0.96)' : 'transparent'),
        pointHoverRadius: (ctx) => (ctx.raw?.risk ? 7 : 5),
      },
    ],
  }), [teamRows, teamSegregation]);

  const teamScatterOptions = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      riskQuadrant: {
        enabled: teamRows.length > 0,
        xCutoff: teamSegregation.volumeThreshold,
        yCutoff: teamSegregation.yieldThreshold,
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.raw?.team_name || ''}: ${ctx.raw.x} videos, ${ctx.raw.y}% yield${ctx.raw?.risk ? ' [high volume + low yield]' : ''}`,
        },
      },
    },
    scales: {
      x: { title: { display: true, text: 'Videos assigned', color: '#a3a3a3', font: { size: 10 } }, ticks: { color: '#a3a3a3', font: { size: 10 } }, grid: { color: C.grid } },
      y: {
        min: 0,
        max: 100,
        title: { display: true, text: 'Yield %', color: '#a3a3a3', font: { size: 10 } },
        ticks: { color: '#a3a3a3', font: { size: 10 }, callback: (v) => `${v}%` },
        grid: { color: C.grid },
      },
    },
  };

  const wasteRanking = data?.absoluteWasteTopChannels || [];
  const maxWasteSlots = useMemo(
    () => Math.max(...wasteRanking.map((r) => Number(r.waste_slots || 0)), 1),
    [wasteRanking],
  );
  const teamWasteRanking = data?.absoluteWasteTopTeams || [];
  const maxTeamWasteSlots = useMemo(
    () => Math.max(...teamWasteRanking.map((r) => Number(r.waste_slots || 0)), 1),
    [teamWasteRanking],
  );

  const publishLagData = useMemo(() => {
    const rows = data?.publishLagDistribution || [];
    return {
      labels: rows.map((r) => r.lag_bucket),
      datasets: [{
        label: 'Posts', data: rows.map((r) => Number(r.post_count || 0)),
        backgroundColor: ['#22c55e', '#34d399', '#6ee7b7', '#f59e0b', '#fbbf24', '#fca5a5', '#ef4444'],
        borderRadius: 4, barPercentage: 0.75,
      }],
    };
  }, [data]);

  const teamEfficiencyData = useMemo(() => {
    const rows = data?.teamEfficiency || [];
    return {
      labels: rows.map((r) => r.team_name),
      datasets: [
        { label: 'Upload→asset ratio', data: rows.map((r) => Number(r.upload_to_asset_ratio || 0)), backgroundColor: C.c2 + '99', borderRadius: 3 },
        { label: 'Asset→publish ×100', data: rows.map((r) => Number(r.asset_to_publish_ratio_x100 || 0)), backgroundColor: C.c3 + '99', borderRadius: 3 },
      ],
    };
  }, [data]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center rounded-full border border-neutral-700/80 bg-neutral-900/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          View context: {viewLabel}
        </span>
        {activeFilters.length > 0 && (
          <span className="inline-flex items-center rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-[10px] font-semibold text-violet-300">
            {activeFilters.length} filter{activeFilters.length > 1 ? 's' : ''} active
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-3">
        <Card>
          <CardTitle title="Volume vs yield — the effort wasted quadrant" desc="Each dot = 1 channel. Bottom-right = high volume, low yield = wasted processing cost." />
          <div className="relative h-[250px]">
            <Chart type="scatter" data={channelEfficiencyScatterData} options={scatterOptions} plugins={[riskQuadrantPlugin]} />
            <div className="pointer-events-none absolute right-2 top-2 rounded border border-neutral-700/80 bg-[#0b0b0bcc] px-2 py-1 text-[10px] leading-tight text-neutral-300">
              <div>Volume cutoff: {HIGH_VOLUME_LABEL}</div>
              <div>Yield cutoff: {LOW_YIELD_LABEL}</div>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[10.5px] text-neutral-500">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full border-2 border-red-400" />
              flagged: {segregation.riskCount} high-volume + low-yield channels
            </span>
            <span>high-volume cutoff ({HIGH_VOLUME_LABEL}): {Math.round(segregation.volumeThreshold)} videos</span>
            <span>low-yield cutoff ({LOW_YIELD_LABEL}): {segregation.yieldThreshold.toFixed(1)}%</span>
          </div>
          {isAdmin && (
            <div className="flex gap-4 mt-3 flex-wrap">
              {clientLegend.map((client, idx) => (
                <div key={client} className="flex items-center gap-1.5 text-[11px] text-neutral-400">
                  <div className="w-2 h-2 rounded-sm" style={{ background: CLIENT_COLORS[idx % CLIENT_COLORS.length] }} />
                  {client}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <CardTitle title="Absolute waste — top 10 channels" desc="videos_assigned × (1 − yield). Volume × inefficiency = true cost." />
          <div className="space-y-2.5 mt-2">
            {wasteRanking.map((row, idx) => {
              const pct = (Number(row.waste_slots || 0) / maxWasteSlots) * 100;
              return (
                <div key={row.channel_name} className="flex items-center gap-2.5">
                  <div className="w-4 text-[10px] text-neutral-600 font-mono">{idx + 1}</div>
                  <div className="min-w-[100px] text-[12px] font-medium text-neutral-200">{row.channel_name}</div>
                  {isAdmin && <div className="text-[10px] text-neutral-600 min-w-[60px]">{row.client_name}</div>}
                  <div className="flex-1 h-[5px] bg-neutral-800 rounded overflow-hidden">
                    <div className="h-full bg-red-500 rounded" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="w-9 text-right text-[11px] font-semibold text-red-400 font-mono">{row.waste_slots}</div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-3">
        <Card>
          <CardTitle title="Team volume vs yield" desc="Each dot = 1 team. Bottom-right zone flags teams carrying high volume with low publish yield." />
          {teamRows.length > 0 ? (
            <>
              <div className="relative h-[230px]">
                <Chart type="scatter" data={teamScatterData} options={teamScatterOptions} plugins={[riskQuadrantPlugin]} />
                <div className="pointer-events-none absolute right-2 top-2 rounded border border-neutral-700/80 bg-[#0b0b0bcc] px-2 py-1 text-[10px] leading-tight text-neutral-300">
                  <div>Volume cutoff: {HIGH_VOLUME_LABEL}</div>
                  <div>Yield cutoff: {LOW_YIELD_LABEL}</div>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-[10.5px] text-neutral-500">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full border-2 border-red-400" />
                  flagged: {teamSegregation.riskCount} high-volume + low-yield teams
                </span>
                <span>high-volume cutoff ({HIGH_VOLUME_LABEL}): {Math.round(teamSegregation.volumeThreshold)} videos</span>
                <span>low-yield cutoff ({LOW_YIELD_LABEL}): {teamSegregation.yieldThreshold.toFixed(1)}%</span>
              </div>
            </>
          ) : (
            <div className="text-[11.5px] text-neutral-500 rounded-lg border border-neutral-800 bg-[#0a0a0a] px-3 py-2">
              Team-level volume vs yield is unavailable for the current role or filters.
            </div>
          )}
        </Card>

        <Card>
          <CardTitle title="Absolute waste — top teams" desc="Teams with largest non-publishing video load (videos assigned minus published videos)." />
          {teamWasteRanking.length > 0 ? (
            <div className="space-y-2.5 mt-2">
              {teamWasteRanking.map((row, idx) => {
                const pct = (Number(row.waste_slots || 0) / maxTeamWasteSlots) * 100;
                return (
                  <div key={row.team_name} className="flex items-center gap-2.5">
                    <div className="w-4 text-[10px] text-neutral-600 font-mono">{idx + 1}</div>
                    <div className="min-w-[130px] text-[12px] font-medium text-neutral-200">{row.team_name}</div>
                    <div className="flex-1 h-[5px] bg-neutral-800 rounded overflow-hidden">
                      <div className="h-full bg-red-500 rounded" style={{ width: `${pct}%` }} />
                    </div>
                    <div className="w-9 text-right text-[11px] font-semibold text-red-400 font-mono">{row.waste_slots}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-[11.5px] text-neutral-500 rounded-lg border border-neutral-800 bg-[#0a0a0a] px-3 py-2">
              No team waste ranking data available for the current role or filters.
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <Card>
          <CardTitle title="Publish lag distribution" desc="Days from asset creation to first published post." />
          <div className="h-[200px]">
            <Chart type="bar" data={publishLagData} options={barOptions} />
          </div>
          <div className="flex gap-3 mt-2">
            {[{ label: 'Fast (<2d)', color: '#22c55e' }, { label: 'Normal (2-10d)', color: '#f59e0b' }, { label: 'Stale (>10d)', color: '#ef4444' }].map((l) => (
              <div key={l.label} className="flex items-center gap-1.5 text-[10.5px] text-neutral-500">
                <div className="w-2 h-2 rounded-sm" style={{ background: l.color }} />{l.label}
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardTitle title="Team efficiency comparison" desc="Upload to asset ratio and asset to publish ratio by team." />
          <div className="h-[200px]">
            <Chart type="bar" data={teamEfficiencyData} options={barOptions} />
          </div>
          <div className="flex gap-3 mt-2">
            <div className="flex items-center gap-1.5 text-[10.5px] text-neutral-500">
              <div className="w-2 h-2 rounded-sm" style={{ background: C.c2 }} />Upload to asset ratio
            </div>
            <div className="flex items-center gap-1.5 text-[10.5px] text-neutral-500">
              <div className="w-2 h-2 rounded-sm" style={{ background: C.c3 }} />Asset to publish x100
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
