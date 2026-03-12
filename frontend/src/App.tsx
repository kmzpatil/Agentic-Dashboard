import React, { useState, useRef } from 'react';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title, 
  Tooltip, 
  Legend, 
  ArcElement, 
  PointElement, 
  LineElement, 
  Filler 
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { Plus, Edit2, X, AlertCircle, Sparkles, Code, Lightbulb, Loader2, RefreshCw, Trash2 } from 'lucide-react';

ChartJS.register(
  CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Filler, Title, Tooltip, Legend
);

// --- Constants ---
const API_BASE = '';  // proxy handles /api -> localhost:8000

const CHART_COLORS = [
  'rgba(88, 166, 255, 0.8)',
  'rgba(188, 140, 255, 0.8)',
  'rgba(57, 211, 83, 0.8)',
  'rgba(247, 129, 102, 0.8)',
  'rgba(255, 196, 0, 0.8)',
  'rgba(248, 81, 73, 0.8)',
  'rgba(121, 192, 255, 0.8)',
  'rgba(210, 153, 255, 0.8)',
];

// --- Types ---
interface ChartConfig {
  type: string;
  x_axis: string;
  y_axis: string[];
  data: {
    labels: string[];
    datasets: { label: string; data: number[]; backgroundColor: string; borderColor: string; borderWidth: number }[];
  };
  options: any;
}

interface Widget {
  id: string;
  description: string;       // The natural-language question (editable)
  title: string;              // Chart title from agent
  sql: string;                // Generated SQL
  chartType: 'bar' | 'pie' | 'line' | 'doughnut';
  data: any[];                // Raw records from DB
  config: ChartConfig | null; // Full Chart.js config from agent
  insights: string;
  loading: boolean;
  error?: string;
}

// --- Default starter descriptions ---
const STARTER_DESCRIPTIONS = [
  'Show me the distribution of posts across all social media platforms',
  'What is the monthly trend of total published content over time?',
  'Show video counts by team',
];

