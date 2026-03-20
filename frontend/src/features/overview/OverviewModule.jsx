import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, PlaySquare, AlertCircle, Plus, X, Wand2 } from "lucide-react";
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

export default function OverviewModule({ onNavigate }) {
  const overview = useApi(`${API_BASE}/overview`, []);
  const insights = useApi(`${API_BASE}/insights?surface=mission-control`, []);

  const loading = overview.loading;
  const error = overview.error || insights.error;
  const data = overview.data || {};
  const [activeExtraKpis, setActiveExtraKpis] = useState([]);
  const [stagedKpis, setStagedKpis] = useState([]);
  const [isSelectionPanelOpen, setIsSelectionPanelOpen] = useState(false);
  const [selectedKpi, setSelectedKpi] = useState(null);
  const [activeOutputTab, setActiveOutputTab] = useState(null);
  const [outputChartMetric, setOutputChartMetric] = useState('created');
  const [showKpiCreator, setShowKpiCreator] = useState(false);
  const [editingKpi, setEditingKpi] = useState(null);  // custom KPI being edited
  const [customKpis, setCustomKpis] = useState([]);  // KPIs created by user

  useEffect(() => {
    if (data?.outputStats?.length > 0 && !activeOutputTab) {
      setActiveOutputTab(data.outputStats[0].label);
    }
  }, [data?.outputStats, activeOutputTab]);

  if (loading) return <OverviewSkeleton />;
  if (error) return <div className="p-6 text-red-400">{error}</div>;

  const kpis = data.kpis || {};

  const handleAddMore = () => {
    setIsSelectionPanelOpen(!isSelectionPanelOpen);
  };

  const handleAddKpi = (id) => {
    if (!activeExtraKpis.includes(id) && !stagedKpis.includes(id)) {
      setStagedKpis([...stagedKpis, id]);
    }
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
    setActiveExtraKpis([...activeExtraKpis, ...stagedKpis]);
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

  const sparklines = data?.sparklines || {};

  return (
    <div className="h-full overflow-y-auto hide-scrollbar bg-[#050505] px-6 py-6 space-y-6">
      {/* KPI row: only the cards scroll, buttons stay fixed on the right */}
      <section className="flex gap-4 items-stretch">
        {/* Scrollable cards area */}
        <div className="flex-1 min-w-0 overflow-x-auto hide-scrollbar">
          <div className="flex gap-4 h-full">
            {[
              { title: 'UPLOADED', value: formatNumber(kpis.uploaded_count), subtitle: formatHours(kpis.uploaded_duration), trendData: [12, 18, 15, 22, 20, 28, 25], id: 'uploaded_count' },
              { title: 'PROCESSED', value: formatNumber(kpis.processed_count), subtitle: 'Videos reaching create stage', trendData: [10, 14, 12, 19, 18, 24, 22], id: 'processed_count' },
              { title: 'CREATED', value: formatNumber(kpis.created_count), subtitle: formatHours(kpis.created_duration), trendData: [45, 52, 48, 60, 58, 65, 62], id: 'created_count' },
              { title: 'PUBLISHED', value: formatNumber(kpis.published_count), subtitle: formatHours(kpis.published_duration), trendData: [20, 25, 22, 30, 28, 35, 32], id: 'published_count' },
            ].map(card => (
              <div key={card.id} className="flex-none min-h-[150px]" style={{ width: 'calc(25% - 12px)' }}>
                <KpiCard
                  title={card.title}
                  value={card.value}
                  subtitle={card.subtitle}
                  trendData={card.trendData}
                  onClick={() => handleCoreKpiClick(card.id)}
                />
              </div>
            ))}

            {visibleExtraKpis.map(kpi => (
              <div key={kpi.id} className="flex-none min-h-[150px]" style={{ width: 'calc(25% - 12px)' }}>
                <KpiCard
                  title={kpi.title}
                  value={kpi.getValue(kpis)}
                  subtitle={kpi.getSubtitle(kpis)}
                  trendData={kpi.trendData}
                  onRemove={() => handleRemoveKpi(kpi.id)}
                  onClick={() => setSelectedKpi(kpi)}
                />
              </div>
            ))}

            {customKpis.map(kpi => (
              <div key={kpi.id} className="flex-none min-h-[150px]" style={{ width: 'calc(25% - 12px)' }}>
                <KpiCard
                  title={kpi.title}
                  value={kpi.getValue(kpis)}
                  subtitle={kpi.getSubtitle(kpis)}
                  trendData={kpi.trendData}
                  onEdit={() => handleEditCustomKpi(kpi)}
                  onRemove={() => handleRemoveCustomKpi(kpi)}
                  onClick={() => handleCustomKpiClick(kpi)}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Fixed Add/Create buttons — never scrolls */}
        <div className="shrink-0 w-52 flex flex-col gap-2 min-h-[150px]">
          <button
            onClick={handleAddMore}
            className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-4 border border-dashed transition-colors ${
              isSelectionPanelOpen
                ? 'bg-[#161616] border-neutral-500 text-white'
                : 'bg-[#111111] border-neutral-700 hover:border-neutral-500 hover:bg-[#161616] text-neutral-400 hover:text-white'
            }`}
          >
            <Plus size={18} className={`transition-transform duration-300 ${isSelectionPanelOpen ? 'rotate-45' : ''}`} />
            <span className="text-sm font-bold uppercase tracking-wider">
              {isSelectionPanelOpen ? 'Close' : 'Add More'}
            </span>
          </button>
          <button
            onClick={() => setShowKpiCreator(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl px-4 border border-dashed border-purple-800/50 bg-purple-950/10 hover:bg-purple-950/20 hover:border-purple-600 text-purple-400 hover:text-purple-300 transition-colors"
          >
            <Wand2 size={18} />
            <span className="text-sm font-bold uppercase tracking-wider">Create KPI</span>
          </button>
        </div>
      </section>

      {/* Staging Panel */}
      {stagedKpis.length > 0 && (
        <section className="rounded-[28px] border-2 border-dashed border-primary-500/30 bg-primary-500/5 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-primary-400">
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
              className="flex flex-col items-center justify-center rounded-xl p-5 border-2 border-primary-500 bg-primary-500/10 hover:bg-primary-500/20 text-primary-400 hover:text-primary-300 transition-all font-black text-lg min-h-[140px]"
            >
              <Plus size={32} className="mb-2" />
              <span>ADD TO DASHBOARD</span>
            </button>
          </div>
        </section>
      )}

      {/* KPI Selection Panel */}
      {isSelectionPanelOpen && (
        <section className="rounded-[28px] border border-neutral-800 bg-[#0D0D0D] p-6 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">
              <Plus size={15} />
              Available KPIs
            </div>
            <button 
              onClick={() => setIsSelectionPanelOpen(false)}
              className="text-neutral-500 hover:text-white transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 max-h-[400px] overflow-y-auto pr-2 hide-scrollbar">
            {KPI_DEFINITIONS.filter(k => !['uploaded_count', 'processed_count', 'created_count', 'published_count'].includes(k.id) && !activeExtraKpis.includes(k.id)).map(kpi => {
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
          <section className="rounded-[28px] border border-neutral-800 bg-[#0D0D0D] p-5">
            <div className="mb-5 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">
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
                      className={`group text-left rounded-xl px-3 py-2.5 transition-all ${
                        isActive
                          ? 'bg-[#171717] border border-neutral-700'
                          : 'border border-transparent hover:bg-[#121212] hover:border-neutral-800'
                      }`}
                    >
                      <div className={`text-xs font-bold tracking-wide ${isActive ? 'text-white' : 'text-neutral-400 group-hover:text-neutral-200'}`}>
                        {stat.label}
                      </div>
                      <div className="mt-1.5 flex items-center gap-2">
                        <div className="flex-1 h-1 rounded-full bg-neutral-800 overflow-hidden">
                          <div className="h-full rounded-full bg-red-500/60 transition-all duration-500" style={{ width: `${barW}%` }} />
                        </div>
                        <span className="text-[10px] text-neutral-500 tabular-nums font-bold">{formatNumber(stat.total_created_count || 0)}</span>
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
                          className={`rounded-xl border bg-[#111] p-4 text-center transition-all ${
                            isActive ? `${s.ring} border-opacity-60` : 'border-neutral-800/60 hover:border-neutral-700'
                          }`}
                        >
                          <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500 mb-1.5">{s.label}</div>
                          <div className={`text-xl font-black ${s.color}`}>{formatNumber(s.count || 0)}</div>
                          <div className="text-[11px] text-neutral-500 mt-1">{formatHours(s.dur || 0)}</div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Time series chart */}
                  <div className="rounded-xl border border-neutral-800/60 bg-[#111] p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">
                        {cfg.label} — Monthly Trend
                      </div>
                      <div className="text-[10px] text-neutral-600">{activeStat.label}</div>
                    </div>
                    <div className="h-44">
                      {tsLabels.length > 0 ? (
                        <Line data={tsData} options={tsOpts} />
                      ) : (
                        <div className="flex items-center justify-center h-full text-xs text-neutral-600">No time series data</div>
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
        <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5 flex flex-col" style={{ height: '580px' }}>
          <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500 shrink-0">Frammer AI Insights</div>
          <div className="flex flex-col gap-3 flex-1 min-h-0 overflow-y-auto hide-scrollbar">
            {insights.loading && [...Array(5)].map((_, i) => (
              <div key={i} className="flex-1 rounded-2xl border border-neutral-800/60 bg-[#0C0C0C] border-l-[3px] border-l-neutral-700 px-4 py-3.5 flex flex-col justify-between">
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
              <div key={insight.id} className="flex-1 flex flex-col min-h-0">
                <InsightCard insight={insight} onNavigate={onNavigate} />
              </div>
            ))}
            {!insights.loading && !(insights.data?.insights || []).length && (
              <div className="rounded-3xl border border-dashed border-neutral-800 p-6 text-sm text-neutral-500">
                No major issues are active in the current scope.
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-6" style={{ height: '580px' }}>
          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">Top Performers</div>
            <div className="space-y-2">
              {(() => {
                const performers = data.topPerformers || [];
                const maxPct = Math.max(...performers.map(i => i.conversion || 0), 1);
                return performers.map((item) => {
                  const pct = item.conversion || 0;
                  return (
                    <div key={item.dimension} className="flex items-center gap-3 rounded-xl border border-neutral-900 bg-[#0C0C0C] px-4 py-3">
                      <div className="text-sm font-semibold text-white shrink-0 w-28 truncate">{item.label}</div>
                      <div className="flex-1 h-1.5 rounded-full bg-neutral-800 overflow-hidden">
                        <div className="h-full rounded-full bg-emerald-500/80" style={{ width: `${Math.min(pct, 100)}%` }} />
                      </div>
                      <div className="text-xs font-bold text-neutral-400 tabular-nums shrink-0">{formatPct(pct)}</div>
                    </div>
                  );
                });
              })()}
            </div>
          </div>

          <div className="rounded-[28px] border border-red-900/40 bg-[#120b0b] p-5 flex-1 overflow-y-auto hide-scrollbar">
            <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-red-300">Alerts</div>
            <div className="space-y-3">
              {(data.alerts || []).map((alert) => (
                <button
                  key={alert.title}
                  onClick={() => onNavigate?.({ view: 'funnel', breakdown: 'channel', [alert.dimension]: alert.value })}
                  className="w-full rounded-2xl border border-red-950/50 bg-[#190f0f] px-4 py-3 text-left transition-colors hover:bg-[#201313]"
                >
                  <div className="text-sm font-semibold text-white">{alert.title}</div>
                  <div className="mt-1 text-xs text-neutral-400">{alert.subtitle}</div>
                </button>
              ))}
              {!data.alerts?.length && <div className="text-sm text-neutral-500">No active alerts in the current scope.</div>}
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
