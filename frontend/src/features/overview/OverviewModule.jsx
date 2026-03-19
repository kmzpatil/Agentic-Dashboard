import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, PlaySquare, AlertCircle, Plus, X, Wand2 } from "lucide-react";
import { Line } from 'react-chartjs-2';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatHours, formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';
import { OverviewSkeleton } from '../../components/common/Skeleton';
import InsightCard from '../../components/insights/InsightCard';
import KpiDetailsModal from './KpiDetailsModal';
import { KPI_DEFINITIONS } from './kpiDefinitions';
import KPICreator from '../../components/KPICreator';

export default function OverviewModule({ onNavigate }) {
  const overview = useApi(`${API_BASE}/overview`, []);
  const insights = useApi(`${API_BASE}/insights?surface=mission-control`, []);

  const loading = overview.loading || insights.loading;
  const error = overview.error || insights.error;
  const data = overview.data || {};
  const [activeExtraKpis, setActiveExtraKpis] = useState([]);
  const [stagedKpis, setStagedKpis] = useState([]);
  const [isSelectionPanelOpen, setIsSelectionPanelOpen] = useState(false);
  const [selectedKpi, setSelectedKpi] = useState(null);
  const [activeOutputTab, setActiveOutputTab] = useState(null);
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
    <div className="h-full overflow-y-auto bg-[#050505] px-6 py-6 space-y-6">
      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard
          title="UPLOADED"
          value={formatNumber(kpis.uploaded_count)}
          subtitle={formatHours(kpis.uploaded_duration)}
          description="Total raw video files uploaded into the pipeline"
          trendData={[12, 18, 15, 22, 20, 28, 25]}
          onClick={() => handleCoreKpiClick('uploaded_count')}
        />
        <KpiCard
          title="PROCESSED"
          value={formatNumber(kpis.processed_count)}
          subtitle="Videos reaching create stage"
          description="Videos that passed through initial processing and slicing"
          trendData={[10, 14, 12, 19, 18, 24, 22]}
          onClick={() => handleCoreKpiClick('processed_count')}
        />
        <KpiCard
          title="CREATED"
          value={formatNumber(kpis.created_count)}
          subtitle={formatHours(kpis.created_duration)}
          description="Individual clip assets generated from all source videos"
          trendData={[45, 52, 48, 60, 58, 65, 62]}
          onClick={() => handleCoreKpiClick('created_count')}
        />
        <KpiCard
          title="PUBLISHED"
          value={formatNumber(kpis.published_count)}
          subtitle={formatHours(kpis.published_duration)}
          description="Posts successfully published to one or more platforms"
          trendData={[20, 25, 22, 30, 28, 35, 32]}
          onClick={() => handleCoreKpiClick('published_count')}
        />
        
        {visibleExtraKpis.map(kpi => (
          <KpiCard
            key={kpi.id}
            title={kpi.title}
            value={kpi.getValue(kpis)}
            subtitle={kpi.getSubtitle(kpis)}
            trendData={kpi.trendData}
            onRemove={() => handleRemoveKpi(kpi.id)}
            onClick={() => setSelectedKpi(kpi)}
          />
        ))}

        {/* Custom KPI cards */}
        {customKpis.map(kpi => (
          <KpiCard
            key={kpi.id}
            title={kpi.title}
            value={kpi.getValue(kpis)}
            subtitle={kpi.getSubtitle(kpis)}
            trendData={kpi.trendData}
            onEdit={() => handleEditCustomKpi(kpi)}
            onRemove={() => handleRemoveCustomKpi(kpi)}
            onClick={() => handleCustomKpiClick(kpi)}
          />
        ))}

        {/* Add More + Create KPI — combined in one grid slot, stacked vertically */}
        <div className="flex flex-col gap-2 min-h-[140px]">
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

      {data?.outputStats && data.outputStats.length > 0 && (
        <section className="rounded-[28px] border border-neutral-800 bg-[#0D0D0D] p-5">
           <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">
              <TrendingUp size={15} />
              Output Types Summary
            </div>
          </div>
          <div className="flex border-b border-neutral-800 mb-6">
            {data.outputStats.map(stat => (
              <button
                key={stat.label}
                onClick={() => setActiveOutputTab(stat.label)}
                className={`px-4 py-2 font-medium tracking-wide transition-colors ${activeOutputTab === stat.label ? 'text-white border-b-2 border-primary-500' : 'text-neutral-500 hover:text-neutral-300'}`}
              >
                {stat.label}
              </button>
            ))}
          </div>
          
          {(() => {
            const activeStat = data?.outputStats?.find(s => s.label === activeOutputTab) || data?.outputStats?.[0];
            if (!activeStat) return null; // Prevent crash if data hasn't loaded or is completely empty
            
            return (
              <div className="grid grid-cols-3 gap-4">
                 <div className="rounded-2xl border border-neutral-900 bg-[#121212] p-4 text-center">
                    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500 mb-2">Uploaded</div>
                    <div className="text-2xl font-bold text-white mb-1">{formatNumber(activeStat?.total_uploaded_count || 0)}</div>
                    <div className="text-xs text-neutral-400">{formatHours(activeStat?.total_uploaded_duration || 0)}</div>
                 </div>
                 <div className="rounded-2xl border border-neutral-900 bg-[#121212] p-4 text-center">
                    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500 mb-2">Created</div>
                    <div className="text-2xl font-bold text-[#10b981] mb-1">{formatNumber(activeStat?.total_created_count || 0)}</div>
                    <div className="text-xs text-neutral-400">{formatHours(activeStat?.total_created_duration || 0)}</div>
                 </div>
                 <div className="rounded-2xl border border-neutral-900 bg-[#121212] p-4 text-center">
                    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500 mb-2">Published</div>
                    <div className="text-2xl font-bold text-[#3b82f6] mb-1">{formatNumber(activeStat?.total_published_count || 0)}</div>
                    <div className="text-xs text-neutral-400">{formatHours(activeStat?.total_published_duration || 0)}</div>
                 </div>
              </div>
            )
          })()}
        </section>
      )}

      <section className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.95fr] gap-6 xl:items-start">
        <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5 xl:max-h-[600px] flex flex-col">
          <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500 shrink-0">Frammer AI Insights</div>
          <div className="grid grid-cols-1 gap-3 overflow-y-auto pr-1 hide-scrollbar min-h-0">
            {(insights.data?.insights || []).map((insight) => (
              <InsightCard key={insight.id} insight={insight} onNavigate={onNavigate} />
            ))}
            {!insights.loading && !(insights.data?.insights || []).length && (
              <div className="rounded-3xl border border-dashed border-neutral-800 p-6 text-sm text-neutral-500">
                No major issues are active in the current scope.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6 xl:max-h-[600px]">
          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">Top Performers</div>
            <div className="space-y-2">
              {(data.topPerformers || []).map((item) => {
                const pct = Math.round((item.conversion || 0) * 100);
                return (
                  <div key={item.dimension} className="flex items-center gap-3 rounded-xl border border-neutral-900 bg-[#0C0C0C] px-4 py-3">
                    <div className="text-sm font-semibold text-white shrink-0 w-28 truncate">{item.label}</div>
                    <div className="flex-1 h-2 rounded-full bg-neutral-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="text-sm font-bold text-white shrink-0 w-12 text-right">{formatPct(item.conversion)}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-[28px] border border-red-900/40 bg-[#120b0b] p-5">
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