// --- API helpers ---
async function queryAgent(question: string): Promise<{
  title: string;
  sql: string;
  config: ChartConfig | null;
  chartType: string;
  insights: string;
  records: any[];
  error?: string;
}> {
  // Step 1: Ask the agent to decompose the question and generate SQL + chart config
  const queryResp = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  
  if (!queryResp.ok) {
    const err = await queryResp.json().catch(() => ({ detail: 'Agent request failed' }));
    throw new Error(err.detail || `HTTP ${queryResp.status}`);
  }
  
  const result = await queryResp.json();
  
  if (result.error && !result.charts?.length) {
    throw new Error(result.error);
  }

  const chart = result.charts?.[0];
  if (!chart) {
    throw new Error('Agent could not generate a chart for this question.');
  }

  // Step 2: Fetch actual data using the generated SQL
  const dataResp = await fetch(`${API_BASE}/api/data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql: chart.sql }),
  });

  let records: any[] = [];
  if (dataResp.ok) {
    const dataResult = await dataResp.json();
    records = dataResult.records || [];
  }

  const chartType = chart.config?.type || 'bar';

  return {
    title: chart.title || question,
    sql: chart.sql || '',
    config: chart.config || null,
    chartType,
    insights: result.insights || '',
    records,
    error: chart.error || undefined,
  };
}

// --- Components ---

const WidgetChart = ({ widget }: { widget: Widget }) => {
  if (widget.loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-3">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
          AI Agent working...
        </span>
      </div>
    );
  }

  if (widget.error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-red-400 text-xs px-6 text-center">
        <AlertCircle size={20} className="mb-2 opacity-50" />
        <span className="font-medium">{widget.error}</span>
      </div>
    );
  }

  if (!widget.data || widget.data.length === 0) {
    return <div className="flex items-center justify-center h-full text-zinc-700 font-medium">Empty Dataset</div>;
  }

  // Build chart data from the raw records, using agent config hints
  const keys = Object.keys(widget.data[0]);
  const xKey = widget.config?.x_axis || keys[0];
  const yKeys: string[] = widget.config?.y_axis || keys.filter(k => k !== xKey && typeof widget.data[0][k] === 'number');
  
  // If no numeric y keys found, try all non-x keys
  const finalYKeys = yKeys.length > 0 ? yKeys : keys.filter(k => k !== xKey);

  const labels = widget.data.map(d => String(d[xKey] ?? ''));
  const datasets = finalYKeys.map((yKey, i) => ({
    label: yKey.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    data: widget.data.map(d => Number(d[yKey]) || 0),
    backgroundColor: widget.chartType === 'bar'
      ? CHART_COLORS[i % CHART_COLORS.length]
      : CHART_COLORS.slice(0, widget.data.length),
    borderColor: widget.chartType === 'line'
      ? CHART_COLORS[i % CHART_COLORS.length]
      : 'rgba(255, 255, 255, 0.05)',
    borderWidth: widget.chartType === 'line' ? 2 : 1,
    borderRadius: widget.chartType === 'bar' ? 6 : undefined,
    tension: widget.chartType === 'line' ? 0.3 : undefined,
    fill: widget.chartType === 'line' ? true : undefined,
    pointRadius: widget.chartType === 'line' ? 4 : undefined,
    pointBackgroundColor: widget.chartType === 'line' ? CHART_COLORS[i % CHART_COLORS.length] : undefined,
  }));

  const chartData = { labels, datasets };

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: datasets.length > 1, labels: { color: '#a1a1aa', font: { size: 10 } } },
      tooltip: {
        backgroundColor: '#09090b',
        titleFont: { size: 12, weight: 'bold' },
        bodyFont: { size: 11 },
        padding: 12,
        cornerRadius: 10,
        displayColors: true,
      },
    },
    scales: widget.chartType === 'pie' || widget.chartType === 'doughnut'
      ? { x: { display: false }, y: { display: false } }
      : {
          x: { grid: { display: false }, ticks: { color: '#52525b', font: { size: 9, weight: 'bold' }, maxRotation: 45 } },
          y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#52525b', font: { size: 9 } } },
        },
  };

  if (widget.chartType === 'line') return <Line data={chartData as any} options={options} />;
  if (widget.chartType === 'pie' || widget.chartType === 'doughnut') return <Doughnut data={chartData as any} options={options} />;
  return <Bar data={chartData as any} options={options} />;
};

const WidgetCard = ({ widget, onEdit, onClick, onDelete }: {
  widget: Widget;
  onEdit: (e: React.MouseEvent) => void;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}) => (
  <div
    onClick={onClick}
    className="bg-zinc-900/50 backdrop-blur-xl border border-zinc-800/80 rounded-2xl overflow-hidden shadow-2xl transition-all duration-500 hover:border-blue-500/40 hover:bg-zinc-900/80 cursor-pointer w-full md:w-[calc(50%-1rem)] lg:w-[calc(33.33%-1rem)] h-[340px] p-6 flex flex-col group"
  >
    <div className="flex justify-between items-start mb-4">
      <div className="space-y-1 flex-1 min-w-0 mr-2">
        <h3 className="text-[10px] font-black text-blue-500 uppercase tracking-[0.15em] truncate">
          {widget.chartType}
        </h3>
        <p className="text-sm font-bold text-white tracking-tight line-clamp-2">{widget.title}</p>
      </div>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onEdit}
          className="p-1.5 text-zinc-600 hover:text-white hover:bg-white/5 rounded-lg transition-all"
          title="Edit description"
        >
          <Edit2 size={14} />
        </button>
        <button
          onClick={onDelete}
          className="p-1.5 text-zinc-600 hover:text-red-400 hover:bg-red-500/5 rounded-lg transition-all"
          title="Remove widget"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
    <p className="text-[11px] text-zinc-500 mb-3 line-clamp-1 italic">"{widget.description}"</p>
    <div className="flex-1 min-h-0 relative">
      <WidgetChart widget={widget} />
    </div>
  </div>
);

const DetailOverlay = ({ widget, onClose, onRerun }: {
  widget: Widget | null;
  onClose: () => void;
  onRerun: () => void;
}) => {
  if (!widget) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-3xl flex items-start justify-center p-6 lg:p-12 overflow-y-auto">
      <button
        onClick={onClose}
        className="fixed top-8 right-12 p-3 text-zinc-500 hover:text-white hover:bg-white/5 rounded-full transition-all z-[110]"
      >
        <X size={28} strokeWidth={3} />
      </button>

      <div className="w-full max-w-7xl flex flex-col gap-10 animate-in fade-in duration-500 mt-4">
        {/* Header */}
        <div className="space-y-2">
          <h2 className="text-4xl lg:text-6xl font-black text-white tracking-tighter">{widget.title}</h2>
          <p className="text-blue-500 uppercase tracking-[0.2em] text-xs font-black flex items-center gap-2">
            <Sparkles size={14} /> Detailed Analysis
          </p>
        </div>

        {/* Chart + Details */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Chart */}
          <div className="lg:col-span-3 h-[400px] lg:h-[500px] bg-zinc-900/50 rounded-3xl p-8 border border-zinc-800/50 shadow-2xl">
            <WidgetChart widget={widget} />
          </div>

          {/* Side Panel */}
          <div className="lg:col-span-2 space-y-8">
            {/* Description */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] flex items-center gap-2">
                <Edit2 size={10} /> Description
              </h4>
              <p className="text-lg text-zinc-300 leading-relaxed font-medium">
                "{widget.description}"
              </p>
            </div>

            {/* Insights */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] flex items-center gap-2">
                <Lightbulb size={10} /> Business Insights
              </h4>
              <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {widget.insights || 'No insights generated yet. Re-run the analysis to generate.'}
              </div>
            </div>

            {/* SQL */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] flex items-center gap-2">
                  <Code size={10} /> SQL Query
                </h4>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-zinc-800 rounded text-[9px] font-bold text-zinc-400">POSTGRESQL</span>
                  <button
                    onClick={onRerun}
                    className="px-3 py-1 bg-blue-600/20 text-blue-400 text-[10px] font-bold rounded-lg hover:bg-blue-600/30 transition-all flex items-center gap-1"
                  >
                    <RefreshCw size={10} /> Re-run
                  </button>
                </div>
              </div>
              <div className="bg-black/60 p-6 rounded-2xl border border-zinc-800/80 font-mono text-xs text-blue-400/80 overflow-x-auto leading-relaxed max-h-[200px] overflow-y-auto">
                <code className="whitespace-pre-wrap">{widget.sql || 'No SQL generated'}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// --- Main App ---

export default function App() {
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [selectedWidget, setSelectedWidget] = useState<Widget | null>(null);
  const [editingWidget, setEditingWidget] = useState<Widget | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newDescription, setNewDescription] = useState('');
  const [initialized, setInitialized] = useState(false);
  const editInputRef = useRef<HTMLTextAreaElement>(null);

  // Load starter widgets on mount
  React.useEffect(() => {
    if (initialized) return;
    setInitialized(true);

    STARTER_DESCRIPTIONS.forEach((desc, i) => {
      const id = `starter-${i}`;
      // Add placeholder
      setWidgets(prev => [
        ...prev,
        {
          id,
          description: desc,
          title: 'Generating...',
          sql: '',
          chartType: 'bar',
          data: [],
          config: null,
          insights: '',
          loading: true,
        },
      ]);

      // Fire off agent query
      runAgentForWidget(id, desc);
    });
  }, [initialized]);

  const runAgentForWidget = async (widgetId: string, description: string) => {
    try {
      const result = await queryAgent(description);

      const chartType = (['pie', 'doughnut'].includes(result.chartType) ? 'doughnut' : result.chartType) as Widget['chartType'];

      setWidgets(prev =>
        prev.map(w =>
          w.id === widgetId
            ? {
                ...w,
                title: result.title,
                sql: result.sql,
                chartType,
                data: result.records,
                config: result.config,
                insights: result.insights,
                loading: false,
                error: result.error,
              }
            : w
        )
      );

      // Update the selected widget if it's the one being updated
      setSelectedWidget(prev =>
        prev && prev.id === widgetId
          ? {
              ...prev,
              title: result.title,
              sql: result.sql,
              chartType,
              data: result.records,
              config: result.config,
              insights: result.insights,
              loading: false,
              error: result.error,
            }
          : prev
      );
    } catch (err: any) {
      setWidgets(prev =>
        prev.map(w =>
          w.id === widgetId
            ? { ...w, title: 'Analysis Failed', loading: false, error: err.message }
            : w
        )
      );
    }
  };

  const handleEditDescription = (id: string, newDesc: string) => {
    if (!newDesc.trim()) return;
    setWidgets(prev =>
      prev.map(w =>
        w.id === id
          ? { ...w, description: newDesc, loading: true, error: undefined, title: 'Re-analyzing...' }
          : w
      )
    );
    setEditingWidget(null);
    runAgentForWidget(id, newDesc);
  };

  const handleAddWidget = (desc: string) => {
    if (!desc.trim()) return;
    const id = `w-${Date.now()}`;
    setWidgets(prev => [
      ...prev,
      {
        id,
        description: desc,
        title: 'Generating...',
        sql: '',
        chartType: 'bar',
        data: [],
        config: null,
        insights: '',
        loading: true,
      },
    ]);
    setShowAddModal(false);
    setNewDescription('');
    runAgentForWidget(id, desc);
  };

  const handleDeleteWidget = (id: string) => {
    setWidgets(prev => prev.filter(w => w.id !== id));
    if (selectedWidget?.id === id) setSelectedWidget(null);
  };

  const handleRerun = (id: string) => {
    const w = widgets.find(x => x.id === id);
    if (!w) return;
    setWidgets(prev => prev.map(x => x.id === id ? { ...x, loading: true, error: undefined } : x));
    runAgentForWidget(id, w.description);
  };

  return (
    <div className="min-h-screen bg-black text-white selection:bg-blue-500/30">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-8 lg:px-12 py-6 flex justify-between items-center bg-black/80 backdrop-blur-xl border-b border-zinc-900">
        <div className="text-xl font-black tracking-tighter text-white/90">
          GCDATA<span className="text-blue-500">.AI</span>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="group relative flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-bold rounded-xl hover:bg-blue-500 active:scale-95 transition-all shadow-lg shadow-blue-900/30"
        >
          <Plus size={18} strokeWidth={3} />
          Add Widget
        </button>
      </nav>

      {/* Hero */}
      <main className="pt-32 pb-20 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center mb-16">
          <h1 className="text-5xl lg:text-8xl font-black tracking-tighter mb-4 bg-gradient-to-b from-white to-zinc-600 bg-clip-text text-transparent">
            Video Analytics
          </h1>
          <p className="text-zinc-500 text-sm uppercase tracking-[0.3em] font-medium">
            AI-powered dashboard · Describe what you want to see
          </p>
        </div>

        {/* Widget Grid */}
        <div className="max-w-[1400px] mx-auto flex flex-wrap justify-center gap-4">
          {widgets.map(w => (
            <WidgetCard
              key={w.id}
              widget={w}
              onEdit={e => { e.stopPropagation(); setEditingWidget(w); }}
              onClick={() => setSelectedWidget(w)}
              onDelete={e => { e.stopPropagation(); handleDeleteWidget(w.id); }}
            />
          ))}

          {widgets.length === 0 && !initialized && (
            <div className="text-zinc-600 text-center py-20">Loading starter widgets...</div>
          )}
        </div>
      </main>

      {/* Detail Overlay */}
      <DetailOverlay
        widget={selectedWidget}
        onClose={() => setSelectedWidget(null)}
        onRerun={() => selectedWidget && handleRerun(selectedWidget.id)}
      />

      {/* Edit Description Modal */}
      {editingWidget && (
        <div className="fixed inset-0 z-[110] bg-black/80 backdrop-blur-md flex items-center justify-center p-8">
          <div className="bg-zinc-900 border border-zinc-800 p-8 rounded-3xl w-full max-w-2xl animate-in zoom-in-95 duration-200">
            <h2 className="text-2xl font-black mb-2 flex items-center gap-3">
              <Sparkles size={20} className="text-blue-500" />
              Edit Widget Description
            </h2>
            <p className="text-zinc-500 text-sm mb-6">
              Describe what data you want to visualize. The AI agent will generate the appropriate SQL query and chart.
            </p>
            <textarea
              ref={editInputRef}
              className="w-full h-32 bg-black/50 border border-zinc-700/50 rounded-2xl p-5 text-base mb-6 outline-none focus:border-blue-500 transition-all placeholder:text-zinc-700 resize-none"
              defaultValue={editingWidget.description}
              placeholder="e.g., Show me the top 5 channels by total YouTube posts"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setEditingWidget(null)}
                className="px-6 py-2.5 text-zinc-400 font-bold hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (editInputRef.current) {
                    handleEditDescription(editingWidget.id, editInputRef.current.value);
                  }
                }}
                className="px-8 py-2.5 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-500 shadow-lg shadow-blue-900/20 active:scale-95 transition-all flex items-center gap-2"
              >
                <Sparkles size={16} />
                Re-analyze
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Widget Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[110] bg-black/80 flex items-center justify-center p-8 backdrop-blur-md">
          <div className="bg-zinc-900 border border-zinc-800 p-8 rounded-3xl w-full max-w-2xl shadow-2xl animate-in fade-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-2 tracking-tight flex items-center gap-3">
              <Sparkles size={24} className="text-blue-500" />
              AI Analytics
            </h2>
            <p className="text-zinc-500 mb-6 text-sm">
              Describe what you want to analyze. The agent will generate the SQL, fetch data, and create the chart.
            </p>
            <textarea
              className="w-full h-36 bg-black/50 border border-zinc-700/50 rounded-2xl p-5 text-base mb-6 outline-none focus:border-blue-500 transition-all placeholder:text-zinc-700 resize-none"
              placeholder="e.g., Show me the monthly trend of uploaded vs published content"
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) handleAddWidget(newDescription); }}
            />
            <div className="flex justify-between items-center">
              <p className="text-[10px] text-zinc-600">⌘ + Enter to submit</p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-6 py-2.5 text-zinc-400 font-bold hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleAddWidget(newDescription)}
                  className="px-8 py-2.5 bg-blue-600 text-white font-black rounded-xl hover:bg-blue-500 shadow-lg shadow-blue-900/30 active:scale-95 transition-all flex items-center gap-2"
                >
                  <Sparkles size={16} />
                  Generate
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
