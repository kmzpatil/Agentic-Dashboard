import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  LayoutDashboard,
  Funnel,
  Microscope,
  Stethoscope,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Calendar,
  Building,
  Tv,
  User,
  Globe,
  Download,
  Upload,
  Tag,
  Sparkles,
  RefreshCcw,
  AlertTriangle,
  Lightbulb,
  Activity,
  Menu,
  Filter,
  Database,
  LineChart,
  Table,
  Layers,
  Search,
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Chart, Line, Bar, Pie } from 'react-chartjs-2';
import { SankeyController, Flow } from 'chartjs-chart-sankey';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  SankeyController,
  Flow,
);

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000/api';

const customStyles = `
  @keyframes flowRight {
    0% { transform: translateX(-10px); opacity: 0; }
    50% { opacity: 1; }
    100% { transform: translateX(20px); opacity: 0; }
  }
  .dot-flow { animation: flowRight 1.5s infinite linear; }
  .dot-flow:nth-child(1) { animation-delay: 0s; }
  .dot-flow:nth-child(2) { animation-delay: 0.5s; }
  .dot-flow:nth-child(3) { animation-delay: 1.0s; }

  @keyframes tickerFlow {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
  }
  .animate-ticker { animation: tickerFlow 30s linear infinite; }
  .hide-scrollbar::-webkit-scrollbar { display: none; }
`;

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return Number(value).toLocaleString();
};

const formatPct = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${Number(value).toFixed(2)}%`;
};

const formatHours = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return `${(Number(value) / 3600).toFixed(1)} hrs`;
};

const useApi = (url, dependencies = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(url));
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;

    if (!url) {
      setLoading(false);
      setError('');
      return () => {
        ignore = true;
      };
    }

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`);
        }
        const payload = await response.json();
        if (!ignore) {
          setData(payload);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || 'Failed to load');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      ignore = true;
    };
  }, dependencies);

  return { data, loading, error };
};

const PipelineStage = ({ title, count, hours, status }) => {
  const borderColors = {
    brand: 'border-red-500',
    warning: 'border-amber-500',
    neutral: 'border-neutral-700',
  };

  return (
    <div className={`flex flex-col items-center bg-[#111111] border-b-4 ${borderColors[status]} rounded-t-lg p-3 w-40 hover:bg-[#1A1A1A] transition-colors`}>
      <span className="text-xs font-bold tracking-wider text-neutral-400 mb-1">{title}</span>
      <span className="text-xl font-black tracking-tight">{count}</span>
      <span className="text-xs text-neutral-500">{hours}</span>
    </div>
  );
};

const FlowConnector = () => (
  <div className="flex items-center justify-center w-16 relative">
    <div className="h-0.5 w-full bg-neutral-800 absolute"></div>
    <div className="flex space-x-1 z-10">
      <div className="w-1.5 h-1.5 bg-red-500 rounded-full dot-flow"></div>
      <div className="w-1.5 h-1.5 bg-red-500 rounded-full dot-flow"></div>
      <div className="w-1.5 h-1.5 bg-red-500 rounded-full dot-flow"></div>
    </div>
  </div>
);

const PipelineRail = ({ overview }) => {
  const kpis = overview?.kpis;
  return (
    <div className="flex items-center justify-between w-full bg-[#050505] text-white p-4 overflow-x-auto hide-scrollbar border-b border-neutral-900">
      <div className="flex items-center space-x-2 min-w-max">
        <PipelineStage title="UPLOADED" count={formatNumber(kpis?.uploaded_count || 0)} hours={formatHours(kpis?.uploaded_duration || 0)} status="neutral" />
        <FlowConnector />
        <PipelineStage title="PROCESSED" count={formatNumber(kpis?.processed_count || 0)} hours={formatHours(kpis?.created_duration || 0)} status="brand" />
        <FlowConnector />
        <PipelineStage title="CREATED" count={formatNumber(kpis?.created_count || 0)} hours={formatHours(kpis?.created_duration || 0)} status="brand" />
        <FlowConnector />
        <PipelineStage title="PUBLISHED" count={formatNumber(kpis?.published_count || 0)} hours={formatHours(kpis?.published_duration || 0)} status="warning" />
      </div>
    </div>
  );
};

