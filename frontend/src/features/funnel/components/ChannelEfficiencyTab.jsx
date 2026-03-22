import React, { useMemo, useState } from 'react';
import { Chart } from 'react-chartjs-2';
import FunnelViewContextStrip from './FunnelViewContextStrip';
import HoverInfoButton from '../../../components/common/HoverInfoButton';
import InfoTooltipContent from '../../../components/common/InfoTooltipContent';

const C = {
  c1: '#8b5cf6', c2: '#60a5fa', c3: '#34d399', c4: '#f97316',
  red: '#ef4444', amber: '#f59e0b', green: '#22c55e',
  grid: 'rgba(255,255,255,0.04)',
};

const Card = ({ children, className = '' }) => (
  <div className={`bg-[#111111] rounded-xl border border-neutral-800 p-4 ${className}`}>{children}</div>
);

const CardTitle = ({ title, desc, infoTooltip }) => (
  <div className="mb-3">
    <div className="flex items-center justify-between gap-2">
      <h3 className="text-[15px] font-semibold text-white">{title}</h3>
      {infoTooltip ? (
        <HoverInfoButton
          ariaLabel={`More information about ${title}`}
          widthClass="w-80"
          buttonClassName="h-5 w-5 text-[10px] font-semibold"
          tooltipClassName="p-3 text-[11px] text-neutral-300"
          tooltip={infoTooltip}
        />
      ) : null}
    </div>
    {desc && <p className="mt-1 text-[12px] text-neutral-500 leading-relaxed">{desc}</p>}
  </div>
);

const barOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#a3a3a3', font: { size: 12 } }, grid: { display: false } },
    y: { ticks: { color: '#a3a3a3', font: { size: 12 } }, grid: { color: C.grid } },
  },
};

const CLIENT_COLORS = [C.c1, C.c2, C.c3, C.c4, '#ec4899', '#22c55e', '#f59e0b', '#a3a3a3'];
const HIGH_VOLUME_PERCENTILE = 0.70;
const LOW_YIELD_PERCENTILE = 0.30;
const HIGH_VOLUME_LABEL = `P${Math.round(HIGH_VOLUME_PERCENTILE * 100)}`;
const LOW_YIELD_LABEL = `P${Math.round(LOW_YIELD_PERCENTILE * 100)}`;
const SCATTER_TICK_FONT_SIZE = 13;
const SCATTER_TITLE_FONT_SIZE = 14;
const SCATTER_TOOLTIP_TITLE_FONT_SIZE = 13;
const SCATTER_TOOLTIP_BODY_FONT_SIZE = 13;

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

function normalizedRange(values = [], { minBound = 0, maxBound = 100, padding = 0.08 } = {}) {
  if (!values.length) {
    return { min: minBound, max: maxBound };
  }

  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = rawMax - rawMin;
  const pad = span > 0 ? span * padding : Math.max(Math.abs(rawMin) * padding, 1);

  const min = Math.max(minBound, rawMin - pad);
  const max = Math.min(maxBound, rawMax + pad);

  if (min === max) {
    return {
      min: Math.max(minBound, min - 1),
      max: Math.min(maxBound, max + 1),
    };
  }

  return { min, max };
}

function pointKey(clientName, channelName) {
  return `${clientName || 'Unknown'}::${channelName || 'Unknown'}`;
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Number(value || 0));
}

function redToGrayGradient(context, startColor = 'rgba(239, 68, 68, 0.85)', endColor = 'rgba(115, 115, 115, 0.45)') {
  const { chart } = context;
  const { ctx, chartArea } = chart;
  if (!chartArea) return startColor;
  const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  gradient.addColorStop(0, startColor);
  gradient.addColorStop(1, endColor);
  return gradient;
}

