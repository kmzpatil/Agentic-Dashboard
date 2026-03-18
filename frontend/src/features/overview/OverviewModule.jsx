import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, PlaySquare, AlertCircle, Plus, X } from "lucide-react";
import { Line } from 'react-chartjs-2';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatHours, formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';
import { OverviewSkeleton } from '../../components/common/Skeleton';
import InsightCard from '../../components/insights/InsightCard';
import KpiDetailsModal from './KpiDetailsModal';
import { KPI_DEFINITIONS } from './kpiDefinitions';

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

  const sparklines = data?.sparklines || {};

  return (
    <div className="h-full overflow-y-auto bg-[#050505] px-6 py-6 space-y-6">
      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard 
          title="UPLOADED" 
          value={formatNumber(kpis.uploaded_count)} 
          subtitle={formatHours(kpis.uploaded_duration)} 
          trendData={[12, 18, 15, 22, 20, 28, 25]}
          onClick={() => handleCoreKpiClick('uploaded_count')}
        />
        <KpiCard 
          title="PROCESSED" 
          value={formatNumber(kpis.processed_count)} 
          subtitle="Videos reaching create stage" 
          trendData={[10, 14, 12, 19, 18, 24, 22]}
          onClick={() => handleCoreKpiClick('processed_count')}
        />
        <KpiCard 
          title="CREATED" 
          value={formatNumber(kpis.created_count)} 
          subtitle={formatHours(kpis.created_duration)} 
          trendData={[45, 52, 48, 60, 58, 65, 62]}
          onClick={() => handleCoreKpiClick('created_count')}
        />
        <KpiCard 
          title="PUBLISHED" 
          value={formatNumber(kpis.published_count)} 
          subtitle={formatHours(kpis.published_duration)} 
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
        
        <button 
          onClick={handleAddMore}
          className={`flex flex-col items-center justify-center rounded-xl p-5 border border-dashed transition-colors min-h-[140px] ${
            isSelectionPanelOpen 
              ? 'bg-[#161616] border-neutral-500 text-white' 
              : 'bg-[#111111] border-neutral-700 hover:border-neutral-500 hover:bg-[#161616] text-neutral-400 hover:text-white'
          }`}
        >
          <Plus size={24} className={`mb-2 transition-transform duration-300 ${isSelectionPanelOpen ? 'rotate-45' : ''}`} />
          <span className="text-sm font-bold uppercase tracking-wider">
            {isSelectionPanelOpen ? 'Close Selection' : 'Add More'}
          </span>
        </button>
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

      <section className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.95fr] gap-6">
        <div className="space-y-6">
          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">Frammer AI Insights</div>
            <div className="grid grid-cols-1 gap-4">
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
        </div>

        <div className="space-y-6">
          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">Top Performers</div>
            <div className="space-y-3">
              {(data.topPerformers || []).map((item) => (
                <div key={item.dimension} className="flex items-center justify-between rounded-2xl border border-neutral-900 bg-[#0C0C0C] px-4 py-3">
                  <div>
                    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500">{item.dimension}</div>
                    <div className="mt-1 text-sm font-semibold text-white">{item.label}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-black text-white">{formatPct(item.conversion)}</div>
                    <div className="text-xs text-neutral-500">publish conversion</div>
                  </div>
                </div>
              ))}
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
    </div>
  );
}