const FilterSelect = ({ icon, label, defaultValue = 'All' }) => (
  <div className="flex items-center justify-between text-sm">
    <span className="flex items-center gap-2 text-neutral-400">{icon} {label}</span>
    <select className="border-none bg-transparent text-white font-medium text-right outline-none cursor-pointer">
      <option>{defaultValue}</option>
    </select>
  </div>
);

const FilterDock = ({ isOpen, setIsOpen }) => (
  <div className={`bg-[#0A0A0A] border-r border-neutral-900 transition-all duration-300 flex flex-col h-full ${isOpen ? 'w-72' : 'w-16'}`}>
    <div className="p-4 border-b border-neutral-900 flex items-center justify-between">
      {isOpen && <span className="font-bold text-white flex items-center gap-2 tracking-tight"><Filter size={18} /> FILTERS</span>}
      <button onClick={() => setIsOpen(!isOpen)} className="p-1 hover:bg-[#1A1A1A] rounded text-neutral-400">
        {isOpen ? <ChevronLeft size={20} /> : <Menu size={20} />}
      </button>
    </div>

    <div className={`p-4 flex-1 overflow-y-auto space-y-6 ${!isOpen && 'hidden'}`}>
      <div className="space-y-3">
        <label className="text-xs font-bold tracking-wider text-neutral-500 flex items-center gap-2"><Calendar size={14} /> DATE RANGE</label>
        <select className="w-full text-sm border border-neutral-800 rounded-md p-2 bg-[#111111] text-white outline-none">
          <option>Mar 2025 - Mar 2026</option>
        </select>
      </div>

      <div className="border-t border-neutral-900 pt-4 space-y-3">
        <FilterSelect icon={<Building size={14} />} label="Company" />
        <FilterSelect icon={<Tv size={14} />} label="Channel" />
        <FilterSelect icon={<User size={14} />} label="User" />
        <FilterSelect icon={<Globe size={14} />} label="Language" />
        <FilterSelect icon={<Upload size={14} />} label="Input Type" />
        <FilterSelect icon={<Download size={14} />} label="Output Type" />
      </div>

      <div className="pt-4 flex gap-2">
        <button className="flex-1 bg-white text-black text-sm font-bold py-2 rounded-full hover:bg-neutral-200 flex items-center justify-center gap-2 transition-colors">
          <Sparkles size={14} /> Apply AI
        </button>
        <button className="flex-1 bg-[#1A1A1A] text-neutral-300 text-sm font-bold py-2 rounded-full hover:bg-[#2A2A2A] flex items-center justify-center gap-2 transition-colors">
          <RefreshCcw size={14} /> Reset
        </button>
      </div>
    </div>
  </div>
);

const KpiCard = ({ title, value, subtitle }) => (
  <div className="bg-[#111111] rounded-xl p-5 border border-neutral-800 hover:border-neutral-600 transition-colors">
    <div className="text-xs font-bold tracking-wider text-neutral-500 mb-1">{title}</div>
    <div className="text-3xl font-black text-white tracking-tight">{value}</div>
    <div className="text-sm text-neutral-400 mt-2">{subtitle}</div>
  </div>
);

const OverviewModule = () => {
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
};

const UsageTrendsModule = () => {
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
};

