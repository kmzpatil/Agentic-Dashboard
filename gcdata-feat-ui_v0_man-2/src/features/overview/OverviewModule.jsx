import React from 'react';
import { AlertTriangle, Lightbulb } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatHours, formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';

export default function OverviewModule() {
  const { data, loading, error } = useApi(`${API_BASE}/overview`, []);

  if (loading) return <div className="p-6 text-neutral-400">Loading overview...</div>;
  if (error) return <div className="p-6 text-red-400">{error}</div>;

  const kpis = data?.kpis || {};

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto relative pb-16 bg-[#050505]">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard title="UPLOADED" value={formatNumber(kpis.uploaded_count)} subtitle={formatHours(kpis.uploaded_duration)} />
        <KpiCard title="PROCESSED" value={formatNumber(kpis.processed_count)} subtitle="Videos that reached create stage" />
        <KpiCard title="CREATED" value={formatNumber(kpis.created_count)} subtitle={formatHours(kpis.created_duration)} />
        <KpiCard title="PUBLISHED" value={formatNumber(kpis.published_count)} subtitle={formatHours(kpis.published_duration)} />
        <KpiCard title="PUBLISH CONVERSION" value={formatPct(kpis.publish_conversion_rate)} subtitle={`Waste Index ${Number(kpis.waste_index || 0).toFixed(2)} sec`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#111111] rounded-xl border border-neutral-800 overflow-hidden">
          <div className="bg-[#161616] px-5 py-3 border-b border-neutral-800 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <h3 className="font-bold text-white tracking-tight">TOP PERFORMERS</h3>
          </div>
          <div className="p-5 space-y-3 text-sm">
            {(data?.topPerformers || []).map((item) => (
              <div key={item.dimension} className="flex items-center justify-between border-b border-neutral-800 pb-2">
                <span className="text-neutral-400">{item.dimension}</span>
                <span className="font-bold text-white">{item.label} ({formatPct(item.conversion)})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#111111] rounded-xl border border-red-900/50 overflow-hidden">
          <div className="bg-[#1A0A0A] px-5 py-3 border-b border-red-900/50 flex items-center gap-2">
            <AlertTriangle className="text-red-400" size={16} />
            <h3 className="font-bold text-red-400 tracking-tight">CRITICAL ALERTS</h3>
          </div>
          <div className="p-5 space-y-3">
            {(data?.alerts || []).map((alert) => (
              <div key={alert.title} className="p-3 bg-[#161616] border border-neutral-800 rounded-lg">
                <div className="font-bold text-white text-sm">{alert.title}</div>
                <div className="text-xs text-neutral-400 mt-1">{alert.subtitle}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-r from-[#1A0A0A] to-[#110A0A] rounded-xl border border-red-500/20 p-5 flex items-start gap-4">
        <div className="bg-red-500/10 p-2 rounded-full text-red-400"><Lightbulb size={24} /></div>
        <div>
          <h4 className="font-bold text-red-400 mb-1 tracking-tight">FRAMMER AI INSIGHT</h4>
          <p className="text-neutral-300 text-sm leading-relaxed">
            Upload-to-create rate is {formatPct(kpis.creation_rate)} while publish conversion is {formatPct(kpis.publish_conversion_rate)}.
            Use the enhanced Funnel to inspect where specific input types lose assets.
          </p>
        </div>
      </div>
    </div>
  );
}
