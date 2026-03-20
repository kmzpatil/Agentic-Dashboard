import React, { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement,
  Tooltip as ChartTooltip, Legend, Filler
} from 'chart.js';
import { Line, Bar, Pie, Scatter } from 'react-chartjs-2';
import { MatrixController, MatrixElement } from 'chartjs-chart-matrix';
import { TreemapController, TreemapElement } from 'chartjs-chart-treemap';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement,
  ChartTooltip, Legend, Filler,
  MatrixController, MatrixElement,
  TreemapController, TreemapElement
);

const ChartCard = ({ title, children }) => (
  <div className="rounded-2xl border border-neutral-800 bg-[#111111] p-5">
    <h4 className="mb-4 text-xs font-bold uppercase tracking-wider text-neutral-500">{title}</h4>
    <div className="h-64 w-full">
      {children}
    </div>
  </div>
);

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: '#888' } } },
  scales: {
    x: { grid: { color: '#222' }, ticks: { color: '#888' } },
    y: { grid: { color: '#222' }, ticks: { color: '#888' } }
  }
};

const hideX = { ...chartOptions, scales: { ...chartOptions.scales, x: { display: false } } };

export default function KpiDetailsModal({ kpi, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!kpi) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    const fetchData = async () => {
      try {
        const token = localStorage.getItem('frammer_auth_token');
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000/api';

        // Custom KPIs use the /api/kpi/:id endpoint; built-ins use /api/advanced-kpis/:id
        const url = kpi.isCustom
          ? `${baseUrl}/kpi/${kpi.kpi_db_id}`
          : `${baseUrl}/advanced-kpis/${kpi.id}`;

        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch KPI data');
        }

        const json = await response.json();

        if (isMounted) {
          // Merge API data with any local fallback structural keys from kpiDefinitions
          setData({ ...kpi.detailsData, ...json });
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
          // Fallback to mock data for layout purposes if API fails during dev
          setData(kpi.detailsData);
        }
      }
    };

    fetchData();

    return () => { isMounted = false; };
  }, [kpi]);

  if (!kpi) return null;

  const renderCharts = () => {
    // ── Custom KPI: time-series line + insights panel ───────────────────────
    if (kpi.isCustom) {
      const rawTimeSeries = data?.time_series || [];
      const granularity = data?.dsl_json?.time_granularity || 'month';

      // Limit data points to keep chart readable:
      // day → last 90 days, week → last 52 weeks, month → all
      const MAX_POINTS = { day: 90, week: 52, month: 999 };
      const maxPts = MAX_POINTS[granularity] ?? 60;
      const timeSeries = rawTimeSeries.length > maxPts
        ? rawTimeSeries.slice(-maxPts)
        : rawTimeSeries;

      // Thin x-axis labels when there are many points
      const labelStep = timeSeries.length > 60 ? Math.ceil(timeSeries.length / 20)
        : timeSeries.length > 30 ? 3 : 1;
      const labels = timeSeries.map((p, i) =>
        i % labelStep === 0 && p.period ? String(p.period).slice(0, 10) : ''
      );
      const values = timeSeries.map((p) => parseFloat(p.value) || 0);
      const insights = data?.insights || {};
      const trendColor =
        insights.trend === 'up' ? '#10b981' :
        insights.trend === 'down' ? '#ef4444' : '#3b82f6';

      // Build chart options — reduce dot clutter for dense daily series
      const kpiChartOptions = {
        ...chartOptions,
        plugins: {
          ...chartOptions.plugins,
          legend: { labels: { color: trendColor } },
        },
        elements: {
          point: { radius: timeSeries.length > 30 ? 0 : 3, hoverRadius: 4 },
        },
        scales: {
          ...chartOptions.scales,
          x: {
            ...chartOptions.scales.x,
            ticks: {
              color: '#888',
              maxRotation: 45,
              autoSkip: true,
              maxTicksLimit: 15,
            },
          },
          y: {
            ...chartOptions.scales.y,
            min: 0,
          },
        },
      };

      return (
        <>
          <ChartCard title={`${kpi.title} — Time Series (${granularity.toUpperCase()})`}>
            <Line
              data={{
                labels,
                datasets: [{
                  label: kpi.title,
                  data: values,
                  borderColor: trendColor,
                  backgroundColor: `${trendColor}20`,
                  fill: true,
                  tension: timeSeries.length > 30 ? 0.2 : 0.4,
                  pointRadius: 0,
                  pointHoverRadius: 4,
                }],
              }}
              options={kpiChartOptions}
            />
          </ChartCard>

          {/* Insights panel */}
          {insights.summary && (
            <div className="rounded-2xl border border-neutral-800 bg-[#111111] p-5 space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-500">Insights</h4>

              <p className="text-sm text-neutral-300 leading-relaxed">{insights.summary}</p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-xl bg-[#0d0d0d] border border-neutral-800 p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Trend</div>
                  <div className={`text-lg font-bold ${
                    insights.trend === 'up' ? 'text-emerald-400' :
                    insights.trend === 'down' ? 'text-red-400' : 'text-blue-400'
                  }`}>
                    {insights.trend === 'up' ? '↑ Up' : insights.trend === 'down' ? '↓ Down' : '→ Stable'}
                  </div>
                </div>

                <div className="rounded-xl bg-[#0d0d0d] border border-neutral-800 p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Change</div>
                  <div className={`text-lg font-bold ${
                    insights.percentage_change > 0 ? 'text-emerald-400' :
                    insights.percentage_change < 0 ? 'text-red-400' : 'text-neutral-300'
                  }`}>
                    {insights.percentage_change > 0 ? '+' : ''}{insights.percentage_change?.toFixed(1)}%
                  </div>
                </div>

                <div className="rounded-xl bg-[#0d0d0d] border border-neutral-800 p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Peak</div>
                  <div className="text-sm font-bold text-white">
                    {parseFloat(insights.max_point?.value || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-0.5">
                    {insights.max_point?.period?.slice(0, 10) || '—'}
                  </div>
                </div>

                <div className="rounded-xl bg-[#0d0d0d] border border-neutral-800 p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Low</div>
                  <div className="text-sm font-bold text-white">
                    {parseFloat(insights.min_point?.value || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-0.5">
                    {insights.min_point?.period?.slice(0, 10) || '—'}
                  </div>
                </div>
              </div>

              {/* DSL info */}
              {data?.dsl_json && (
                <div className="rounded-xl bg-[#0a0a0a] border border-neutral-800/50 p-3">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-600 mb-1">DSL Definition</div>
                  <pre className="text-[11px] text-neutral-500 font-mono overflow-auto max-h-20">
                    {JSON.stringify(data.dsl_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </>
      );
    }

    switch (kpi.id) {
      case 'publish_conversion':
      case 'processing_efficiency':
        return (
          <>
            <ChartCard title="Time Series (MoM)">
              <Line data={{ labels: data?.timeSeries?.labels || [], datasets: [{ label: 'Rate', data: data?.timeSeries?.data || [], borderColor: '#10b981', backgroundColor: '#10b98120', fill: true, tension: 0.4 }] }} options={chartOptions} />
            </ChartCard>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Top 20 Channels">
                <Bar data={{ labels: data?.channels?.labels || [], datasets: [{ label: 'Rate', data: data?.channels?.data || [], backgroundColor: '#3b82f6' }] }} options={hideX} />
              </ChartCard>
              <ChartCard title="Top 20 Users">
                <Bar data={{ labels: data?.users?.labels || [], datasets: [{ label: 'Rate', data: data?.users?.data || [], backgroundColor: '#8b5cf6' }] }} options={hideX} />
              </ChartCard>
              <ChartCard title="Top 5 Input Types">
                <Bar data={{ labels: data?.inputs?.labels || [], datasets: [{ label: 'Rate', data: data?.inputs?.data || [], backgroundColor: '#f59e0b' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Top 5 Output Types">
                <Bar data={{ labels: data?.outputs?.labels || [], datasets: [{ label: 'Rate', data: data?.outputs?.data || [], backgroundColor: '#ec4899' }] }} options={chartOptions} />
              </ChartCard>
            </div>
          </>
        );

      case 'month_by_month_use_rate':
        return (
          <>
            <ChartCard title="Time Series Growth Rate">
              <Line data={{ labels: data?.timeSeries?.labels || [], datasets: [{ label: 'Growth %', data: data?.timeSeries?.data || [], borderColor: '#3b82f6', tension: 0.4 }] }} options={chartOptions} />
            </ChartCard>
            <ChartCard title="Channel Upload Share (Treemap)">
              <Bar data={{
                datasets: [{
                  type: 'treemap',
                  tree: data?.channelTreemap || [],
                  key: 'value',
                  groups: ['name'],
                  backgroundColor: '#3b82f680',
                  labels: { display: true, color: 'white' }
                }]
              }} options={{ responsive: true, maintainAspectRatio: false }} />
            </ChartCard>
          </>
        );

      case 'creation_rate':
        return (
          <>
            <ChartCard title="Time Series Creation Rate">
              <Line data={{ labels: data?.timeSeries?.labels || [], datasets: [{ label: 'Clips / Upload', data: data?.timeSeries?.data || [], borderColor: '#10b981', tension: 0.4 }] }} options={chartOptions} />
            </ChartCard>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Top 7 Input Types">
                <Bar data={{ labels: data?.inputs?.labels || [], datasets: [{ label: 'Creation Rate', data: data?.inputs?.data || [], backgroundColor: '#f59e0b' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Top 20 Channels">
                <Bar data={{ labels: data?.channels?.labels || [], datasets: [{ label: 'Creation Rate', data: data?.channels?.data || [], backgroundColor: '#3b82f6' }] }} options={hideX} />
              </ChartCard>
            </div>
          </>
        );

      case 'waste_index':
        return (
          <>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Top 20 Users Waste Index">
                <Bar data={{ labels: data?.users?.labels || [], datasets: [{ label: 'Index', data: data?.users?.data || [], backgroundColor: '#ef4444' }] }} options={hideX} />
              </ChartCard>
              <ChartCard title="Top 20 Channels Waste Index">
                <Bar data={{ labels: data?.channels?.labels || [], datasets: [{ label: 'Index', data: data?.channels?.data || [], backgroundColor: '#ec4899' }] }} options={hideX} />
              </ChartCard>
            </div>
            <ChartCard title="Channel Total Raw Waste (Treemap)">
              <Bar data={{
                datasets: [{
                  type: 'treemap',
                  tree: data?.channelTreemap || [],
                  key: 'value',
                  groups: ['name'],
                  backgroundColor: '#ef444480',
                  labels: { display: true, color: 'white' }
                }]
              }} options={{ responsive: true, maintainAspectRatio: false }} />
            </ChartCard>
          </>
        );

      case 'upload_failure_rate':
        return (
          <>
            <ChartCard title="Time Series Failure Rate">
              <Line data={{ labels: data?.timeSeries?.labels || [], datasets: [{ label: 'Failure Rate', data: data?.timeSeries?.data || [], borderColor: '#ef4444', tension: 0.4 }] }} options={chartOptions} />
            </ChartCard>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Top 15 Channels">
                <Bar data={{ labels: data?.channels?.labels || [], datasets: [{ label: 'Failure Rate', data: data?.channels?.data || [], backgroundColor: '#3b82f6' }] }} options={hideX} />
              </ChartCard>
              <ChartCard title="Top 15 Users">
                <Bar data={{ labels: data?.users?.labels || [], datasets: [{ label: 'Failure Rate', data: data?.users?.data || [], backgroundColor: '#8b5cf6' }] }} options={hideX} />
              </ChartCard>
            </div>
          </>
        );

      case 'roi':
        return (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ChartCard title="Users ROI Matrix">
                <Scatter data={{ datasets: [{ label: 'Users', data: data?.users || [], backgroundColor: '#8b5cf680' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Channels ROI Matrix">
                <Scatter data={{ datasets: [{ label: 'Channels', data: data?.channels || [], backgroundColor: '#3b82f680' }] }} options={chartOptions} />
              </ChartCard>
            </div>
            <div className="text-sm text-neutral-500 mt-2 px-2">* X-axis: Resource Intensity, Y-axis: Selection Success</div>
          </>
        );

      case 'cdas':
        return (
          <div className="grid grid-cols-1 gap-4">
            <ChartCard title="CDAS by Input Type">
              <Bar data={{ labels: data?.inputs?.labels || [], datasets: [{ label: 'CDAS Score', data: data?.inputs?.data || [], backgroundColor: '#10b981' }] }} options={chartOptions} />
            </ChartCard>
            <ChartCard title="Avg Created vs Published Duration">
              <Bar data={{
                labels: data?.durations?.labels || [],
                datasets: [
                  { label: 'Avg Created', data: data?.durations?.datasets?.[0]?.data || [], backgroundColor: '#3b82f6' },
                  { label: 'Avg Published', data: data?.durations?.datasets?.[1]?.data || [], backgroundColor: '#10b981' }
                ]
              }} options={chartOptions} />
            </ChartCard>
          </div>
        );

      case 'interaction_lift':
      case 'multidimensional_waste': {
        const rawHeatmapData = data?.heatmap || [];
        const xLabels = [...new Set(rawHeatmapData.map(d => d.x).filter(Boolean))];
        const yLabels = [...new Set(rawHeatmapData.map(d => d.y).filter(Boolean))];

        // Ensure no cells are empty by filling missing intersections with v = 0
        const heatmapData = [];
        xLabels.forEach(x => {
          yLabels.forEach(y => {
            const existing = rawHeatmapData.find(d => d.x === x && d.y === y);
            heatmapData.push({ x, y, v: existing ? parseFloat(existing.v) : 0 });
          });
        });

        const minV = Math.min(...heatmapData.map(d => d.v));
        const maxV = Math.max(...heatmapData.map(d => d.v));

        return (
          <ChartCard title="Interaction Heatmap">
             <Bar data={{
                datasets: [{
                  label: 'Matrix',
                  data: heatmapData,
                  backgroundColor: (ctx) => {
                    const value = ctx.raw?.v;
                    if (value === undefined) return '#222';
                    
                    // Normalize value to 0.0 - 1.0 range
                    const range = maxV - minV;
                    let normalized = 0;
                    if (range > 0) {
                      normalized = (value - minV) / range;
                    }
                    
                    // Map 0 -> Red (0 hue), 1 -> Green (120 hue)
                    let hue = Math.round(normalized * 120);
                    
                    if (kpi.id === 'multidimensional_waste') {
                       // Reverse logic: High waste = Red (0 hue), Low waste = Green (120 hue)
                       hue = 120 - hue;
                    }
                    
                    return `hsl(${hue}, 80%, 45%)`;
                  },
                  width: (ctx) => ctx.chart.chartArea ? (ctx.chart.chartArea.right - ctx.chart.chartArea.left) / Math.max(xLabels.length, 1) - 2 : 0,
                  height: (ctx) => ctx.chart.chartArea ? (ctx.chart.chartArea.bottom - ctx.chart.chartArea.top) / Math.max(yLabels.length, 1) - 2 : 0,
                  type: 'matrix'
                }]
              }} options={{
                responsive: true, maintainAspectRatio: false,
                plugins: {
                  tooltip: {
                    callbacks: {
                      title: () => '',
                      label: (context) => {
                        const v = context.raw.v;
                        return `${context.raw.x} x ${context.raw.y}: ${v.toFixed(2)}`;
                      }
                    }
                  }
                },
                scales: {
                  x: { type: 'category', labels: xLabels, grid: { display: false } },
                  y: { type: 'category', labels: yLabels, grid: { display: false } }
                }
              }} />
          </ChartCard>
        );
      }

      case 'cross_dimension_entropy':
        return (
          <>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Top 20 Users Entropy">
                <Bar data={{ labels: data?.users?.labels || [], datasets: [{ label: 'Entropy', data: data?.users?.data || [], backgroundColor: '#8b5cf6' }] }} options={hideX} />
              </ChartCard>
              <ChartCard title="Share of Uploads (Highest User)">
                <Pie data={{ labels: data?.userHighestShare?.labels || [], datasets: [{ data: data?.userHighestShare?.data || [], backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ec4899'] }] }} options={{ ...chartOptions, scales: {} }} />
              </ChartCard>
              <ChartCard title="Teams Entropy">
                <Bar data={{ labels: data?.teams?.labels || [], datasets: [{ label: 'Entropy', data: data?.teams?.data || [], backgroundColor: '#f59e0b' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Share of Uploads (Highest Team)">
                <Pie data={{ labels: data?.teamHighestShare?.labels || [], datasets: [{ data: data?.teamHighestShare?.data || [], backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ec4899'] }] }} options={{ ...chartOptions, scales: {} }} />
              </ChartCard>
            </div>
          </>
        );

      case 'publish_dependency_index':
        return (
          <div className="grid grid-cols-1 gap-4">
            <ChartCard title="Cramér's V by Categorical Sector">
              <Bar data={{ labels: data?.sectors?.labels || [], datasets: [{ label: 'V Score', data: data?.sectors?.data || [], backgroundColor: '#3b82f6' }] }} options={chartOptions} />
            </ChartCard>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Conv. Rate by User Id">
                 <Bar data={{ labels: data?.categories?.userId?.labels || [], datasets: [{ label: 'Rate', data: data?.categories?.userId?.data || [], backgroundColor: '#8b5cf6' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Conv. Rate by Input Type">
                 <Bar data={{ labels: data?.categories?.inputType?.labels || [], datasets: [{ label: 'Rate', data: data?.categories?.inputType?.data || [], backgroundColor: '#f59e0b' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Conv. Rate by Output Type">
                 <Bar data={{ labels: data?.categories?.outputType?.labels || [], datasets: [{ label: 'Rate', data: data?.categories?.outputType?.data || [], backgroundColor: '#ec4899' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Conv. Rate by Language">
                 <Bar data={{ labels: data?.categories?.language?.labels || [], datasets: [{ label: 'Rate', data: data?.categories?.language?.data || [], backgroundColor: '#10b981' }] }} options={chartOptions} />
              </ChartCard>
            </div>
          </div>
        );

      case 'point_biserial':
        return (
          <div className="grid grid-cols-1 gap-4">
             <ChartCard title="Point Biserial Correlation">
              <Bar data={{ labels: data?.correlations?.labels || [], datasets: [{ label: 'Correlation', data: data?.correlations?.data || [], backgroundColor: '#3b82f6' }] }} options={chartOptions} />
            </ChartCard>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Avg Created by Success">
                <Bar data={{ labels: data?.createdDurations?.labels || [], datasets: [{ label: 'Created Duration', data: data?.createdDurations?.datasets?.[0]?.data || [], backgroundColor: '#f59e0b' }] }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Avg Uploaded by Success">
                <Bar data={{ labels: data?.uploadedDurations?.labels || [], datasets: [{ label: 'Uploaded Duration', data: data?.uploadedDurations?.datasets?.[0]?.data || [], backgroundColor: '#8b5cf6' }] }} options={chartOptions} />
              </ChartCard>
            </div>
          </div>
        );

      case 'ctas':
        return (
          <>
            <ChartCard title="Top 20 Channel Alignment Scores">
              <Bar data={{ labels: data?.channels?.labels || [], datasets: [{ label: 'Score', data: data?.channels?.data || [], backgroundColor: '#10b981' }] }} options={hideX} />
            </ChartCard>
            <div className="grid grid-cols-2 gap-4">
               <ChartCard title="Uploaded Share (Highest Align Channel)">
                <Pie data={{ labels: data?.userUploaded?.labels || [], datasets: [{ data: data?.userUploaded?.data || [], backgroundColor: ['#3b82f6', '#10b981', '#f59e0b'] }] }} options={{ ...chartOptions, scales: {} }} />
              </ChartCard>
              <ChartCard title="Published Share (Highest Align Channel)">
                <Pie data={{ labels: data?.userPublished?.labels || [], datasets: [{ data: data?.userPublished?.data || [], backgroundColor: ['#3b82f6', '#10b981', '#f59e0b'] }] }} options={{ ...chartOptions, scales: {} }} />
              </ChartCard>
            </div>
          </>
        );

      case 'rei':
        return (
          <div className="grid grid-cols-1 gap-4">
            <ChartCard title="Relative Efficiency (Top 20 Users)">
              <Bar data={{ labels: data?.users?.labels || [], datasets: [{ label: 'REI Score', data: data?.users?.data || [], backgroundColor: '#8b5cf6' }] }} options={hideX} />
            </ChartCard>
            <ChartCard title="User Conv vs Global Baseline (Highest REI User)">
              <Bar data={{
                labels: data?.doubleBar?.labels || [],
                datasets: [
                  { label: 'User Conversion', data: data?.doubleBar?.datasets?.[0]?.data || [], backgroundColor: '#10b981' },
                  { label: 'Global Baseline', data: data?.doubleBar?.datasets?.[1]?.data || [], backgroundColor: '#3b82f6' }
                ]
              }} options={chartOptions} />
            </ChartCard>
          </div>
        );

      case 'uploaded_count':
      case 'processed_count':
      case 'created_count':
      case 'published_count':
        return (
          <>
            <ChartCard title="Month Wise Count">
              <Bar data={{ 
                labels: data?.timeSeries?.labels || [], 
                datasets: [{ 
                  label: 'Count', 
                  data: data?.timeSeries?.data || [], 
                  backgroundColor: '#3b82f6'
                }] 
              }} options={chartOptions} />
            </ChartCard>
            <div className="grid grid-cols-3 gap-4">
              <ChartCard title="Input Type Breakdown">
                <Bar data={{ 
                  labels: data?.inputs?.labels || [], 
                  datasets: [{ label: 'Count', data: data?.inputs?.data || [], backgroundColor: '#f59e0b' }] 
                }} options={chartOptions} />
              </ChartCard>
              <ChartCard title="Top 20 Channels">
                <Bar data={{ 
                  labels: data?.channels?.labels || [], 
                  datasets: [{ label: 'Count', data: data?.channels?.data || [], backgroundColor: '#3b82f6' }] 
                }} options={hideX} />
              </ChartCard>
              <ChartCard title="Top 20 Users">
                <Bar data={{ 
                  labels: data?.users?.labels || [], 
                  datasets: [{ label: 'Count', data: data?.users?.data || [], backgroundColor: '#8b5cf6' }] 
                }} options={hideX} />
              </ChartCard>
            </div>
          </>
        );

      default:
        return <div className="text-neutral-500 py-10 text-center">Charts in development</div>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/80" onClick={onClose}>
      <div className="flex min-h-full items-start justify-center p-6 py-10">
      <div
        className="relative w-full max-w-5xl rounded-3xl border border-neutral-800 bg-[#0d0d0d] p-8 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute right-6 top-6 text-neutral-500 hover:text-white transition-colors z-10 bg-black/50 p-2 rounded-full backdrop-blur-md"
        >
          <X size={24} />
        </button>
        
        <div className="mb-8 border-b border-neutral-800 pb-6 pr-12">
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-500 mb-2">KPI Deep Dive</div>
          <h3 className="text-3xl font-black text-white tracking-tight leading-tight">{kpi.title}</h3>
          
          <div className="mt-6 flex flex-col gap-4">
            <div className="rounded-xl bg-[#141414] p-4 border border-neutral-800/50">
              <div className="text-xs font-bold uppercase tracking-wider text-neutral-500 mb-1">Definition</div>
              <p className="text-sm text-neutral-300 leading-relaxed">{kpi.definition}</p>
            </div>
            
            <div className="rounded-xl bg-blue-950/20 p-4 border border-blue-900/30">
              <div className="text-xs font-bold uppercase tracking-wider text-blue-400 mb-1">Formula Calculation</div>
              <code className="text-sm text-blue-200 font-mono break-all">{kpi.formula}</code>
            </div>

            <div className="rounded-xl bg-[#141414] p-4 border border-neutral-800/50">
              <div className="text-xs font-bold uppercase tracking-wider text-neutral-500 mb-1">Significance</div>
              <p className="text-sm text-neutral-300 leading-relaxed">{kpi.significance}</p>
            </div>
          </div>
        </div>
        
        <div className="space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-neutral-500">
              <Loader2 className="animate-spin mb-4" size={32} />
              <p>Aggregating Live Data...</p>
            </div>
          ) : error ? (
            <div className="text-center py-10">
              <p className="text-red-400 mb-2">Error loading live data: {error}</p>
              <p className="text-neutral-500 text-sm">Showing simulated visualization layout.</p>
              <div className="mt-6 text-left">{renderCharts()}</div>
            </div>
          ) : (
            renderCharts()
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