const FunnelModule = () => {
  const [breakdown, setBreakdown] = useState('channel');
  const [zoomFilter, setZoomFilter] = useState({ dimension: '', value: '' });
  const [selectedVideoId, setSelectedVideoId] = useState(null);

  const funnelQuery = `${API_BASE}/funnel?breakdown=${encodeURIComponent(breakdown)}${zoomFilter.dimension ? `&dimension=${encodeURIComponent(zoomFilter.dimension)}&value=${encodeURIComponent(zoomFilter.value)}` : ''}`;
  const { data, loading, error } = useApi(funnelQuery, [breakdown, zoomFilter.dimension, zoomFilter.value]);
  const videoDetails = useApi(selectedVideoId ? `${API_BASE}/funnel/video/${selectedVideoId}` : null, [selectedVideoId]);

  const stageSankeyData = useMemo(() => ({
    datasets: [{
      data: data?.sankeyLinks || [],
      colorFrom: '#6b7280',
      colorTo: '#ef4444',
      colorMode: 'gradient',
      borderWidth: 1,
    }],
  }), [data]);

  const compositionSankeyData = useMemo(() => ({
    datasets: [{
      data: data?.compositionLinks || [],
      colorFrom: '#60a5fa',
      colorTo: '#ef4444',
      colorMode: 'gradient',
      borderWidth: 0.5,
    }],
  }), [data]);

  const handleCompositionClick = (_event, elements) => {
    if (!elements?.length || !data?.compositionLinks?.length) return;
    const link = data.compositionLinks[elements[0].index];
    if (!link) return;

    if (link.to.startsWith('Input: ')) {
      setZoomFilter({ dimension: 'input_type', value: link.to.replace('Input: ', '') });
    } else if (link.to.startsWith('Output: ')) {
      setZoomFilter({ dimension: 'output_type', value: link.to.replace('Output: ', '') });
    }
  };

  const sankeyOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
  };

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-neutral-500 mb-2">BREAKDOWN</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={breakdown} onChange={(e) => setBreakdown(e.target.value)}>
            <option value="channel">channel</option>
            <option value="input_type">input_type</option>
            <option value="language">language</option>
            <option value="output_type">output_type</option>
          </select>
        </div>
        <button onClick={() => setZoomFilter({ dimension: '', value: '' })} className="px-4 py-2 rounded-full bg-[#1A1A1A] text-neutral-200 text-sm hover:bg-[#2A2A2A]">Reset zoom</button>
        {zoomFilter.dimension && <div className="text-sm text-neutral-400">Zoomed: {zoomFilter.dimension} = <span className="text-white font-semibold">{zoomFilter.value}</span></div>}
      </div>

      {loading && <div className="text-neutral-400">Loading funnel...</div>}
      {error && <div className="text-red-400">{error}</div>}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <KpiCard title="UPLOADED" value={formatNumber(data?.stageCounts?.uploaded_count)} subtitle="Raw videos" />
            <KpiCard title="PROCESSED" value={formatNumber(data?.stageCounts?.processed_count)} subtitle="Reached creation" />
            <KpiCard title="CREATED" value={formatNumber(data?.stageCounts?.created_count)} subtitle="Assets generated" />
            <KpiCard title="PUBLISHED" value={formatNumber(data?.stageCounts?.published_count)} subtitle="Published posts" />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
              <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Layers size={16} /> STAGE FLOW</h3>
              <div className="h-[300px]">
                <Chart type="sankey" data={stageSankeyData} options={sankeyOptions} />
              </div>
            </div>
            <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
              <h3 className="font-bold text-white mb-1 flex items-center gap-2"><Layers size={16} /> INPUT → OUTPUT → PUBLISH FLOW</h3>
              <p className="text-xs text-neutral-500 mb-3">Click a flow link to zoom into an input type or output type journey.</p>
              <div className="h-[300px]">
                <Chart type="sankey" data={compositionSankeyData} options={{ ...sankeyOptions, onClick: handleCompositionClick }} />
              </div>
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4">Top-down breakdown ({breakdown})</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-neutral-500 border-b border-neutral-800">
                    <th className="text-left py-2">Label</th>
                    <th className="text-right py-2">Uploaded</th>
                    <th className="text-right py-2">Created</th>
                    <th className="text-right py-2">Published</th>
                    <th className="text-right py-2">Conversion</th>
                    <th className="text-right py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.breakdown || []).map((row) => (
                    <tr key={row.label} className="border-b border-neutral-900">
                      <td className="py-2 text-white">{row.label || '(unknown)'}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.uploaded_count)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.created_count)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.published_count)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatPct(row.conversion)}</td>
                      <td className="py-2 text-right">
                        <button className="px-3 py-1 rounded-full text-xs bg-[#1A1A1A] text-neutral-200 hover:bg-[#2A2A2A]" onClick={() => setZoomFilter({ dimension: breakdown, value: row.label })}>zoom</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4">Raw Video Journey Inspector</h3>
            <div className="overflow-auto max-h-[320px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-[#0A0A0A]">
                  <tr className="text-neutral-500 border-b border-neutral-800">
                    <th className="text-left py-2">Video ID</th>
                    <th className="text-left py-2">Input</th>
                    <th className="text-left py-2">Language</th>
                    <th className="text-right py-2">Created</th>
                    <th className="text-right py-2">Published</th>
                    <th className="text-right py-2">Conv</th>
                    <th className="text-left py-2">Output mix</th>
                    <th className="text-right py-2">Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.journeyVideos || []).slice(0, 40).map((row) => (
                    <tr key={row.video_id} className="border-b border-neutral-900">
                      <td className="py-2 text-white">{row.video_id}</td>
                      <td className="py-2 text-neutral-300">{row.input_type || '-'}</td>
                      <td className="py-2 text-neutral-300">{row.language || '-'}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.created_assets)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.published_posts)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatPct(row.conversion)}</td>
                      <td className="py-2 text-neutral-400 text-xs">{(row.output_mix || []).join(' | ') || '-'}</td>
                      <td className="py-2 text-right">
                        <button className="px-3 py-1 rounded-full text-xs bg-[#1A1A1A] text-neutral-200 hover:bg-[#2A2A2A]" onClick={() => setSelectedVideoId(row.video_id)}>view</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {selectedVideoId && (
            <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-white">Video {selectedVideoId} detailed asset journey</h3>
                <button className="text-xs px-3 py-1 rounded-full bg-[#1A1A1A] hover:bg-[#2A2A2A]" onClick={() => setSelectedVideoId(null)}>Close</button>
              </div>
              {videoDetails.loading && <div className="text-neutral-400">Loading video details...</div>}
              {videoDetails.error && <div className="text-red-400">{videoDetails.error}</div>}
              {videoDetails.data && (
                <div className="space-y-3 text-sm">
                  <div className="text-neutral-300">{videoDetails.data.video.headline || '(no headline)'}</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Input: {videoDetails.data.video.input_type || '-'}</div>
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Language: {videoDetails.data.video.language || '-'}</div>
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Channels: {(videoDetails.data.video.channels || []).join(', ') || '-'}</div>
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Uploaded duration: {formatNumber(videoDetails.data.video.uploaded_duration)}</div>
                  </div>
                  <div className="overflow-auto max-h-[280px]">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-[#0A0A0A]">
                        <tr>
                          <th className="text-left py-2">Asset</th>
                          <th className="text-left py-2">Output</th>
                          <th className="text-right py-2">Created Dur</th>
                          <th className="text-left py-2">Post</th>
                          <th className="text-left py-2">Platforms</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(videoDetails.data.assets || []).map((a) => (
                          <tr key={a.asset_id} className="border-b border-neutral-900">
                            <td className="py-2">{a.asset_id}</td>
                            <td className="py-2">{a.output_type || '-'}</td>
                            <td className="py-2 text-right">{formatNumber(a.created_duration)}</td>
                            <td className="py-2">{a.post_id || '-'}</td>
                            <td className="py-2">{(a.platforms || []).join(', ') || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

const ExplorerModule = () => {
  const { data: tableData } = useApi(`${API_BASE}/explorer/tables`, []);
  const { data: dimsData } = useApi(`${API_BASE}/explorer/dimensions`, []);

  const [tableName, setTableName] = useState('');
  const [chartType, setChartType] = useState('bar');
  const [xColumn, setXColumn] = useState('');
  const [aggregation, setAggregation] = useState('count');
  const [yColumn, setYColumn] = useState('');

  const [dim1, setDim1] = useState('channel');
  const [dim2, setDim2] = useState('language');
  const [measure, setMeasure] = useState('uploaded_videos');
  const [timeGrain, setTimeGrain] = useState('none');
  const [dateField, setDateField] = useState('upload_date');
  const [dim1Value, setDim1Value] = useState('');

  useEffect(() => {
    if (!tableName && tableData?.tables?.length) setTableName(tableData.tables[0]);
  }, [tableData, tableName]);

  const tableUrl = tableName ? `${API_BASE}/explorer/table/${encodeURIComponent(tableName)}?limit=120` : null;
  const { data: rowsData, loading: rowsLoading, error: rowsError } = useApi(tableUrl, [tableUrl]);

  useEffect(() => {
    if (rowsData?.columns?.length) {
      if (!xColumn) setXColumn(rowsData.columns[0]);
      if (!yColumn) setYColumn(rowsData.columns[0]);
    }
  }, [rowsData, xColumn, yColumn]);

  const chartQuery = tableName && xColumn
    ? `${API_BASE}/explorer/chart?table=${encodeURIComponent(tableName)}&x=${encodeURIComponent(xColumn)}&aggregation=${encodeURIComponent(aggregation)}${aggregation === 'sum' ? `&y=${encodeURIComponent(yColumn)}` : ''}`
    : null;
  const { data: chartRows } = useApi(chartQuery, [chartQuery]);

  const multiQuery = `${API_BASE}/explorer/multidim?dim1=${encodeURIComponent(dim1)}&dim2=${encodeURIComponent(dim2)}&measure=${encodeURIComponent(measure)}&timeGrain=${encodeURIComponent(timeGrain)}&dateField=${encodeURIComponent(dateField)}${dim1Value ? `&dim1Value=${encodeURIComponent(dim1Value)}` : ''}`;
  const multi = useApi(multiQuery, [dim1, dim2, measure, timeGrain, dateField, dim1Value]);

  const tableChartData = useMemo(() => {
    const labels = (chartRows?.rows || []).map((row) => row.label || '(null)');
    const values = (chartRows?.rows || []).map((row) => Number(row.value || 0));
    return {
      labels,
      datasets: [{
        label: `${aggregation}(${aggregation === 'sum' ? yColumn : '*'}) by ${xColumn}`,
        data: values,
        backgroundColor: labels.map((_l, idx) => (idx % 2 === 0 ? 'rgba(239,68,68,0.65)' : 'rgba(96,165,250,0.65)')),
        borderColor: 'rgba(239,68,68,1)',
        borderWidth: 1,
      }],
    };
  }, [chartRows, aggregation, xColumn, yColumn]);

  const ChartComponent = chartType === 'pie' ? Pie : chartType === 'line' ? Line : Bar;

  const matrixChartData = useMemo(() => {
    const rows = multi.data?.matrixRows || [];
    const dim1Vals = [...new Set(rows.map((r) => r.dim1))].slice(0, 12);
    const dim2Vals = [...new Set(rows.map((r) => r.dim2))].slice(0, 8);

    const lookup = new Map(rows.map((r) => [`${r.dim1}|||${r.dim2}`, Number(r.value || 0)]));

    return {
      labels: dim1Vals,
      datasets: dim2Vals.map((d2, idx) => ({
        label: d2,
        data: dim1Vals.map((d1) => lookup.get(`${d1}|||${d2}`) || 0),
        backgroundColor: `hsla(${(idx * 47) % 360}, 70%, 55%, 0.6)`,
        borderColor: `hsla(${(idx * 47) % 360}, 70%, 55%, 1)`,
        borderWidth: 1,
      })),
    };
  }, [multi.data]);

  const timeSeriesChartData = useMemo(() => {
    const rows = multi.data?.timeSeriesRows || [];
    const periods = [...new Set(rows.map((r) => String(r.period).slice(0, 10)))];
    const dim2Vals = [...new Set(rows.map((r) => r.dim2))].slice(0, 10);

    const lookup = new Map(rows.map((r) => [`${String(r.period).slice(0, 10)}|||${r.dim2}`, Number(r.value || 0)]));

    return {
      labels: periods,
      datasets: dim2Vals.map((d2, idx) => ({
        label: d2,
        data: periods.map((p) => lookup.get(`${p}|||${d2}`) || 0),
        backgroundColor: `hsla(${(idx * 47) % 360}, 70%, 55%, 0.55)`,
        borderColor: `hsla(${(idx * 47) % 360}, 70%, 55%, 1)`,
        borderWidth: 1,
        stack: 'stacked',
      })),
    };
  }, [multi.data]);

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
        <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Database size={16} /> MULTI-DIMENSION ANALYSIS</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-4">
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dim1} onChange={(e) => setDim1(e.target.value)}>
            {(dimsData?.dimensions || []).map((d) => <option key={`d1-${d.key}`} value={d.key}>Dim1: {d.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dim2} onChange={(e) => setDim2(e.target.value)}>
            {(dimsData?.dimensions || []).map((d) => <option key={`d2-${d.key}`} value={d.key}>Dim2: {d.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={measure} onChange={(e) => setMeasure(e.target.value)}>
            {(dimsData?.measures || []).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={timeGrain} onChange={(e) => setTimeGrain(e.target.value)}>
            <option value="none">No time split</option>
            <option value="day">By day</option>
            <option value="week">By week</option>
            <option value="month">By month</option>
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dateField} onChange={(e) => setDateField(e.target.value)}>
            {(dimsData?.dateFields || []).map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dim1Value} onChange={(e) => setDim1Value(e.target.value)}>
            <option value="">All {dim1}</option>
            {(multi.data?.dim1Values || []).slice(0, 80).map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>

        {multi.loading && <div className="text-neutral-400">Loading multidim data...</div>}
        {multi.error && <div className="text-red-400">{multi.error}</div>}

        {!multi.loading && !multi.error && (
          <>
            <div className="h-[360px] mb-4">
              {timeGrain === 'none'
                ? <Bar data={matrixChartData} options={{ responsive: true, maintainAspectRatio: false }} />
                : <Bar data={timeSeriesChartData} options={{ responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } } }} />}
            </div>

            <div className="overflow-auto max-h-[300px]">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-[#0A0A0A]">
                  <tr>
                    <th className="text-left px-2 py-2 text-neutral-400">{dim1}</th>
                    <th className="text-left px-2 py-2 text-neutral-400">{dim2}</th>
                    <th className="text-right px-2 py-2 text-neutral-400">value</th>
                  </tr>
                </thead>
                <tbody>
                  {(multi.data?.matrixRows || []).slice(0, 200).map((r, idx) => (
                    <tr key={`${r.dim1}-${r.dim2}-${idx}`} className="border-b border-neutral-900">
                      <td className="px-2 py-2 text-neutral-200">{r.dim1}</td>
                      <td className="px-2 py-2 text-neutral-200">{r.dim2}</td>
                      <td className="px-2 py-2 text-right text-neutral-200">{formatNumber(r.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-neutral-500 mb-2">TABLE</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={tableName} onChange={(e) => setTableName(e.target.value)}>
            {(tableData?.tables || []).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-neutral-500 mb-2">X COLUMN</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={xColumn} onChange={(e) => setXColumn(e.target.value)}>
            {(rowsData?.columns || []).map((col) => <option key={col} value={col}>{col}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-neutral-500 mb-2">AGGREGATION</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={aggregation} onChange={(e) => setAggregation(e.target.value)}>
            <option value="count">count</option>
            <option value="sum">sum</option>
          </select>
        </div>
        {aggregation === 'sum' && (
          <div>
            <label className="block text-xs text-neutral-500 mb-2">Y COLUMN</label>
            <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={yColumn} onChange={(e) => setYColumn(e.target.value)}>
              {(rowsData?.columns || []).map((col) => <option key={col} value={col}>{col}</option>)}
            </select>
          </div>
        )}
        <div>
          <label className="block text-xs text-neutral-500 mb-2">CHART TYPE</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={chartType} onChange={(e) => setChartType(e.target.value)}>
            <option value="bar">bar</option>
            <option value="line">line</option>
            <option value="pie">pie</option>
          </select>
        </div>
      </div>

      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
        <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Database size={16} /> TABLE CHART BUILDER</h3>
        <div className="h-[340px]">
          <ChartComponent data={tableChartData} options={{ responsive: true, maintainAspectRatio: false }} />
        </div>
      </div>

      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
        <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Table size={16} /> TABLE DATA ({tableName || '-'})</h3>
        {rowsLoading && <div className="text-neutral-400">Loading table...</div>}
        {rowsError && <div className="text-red-400">{rowsError}</div>}
        {!rowsLoading && !rowsError && (
          <div className="overflow-auto max-h-[420px]">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-[#0A0A0A]">
                <tr>
                  {(rowsData?.columns || []).map((col) => <th key={col} className="text-left px-3 py-2 text-neutral-400 border-b border-neutral-800">{col}</th>)}
                </tr>
              </thead>
              <tbody>
                {(rowsData?.rows || []).map((row, idx) => (
                  <tr key={`${tableName}-${idx}`} className="border-b border-neutral-900 hover:bg-[#0A0A0A]">
                    {(rowsData?.columns || []).map((col) => <td key={`${idx}-${col}`} className="px-3 py-2 text-neutral-200 whitespace-nowrap">{String(row[col] ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const ComingSoonModule = ({ title }) => (
  <div className="flex flex-col items-center justify-center h-full text-neutral-600 gap-2">
    <Stethoscope className="opacity-40" size={26} />
    <h2 className="text-xl font-bold text-neutral-400">{title}</h2>
    <p className="text-sm">Not part of this build scope.</p>
  </div>
);

const App = () => {
  const [activeTab, setActiveTab] = useState('Overview');
  const [isFilterOpen, setIsFilterOpen] = useState(true);
  const [isAiOpen, setIsAiOpen] = useState(false);

  const overview = useApi(`${API_BASE}/overview`, []);

  const navItems = [
    { id: 'Overview', icon: <LayoutDashboard size={16} /> },
    { id: 'Usage & Trends', icon: <BarChart3 size={16} /> },
    { id: 'Funnel', icon: <Funnel size={16} /> },
    { id: 'Explorer', icon: <Microscope size={16} /> },
    { id: 'Data Health', icon: <Stethoscope size={16} />, disabled: true },
  ];

  return (
    <div className="h-screen w-full bg-[#0A0A0A] flex flex-col font-sans overflow-hidden text-white">
      <style>{customStyles}</style>
      <div className="flex items-center px-6 py-4 bg-[#050505] border-b border-neutral-900">
        <h1 className="text-red-500 font-black text-2xl tracking-tighter">FRAMMER AI</h1>
        <div className="ml-4 text-xs font-bold tracking-widest text-neutral-600 uppercase mt-1">Nerve Center</div>
      </div>

      <PipelineRail overview={overview.data} />

      <div className="bg-[#0A0A0A] border-b border-neutral-900 px-4 py-3 flex items-center justify-between z-10">
        <div className="flex space-x-2 overflow-auto hide-scrollbar">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => !item.disabled && setActiveTab(item.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold transition-colors ${
                activeTab === item.id ? 'bg-[#1A1A1A] text-white' : item.disabled ? 'text-neutral-700 cursor-not-allowed' : 'text-neutral-500 hover:bg-[#111111] hover:text-neutral-300'
              }`}
            >
              {item.icon} {item.id}
            </button>
          ))}
        </div>
        <button onClick={() => setIsAiOpen(true)} className="flex items-center gap-2 px-6 py-2 bg-white text-black rounded-full text-sm font-bold hover:bg-neutral-200 transition-colors">
          <MessageSquare size={16} /> Ask Frammer AI
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden relative">
        <FilterDock isOpen={isFilterOpen} setIsOpen={setIsFilterOpen} />

        <main className="flex-1 bg-[#050505] relative overflow-hidden">
          {activeTab === 'Overview' && <OverviewModule />}
          {activeTab === 'Usage & Trends' && <UsageTrendsModule />}
          {activeTab === 'Funnel' && <FunnelModule />}
          {activeTab === 'Explorer' && <ExplorerModule />}
          {activeTab === 'Data Health' && <ComingSoonModule title="Data Health" />}
        </main>

        {!isAiOpen && (
          <button onClick={() => setIsAiOpen(true)} className="absolute bottom-16 right-6 w-14 h-14 bg-white text-black rounded-full shadow-lg flex items-center justify-center hover:bg-neutral-200 hover:scale-105 transition-all z-20">
            <Sparkles size={24} />
          </button>
        )}

        <div className={`absolute top-0 right-0 h-full w-[400px] bg-[#0A0A0A] shadow-2xl border-l border-neutral-900 transform transition-transform duration-300 ease-in-out z-30 flex flex-col ${isAiOpen ? 'translate-x-0' : 'translate-x-full'}`}>
          <div className="p-5 border-b border-neutral-900 flex items-center justify-between bg-[#050505] text-white">
            <div className="flex items-center gap-2 font-black tracking-tight text-red-400"><MessageSquare size={18} /> FRAMMER AI COPILOT</div>
            <button onClick={() => setIsAiOpen(false)} className="text-neutral-500 hover:text-white transition-colors"><ChevronRight size={20} /></button>
          </div>
          <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-[#0A0A0A] text-sm text-neutral-400">
            <p>AI copilot is intentionally out-of-scope in this phase.</p>
            <p>Use Usage & Trends, Funnel, and Explorer for analysis and drilldowns.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
