import React, { useMemo, useState, useEffect } from 'react';
import { Activity, LineChart, BarChart2 } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';
import { UsageTrendsSkeleton, ChartSkeleton, Skeleton } from '../../components/common/Skeleton';

const MULTI_DIM_OPTIONS = [
  { value: 'none', label: 'None' },
  { value: 'output_type', label: 'Output Type' },
  { value: 'input_type_proportion', label: 'Input Type Proportion' },
  { value: 'volume_dynamics', label: 'Volume Dynamics' },
  { value: 'duration_dynamics', label: 'Duration Dynamics' },
  { value: 'success_scores', label: 'Success Scores' },
];

const MULTIDIM_COLORS = [
  '#38BDF8', '#F472B6', '#34D399', '#FBBF24', '#A78BFA',
  '#FB923C', '#60A5FA', '#F87171', '#4ADE80', '#E879F9',
];

const CLIENT_OPTIONAL_DIMS = new Set(['output_type', 'input_type_proportion']);

export default function UsageTrendsModule() {
  const [metric, setMetric] = useState('uploaded_count');
  const [granularity, setGranularity] = useState('day');
  const [showPrediction, setShowPrediction] = useState(false);
  const [predictionLength, setPredictionLength] = useState(7);
  const [multiDim, setMultiDim] = useState('none');
  const [clientFilter, setClientFilter] = useState('');

  // future_forecast → auto-enable prediction
  useEffect(() => {
    if (metric === 'future_forecast') setShowPrediction(true);
  }, [metric]);

  // Derive the actual pipeline metric key to query
  const resolvedMetric = metric === 'future_forecast' ? 'uploaded_count'
    : metric === 'turnaround_time' ? 'turnaround_time'
    : metric;

  // For turnaround_time we could use avg_days_to_publish from pipeline-metrics or client timeline.
  // We pull pipeline-metrics for the main chart because it includes turnaround_time from the resampler.
  const metricsUrl = `${API_BASE}/usage-trends/v1/pipeline-metrics?granularity=${encodeURIComponent(granularity)}`;
  const forecastUrl = showPrediction
    ? `${API_BASE}/usage-trends/v1/forecast/all-clients?metric=${encodeURIComponent(resolvedMetric === 'turnaround_time' ? 'uploaded_count' : resolvedMetric)}&granularity=${encodeURIComponent(granularity)}&prediction_length=${encodeURIComponent(predictionLength)}`
    : null;

  const { data, loading, error } = useApi(
    metricsUrl,
    [resolvedMetric, granularity],
  );

  const { data: forecastData, loading: forecastLoading, error: forecastError } = useApi(
    forecastUrl,
    [showPrediction, resolvedMetric, granularity, predictionLength],
  );

  const multiDimUrl = (multiDim !== 'none')
    ? `${API_BASE}/usage-trends/v1/multi-dim?analysis=${encodeURIComponent(multiDim)}&granularity=${encodeURIComponent(granularity)}${clientFilter ? `&client_name=${encodeURIComponent(clientFilter)}` : ''}`
    : null;
  // output_type / input_type_proportion can work without a client now, so no suppression needed

  const { data: multiDimData, loading: multiDimLoading, error: multiDimError } = useApi(
    multiDimUrl,
    [multiDim, granularity, clientFilter],
  );

  const rateMetrics = new Set(['publish_conversion_rate', 'creation_rate', 'processing_efficiency', 'waste_index']);

  const historySeries = useMemo(() => {
    const rows = Array.isArray(data?.data) ? data.data : [];
    const grouped = new Map();

    rows.forEach((row) => {
      const dateKey = String(row.Date || '').slice(0, 10);
      if (!dateKey) return;

      const value = Number(row?.[resolvedMetric] || 0);
      if (!grouped.has(dateKey)) {
        grouped.set(dateKey, { sum: 0, count: 0 });
      }
      const bucket = grouped.get(dateKey);
      bucket.sum += value;
      bucket.count += 1;
    });

    return Array.from(grouped.entries())
      .sort(([left], [right]) => new Date(left) - new Date(right))
      .map(([period, bucket]) => ({
        period,
        value: rateMetrics.has(resolvedMetric) ? (bucket.count ? bucket.sum / bucket.count : 0) : bucket.sum,
      }));
  }, [data, resolvedMetric]);

  const predictionSeries = useMemo(() => {
    if (!showPrediction || !forecastData?.clients) return [];

    const grouped = new Map();
    const forecastKey = `Forecast_${resolvedMetric === 'turnaround_time' ? 'uploaded_count' : resolvedMetric}`;

    Object.values(forecastData.clients).forEach((clientPayload) => {
      const rows = Array.isArray(clientPayload?.forecast) ? clientPayload.forecast : [];
      rows.forEach((row) => {
        const dateKey = String(row.Date || '').slice(0, 10);
        if (!dateKey) return;

        const value = Number(row?.[forecastKey] || 0);
        if (!grouped.has(dateKey)) {
          grouped.set(dateKey, { sum: 0, count: 0 });
        }
        const bucket = grouped.get(dateKey);
        bucket.sum += value;
        bucket.count += 1;
      });
    });

    return Array.from(grouped.entries())
      .sort(([left], [right]) => new Date(left) - new Date(right))
      .map(([period, bucket]) => ({
        period,
        value: rateMetrics.has(resolvedMetric) ? (bucket.count ? bucket.sum / bucket.count : 0) : bucket.sum,
      }));
  }, [forecastData, resolvedMetric, rateMetrics, showPrediction]);

  const summary = useMemo(() => {
    const latest = historySeries[historySeries.length - 1] || null;
    const previous = historySeries[historySeries.length - 2] || null;
    const deltaPct = latest && previous && previous.value !== 0
      ? ((latest.value - previous.value) / previous.value) * 100
      : null;

    return {
      latestValue: latest ? latest.value : 0,
      latestPeriod: latest ? latest.period : null,
      deltaVsPreviousPct: deltaPct,
    };
  }, [historySeries]);

  const chartData = useMemo(() => {
    const historyByDate = new Map(historySeries.map((point) => [point.period, Number(point.value || 0)]));
    const predictionByDate = new Map(predictionSeries.map((point) => [point.period, Number(point.value || 0)]));
    const labels = Array.from(new Set([...historyByDate.keys(), ...predictionByDate.keys()]))
      .sort((left, right) => new Date(left) - new Date(right));

    const datasets = [{
      label: metric,
      data: labels.map((label) => (historyByDate.has(label) ? historyByDate.get(label) : null)),
      borderColor: '#EF4444',
      backgroundColor: 'rgba(239, 68, 68, 0.15)',
      tension: 0.25,
      fill: true,
      pointRadius: 3,
    }];

    if (showPrediction) {
      datasets.push({
        label: `forecast_${metric}`,
        data: labels.map((label) => (predictionByDate.has(label) ? predictionByDate.get(label) : null)),
        borderColor: '#38BDF8',
        backgroundColor: 'rgba(56, 189, 248, 0.08)',
        tension: 0.25,
        fill: false,
        pointRadius: 2,
      });
    }

    return { labels, datasets };
  }, [historySeries, metric, predictionSeries, showPrediction]);

  const multiDimChartData = useMemo(() => {
    if (!multiDimData?.data || !multiDimData?.series_keys) return null;

    const labels = multiDimData.data.map((row) => String(row.Date || '').slice(0, 10)).sort();
    const dataByDate = {};
    multiDimData.data.forEach((row) => {
      dataByDate[String(row.Date || '').slice(0, 10)] = row;
    });

    const datasets = multiDimData.series_keys.map((key, idx) => ({
      label: multiDimData.labels?.[key] || key,
      data: labels.map((d) => Number(dataByDate[d]?.[key] || 0)),
      borderColor: MULTIDIM_COLORS[idx % MULTIDIM_COLORS.length],
      backgroundColor: `${MULTIDIM_COLORS[idx % MULTIDIM_COLORS.length]}22`,
      tension: 0.25,
      fill: false,
      pointRadius: 2,
    }));

    return { labels, datasets };
  }, [multiDimData]);

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
    'turnaround_time', 'future_forecast',
  ];

  const needsClientFilter = CLIENT_OPTIONAL_DIMS.has(multiDim);

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      {/* Controls */}
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
        <div>
          <label className="block text-xs text-neutral-500 mb-2">MULTI-DIMENSION</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={multiDim} onChange={(e) => setMultiDim(e.target.value)}>
            {MULTI_DIM_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        {needsClientFilter && (
          <div>
            <label className="block text-xs text-neutral-500 mb-2">CLIENT NAME <span className="text-neutral-600">(optional)</span></label>
            <input
              className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white placeholder-neutral-600 w-48"
              placeholder="e.g. Acme Corp"
              value={clientFilter}
              onChange={(e) => setClientFilter(e.target.value)}
            />
          </div>
        )}
        <label className="inline-flex items-center gap-3 text-sm text-neutral-300 select-none cursor-pointer">
          <span className="font-medium">Show prediction</span>
          <span className="relative inline-flex items-center">
            <input
              type="checkbox"
              className="peer sr-only"
              checked={showPrediction}
              onChange={(e) => setShowPrediction(e.target.checked)}
            />
            <span className="h-6 w-11 rounded-full border border-neutral-700 bg-[#0A0A0A] transition-all duration-300 peer-checked:bg-[#0EA5E9]/25 peer-checked:border-[#38BDF8] peer-focus-visible:ring-2 peer-focus-visible:ring-[#38BDF8]/50" />
            <span className="pointer-events-none absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-neutral-200 shadow-[0_0_0_1px_rgba(255,255,255,0.08)] transition-all duration-300 peer-checked:translate-x-5 peer-checked:bg-[#38BDF8] peer-checked:shadow-[0_0_14px_rgba(56,189,248,0.65)]" />
          </span>
        </label>
        {showPrediction && (
          <div>
            <label className="block text-xs text-neutral-500 mb-2">PREDICTION LENGTH</label>
            <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={predictionLength} onChange={(e) => setPredictionLength(Number(e.target.value))}>
              <option value={7}>7</option>
              <option value={30}>30</option>
              <option value={60}>60</option>
              <option value={90}>90</option>
            </select>
          </div>
        )}
      </div>

      {loading && <UsageTrendsSkeleton />}
      {error && <div className="text-red-400">{error}</div>}
      {showPrediction && forecastLoading && (
        <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-[200px] w-full rounded-lg" />
        </div>
      )}
      {showPrediction && forecastError && <div className="text-red-400">{forecastError}</div>}

      {!loading && !error && (!showPrediction || !forecastError) && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KpiCard title="LATEST VALUE" value={formatNumber(summary.latestValue)} subtitle={summary.latestPeriod || '-'} />
            <KpiCard title="DELTA VS PREVIOUS" value={summary.deltaVsPreviousPct === null ? '-' : `${summary.deltaVsPreviousPct.toFixed(2)}%`} subtitle="Sequential change" />
            <KpiCard title="POINTS" value={formatNumber(historySeries.length)} subtitle="Time buckets" />
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2"><LineChart size={16} /> TIME SERIES — {metric}</h3>
            <div className="h-[380px] w-full">
              <Line data={chartData} options={chartOptions} />
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Activity size={16} /> PREDICTION STATUS</h3>
            <div className="space-y-3 text-sm">
              {!showPrediction && <div className="text-neutral-500">Enable "Show prediction" to overlay forecast values.</div>}
              {showPrediction && forecastLoading && <Skeleton className="h-4 w-48" />}
              {showPrediction && !forecastLoading && !forecastError && (
                <div className="p-3 rounded border border-neutral-800 bg-[#0A0A0A] text-neutral-300">
                  Forecast loaded for {formatNumber(Object.keys(forecastData?.clients || {}).length)} clients with {predictionLength} future points.
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Multi-dimension chart */}
      {multiDim !== 'none' && (
        <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
          <h3 className="font-bold text-white mb-1 flex items-center gap-2">
            <BarChart2 size={16} /> MULTI-DIM — {MULTI_DIM_OPTIONS.find((o) => o.value === multiDim)?.label}
          </h3>
          {needsClientFilter && !clientFilter && (
            <div className="text-neutral-500 text-sm mb-3">Showing all clients. Enter a client name above to filter {MULTI_DIM_OPTIONS.find((o) => o.value === multiDim)?.label} data.</div>
          )}
          {multiDimLoading && <ChartSkeleton height={320} />}
          {multiDimError && <div className="text-red-400 text-sm">{multiDimError}</div>}
          {!multiDimLoading && !multiDimError && multiDimChartData && (
            <div className="h-[320px] w-full mt-2">
              <Line data={multiDimChartData} options={chartOptions} />
            </div>
          )}
          {!multiDimLoading && !multiDimError && !multiDimChartData && !needsClientFilter && (
            <div className="text-neutral-500 text-sm">No data available.</div>
          )}
        </div>
      )}
    </div>
  );
}
