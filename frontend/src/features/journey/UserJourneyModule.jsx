import React, { useMemo, useState } from 'react';
import { Doughnut, Line, Bar } from 'react-chartjs-2';
import { X } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber, formatPct } from '../../lib/formatters';

// ─── Platform palette (red → dark, on-brand) ─────────────────────────────────
const PLATFORM_COLORS = ['#ef4444','#dc2626','#b91c1c','#991b1b','#7f1d1d','#737373','#525252','#3a3a3a'];

// ─── Granularity ──────────────────────────────────────────────────────────────
const GRANULARITIES = [
  { value: 'day', label: 'D' },
  { value: 'week', label: 'W' },
  { value: 'month', label: 'M' },
  { value: 'quarter', label: 'Q' },
];

// ─── Stat Card (matches KpiCard design from other tabs exactly) ───────────────
function StatCard({ title, value, subtitle, trendData }) {
  const isUp = trendData?.length > 1 && trendData[trendData.length - 1] >= trendData[0];
  const lineColor = isUp ? '#10b981' : '#ef4444';

  const chartData = trendData?.length ? {
    labels: trendData.map((_, i) => i),
    datasets: [{
      data: trendData,
      borderColor: lineColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 0,
      fill: true,
      backgroundColor: (ctx) => {
        const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
        g.addColorStop(0, `${lineColor}40`);
        g.addColorStop(1, `${lineColor}00`);
        return g;
      },
    }],
  } : null;

  const chartOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: { x: { display: false }, y: { display: false, min: trendData ? Math.min(...trendData) * 0.9 : 0 } },
    animation: { duration: 600 },
  };

  return (
    <div className="bg-[#111111] rounded-xl p-5 border border-neutral-800 flex justify-between items-start min-h-[120px]">
      <div className="flex-1 flex flex-col justify-between h-full">
        <div>
          <div className="text-xs font-bold tracking-wider text-neutral-500 mb-1">{title}</div>
          <div className="text-3xl font-black text-white tracking-tight">{value}</div>
        </div>
        <div className="text-sm text-neutral-400 mt-2">{subtitle}</div>
      </div>
      {chartData && (
        <div className="w-24 h-16 ml-4 mt-2 shrink-0">
          <Line data={chartData} options={chartOpts} />
        </div>
      )}
    </div>
  );
}

// ─── Gauge using Chart.js Doughnut (270° arc) ────────────────────────────────
// max is the "full scale" value so the arc fill is meaningful at typical real values
function MetricGauge({ label, value, max, note }) {
  const pct = Math.min((value / max) * 100, 100);

  const data = {
    datasets: [{
      data: [pct, 100 - pct],
      backgroundColor: ['#ef4444', '#1c1c1c'],
      borderWidth: 0,
      circumference: 270,
      rotation: -135,
    }],
  };

  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '76%',
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    animation: { animateRotate: true, duration: 1200, easing: 'easeInOutQuart' },
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: 148, height: 148 }}>
        <Doughnut data={data} options={opts} />
        <div className="absolute inset-0 flex items-center justify-center" style={{ paddingBottom: 20 }}>
          <span className="text-2xl font-black text-white">{Number(value).toFixed(1)}%</span>
        </div>
      </div>
      <div className="text-center">
        <div className="text-xs font-bold uppercase tracking-[0.18em] text-neutral-400">{label}</div>
        {note && <div className="text-[11px] text-neutral-600 mt-0.5">{note}</div>}
      </div>
    </div>
  );
}

// ─── Animated bar row (platform leaderboard) ─────────────────────────────────
// ─── Granularity Pills ────────────────────────────────────────────────────────
function GranularityPills({ value, onChange }) {
  return (
    <div className="flex gap-1 rounded-xl border border-neutral-800 bg-[#111111] p-1">
      {GRANULARITIES.map((item) => (
        <button key={item.value} onClick={() => onChange(item.value)} title={item.value}
          className={`h-8 w-8 rounded-lg text-xs font-bold transition-colors ${
            item.value === value ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'
          }`}
        >{item.label}</button>
      ))}
    </div>
  );
}

