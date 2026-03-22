import React, { useState, useEffect } from 'react';
import { TrendingUp, Plus, X, Wand2, Info } from "lucide-react";
import { Line } from 'react-chartjs-2';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatHours, formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';
import { OverviewSkeleton, Skeleton } from '../../components/common/Skeleton';
import InsightCard from '../../components/insights/InsightCard';
import KpiDetailsModal from './KpiDetailsModal';
import { KPI_DEFINITIONS } from './kpiDefinitions';
import KPICreator from '../../components/KPICreator';

const CORE_KPI_KEYS = [
  { id: 'uploaded_count',          title: 'UPLOADED',                  trendMetric: 'uploaded_count',          getValue: (k) => formatNumber(k.uploaded_count ?? 0),                                           getSubtitle: (k) => formatHours(k.uploaded_duration ?? 0) },
  { id: 'created_count',           title: 'CREATED',                   trendMetric: 'created_count',           getValue: (k) => formatNumber(k.created_count ?? 0),                                            getSubtitle: (k) => formatHours(k.created_duration ?? 0) },
  { id: 'published_count',         title: 'PUBLISHED',                 trendMetric: 'published_count',         getValue: (k) => formatNumber(k.published_count ?? 0),                                          getSubtitle: (k) => formatHours(k.published_duration ?? 0) },
  { id: 'publish_conversion_rate', title: 'PUBLISH CONVERSION RATE',   trendMetric: 'publish_conversion_rate', getValue: (k) => formatPct(k.publish_conversion_rate ?? 0),                                      getSubtitle: () => 'Avg. conversion rate' },
  { id: 'waste_index',             title: 'WASTE INDEX',               trendMetric: 'waste_index',             getValue: (k) => k.waste_index !== undefined ? Number(k.waste_index).toFixed(2) : '—',           getSubtitle: () => 'Logarithmic waste' },
];

const TOP_PERFORMER_DIMENSION_MAP = {
  channel: 'channel',
  user: 'user',
  'input type': 'input_type',
  input_type: 'input_type',
  'output type': 'output_type',
  output_type: 'output_type',
  language: 'language',
  team: 'team',
  client: 'client',
};

const FUNNEL_FILTER_KEYS = ['client', 'input_type', 'output_type', 'language', 'channel', 'user', 'team'];
function buildCoreKpiCards(kpis, monthlyTrends) {
  return CORE_KPI_KEYS.map(({ id, title, trendMetric, getValue, getSubtitle }) => ({
    id,
    title,
    value: getValue(kpis),
    subtitle: getSubtitle(kpis),
    trendData: trendMetric && monthlyTrends[trendMetric]
      ? monthlyTrends[trendMetric].map(p => p.value)
      : [],
  }));
}

