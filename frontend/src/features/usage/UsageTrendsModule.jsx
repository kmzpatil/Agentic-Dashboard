import React, { useMemo, useState } from 'react';
import { Activity, LineChart } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';

export default function UsageTrendsModule() {
  const [metric, setMetric] = useState('uploaded_count');
  const [granularity, setGranularity] = useState('month');

  const { data, loading, error } = useApi(
    `${API_BASE}/usage-trends?metric=${encodeURIComponent(metric)}&granularity=${encodeURIComponent(granularity)}`,
    [metric, granularity],
  );

  const chartData = useMemo(() => ({
    labels: (data?.series || []).map((point) => point.period?.slice(0, 10)),
    datasets: [{
      label: metric,
      data: (data?.series || []).map((point) => Number(point.value || 0)),
      borderColor: '#EF4444',
      backgroundColor: 'rgba(239, 68, 68, 0.15)',
      tension: 0.25,
      fill: true,
      pointRadius: 3,
    }],
  }), [data, metric]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { labels: { color: '#d1d5db' } } },
    scales: {
      x: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  }), []);

  const metricOptions = [
    'uploaded_count', 'created_count', 'published_count',
    'uploaded_duration', 'created_duration', 'published_duration',
    'publish_conversion_rate', 'creation_rate', 'processing_efficiency', 'waste_index',
  ];

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-neutral-500 mb-2">METRIC</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={metric} onChange={(e) => setMetric(e.target.value)}>
            {metricOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-neutral-500 mb-2">GRANULARITY</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={granularity} onChange={(e) => setGranularity(e.target.value)}>
            <option value="day">day</option>
            <option value="week">week</option>
            <option value="month">month</option>
            <option value="quarter">quarter</option>
          </select>
        </div>
      </div>

      {loading && <div className="text-neutral-400">Loading trends...</div>}
      {error && <div className="text-red-400">{error}</div>}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KpiCard title="LATEST VALUE" value={formatNumber(data?.summary?.latestValue)} subtitle={data?.summary?.latestPeriod || '-'} />
            <KpiCard title="DELTA VS PREVIOUS" value={data?.summary?.deltaVsPreviousPct === null ? '-' : `${data.summary.deltaVsPreviousPct}%`} subtitle="Sequential change" />
            <KpiCard title="POINTS" value={formatNumber(data?.series?.length || 0)} subtitle="Time buckets" />
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2"><LineChart size={16} /> TIME SERIES</h3>
            <div className="h-[380px] w-full">
              <Line data={chartData} options={chartOptions} />
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Activity size={16} /> HEURISTICS & ANOMALIES</h3>
            <div className="space-y-3 text-sm">
              {(data?.anomalies || []).length === 0 && <div className="text-neutral-500">No strong anomalies detected at current threshold.</div>}
              {(data?.anomalies || []).map((item) => (
                <div key={`${item.period}-${item.zScore}`} className="p-3 rounded border border-neutral-800 bg-[#0A0A0A]">
                  <div className="font-semibold text-white">{item.period?.slice(0, 10)}: {item.direction} ({item.severity})</div>
                  <div className="text-neutral-400">Value: {formatNumber(item.value)} | Z-score: {item.zScore}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
