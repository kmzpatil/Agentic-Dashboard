import React from 'react';
import { ArrowRight, TrendingUp } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatHours, formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';
import { OverviewSkeleton } from '../../components/common/Skeleton';
import InsightCard from '../../components/insights/InsightCard';

function PipelineStage({ stage }) {
  return (
    <div className="rounded-3xl border border-neutral-800 bg-[#101010] p-4 min-w-[180px]">
      <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-500">{stage.label}</div>
      <div className="mt-2 text-2xl font-black tracking-tight text-white">{formatNumber(stage.count)}</div>
      <div className="mt-1 text-sm text-neutral-500">{formatHours(stage.duration)}</div>
    </div>
  );
}

export default function OverviewModule({ onNavigate }) {
  const overview = useApi(`${API_BASE}/overview`, []);
  const insights = useApi(`${API_BASE}/insights?surface=mission-control`, []);

  if (overview.loading) return <OverviewSkeleton />;
  if (overview.error) return <div className="p-6 text-red-400">{overview.error}</div>;

  const data = overview.data || {};
  const kpis = data.kpis || {};

  return (
    <div className="h-full overflow-y-auto bg-[#050505] px-6 py-6 space-y-6">
      <section className="rounded-[30px] border border-neutral-800 bg-[radial-gradient(circle_at_top_left,_rgba(239,68,68,0.2),_transparent_50%),linear-gradient(180deg,#121212,_#080808)] p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="text-[11px] font-bold uppercase tracking-[0.24em] text-neutral-500">Mission Control</div>
            <h2 className="mt-2 text-3xl font-black tracking-tight text-white">One surface for pipeline health, routed insights, and next actions.</h2>
            <p className="mt-3 text-sm leading-6 text-neutral-400">
              The backend now owns the analytics contracts, and Frammer AI insights route directly into Trends, Funnel,
              Explorer, or Copilot without relying on disconnected agent-only flows.
            </p>
          </div>
          <button
            onClick={() => onNavigate?.({ view: 'copilot' })}
            className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-bold text-black transition-colors hover:bg-neutral-200"
          >
            Open Copilot
            <ArrowRight size={16} />
          </button>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <KpiCard title="UPLOADED" value={formatNumber(kpis.uploaded_count)} subtitle={formatHours(kpis.uploaded_duration)} />
        <KpiCard title="PROCESSED" value={formatNumber(kpis.processed_count)} subtitle="Videos reaching create stage" />
        <KpiCard title="CREATED" value={formatNumber(kpis.created_count)} subtitle={formatHours(kpis.created_duration)} />
        <KpiCard title="PUBLISHED" value={formatNumber(kpis.published_count)} subtitle={formatHours(kpis.published_duration)} />
        <KpiCard title="PUBLISH CONVERSION" value={formatPct(kpis.publish_conversion_rate)} subtitle={`Creation rate ${formatPct(kpis.creation_rate)}`} />
      </section>

      <section className="rounded-[28px] border border-neutral-800 bg-[#0D0D0D] p-5">
        <div className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">
          <TrendingUp size={15} />
          Pipeline Motion
        </div>
        <div className="flex gap-4 overflow-auto hide-scrollbar">
          {(data.pipeline || []).map((stage) => (
            <PipelineStage key={stage.id} stage={stage} />
          ))}
        </div>
      </section>

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
                  No routed insights fired yet for this surface.
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
                    <div className="text-xs text-neutral-500">conversion</div>
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
                  onClick={() => onNavigate?.({ view: 'funnel', breakdown: 'channel', dimension: alert.dimension, value: alert.value })}
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
    </div>
  );
}
