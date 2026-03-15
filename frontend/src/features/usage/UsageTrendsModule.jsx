import React from 'react';
import { AlertTriangle, TrendingUp } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';
import { UsageTrendsSkeleton } from '../../components/common/Skeleton';
import ArtifactCanvas from '../../components/artifacts/ArtifactCanvas';
import InsightCard from '../../components/insights/InsightCard';

const METRIC_OPTIONS = [
  'uploaded_count',
  'created_count',
  'published_count',
  'uploaded_duration',
  'created_duration',
  'published_duration',
  'publish_conversion_rate',
  'creation_rate',
  'processing_efficiency',
  'waste_index',
];

function formatMetricValue(metric, value) {
  if (metric.includes('rate') || metric.includes('efficiency')) return formatPct(value);
  return formatNumber(value);
}

export default function UsageTrendsModule({ routeState, onNavigate }) {
  const metric = routeState.metric || 'uploaded_count';
  const granularity = routeState.granularity || 'month';

  const trends = useApi(`${API_BASE}/trends?metric=${encodeURIComponent(metric)}&granularity=${encodeURIComponent(granularity)}`, [metric, granularity]);
  const insights = useApi(`${API_BASE}/insights?surface=trends`, [metric, granularity]);

  if (trends.loading) {
    return (
      <div className="p-6">
        <UsageTrendsSkeleton />
      </div>
    );
  }

  if (trends.error) return <div className="p-6 text-red-400">{trends.error}</div>;

  const data = trends.data || {};
  const summary = data.summary || {};
  const latest = summary.latest?.value ?? 0;
  const previous = summary.previous?.value ?? 0;

  return (
    <div className="h-full overflow-y-auto bg-[#050505] px-6 py-6 space-y-6">
      <section className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-neutral-500">Metric</label>
            <select
              className="rounded-2xl border border-neutral-700 bg-[#0A0A0A] px-4 py-3 text-white"
              value={metric}
              onChange={(event) => onNavigate?.({ view: 'trends', metric: event.target.value, granularity })}
            >
              {METRIC_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-neutral-500">Granularity</label>
            <select
              className="rounded-2xl border border-neutral-700 bg-[#0A0A0A] px-4 py-3 text-white"
              value={granularity}
              onChange={(event) => onNavigate?.({ view: 'trends', metric, granularity: event.target.value })}
            >
              <option value="day">day</option>
              <option value="week">week</option>
              <option value="month">month</option>
              <option value="quarter">quarter</option>
            </select>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard title="LATEST" value={formatMetricValue(metric, latest)} subtitle={summary.latest?.period || 'No data'} />
        <KpiCard title="PREVIOUS" value={formatMetricValue(metric, previous)} subtitle={summary.previous?.period || 'No prior point'} />
        <KpiCard title="DELTA VS PRIOR" value={formatPct(summary.deltaPct || 0)} subtitle={data.metricLabel || metric} />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.95fr] gap-6">
        <div className="space-y-6">
          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">
              <TrendingUp size={15} />
              Typed Artifact Canvas
            </div>
            <ArtifactCanvas artifacts={data.artifacts || []} datasets={data.datasets || []} />
          </div>

          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">Routed Insights</div>
            <div className="grid grid-cols-1 gap-4">
              {(insights.data?.insights || []).map((insight) => (
                <InsightCard key={insight.id} insight={insight} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-[28px] border border-neutral-800 bg-[#101010] p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.2em] text-neutral-500">
              <AlertTriangle size={15} />
              Trend Anomalies
            </div>
            <div className="space-y-3">
              {(data.anomalies || []).map((anomaly) => (
                <div key={`${anomaly.period}-${anomaly.direction}`} className="rounded-2xl border border-neutral-900 bg-[#0C0C0C] p-4">
                  <div className="text-sm font-semibold text-white">
                    {anomaly.direction === 'drop' ? 'Drop' : 'Spike'} around {anomaly.period}
                  </div>
                  <div className="mt-1 text-sm text-neutral-400">
                    Value {formatMetricValue(metric, anomaly.value)} · z-score {anomaly.zScore}
                  </div>
                </div>
              ))}
              {!data.anomalies?.length && <div className="text-sm text-neutral-500">No significant anomalies detected in the selected series.</div>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