export default function ChannelEfficiencyTab({ authUser, data, breakdown, filters }) {
  const isAdmin = authUser?.role === 'website_admin';
  const [scatterView, setScatterView] = useState('channels');
  const [wasteView, setWasteView] = useState('channels');
  const [isFlaggedDialogOpen, setIsFlaggedDialogOpen] = useState(false);
  const rows = data?.channelEfficiency || [];
  const teamRows = data?.teamVolumeYield || [];

  const segregation = useMemo(() => {
    if (!rows.length) {
      return {
        volumeThreshold: 0,
        yieldThreshold: 0,
        xMin: 0,
        xMax: 1,
        yMin: 0,
        yMax: 100,
        riskKeys: new Set(),
        riskCount: 0,
      };
    }

    const volumes = rows.map((row) => Number(row.videos_assigned || 0));
    const yields = rows.map((row) => Number(row.yield_pct || 0));
    const volumeThreshold = percentile(volumes, HIGH_VOLUME_PERCENTILE);
    const yieldThreshold = percentile(yields, LOW_YIELD_PERCENTILE);
    const xMin = Math.max(0, Math.min(...volumes) * 0.92);
    const xMax = Math.max(...volumes) * 1.08;
    const { min: yMin, max: yMax } = normalizedRange(yields, { minBound: 0, maxBound: 100, padding: 0.08 });

    const riskKeys = new Set(
      rows
        .filter((row) => Number(row.videos_assigned || 0) >= volumeThreshold && Number(row.yield_pct || 0) <= yieldThreshold)
        .map((row) => pointKey(row.client_name, row.channel_name)),
    );

    return { volumeThreshold, yieldThreshold, xMin, xMax, yMin, yMax, riskKeys, riskCount: riskKeys.size };
  }, [rows]);

  const clientLegend = useMemo(
    () => Array.from(new Set(rows.map((row) => row.client_name || 'Unknown'))),
    [rows],
  );

  const clientLegendItems = useMemo(() => {
    const counts = new Map();
    rows.forEach((row) => {
      const name = row.client_name || 'Unknown';
      counts.set(name, (counts.get(name) || 0) + 1);
    });
    return clientLegend.map((client) => ({ client, count: counts.get(client) || 0 }));
  }, [rows, clientLegend]);

  const teamSegregation = useMemo(() => {
    if (!teamRows.length) {
      return { volumeThreshold: 0, yieldThreshold: 0, yMin: 0, yMax: 100, riskKeys: new Set(), riskCount: 0 };
    }

    const volumes = teamRows.map((row) => Number(row.videos_assigned || 0));
    const yields = teamRows.map((row) => Number(row.yield_pct || 0));
    const volumeThreshold = percentile(volumes, HIGH_VOLUME_PERCENTILE);
    const yieldThreshold = percentile(yields, LOW_YIELD_PERCENTILE);
    const { min: yMin, max: yMax } = normalizedRange(yields, { minBound: 0, maxBound: 100, padding: 0.08 });

    const riskKeys = new Set(
      teamRows
        .filter((row) => Number(row.videos_assigned || 0) >= volumeThreshold && Number(row.yield_pct || 0) <= yieldThreshold)
        .map((row) => row.team_name || 'Unknown'),
    );

    return { volumeThreshold, yieldThreshold, yMin, yMax, riskKeys, riskCount: riskKeys.size };
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
    layout: { padding: { top: 6, right: 6, bottom: 2, left: 2 } },
    plugins: {
      legend: {
        display: false,
      },
      riskQuadrant: {
        enabled: rows.length > 0,
        xCutoff: segregation.volumeThreshold,
        yCutoff: segregation.yieldThreshold,
      },
      tooltip: {
        titleFont: { size: SCATTER_TOOLTIP_TITLE_FONT_SIZE },
        bodyFont: { size: SCATTER_TOOLTIP_BODY_FONT_SIZE },
        callbacks: {
          label: (ctx) => `${ctx.raw?.channel_name || ''}: ${ctx.raw.x} videos, ${ctx.raw.y}% yield${ctx.raw?.risk ? ' [high volume + low yield]' : ''}`,
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Videos assigned', color: '#a3a3a3', font: { size: SCATTER_TITLE_FONT_SIZE } },
        ticks: { color: '#a3a3a3', font: { size: SCATTER_TICK_FONT_SIZE } },
        grid: { color: C.grid },
      },
      y: {
        min: segregation.yMin,
        max: segregation.yMax,
        title: { display: true, text: 'Yield %', color: '#a3a3a3', font: { size: SCATTER_TITLE_FONT_SIZE } },
        ticks: { color: '#a3a3a3', font: { size: SCATTER_TICK_FONT_SIZE }, callback: (v) => `${Number(v).toFixed(2)}%` },
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
    layout: { padding: { top: 6, right: 6, bottom: 2, left: 2 } },
    plugins: {
      legend: { display: false },
      riskQuadrant: {
        enabled: teamRows.length > 0,
        xCutoff: teamSegregation.volumeThreshold,
        yCutoff: teamSegregation.yieldThreshold,
      },
      tooltip: {
        titleFont: { size: SCATTER_TOOLTIP_TITLE_FONT_SIZE },
        bodyFont: { size: SCATTER_TOOLTIP_BODY_FONT_SIZE },
        callbacks: {
          label: (ctx) => `${ctx.raw?.team_name || ''}: ${ctx.raw.x} videos, ${ctx.raw.y}% yield${ctx.raw?.risk ? ' [high volume + low yield]' : ''}`,
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Videos assigned', color: '#a3a3a3', font: { size: SCATTER_TITLE_FONT_SIZE } },
        ticks: { color: '#a3a3a3', font: { size: SCATTER_TICK_FONT_SIZE } },
        grid: { color: C.grid },
      },
      y: {
        min: teamSegregation.yMin,
        max: teamSegregation.yMax,
        title: { display: true, text: 'Yield %', color: '#a3a3a3', font: { size: SCATTER_TITLE_FONT_SIZE } },
        ticks: { color: '#a3a3a3', font: { size: SCATTER_TICK_FONT_SIZE }, callback: (v) => `${Number(v).toFixed(2)}%` },
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
  const normalizedWasteScale = useMemo(
    () => Math.max(maxWasteSlots, maxTeamWasteSlots, 1),
    [maxWasteSlots, maxTeamWasteSlots],
  );
  const channelWasteTotal = useMemo(
    () => wasteRanking.reduce((sum, row) => sum + Number(row.waste_slots || 0), 0),
    [wasteRanking],
  );
  const teamWasteTotal = useMemo(
    () => teamWasteRanking.reduce((sum, row) => sum + Number(row.waste_slots || 0), 0),
    [teamWasteRanking],
  );
  const channelTopShare = channelWasteTotal > 0 ? (Number(wasteRanking[0]?.waste_slots || 0) / channelWasteTotal) * 100 : 0;
  const teamTopShare = teamWasteTotal > 0 ? (Number(teamWasteRanking[0]?.waste_slots || 0) / teamWasteTotal) * 100 : 0;
  const scatterViewOptions = useMemo(() => ([
    { key: 'channels', label: 'Channels' },
    { key: 'teams', label: 'Teams' },
  ]), []);
  const activeScatter = useMemo(() => {
    if (scatterView === 'teams') {
      return {
        key: 'teams',
        title: 'Team volume vs yield',
        data: teamScatterData,
        options: teamScatterOptions,
        rows: teamRows,
        flagged: teamSegregation.riskCount,
        volumeThreshold: teamSegregation.volumeThreshold,
        yieldThreshold: teamSegregation.yieldThreshold,
        emptyText: 'Team-level volume vs yield is unavailable for the current role or filters.',
      };
    }

    return {
      key: 'channels',
      title: 'Volume vs yield',
      data: channelEfficiencyScatterData,
      options: scatterOptions,
      rows,
      flagged: segregation.riskCount,
      volumeThreshold: segregation.volumeThreshold,
      yieldThreshold: segregation.yieldThreshold,
      emptyText: 'Channel-level volume vs yield is unavailable for the current role or filters.',
    };
  }, [scatterView, teamScatterData, teamScatterOptions, teamRows, teamSegregation, channelEfficiencyScatterData, scatterOptions, rows, segregation]);
  const flaggedEntities = useMemo(() => {
    if (scatterView === 'teams') {
      return teamRows
        .filter((row) => teamSegregation.riskKeys.has(row.team_name || 'Unknown'))
        .map((row) => ({
          key: row.team_name || 'Unknown',
          name: row.team_name || 'Unknown',
          subLabel: '',
          videosAssigned: Number(row.videos_assigned || 0),
          yieldPct: Number(row.yield_pct || 0),
        }))
        .sort((a, b) => b.videosAssigned - a.videosAssigned);
    }

    return rows
      .filter((row) => segregation.riskKeys.has(pointKey(row.client_name, row.channel_name)))
      .map((row) => ({
        key: pointKey(row.client_name, row.channel_name),
        name: row.channel_name || 'Unknown',
        subLabel: isAdmin ? (row.client_name || 'Unknown') : '',
        videosAssigned: Number(row.videos_assigned || 0),
        yieldPct: Number(row.yield_pct || 0),
      }))
      .sort((a, b) => b.videosAssigned - a.videosAssigned);
  }, [scatterView, teamRows, teamSegregation, rows, segregation, isAdmin]);
  const scatterLegendItems = useMemo(() => {
    if (scatterView === 'channels' && isAdmin) {
      return clientLegendItems.map(({ client, count }, idx) => ({
        key: `${client}-${idx}`,
        label: client,
        count,
        color: CLIENT_COLORS[idx % CLIENT_COLORS.length],
      }));
    }

    if (scatterView === 'teams') {
      return [{ key: 'teams', label: 'Teams', color: C.c3 }];
    }

    return [{ key: 'channels', label: 'Channels', color: C.c2 }];
  }, [scatterView, isAdmin, clientLegendItems]);
  const wasteViewOptions = useMemo(() => ([
    { key: 'channels', label: 'Channels' },
    { key: 'teams', label: 'Teams' },
  ]), []);
  const activeWaste = useMemo(() => {
    if (wasteView === 'teams') {
      return {
        key: 'teams',
        title: 'Team',
        entries: teamWasteRanking,
        total: teamWasteTotal,
        topShare: teamTopShare,
        emptyText: 'No team waste ranking data available for the current role or filters.',
      };
    }

    return {
      key: 'channels',
      title: isAdmin ? 'Channel / Client' : 'Channel',
      entries: wasteRanking,
      total: channelWasteTotal,
      topShare: channelTopShare,
      emptyText: 'No channel waste ranking data available for the current role or filters.',
    };
  }, [wasteView, isAdmin, wasteRanking, channelWasteTotal, channelTopShare, teamWasteRanking, teamWasteTotal, teamTopShare]);

  const publishLagRows = data?.publishLagDistribution || [];
  const publishLagStats = useMemo(() => {
    const totalPosts = publishLagRows.reduce((sum, row) => sum + Number(row.post_count || 0), 0);
    const dominantBucket = publishLagRows.reduce(
      (best, row) => {
        const count = Number(row.post_count || 0);
        return count > best.count ? { bucket: row.lag_bucket || 'N/A', count } : best;
      },
      { bucket: 'N/A', count: 0 },
    );

    const stalePosts = publishLagRows
      .filter((row) => />\s*10|10\+|stale/i.test(String(row.lag_bucket || '')))
      .reduce((sum, row) => sum + Number(row.post_count || 0), 0);
    const staleShare = totalPosts > 0 ? (stalePosts / totalPosts) * 100 : 0;

    return { totalPosts, dominantBucket, staleShare };
  }, [publishLagRows]);

  const publishLagData = useMemo(() => ({
    labels: publishLagRows.map((r) => r.lag_bucket),
    datasets: [{
      label: 'Posts',
      data: publishLagRows.map((r) => Number(r.post_count || 0)),
      backgroundColor: (ctx) => redToGrayGradient(ctx, 'rgba(248, 113, 113, 0.9)', 'rgba(115, 115, 115, 0.38)'),
      borderColor: 'rgba(248, 113, 113, 0.92)',
      borderWidth: 1,
      borderRadius: 5,
      borderSkipped: false,
      barThickness: 18,
      maxBarThickness: 22,
      categoryPercentage: 0.7,
      barPercentage: 0.9,
    }],
  }), [publishLagRows]);

  const publishLagOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        titleFont: { size: 11 },
        bodyFont: { size: 11 },
        callbacks: {
          label: (ctx) => `${ctx.raw} posts`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: '#a3a3a3', font: { size: 10 }, maxRotation: 0, minRotation: 0 },
        grid: { display: false },
      },
      y: {
        beginAtZero: true,
        ticks: { color: '#a3a3a3', font: { size: 10 } },
        grid: { color: C.grid },
      },
    },
  };

  const teamEfficiencyRows = data?.teamEfficiency || [];
  const teamEfficiencyStats = useMemo(() => {
    if (!teamEfficiencyRows.length) {
      return { avgPublishRatio: 0, topTeam: 'N/A', topPublishRatio: 0 };
    }

    const publishRatios = teamEfficiencyRows.map((r) => Number(r.asset_to_publish_ratio_x100 || 0));
    const avgPublishRatio = publishRatios.reduce((sum, v) => sum + v, 0) / publishRatios.length;
    const best = teamEfficiencyRows.reduce(
      (current, row) => {
        const ratio = Number(row.asset_to_publish_ratio_x100 || 0);
        return ratio > current.ratio ? { team: row.team_name || 'Unknown', ratio } : current;
      },
      { team: 'N/A', ratio: 0 },
    );

    return { avgPublishRatio, topTeam: best.team, topPublishRatio: best.ratio };
  }, [teamEfficiencyRows]);

  const teamEfficiencyData = useMemo(() => ({
    labels: teamEfficiencyRows.map((r) => r.team_name),
    datasets: [
      {
        label: 'Upload→asset ratio',
        data: teamEfficiencyRows.map((r) => Number(r.upload_to_asset_ratio || 0)),
        backgroundColor: (ctx) => redToGrayGradient(ctx, 'rgba(59, 130, 246, 0.82)', 'rgba(100, 116, 139, 0.38)'),
        borderColor: 'rgba(59, 130, 246, 0.96)',
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 16,
      },
      {
        label: 'Asset→publish ×100',
        data: teamEfficiencyRows.map((r) => Number(r.asset_to_publish_ratio_x100 || 0)),
        backgroundColor: (ctx) => redToGrayGradient(ctx, 'rgba(244, 63, 94, 0.84)', 'rgba(107, 114, 128, 0.28)'),
        borderColor: 'rgba(251, 113, 133, 0.98)',
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 16,
      },
    ],
  }), [teamEfficiencyRows]);

  const teamEfficiencyOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        titleFont: { size: 11 },
        bodyFont: { size: 11 },
      },
    },
    scales: {
      x: {
        ticks: { color: '#a3a3a3', font: { size: 10 }, maxRotation: 0, minRotation: 0 },
        grid: { display: false },
      },
      y: {
        beginAtZero: true,
        ticks: { color: '#a3a3a3', font: { size: 10 } },
        grid: { color: C.grid },
      },
    },
  };

  return (
    <div className="space-y-3">
      <FunnelViewContextStrip breakdown={breakdown} filters={filters} />
      <div className="grid grid-cols-1 items-start xl:grid-cols-[1.5fr_1fr] gap-3">
        <div className="space-y-3">
          <Card className="p-2.5 md:p-3 h-[430px] md:h-[460px] flex flex-col">
            <CardTitle
              title="Volume vs yield"
              desc="Switch between channel and team distributions with shared risk highlighting."
              infoTooltip={
                <InfoTooltipContent
                  eyebrow="Volume vs Yield"
                  summary="This scatter compares scale versus efficiency: x-axis is assigned videos and y-axis is yield percentage."
                  bullets={[
                    { label: 'Risk zone', text: 'Lower-right points are high-volume but low-yield entities.' },
                    { label: 'Threshold logic', text: 'Flagging uses high-volume and low-yield percentile cutoffs.' },
                    { label: 'Operational meaning', text: 'These entities consume capacity while producing weak publish return.' },
                  ]}
                  takeaway="Prioritize flagged entities for workflow fixes, assignment rebalancing, or content-fit review."
                />
              }
            />
            <div className="mb-2 inline-flex w-fit self-start rounded-md border border-neutral-800 bg-black/30 p-0.5">
              {scatterViewOptions.map((option) => {
                const active = option.key === scatterView;
                return (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => setScatterView(option.key)}
                    aria-pressed={active}
                    className={`rounded px-2.5 py-1 text-[12px] font-semibold whitespace-nowrap transition-colors ${active ? 'bg-neutral-200 text-neutral-900' : 'text-neutral-400 hover:text-neutral-200'}`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
            {activeScatter.rows.length > 0 ? (
              <>
                <div className="relative h-[205px] md:h-[225px]">
                  <Chart type="scatter" data={activeScatter.data} options={activeScatter.options} plugins={[riskQuadrantPlugin]} />
                </div>
                <div className="mt-2 grid grid-cols-1 gap-1.5 text-[12px] text-neutral-400 sm:grid-cols-3">
                  <button
                    type="button"
                    onClick={() => setIsFlaggedDialogOpen(true)}
                    className="rounded-md border border-neutral-800 bg-black/30 px-2.5 py-1.5 text-left transition-colors hover:border-red-400/40 hover:bg-red-500/5"
                  >
                    <span className="text-neutral-500">Flagged</span>
                    <div className="mt-0.5 font-semibold text-red-300">{activeScatter.flagged} {activeScatter.key === 'teams' ? 'teams' : 'channels'}</div>
                  </button>
                  <div className="rounded-md border border-neutral-800 bg-black/30 px-2.5 py-1.5">
                    <span className="text-neutral-500">High-volume ({HIGH_VOLUME_LABEL})</span>
                    <div className="mt-0.5 font-semibold text-neutral-200">{Math.round(activeScatter.volumeThreshold)} videos</div>
                  </div>
                  <div className="rounded-md border border-neutral-800 bg-black/30 px-2.5 py-1.5">
                    <span className="text-neutral-500">Low-yield ({LOW_YIELD_LABEL})</span>
                    <div className="mt-0.5 font-semibold text-neutral-200">{activeScatter.yieldThreshold.toFixed(1)}%</div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <div className={`flex max-h-[50px] flex-wrap gap-1 overflow-y-auto pr-1`}>
                    {scatterLegendItems.map((item) => (
                      <div key={item.key} className="inline-flex items-center gap-1 rounded-md border border-neutral-800 bg-black/30 px-1.5 py-0.5 text-[10px] text-neutral-300">
                        <div className="h-2 w-2 rounded-sm" style={{ background: item.color }} />
                        <span>{item.label}</span>
                        {typeof item.count === 'number' ? <span className="text-neutral-500">({item.count})</span> : null}
                      </div>
                    ))}
                  </div>
                  <div className="inline-flex items-center gap-1 rounded-md border border-neutral-800 bg-black/30 px-1.5 py-0.5 text-[10px] text-neutral-300">
                    <span className="h-2 w-2 rounded-full border border-red-300 bg-red-500/15" />
                    <span>Risk point</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-[13px] text-neutral-500 rounded-lg border border-neutral-800 bg-[#0a0a0a] px-3 py-2">
                {activeScatter.emptyText}
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-3">
          <Card className="p-2.5 md:p-3 h-[430px] md:h-[460px] flex flex-col">
            <CardTitle
              title="Absolute waste"
              desc="Ranked by waste slots."
              infoTooltip={
                <InfoTooltipContent
                  eyebrow="Absolute Waste"
                  summary="Waste slots are assigned videos minus published outputs, showing absolute production leakage."
                  bullets={[
                    { label: 'Concentration', text: 'Rank and top-share indicate whether waste is localized or broad.' },
                    { label: 'Severity', text: 'Higher values represent more assigned effort that never reached publish.' },
                    { label: 'Root causes', text: 'Persistent waste often points to process friction or capacity mismatch.' },
                  ]}
                  takeaway="Use concentration plus trend direction to target interventions at the right level."
                />
              }
            />
            <div className="mb-2 inline-flex w-fit self-start rounded-md border border-neutral-800 bg-black/30 p-0.5">
              {wasteViewOptions.map((option) => {
                const active = option.key === wasteView;
                return (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => setWasteView(option.key)}
                    aria-pressed={active}
                    className={`rounded px-2.5 py-1 text-[12px] font-semibold whitespace-nowrap transition-colors ${active ? 'bg-neutral-200 text-neutral-900' : 'text-neutral-400 hover:text-neutral-200'}`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>

            {activeWaste.entries.length > 0 ? (
              <>
                <div className="mb-1 text-[11px] text-neutral-500">Entries shown: {activeWaste.entries.length}</div>
                <div className="overflow-hidden rounded-lg border border-neutral-800 bg-[#0c0c0c]">
                  <div className="grid grid-cols-[44px_minmax(0,1fr)_84px] border-b border-neutral-800 bg-black/30 px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                    <span>Rank</span>
                    <span>{activeWaste.title}</span>
                    <span className="text-right">Waste</span>
                  </div>
                  <div className={`h-[190px] overflow-y-auto md:h-[210px]`}>
                    {activeWaste.entries.map((row, idx) => {
                      const waste = Number(row.waste_slots || 0);
                      const pct = (waste / normalizedWasteScale) * 100;
                      const primaryName = activeWaste.key === 'channels' ? row.channel_name : row.team_name;
                      const secondaryName = activeWaste.key === 'channels' && isAdmin ? row.client_name : '';
                      const rowKey = activeWaste.key === 'channels'
                        ? `${row.channel_name || 'Unknown'}::${row.client_name || 'Unknown'}::${idx}`
                        : `${row.team_name || 'Unknown'}::${idx}`;

                      return (
                        <div key={rowKey} className="relative isolate border-b border-neutral-900/80 px-2 py-1.5 last:border-b-0 hover:bg-white/[0.02]">
                          <div className="absolute inset-y-0 left-0 z-0 bg-red-500/15" style={{ width: `${pct}%` }} />
                          <div className="relative z-10 grid grid-cols-[44px_minmax(0,1fr)_84px] items-center gap-2">
                            <span className="inline-flex w-8 items-center justify-center rounded bg-neutral-800/80 text-[11px] font-mono text-neutral-300">#{idx + 1}</span>
                            <div className="min-w-0">
                              <div className="truncate text-[13px] font-medium text-neutral-100" title={primaryName}>{primaryName}</div>
                              {secondaryName ? <div className="truncate text-[10.5px] text-neutral-500" title={secondaryName}>{secondaryName}</div> : null}
                            </div>
                            <div className="text-right text-[12px] font-semibold text-red-300 font-mono">{formatCompactNumber(waste)}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="mt-1.5 grid grid-cols-2 gap-1 text-[11px]">
                  <div className="rounded-md border border-neutral-800 bg-black/30 px-2 py-1.5 text-neutral-400">
                    <div className="text-neutral-500">Total waste</div>
                    <div className="mt-0.5 text-[12px] font-semibold text-neutral-200">{formatCompactNumber(activeWaste.total)}</div>
                  </div>
                  <div className="rounded-md border border-neutral-800 bg-black/30 px-2 py-1.5 text-neutral-400">
                    <div className="text-neutral-500">Top contributor share</div>
                    <div className="mt-0.5 text-[12px] font-semibold text-neutral-200">{activeWaste.topShare.toFixed(1)}%</div>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-[13px] text-neutral-500 rounded-lg border border-neutral-800 bg-[#0a0a0a] px-3 py-2">
                {activeWaste.emptyText}
              </div>
            )}
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <Card className="p-2.5 md:p-3">
          <CardTitle
            title="Publish lag distribution"
            desc="Days from asset creation to first published post."
            infoTooltip={
              <InfoTooltipContent
                eyebrow="Publish Lag"
                summary="Histogram of days from asset creation to first published post."
                bullets={[
                  { label: 'Fast flow', text: 'A left-heavy shape indicates quicker turnaround.' },
                  { label: 'Backlog signal', text: 'A growing right tail suggests delayed publishing or queue buildup.' },
                  { label: 'Change tracking', text: 'Compare shape shifts to evaluate whether process updates reduced lag.' },
                ]}
                takeaway="Monitor tail behavior, not only averages, to catch hidden cycle-time risk."
              />
            }
          />
          <div className="h-[185px] md:h-[200px]">
            <Chart type="bar" data={publishLagData} options={publishLagOptions} />
          </div>
          
        </Card>

        <Card className="p-2.5 md:p-3">
          <CardTitle
            title="Team efficiency comparison"
            desc="Upload to asset ratio and asset to publish ratio by team."
            infoTooltip={
              <InfoTooltipContent
                eyebrow="Team Efficiency"
                summary="Compares two stage efficiencies per team: upload-to-asset conversion and asset-to-publish conversion."
                bullets={[
                  { label: 'Balanced strength', text: 'Teams high on both bars are healthy end-to-end.' },
                  { label: 'Gap diagnosis', text: 'Large bar gaps reveal whether friction is in creation or publishing.' },
                  { label: 'Action path', text: 'Use stage imbalance to choose targeted coaching or workflow fixes.' },
                ]}
                takeaway="Treat this as a stage-diagnostic view, not just a leaderboard."
              />
            }
          />
          <div className="mb-2 flex flex-wrap items-center gap-2 text-[10px] text-neutral-400">
            <div className="inline-flex items-center gap-1.5 rounded-md border border-neutral-800 bg-black/30 px-2 py-1">
              <span className="h-2.5 w-2.5 rounded-sm border border-blue-300/80 bg-blue-500/80" />
              <span>Upload→asset ratio</span>
            </div>
            <div className="inline-flex items-center gap-1.5 rounded-md border border-neutral-800 bg-black/30 px-2 py-1">
              <span className="h-2.5 w-2.5 rounded-[2px] border border-rose-300/90 bg-rose-500/80" />
              <span>Asset→publish ×100</span>
            </div>
          </div>
          
          <div className="h-[185px] md:h-[200px]">
            <Chart type="bar" data={teamEfficiencyData} options={teamEfficiencyOptions} />
          </div>
        </Card>
      </div>

      {isFlaggedDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 px-3"
          onClick={() => setIsFlaggedDialogOpen(false)}
        >
          <div
            className="w-full max-w-2xl rounded-xl border border-neutral-800 bg-[#111111] p-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-[16px] font-semibold text-white">
                  Flagged {scatterView === 'teams' ? 'teams' : 'channels'}
                </h3>
                <p className="mt-1 text-[11px] text-neutral-500">
                  High volume ({'>='} {HIGH_VOLUME_LABEL}) and low yield ({'<='} {LOW_YIELD_LABEL}) entities.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsFlaggedDialogOpen(false)}
                className="rounded border border-neutral-700 px-2 py-1 text-[11px] font-semibold text-neutral-300 hover:border-neutral-500 hover:text-white"
              >
                Close
              </button>
            </div>

            {flaggedEntities.length > 0 ? (
              <div className="overflow-hidden rounded-lg border border-neutral-800 bg-black/30">
                <div className="grid grid-cols-[minmax(0,1fr)_96px_80px] border-b border-neutral-800 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                  <span>{scatterView === 'teams' ? 'Team' : (isAdmin ? 'Channel / Client' : 'Channel')}</span>
                  <span className="text-right">Videos</span>
                  <span className="text-right">Yield</span>
                </div>
                <div className={`max-h-[300px] overflow-y-auto`}>
                  {flaggedEntities.map((entity) => (
                    <div key={entity.key} className="grid grid-cols-[minmax(0,1fr)_96px_80px] items-center gap-2 border-b border-neutral-900/70 px-3 py-2 text-[12px] last:border-b-0">
                      <div className="min-w-0">
                        <div className="truncate font-medium text-neutral-100" title={entity.name}>{entity.name}</div>
                        {entity.subLabel ? (
                          <div className="truncate text-[11px] text-neutral-500" title={entity.subLabel}>{entity.subLabel}</div>
                        ) : null}
                      </div>
                      <div className="text-right font-mono text-neutral-300">{entity.videosAssigned}</div>
                      <div className="text-right font-mono text-red-300">{entity.yieldPct.toFixed(2)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-neutral-800 bg-black/30 px-3 py-2 text-[12px] text-neutral-400">
                No flagged entities found for the current view.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