// ─── Chart tooltip base ───────────────────────────────────────────────────────
const TOOLTIP = { backgroundColor: '#111', borderColor: '#2a2a2a', borderWidth: 1, titleColor: '#fff', bodyColor: '#737373', padding: 10 };
const SCALE_X = { ticks: { color: '#404040', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } };
const SCALE_Y = { ticks: { color: '#404040', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } };

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function UserJourneyModule() {
  const [granularity, setGranularity] = useState('week');
  const [activeChart, setActiveChart] = useState('engagement');
  const [selectedPlatform, setSelectedPlatform] = useState(null);

  const apiQuery = `${API_BASE}/user-journey?granularity=${granularity}`;
  const { data, loading, error } = useApi(apiQuery, [apiQuery]);

  const timeseries  = data?.timeseries            || [];
  const summary     = data?.summary               || {};
  const platformBD  = data?.platform_breakdown    || [];
  const outputBD    = data?.output_type_breakdown || [];
  const recent      = data?.recent_journey        || [];

  // ── Derived totals ──────────────────────────────────────────
  const totalViews   = Number(summary.views    || 0);
  const totalLikes   = Number(summary.likes    || 0);
  const totalComments= Number(summary.comments || 0);
  const totalShares  = Number(summary.shares   || 0);
  const totalInteract= totalLikes + totalComments + totalShares;
  const virality     = totalViews > 0 ? (totalShares / totalViews) * 100 : 0;
  const avgViewsDist = (summary.distributions || 0) > 0 ? totalViews / summary.distributions : 0;

  // ── Sparklines from timeseries ───────────────────────────────
  const spkViews   = useMemo(() => timeseries.map(r => r.views || 0), [timeseries]);
  const spkInteract= useMemo(() => timeseries.map(r => (r.likes||0)+(r.comments||0)+(r.shares||0)), [timeseries]);
  const spkER      = useMemo(() => timeseries.map(r => r.engagement_rate_pct || 0), [timeseries]);
  const spkViral   = useMemo(() => timeseries.map(r => (r.views||0) > 0 ? (r.shares/r.views)*100 : 0), [timeseries]);
  const spkUploaded= useMemo(() => timeseries.map(r => r.uploaded_videos || 0), [timeseries]);
  const spkPublish = useMemo(() => timeseries.map(r => r.published_posts || 0), [timeseries]);
  const spkDist    = useMemo(() => timeseries.map(r => r.distributions || 0), [timeseries]);
  const spkAvgV    = useMemo(() => timeseries.map(r => (r.distributions||0) > 0 ? r.views/r.distributions : 0), [timeseries]);

  // ── Selected platform drill-down (from recent_journey) ───────
  const platformStats = useMemo(() => {
    if (!selectedPlatform) return null;
    const rows = recent.filter(r => r.platform === selectedPlatform);
    const v = rows.reduce((s, r) => s + (r.views||0), 0);
    const l = rows.reduce((s, r) => s + (r.likes||0), 0);
    const c = rows.reduce((s, r) => s + (r.comments||0), 0);
    const sh= rows.reduce((s, r) => s + (r.shares||0), 0);
    const int = l + c + sh;
    return { views: v, likes: l, comments: c, shares: sh, er: v > 0 ? (int/v*100).toFixed(2) : '0.00', count: rows.length };
  }, [selectedPlatform, recent]);

  // ── Language breakdown from recent_journey ─────────────────
  const langBD = useMemo(() => {
    const m = {};
    recent.forEach(r => { const k = r.language || 'Unknown'; m[k] = (m[k]||0) + (r.views||0); });
    return Object.entries(m).sort(([,a],[,b]) => b-a).slice(0,6);
  }, [recent]);
  const maxLang = Math.max(...langBD.map(([,v]) => v), 1);

  // ── Input type breakdown ────────────────────────────────────
  const inputBD = useMemo(() => {
    const m = {};
    recent.forEach(r => { const k = r.input_type || 'Unknown'; m[k] = (m[k]||0) + (r.views||0); });
    return Object.entries(m).sort(([,a],[,b]) => b-a).slice(0,6);
  }, [recent]);
  const maxInput = Math.max(...inputBD.map(([,v]) => v), 1);

  // ── Quick insights ──────────────────────────────────────────
  const topByViews = platformBD.reduce((b, p) => !b || p.views > b.views ? p : b, null);
  const topByER    = platformBD.reduce((b, p) => !b || p.engagement_rate_pct > b.engagement_rate_pct ? p : b, null);
  const topOutput  = outputBD.reduce((b, o) => !b || o.views_per_post > b.views_per_post ? o : b, null);


  // ── Chart tab config ────────────────────────────────────────
  const TABS = [
    { id: 'engagement', label: 'Views & Interactions' },
    { id: 'rate',       label: 'Engagement Rate'      },
    { id: 'platforms',  label: 'Platforms'             },
    { id: 'virality',   label: 'Virality'              },
  ];

  const engagementData = useMemo(() => ({
    labels: timeseries.map(r => r.period),
    datasets: [
      { label: 'Views', data: timeseries.map(r => r.views||0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', tension: 0.4, fill: true, pointRadius: 0, pointHoverRadius: 5 },
      { label: 'Interactions', data: timeseries.map(r => (r.likes||0)+(r.comments||0)+(r.shares||0)), borderColor: 'rgba(255,255,255,0.25)', backgroundColor: 'transparent', tension: 0.4, fill: false, pointRadius: 0, pointHoverRadius: 5, borderDash: [4, 4] },
    ],
  }), [timeseries]);

  const rateData = useMemo(() => ({
    labels: timeseries.map(r => r.period),
    datasets: [{ label: 'Engagement Rate %', data: timeseries.map(r => r.engagement_rate_pct||0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', tension: 0.4, fill: true, pointRadius: 0, pointHoverRadius: 5 }],
  }), [timeseries]);

  const viralityData = useMemo(() => ({
    labels: timeseries.map(r => r.period),
    datasets: [{ label: 'Virality %', data: timeseries.map(r => (r.views||0) > 0 ? (r.shares/r.views)*100 : 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', tension: 0.4, fill: true, pointRadius: 0, pointHoverRadius: 5 }],
  }), [timeseries]);

  const platformData = useMemo(() => ({
    labels: platformBD.map(r => r.platform),
    datasets: [
      { label: 'Views', data: platformBD.map(r => r.views||0), backgroundColor: 'rgba(239,68,68,0.65)', borderRadius: 6, borderSkipped: false },
      { label: 'Likes', data: platformBD.map(r => r.likes||0), backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 6, borderSkipped: false },
    ],
  }), [platformBD]);

  const doughnutData = useMemo(() => ({
    labels: ['Likes', 'Comments', 'Shares'],
    datasets: [{
      data: [totalLikes, totalComments, totalShares],
      backgroundColor: ['#ef4444', '#525252', '#262626'],
      borderColor: ['#ef4444', '#525252', '#262626'],
      borderWidth: 0,
      hoverOffset: 8,
    }],
  }), [totalLikes, totalComments, totalShares]);

  const platformDoughnutData = useMemo(() => ({
    labels: platformBD.map(p => p.platform),
    datasets: [{
      data: platformBD.map(p => p.views),
      backgroundColor: PLATFORM_COLORS.slice(0, platformBD.length),
      borderColor: '#111111',
      borderWidth: 2,
      hoverOffset: 8,
    }],
  }), [platformBD]);

  const platformDoughnutOpts = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    cutout: '48%',
    plugins: {
      legend: { position: 'right', labels: { color: '#737373', font: { size: 11 }, boxWidth: 10, padding: 12 } },
      tooltip: { ...TOOLTIP, callbacks: { label: ctx => ` ${ctx.label}: ${formatNumber(ctx.raw)} views` } },
    },
    onClick: (_evt, elements) => {
      if (elements.length > 0) {
        const platform = platformBD[elements[0].index]?.platform;
        if (platform) setSelectedPlatform(prev => prev === platform ? null : platform);
      }
    },
    animation: { duration: 700 },
  }), [platformBD, setSelectedPlatform]);

  const baseOpts = {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 600 },
    plugins: { legend: { labels: { color: '#525252', font: { size: 11 }, boxWidth: 12, padding: 16 } }, tooltip: TOOLTIP },
    scales: { x: SCALE_X, y: SCALE_Y },
  };
  const rateOpts  = { ...baseOpts, scales: { x: SCALE_X, y: { ...SCALE_Y, ticks: { ...SCALE_Y.ticks, callback: v => `${v}%` } } } };
  const doughOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'right', labels: { color: '#737373', font: { size: 11 }, boxWidth: 10, padding: 12 } },
      tooltip: { ...TOOLTIP, callbacks: { label: ctx => ` ${ctx.label}: ${formatNumber(ctx.raw)}${totalInteract > 0 ? ` · ${((ctx.raw/totalInteract)*100).toFixed(1)}%` : ''}` } },
    },
    animation: { duration: 900 },
  };

  // ── Active chart renderer ────────────────────────────────────
  const chartEl = (() => {
    if (activeChart === 'engagement') return <Line data={engagementData} options={baseOpts} />;
    if (activeChart === 'rate')       return <Line data={rateData}       options={rateOpts} />;
    if (activeChart === 'virality')   return <Line data={viralityData}   options={rateOpts} />;
    if (activeChart === 'platforms')  return <Bar  data={platformData}   options={baseOpts} />;
    return null;
  })();

  // ─────────────────────────────────────────────────────────────
  if (loading) return <div className="h-full flex items-center justify-center text-sm text-neutral-500">Loading engagement metrics...</div>;
  if (error)   return <div className="p-6 text-sm text-red-400">{error}</div>;

  return (
    <div className="h-full overflow-y-auto bg-[#050505] px-6 py-6 space-y-6 text-white">

      {/* ── Header ── */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Analytics</div>
          <h2 className="mt-1 text-2xl font-black tracking-tight">Engagement Metrics</h2>
          <p className="mt-1 text-sm text-neutral-500">End-to-end content performance — upload to audience engagement.</p>
        </div>
        <GranularityPills value={granularity} onChange={setGranularity} />
      </div>

      {/* ── KPI Cards Row 1 — Engagement ── */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="VIEWS"            value={formatNumber(totalViews)}    subtitle={`${formatPct(summary.interaction_rate_pct||0)} engagement rate`} trendData={spkViews} />
        <StatCard title="INTERACTIONS"     value={formatNumber(totalInteract)} subtitle={`${formatNumber(totalLikes)} likes · ${formatNumber(totalShares)} shares`} trendData={spkInteract} />
        <StatCard title="ENGAGEMENT RATE"  value={`${Number(summary.interaction_rate_pct||0).toFixed(2)}%`} subtitle="(likes + comments + shares) ÷ views" trendData={spkER} />
        <StatCard title="VIRALITY SCORE"   value={`${virality.toFixed(2)}%`}   subtitle={`${formatNumber(totalShares)} shares total`} trendData={spkViral} />
      </section>

      {/* ── KPI Cards Row 2 — Pipeline ── */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="UPLOADED"         value={formatNumber(summary.uploaded_videos||0)}  subtitle="raw videos"                   trendData={spkUploaded} />
        <StatCard title="PUBLISHED"        value={formatNumber(summary.published_posts||0)}   subtitle={`${formatPct(summary.publish_from_upload_pct||0)} of uploads`} trendData={spkPublish} />
        <StatCard title="DISTRIBUTIONS"    value={formatNumber(summary.distributions||0)}     subtitle={`${formatPct(summary.distribution_from_publish_pct||0)} from published`} trendData={spkDist} />
        <StatCard title="AVG VIEWS / DIST" value={formatNumber(Math.round(avgViewsDist))}     subtitle="reach per distribution"       trendData={spkAvgV} />
      </section>

      {/* ── Performance Overview — Gauges + Insights ── */}
      <section className="rounded-[28px] border border-neutral-800 bg-[#111111] p-6">
        <div className="mb-6 text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Pipeline Conversion Rates</div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">

          {/* Gauges */}
          <div className="flex flex-wrap justify-around gap-6">
            <MetricGauge label="Publish Rate"      value={Number(summary.publish_from_upload_pct||0)}       max={100} note="% of uploads published" />
            <MetricGauge label="Distribution Rate" value={Number(summary.distribution_from_publish_pct||0)} max={100} note="% posts distributed" />
            <MetricGauge label="Engagement Rate"   value={Number(summary.interaction_rate_pct||0)}          max={100} note="% interactions per view" />
          </div>

          {/* Quick Insights */}
          <div className="space-y-1 divide-y divide-neutral-800/60">
            {[
              { label: 'Top Platform by Views',  main: topByViews?.platform || '—',    sub: topByViews ? formatNumber(topByViews.views) + ' views' : '' },
              { label: 'Best Engagement Rate',   main: topByER?.platform || '—',       sub: topByER ? formatPct(topByER.engagement_rate_pct) + ' ER' : '' },
              { label: 'Top Output Type',        main: topOutput?.output_type || '—',  sub: topOutput ? formatNumber(topOutput.views_per_post) + ' views/post' : '' },
              { label: 'Virality',               main: `${virality.toFixed(2)}% share rate`, sub: formatNumber(totalShares) + ' shares' },
            ].map(({ label, main, sub }) => (
              <div key={label} className="flex items-center justify-between py-3">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-neutral-600">{label}</div>
                  <div className="mt-0.5 font-semibold text-white">{main}</div>
                </div>
                <div className="text-sm text-neutral-500 text-right">{sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Interactive Chart Section ── */}
      <section className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
        {/* Tab bar — matches OverviewModule output type tabs */}
        <div className="flex border-b border-neutral-800 mb-5 gap-1">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveChart(tab.id)}
              className={`px-4 py-2 text-sm font-medium tracking-wide transition-colors ${
                activeChart === tab.id
                  ? 'text-white border-b-2 border-[#ef4444]'
                  : 'text-neutral-500 hover:text-neutral-300'
              }`}
            >{tab.label}</button>
          ))}
        </div>
        <div className="h-[300px]">{chartEl}</div>
      </section>

      {/* ── Platform Leaderboard (Interactive) + Interaction Breakdown ── */}
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Platform — click to drill down */}
        <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Platform Performance</div>
            {selectedPlatform && (
              <button onClick={() => setSelectedPlatform(null)}
                className="flex items-center gap-1 text-xs text-neutral-500 hover:text-white transition-colors">
                <X size={12} /> Clear
              </button>
            )}
          </div>

          {/* Drill-down panel */}
          {platformStats && (
            <div className="mb-4 rounded-xl border border-neutral-800 bg-[#0d0d0d] px-4 py-3">
              <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-600 mb-2">{selectedPlatform}</div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="text-lg font-black text-white">{formatNumber(platformStats.views)}</div>
                  <div className="text-[10px] text-neutral-600 uppercase tracking-wider">Views</div>
                </div>
                <div>
                  <div className="text-lg font-black text-[#ef4444]">{platformStats.er}%</div>
                  <div className="text-[10px] text-neutral-600 uppercase tracking-wider">ER</div>
                </div>
                <div>
                  <div className="text-lg font-black text-white">{formatNumber(platformStats.shares)}</div>
                  <div className="text-[10px] text-neutral-600 uppercase tracking-wider">Shares</div>
                </div>
              </div>
            </div>
          )}

          <div className="flex-1 min-h-0" style={{ height: platformStats ? 260 : 320 }}>
            <Doughnut data={platformDoughnutData} options={platformDoughnutOpts} />
          </div>
        </div>

        {/* Interaction Breakdown */}
        <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5 flex flex-col">
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Interaction Breakdown</div>
          {totalInteract > 0 ? (
            <>
              <div className="flex-1 min-h-0" style={{ minHeight: 200 }}>
                <Doughnut data={doughnutData} options={doughOpts} />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 border-t border-neutral-800 pt-4">
                {[['Likes', totalLikes, '#ef4444'], ['Comments', totalComments, '#737373'], ['Shares', totalShares, '#525252']].map(([l, v, c]) => (
                  <div key={l} className="text-center">
                    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: c }}>{l}</div>
                    <div className="text-xl font-black text-white mt-1">{formatNumber(v)}</div>
                    <div className="text-[11px] text-neutral-600">{formatPct((v/totalInteract)*100)}</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-neutral-700">No interaction data</div>
          )}
        </div>
      </section>

      {/* ── Output Type Cards (hover reveals detail) ── */}
      <section className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Output Type Performance</div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {outputBD.map(row => (
            <div key={row.output_type}
              className="group relative rounded-xl border border-neutral-800 bg-[#0d0d0d] p-4 overflow-hidden cursor-default hover:border-neutral-600 transition-colors"
            >
              {/* Default view */}
              <div className="transition-opacity duration-200 group-hover:opacity-0">
                <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-500">{row.output_type}</div>
                <div className="mt-3 text-2xl font-black text-white">{formatNumber(row.views_per_post)}</div>
                <div className="mt-1 text-[11px] text-neutral-600">views per post</div>
              </div>
              {/* Hover view */}
              <div className="absolute inset-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-between">
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#ef4444]">{row.output_type}</div>
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-neutral-500">Views</span>
                    <span className="font-bold text-white">{formatNumber(row.views)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-neutral-500">Posts</span>
                    <span className="font-bold text-white">{formatNumber(row.posts_distributed)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-neutral-500">Interactions</span>
                    <span className="font-bold text-white">{formatNumber(row.interactions)}</span>
                  </div>
                  <div className="flex justify-between text-xs border-t border-neutral-800 pt-2">
                    <span className="text-neutral-500">Views/Post</span>
                    <span className="font-black text-[#ef4444]">{formatNumber(row.views_per_post)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Language + Input Type Breakdown ── */}
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Views by Language</div>
          <div className="space-y-4">
            {langBD.map(([lang, views]) => {
              const pct = Math.max((views / maxLang) * 100, 2);
              return (
                <div key={lang}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="font-medium text-neutral-300">{lang}</span>
                    <span className="text-neutral-500 tabular-nums text-xs">{formatNumber(views)}</span>
                  </div>
                  <div className="h-1.5 bg-neutral-900 rounded-full overflow-hidden">
                    <div className="h-full bg-[#ef4444] rounded-full" style={{ width: `${pct}%`, opacity: 0.6 }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Views by Input Type</div>
          <div className="space-y-4">
            {inputBD.map(([type, views]) => {
              const pct = Math.max((views / maxInput) * 100, 2);
              return (
                <div key={type}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="font-medium text-neutral-300">{type}</span>
                    <span className="text-neutral-500 tabular-nums text-xs">{formatNumber(views)}</span>
                  </div>
                  <div className="h-1.5 bg-neutral-900 rounded-full overflow-hidden">
                    <div className="h-full bg-[#ef4444] rounded-full" style={{ width: `${pct}%`, opacity: 0.6 }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

    </div>
  );
}