function GraphInfoButton({ description = 'Graph context and definitions will be available here.' }) {
  return (
    <div className="relative group">
      <button
        type="button"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
        aria-label="Graph information"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-neutral-700 bg-[#0f1116] text-neutral-400 transition-colors hover:border-neutral-500 hover:text-white"
      >
        <Info size={12} />
      </button>
      <div className="pointer-events-none absolute right-0 top-7 z-20 w-52 rounded-lg border border-neutral-700 bg-[#0b0d11] px-2.5 py-2 text-[11px] leading-relaxed text-neutral-300 opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
        {description}
      </div>
    </div>
  );
}

function MissionRailMetricCard({ title, value, subtitle, trendData, onClick, onRemove }) {
  const points = Array.isArray(trendData) && trendData.length ? trendData : [8, 12, 10, 16, 14, 19, 17];
  const isPositive = points[points.length - 1] >= points[0];
  const color = isPositive ? '#00d8a0' : '#ef4444';
  const data = {
    labels: points.map((_, i) => i.toString()),
    datasets: [
      {
        data: points,
        borderColor: color,
        borderWidth: 2.4,
        tension: 0.42,
        pointRadius: 0,
        fill: true,
        backgroundColor: (ctx) => {
          const chart = ctx.chart;
          const gradient = chart.ctx.createLinearGradient(0, 0, 0, chart.height);
          gradient.addColorStop(0, `${color}3d`);
          gradient.addColorStop(1, `${color}00`);
          return gradient;
        },
      },
    ],
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: { x: { display: false }, y: { display: false } },
    interaction: { mode: 'index', intersect: false },
  };

  const inner = (
    <div className="flex h-full items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-500">
          {title}
        </div>
        <div className="mt-1 text-[36px] leading-none font-black tracking-tight text-white">
          {value}
        </div>
        <div className="mt-2 text-[12px] text-neutral-400 leading-snug">
          {subtitle}
        </div>
      </div>
      <div className="h-[64px] w-[96px] shrink-0 mt-4">
        <Line data={data} options={options} />
      </div>
    </div>
  );

  if (onRemove) {
    return (
      <div className="group relative h-full">
        <button
          type="button"
          onClick={onClick}
          className="h-full w-full min-h-[128px] rounded-xl border border-neutral-800 bg-[#0f1218] px-4 py-4 text-left transition-colors hover:border-neutral-600 overflow-hidden"
        >
          {inner}
        </button>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-neutral-800 text-neutral-400 opacity-0 transition-opacity hover:bg-neutral-700 hover:text-white group-hover:opacity-100"
        >
          <X size={11} />
        </button>
      </div>
    );
  }

  const content = (
    <div className="h-full min-h-[128px] rounded-xl border border-neutral-800 bg-[#0f1218] px-4 py-4 transition-colors hover:border-neutral-600 overflow-hidden">
      {inner}
    </div>
  );

  if (!onClick) return content;
  return (
    <button type="button" onClick={onClick} className="w-full h-full text-left">
      {content}
    </button>
  );
}

function MissionRailActionCard({ icon, label, onClick, tone = 'neutral' }) {
  const toneClass = tone === 'brand'
    ? 'border-violet-700/50 bg-violet-950/20 text-violet-300 hover:border-violet-500/60 hover:bg-violet-950/30'
    : 'border-neutral-700 bg-[#12151b] text-neutral-200 hover:border-neutral-500 hover:bg-[#171b22]';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-full w-full rounded-xl border px-3 py-2 transition-colors ${toneClass}`}
    >
      <div className="flex h-full items-center justify-center gap-1.5">
        {icon}
        <span className="text-[11px] font-bold uppercase tracking-[0.08em]">{label}</span>
      </div>
    </button>
  );
}

export default function OverviewModule({ onNavigate }) {
  const overview = useApi(`${API_BASE}/overview`, []);
  const insights = useApi(`${API_BASE}/insights?surface=mission-control`, []);
  const uploadedTrend   = useApi(`${API_BASE}/trends?metric=uploaded_count&granularity=month`, []);
  const createdTrend    = useApi(`${API_BASE}/trends?metric=created_count&granularity=month`, []);
  const publishedTrend  = useApi(`${API_BASE}/trends?metric=published_count&granularity=month`, []);
  const conversionTrend = useApi(`${API_BASE}/trends?metric=publish_conversion_rate&granularity=month`, []);
  const wasteTrend      = useApi(`${API_BASE}/trends?metric=waste_index&granularity=month`, []);

  const monthlyTrends = {
    uploaded_count:          uploadedTrend.data?.series   || [],
    created_count:           createdTrend.data?.series    || [],
    published_count:         publishedTrend.data?.series  || [],
    publish_conversion_rate: conversionTrend.data?.series || [],
    waste_index:             wasteTrend.data?.series      || [],
  };

  const loading = overview.loading;
  const error = overview.error || insights.error;
  const data = overview.data || {};
  const [activeExtraKpis, setActiveExtraKpis] = useState(() => {
    try { return JSON.parse(localStorage.getItem('mc_extra_kpis')) || []; } catch { return []; }
  });
  const [stagedKpis, setStagedKpis] = useState([]);
  const [isSelectionPanelOpen, setIsSelectionPanelOpen] = useState(false);
  const [selectedKpi, setSelectedKpi] = useState(null);
  const [activeOutputTab, setActiveOutputTab] = useState(null);
  const [outputChartMetric, setOutputChartMetric] = useState('created');
  const [showKpiCreator, setShowKpiCreator] = useState(false);
  const [editingKpi, setEditingKpi] = useState(null);  // custom KPI being edited
  const [customKpis, setCustomKpis] = useState([]);  // KPIs created by user

  const handleTopPerformerClick = (item) => {
    const rawDimension = String(item?.dimension || '').trim().toLowerCase();
    const mappedDimension = TOP_PERFORMER_DIMENSION_MAP[rawDimension];
    const label = item?.label ? String(item.label) : '';
    if (!mappedDimension || !label) return;

    const clearedFilters = FUNNEL_FILTER_KEYS.reduce((acc, key) => {
      acc[key] = '';
      return acc;
    }, {});

    onNavigate?.({
      view: 'funnel',
      tab: 'channel',
      breakdown: mappedDimension,
      ...clearedFilters,
      [mappedDimension]: label,
    });
  };

  useEffect(() => {
    if (data?.outputStats?.length > 0 && !activeOutputTab) {
      setActiveOutputTab(data.outputStats[0].label);
    }
  }, [data?.outputStats, activeOutputTab]);

  // Persist extra KPIs to localStorage
  useEffect(() => {
    localStorage.setItem('mc_extra_kpis', JSON.stringify(activeExtraKpis));
  }, [activeExtraKpis]);

  const kpis = data.kpis || {};

  const _formatKpiValue = (value, dsl) => {
    if (value === null || value === undefined) return '—';
    const num = parseFloat(value);
    if (Number.isNaN(num)) return '—';
    const metric = dsl?.metric || '';
    const formula = dsl?.formula || '';
    const operands = dsl?.operands || [];
    const durationAtoms = ['uploaded_duration', 'created_duration', 'published_duration'];
    const rateMetrics = ['publish_conversion_rate', 'creation_rate', 'processing_efficiency'];
    // Known single-metric types
    if (rateMetrics.includes(metric)) return formatPct(num);
    if (metric === 'waste_index') return `${num.toFixed(2)}s`;  // seconds difference
    if (durationAtoms.includes(metric)) return formatHours(num);
    // Formula: if it contains division → it's a dimensionless ratio regardless of operand types
    const hasDiv = formula.includes('/');
    const isRate = hasDiv && (formula.includes('* 100') || formula.includes('*100'));
    if (isRate) return formatPct(num);
    // Duration atoms summed/subtracted (no division) → display as hours
    if (!hasDiv && operands.length > 0 && operands.every(o => durationAtoms.includes(o))) return formatHours(num);
    // Dimensionless ratio or count
    if (hasDiv) return num.toFixed(2);
    return num >= 1000 ? formatNumber(Math.round(num)) : num % 1 === 0 ? formatNumber(num) : num.toFixed(2);
  };

  const buildCustomKpiObj = (record, timeSeries = null) => {
    const values = (timeSeries || []).map(p => parseFloat(p.value) || 0);
    // Use last non-zero value so trailing empty periods don't show "0" on the card
    const latestValue = [...values].reverse().find(v => v !== 0) ?? (values.length > 0 ? values[values.length - 1] : null);
    const granularity = record.dsl_json?.time_granularity || 'month';
    return {
      id: `custom_${record.id}`,
      kpi_db_id: record.id,
      title: record.name.toUpperCase(),
      name: record.name,
      description: record.description || '',
      definition: record.description || 'User-defined custom KPI.',
      formula: record.dsl_json?.formula || record.dsl_json?.metric || 'Custom formula',
      significance: `Custom KPI created via ${record.dsl_json?.type === 'formula' ? 'formula' : 'natural language'}.`,
      isCustom: true,
      dsl_json: record.dsl_json,
      getValue: () => latestValue !== null ? _formatKpiValue(latestValue, record.dsl_json) : '—',
      getSubtitle: () => granularity,
      trendData: values.length > 1 ? values : null,
      detailsData: {},
    };
  };

  const _fetchAndPatchKpi = async (record, stateId) => {
    try {
      const token = localStorage.getItem('frammer_auth_token');
      const res = await fetch(`${API_BASE}/kpi/${record.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      const timeSeries = data.time_series || [];
      if (!timeSeries.length) return;
      const updated = buildCustomKpiObj(record, timeSeries);
      setCustomKpis(prev => prev.map(k => k.id === stateId ? updated : k));
    } catch {
      // silently ignore — card stays with '—' placeholder
    }
  };

  // No longer persisting to localStorage — server is the source of truth

  // Fetch custom KPIs from server on mount (scoped to logged-in user)
  useEffect(() => {
    const fetchCustomKpis = async () => {
      try {
        const token = localStorage.getItem('frammer_auth_token');
        if (!token) return;
        const res = await fetch(`${API_BASE}/kpi/list`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const { kpis: records } = await res.json();
        if (!Array.isArray(records) || records.length === 0) {
          setCustomKpis([]);
          return;
        }
        const restored = records.map(r => buildCustomKpiObj(r, null));
        setCustomKpis(restored);
        records.forEach(r => _fetchAndPatchKpi(r, `custom_${r.id}`));
      } catch { /* ignore — fall back to empty */ }
    };
    fetchCustomKpis();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddMore = () => {
    setIsSelectionPanelOpen(!isSelectionPanelOpen);
  };

  const handleStageKpi = (id) => {
    if (!activeExtraKpis.includes(id) && !stagedKpis.includes(id)) {
      setStagedKpis([...stagedKpis, id]);
    }
  };

  const handleUnstageKpi = (id) => {
    setStagedKpis(prev => prev.filter(k => k !== id));
  };

  const handlePromoteKpis = () => {
    setActiveExtraKpis([...stagedKpis, ...activeExtraKpis]);
    setStagedKpis([]);
  };

  const handleRemoveKpi = (id) => {
    setActiveExtraKpis(prev => prev.filter(k => k !== id));
  };

  const visibleExtraKpis = KPI_DEFINITIONS.filter(kpi => activeExtraKpis.includes(kpi.id));

  const handleCoreKpiClick = (id) => {
    const kpi = KPI_DEFINITIONS.find(k => k.id === id);
    if (kpi) setSelectedKpi(kpi);
  };

  const handleCustomKpiCreated = (record) => {
    const customKpi = buildCustomKpiObj(record, null);
    if (editingKpi) {
      setCustomKpis((prev) => prev.map((k) => k.id === editingKpi.id ? customKpi : k));
      setEditingKpi(null);
    } else {
      setCustomKpis((prev) => [customKpi, ...prev]);
    }
    setShowKpiCreator(false);
    // Async fetch real values to replace the placeholder
    _fetchAndPatchKpi(record, customKpi.id);
  };

  const handleCustomKpiClick = (kpi) => {
    setSelectedKpi(kpi);
  };

  const handleEditCustomKpi = (kpi) => {
    setEditingKpi(kpi);
    setShowKpiCreator(true);
  };

  const handleRemoveCustomKpi = async (kpi) => {
    // Optimistically remove from UI
    setCustomKpis((prev) => prev.filter((k) => k.id !== kpi.id));
    try {
      const token = localStorage.getItem('frammer_auth_token');
      await fetch(`${API_BASE}/kpi/${kpi.kpi_db_id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // silently ignore — record will be cleaned up on next list fetch
    }
  };

  if (loading) return <OverviewSkeleton />;
  if (error) return <div className="p-6 text-red-400">{error}</div>;

  return (
    <div className="h-full overflow-y-auto hide-scrollbar bg-[#050505] px-6 py-6 space-y-6">
      {/* KPI slider rail */}
      <section>
        <div className="flex items-start gap-4">
          <div className="min-w-0 flex-1">
            <div className="relative">
              <div
                className="flex gap-4 overflow-x-auto hide-scrollbar snap-x snap-mandatory pb-1 pr-1"
              >
                {/* Added KPI cards (custom + extra) — shown first */}
                {customKpis.map((kpi) => (
                  <div key={kpi.id} className="w-[220px] sm:w-[240px] lg:w-[260px] h-[128px] shrink-0 snap-start">
                    <MissionRailMetricCard
                      title={kpi.title}
                      value={kpi.getValue(kpis)}
                      subtitle={kpi.getSubtitle(kpis)}
                      trendData={kpi.trendData}
                      onClick={() => handleCustomKpiClick(kpi)}
                      onRemove={() => handleRemoveCustomKpi(kpi)}
                    />
                  </div>
                ))}

                {visibleExtraKpis.map((kpi) => (
                  <div key={kpi.id} className="w-[220px] sm:w-[240px] lg:w-[260px] h-[128px] shrink-0 snap-start">
                    <MissionRailMetricCard
                      title={kpi.title}
                      value={kpi.getValue(kpis)}
                      subtitle={kpi.getSubtitle(kpis)}
                      trendData={kpi.trendData}
                      onClick={() => setSelectedKpi(kpi)}
                      onRemove={() => handleRemoveKpi(kpi.id)}
                    />
                  </div>
                ))}

                {/* Core KPI cards from API */}
                {buildCoreKpiCards(kpis, monthlyTrends).map((card) => (
                  <div key={card.id} className="w-[220px] sm:w-[240px] lg:w-[260px] h-[128px] shrink-0 snap-start">
                    <MissionRailMetricCard
                      title={card.title}
                      value={card.value}
                      subtitle={card.subtitle}
                      trendData={card.trendData}
                      onClick={() => handleCoreKpiClick(card.id)}
                    />
                  </div>
                ))}
              </div>

            </div>

          </div>

          <div className="w-[140px] sm:w-[150px] lg:w-[160px] shrink-0 h-[128px] grid grid-rows-2 gap-2">
            <div className="h-full">
              <MissionRailActionCard
                icon={isSelectionPanelOpen ? <X size={16} /> : <Plus size={16} />}
                label={isSelectionPanelOpen ? 'Close' : 'Add More'}
                onClick={handleAddMore}
              />
            </div>
            <div className="h-full">
              <MissionRailActionCard
                icon={<Wand2 size={16} />}
                label="Create KPI"
                onClick={() => setShowKpiCreator(true)}
                tone="brand"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Staging Panel */}
      {stagedKpis.length > 0 && (
        <section className="rounded-[24px] border border-emerald-700/40 bg-emerald-950/10 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.14em] text-emerald-300">
              <TrendingUp size={15} />
              Staged for Deployment ({stagedKpis.length})
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
            {KPI_DEFINITIONS.filter(k => stagedKpis.includes(k.id)).map(kpi => (
              <KpiCard 
                key={kpi.id}
                title={kpi.title} 
                value={kpi.getValue(kpis)} 
                subtitle={kpi.getSubtitle(kpis)} 
                trendData={kpi.trendData}
                onRemove={() => handleUnstageKpi(kpi.id)}
              />
            ))}
            <button 
              onClick={handlePromoteKpis}
              className="flex flex-col items-center justify-center rounded-xl p-5 border border-emerald-500/70 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 hover:text-emerald-200 transition-all font-black text-lg min-h-[140px]"
            >
              <Plus size={32} className="mb-2" />
              <span>ADD TO DASHBOARD</span>
            </button>
          </div>
        </section>
      )}

      {/* KPI Selection Panel */}
      {isSelectionPanelOpen && (
        <section className="rounded-[24px] border border-neutral-800 bg-[#101216] p-6 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.14em] text-neutral-300">
              <Plus size={15} />
              Available KPIs
            </div>
            <button 
              onClick={() => setIsSelectionPanelOpen(false)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-neutral-700 bg-[#0f1114] text-neutral-400 hover:text-white hover:border-neutral-500 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 max-h-[400px] overflow-y-auto pr-2 hide-scrollbar">
            {KPI_DEFINITIONS.filter(k => !['uploaded_count', 'created_count', 'published_count'].includes(k.id) && !activeExtraKpis.includes(k.id)).map(kpi => {
              const isStaged = stagedKpis.includes(kpi.id);
              return (
                <KpiCard 
                  key={kpi.id}
                  title={kpi.title} 
                  value={kpi.getValue(kpis)} 
                  subtitle={kpi.getSubtitle(kpis)} 
                  trendData={kpi.trendData}
                  onRemove={isStaged ? () => handleUnstageKpi(kpi.id) : undefined}
                  onAdd={!isStaged ? () => handleStageKpi(kpi.id) : undefined}
                  onClick={() => handleStageKpi(kpi.id)}
                />
              );
            })}
          </div>
        </section>
      )}

      {data?.outputStats && data.outputStats.length > 0 && (() => {
        const activeStat = data.outputStats.find(s => s.label === activeOutputTab) || data.outputStats[0];
        const allStats = data.outputStats;
        const maxCreated = Math.max(...allStats.map(s => s.total_created_count || 0), 1);

        // Build time series for the active output type
        const tsRows = (data.outputTimeseries || []).filter(r => r.output_type === activeStat?.label);
        const tsLabels = tsRows.map(r => r.period);
        const METRIC_CFG = {
          uploaded:  { label: 'Uploaded',  color: '#a3a3a3', bg: 'rgba(163,163,163,0.08)' },
          created:   { label: 'Created',   color: '#10b981', bg: 'rgba(16,185,129,0.08)' },
          published: { label: 'Published', color: '#3b82f6', bg: 'rgba(59,130,246,0.08)' },
        };
        const cfg = METRIC_CFG[outputChartMetric];
        const tsData = {
          labels: tsLabels,
          datasets: [{
            label: cfg.label,
            data: tsRows.map(r => r[outputChartMetric] || 0),
            borderColor: cfg.color,
            backgroundColor: cfg.bg,
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: tsLabels.length > 20 ? 0 : 3,
            pointHoverRadius: 4,
          }],
        };
        const tsOpts = {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 400 },
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#525252', font: { size: 9 }, maxTicksLimit: 12 }, grid: { color: 'rgba(255,255,255,0.03)' } },
            y: { ticks: { color: '#525252', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
          },
        };

        return (
          <section className="rounded-[24px] border border-neutral-800 bg-[#101216] p-5">
            <div className="mb-5 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.14em] text-neutral-300">
              <TrendingUp size={15} />
              Output Types Summary
            </div>

            <div className="flex gap-5">
              {/* ── Vertical tabs ── */}
              <div className="shrink-0 flex flex-col gap-1 w-40">
                {allStats.map(stat => {
                  const isActive = stat.label === activeStat?.label;
                  const barW = (stat.total_created_count || 0) / maxCreated * 100;
                  return (
                    <button
                      key={stat.label}
                      onClick={() => setActiveOutputTab(stat.label)}
                      className={`group text-left rounded-xl px-3 py-2.5 transition-all border ${
                        isActive
                          ? 'bg-[#1a1d22] border-neutral-600'
                          : 'bg-[#111317] border-neutral-800 hover:bg-[#161a20] hover:border-neutral-700'
                      }`}
                    >
                      <div className={`text-xs font-semibold tracking-wide ${isActive ? 'text-white' : 'text-neutral-300 group-hover:text-white'}`}>
                        {stat.label}
                      </div>
                      <div className="mt-1.5 flex items-center gap-2">
                        <div className="flex-1 h-1 rounded-full bg-neutral-800/80 overflow-hidden">
                          <div className="h-full rounded-full bg-sky-400/70 transition-all duration-500" style={{ width: `${barW}%` }} />
                        </div>
                        <span className="text-[10px] text-neutral-400 tabular-nums font-bold">{formatNumber(stat.total_created_count || 0)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* ── Content ── */}
              {activeStat && (
                <div className="flex-1 min-w-0 space-y-4">
                  {/* Stat cards — clickable to switch chart metric */}
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { key: 'uploaded',  label: 'Uploaded',  count: activeStat.total_uploaded_count,  dur: activeStat.total_uploaded_duration,  color: 'text-white',        ring: 'border-neutral-500' },
                      { key: 'created',   label: 'Created',   count: activeStat.total_created_count,   dur: activeStat.total_created_duration,   color: 'text-emerald-400',   ring: 'border-emerald-500' },
                      { key: 'published', label: 'Published', count: activeStat.total_published_count, dur: activeStat.total_published_duration, color: 'text-blue-400',      ring: 'border-blue-500' },
                    ].map(s => {
                      const isActive = outputChartMetric === s.key;
                      return (
                        <button
                          key={s.key}
                          onClick={() => setOutputChartMetric(s.key)}
                          className={`rounded-xl border bg-[#121418] p-4 text-center transition-all ${
                            isActive ? `${s.ring} border-opacity-60` : 'border-neutral-800/60 hover:border-neutral-700'
                          }`}
                        >
                          <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-neutral-400 mb-1.5">{s.label}</div>
                          <div className={`text-xl font-black ${s.color}`}>{formatNumber(s.count || 0)}</div>
                          <div className="text-[11px] text-neutral-400 mt-1">{formatHours(s.dur || 0)}</div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Time series chart */}
                  <div className="rounded-xl border border-neutral-800/70 bg-[#121418] p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-neutral-400">
                        {cfg.label} — Monthly Trend
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-[10px] text-neutral-500">{activeStat.label}</div>
                        <GraphInfoButton description="This trend chart tracks the selected metric over time for the chosen output type." />
                      </div>
                    </div>
                    <div className="h-44">
                      {tsLabels.length > 0 ? (
                        <Line data={tsData} options={tsOpts} />
                      ) : (
                        <div className="flex items-center justify-center h-full text-xs text-neutral-400">No time series data</div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        );
      })()}

      <section className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.95fr] gap-6 xl:items-stretch">
        <div className="rounded-[24px] border border-neutral-800 bg-[#101216] p-6 flex flex-col" style={{ height: '680px' }}>
          <div className="mb-4 flex items-center justify-between gap-2 shrink-0">
            <div className="text-sm font-bold uppercase tracking-[0.14em] text-neutral-200">ATLAS Insights</div>
            <GraphInfoButton description="AI insights summarize notable patterns, risks, and opportunities from the current mission control scope." />
          </div>
          <div className="flex flex-col gap-2.5 flex-1 min-h-0 overflow-y-auto hide-scrollbar">
            {insights.loading && [...Array(5)].map((_, i) => (
              <div key={i} className="rounded-2xl border border-neutral-700/70 bg-[#111214] px-4 py-3.5 min-h-[108px] flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-4 w-16 rounded-md" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-3 w-8 shrink-0" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
                <div className="flex items-center justify-between mt-2.5">
                  <div className="flex gap-1.5">
                    <Skeleton className="h-4 w-20 rounded-md" />
                    <Skeleton className="h-4 w-16 rounded-md" />
                  </div>
                  <Skeleton className="h-6 w-20 rounded-lg" />
                </div>
              </div>
            ))}
            {!insights.loading && (insights.data?.insights || []).map((insight) => (
              <div key={insight.id} className="shrink-0">
                <InsightCard insight={insight} onNavigate={onNavigate} />
              </div>
            ))}
            {!insights.loading && !(insights.data?.insights || []).length && (
              <div className="rounded-3xl border border-dashed border-neutral-600 bg-[#121317] p-6 text-sm text-neutral-300">
                No major issues are active in the current scope.
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-rows-2 gap-6" style={{ height: '680px' }}>
          <div className="rounded-[24px] border border-neutral-800 bg-[#101216] p-4 flex flex-col min-h-0">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-[13px] font-bold uppercase tracking-[0.12em] text-neutral-300">Top Performers</div>
              <GraphInfoButton description="Bars represent conversion rate by performer for the active scope." />
            </div>
            <div className="space-y-1.5 flex-1 min-h-0 overflow-y-auto hide-scrollbar pr-1">
              {(() => {
                const performers = data.topPerformers || [];
                return performers.map((item, index) => {
                  const pct = item.conversion || 0;
                  const barWidth = Math.min(Math.max(pct, 0), 100);
                  return (
                    <button
                      type="button"
                      key={`${item.dimension}-${item.label}`}
                      onClick={() => handleTopPerformerClick(item)}
                      className="w-full rounded-xl border border-neutral-800 bg-[#0f1217] px-3 py-2.5 text-left transition-colors hover:border-neutral-700"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="mb-1 flex items-center gap-1.5">
                            <span className="inline-flex h-4.5 items-center rounded-full border border-neutral-700 bg-neutral-900/70 px-2 text-[9px] font-bold uppercase tracking-[0.11em] text-neutral-300">
                              {item.dimension || 'Category'}
                            </span>
                            <span className="text-[9px] font-semibold uppercase tracking-[0.1em] text-neutral-500">
                              #{index + 1}
                            </span>
                          </div>
                          <div className="truncate text-[15px] font-semibold text-white leading-tight">
                            {item.label || 'Unlabeled'}
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-[10px] uppercase tracking-[0.1em] text-neutral-500">Conversion</div>
                          <div className="text-lg font-black tabular-nums text-emerald-300 leading-tight">{formatPct(pct)}</div>
                        </div>
                      </div>

                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-800/70">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-500/90 via-emerald-400/90 to-teal-300/90"
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </button>
                  );
                });
              })()}
            </div>
          </div>

          <div className="rounded-[24px] border border-amber-700/30 bg-[#15120f] p-5 overflow-y-auto hide-scrollbar">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div className="text-sm font-bold uppercase tracking-[0.14em] text-amber-300">Alerts</div>
              <GraphInfoButton description="Alert cards flag noteworthy changes that may need action. Click an alert to jump to funnel analysis with the relevant breakdown pre-applied." />
            </div>
            <div className="space-y-3">
              {(data.alerts || []).map((alert) => (
                <button
                  key={alert.title}
                  onClick={() => onNavigate?.({ view: 'funnel', breakdown: 'channel', [alert.dimension]: alert.value })}
                  className="w-full rounded-xl border border-amber-800/30 bg-[#1b1713] px-4 py-3 text-left transition-colors hover:bg-[#231d17] hover:border-amber-700/40"
                >
                  <div className="text-sm font-semibold text-white">{alert.title}</div>
                  <div className="mt-1 text-xs text-neutral-300">{alert.subtitle}</div>
                </button>
              ))}
              {!data.alerts?.length && <div className="text-sm text-neutral-400">No active alerts in the current scope.</div>}
            </div>
          </div>
        </div>
      </section>
      <KpiDetailsModal kpi={selectedKpi} onClose={() => setSelectedKpi(null)} />
      {showKpiCreator && (
        <KPICreator
          onCreated={handleCustomKpiCreated}
          onClose={() => { setShowKpiCreator(false); setEditingKpi(null); }}
          initialData={editingKpi ? {
            name: editingKpi.name,
            description: editingKpi.description,
            mode: editingKpi.dsl_json?.type === 'formula' ? 'formula' : editingKpi.dsl_json?.type === 'single_metric' ? 'formula' : 'formula',
            expression: editingKpi.dsl_json?.formula || editingKpi.dsl_json?.metric || '',
            time_granularity: editingKpi.dsl_json?.time_granularity || 'month',
          } : null}
        />
      )}
    </div>
  );
}
