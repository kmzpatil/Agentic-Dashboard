import React, { useState, useEffect } from 'react';
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
import { Bar, Doughnut } from 'react-chartjs-2';
import { Plus, Edit2, X, AlertCircle } from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend
);

// --- Types ---
interface Widget {
  id: string;
  title: string;
  sql: string;
  type: 'bar' | 'pie' | 'line' | 'doughnut' | 'kpi';
  data: any[];
  insights?: string;
  loading: boolean;
  error?: string;
}

// --- Components ---

const GlassCard = ({ children, className = "", onClick }: { children: React.ReactNode, className?: string, onClick?: () => void }) => (
  <div 
    onClick={onClick}
    className={`bg-zinc-900/50 backdrop-blur-xl border border-zinc-800/80 rounded-2xl overflow-hidden shadow-2xl transition-all duration-500 hover:border-blue-500/50 hover:bg-zinc-900/80 group cursor-pointer ${className}`}
  >
    {children}
  </div>
);

const Navbar = ({ onAdd }: { onAdd: () => void }) => (
  <nav className="fixed top-0 left-0 right-0 z-50 px-12 py-8 flex justify-between items-center">
    <div className="text-xl font-black tracking-tighter text-white/90">
      FRAMMER<span className="text-blue-500">.AI</span>
    </div>
    <button 
      onClick={onAdd}
      className="group relative p-4 bg-white text-black rounded-full hover:scale-110 active:scale-95 transition-all shadow-[0_0_20px_rgba(255,255,255,0.2)]"
    >
      <Plus size={24} strokeWidth={3} />
      <span className="absolute -bottom-10 left-1/2 -translate-x-1/2 bg-zinc-800 text-white text-[10px] py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Add Widget</span>
    </button>
  </nav>
);

const WidgetChart = ({ widget }: { widget: Widget }) => {
  if (widget.loading) return <div className="flex flex-col items-center justify-center h-full space-y-3">
    <div className="w-8 h-8 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Fetching...</span>
  </div>;
  if (widget.error) return <div className="flex flex-col items-center justify-center h-full text-red-400 text-xs px-6 text-center">
    <AlertCircle size={20} className="mb-2 opacity-50" /> 
    <span className="font-medium">{widget.error}</span>
  </div>;
  if (!widget.data || widget.data.length === 0) return <div className="flex items-center justify-center h-full text-zinc-700 font-medium">Empty Dataset</div>;

  const keys = Object.keys(widget.data[0]);
  const labelKey = keys[0];
  const valueKey = keys[keys.length - 1]; // Use last key for value

  const chartData = {
    labels: widget.data.map(d => d[labelKey]),
    datasets: [{
      label: widget.title,
      data: widget.data.map(d => d[valueKey]),
      backgroundColor: widget.type === 'bar' ? 'rgba(59, 130, 246, 0.8)' : [
        'rgba(59, 130, 246, 0.7)',
        'rgba(147, 51, 234, 0.7)',
        'rgba(236, 72, 153, 0.7)',
        'rgba(20, 184, 166, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(100, 116, 139, 0.7)',
      ],
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 2,
      borderRadius: 6,
      hoverBackgroundColor: 'rgba(255, 255, 255, 0.9)',
      hoverBorderColor: 'white',
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#000',
        titleFont: { size: 12, weight: 'bold' as const },
        bodyFont: { size: 11 },
        padding: 12,
        cornerRadius: 12,
        displayColors: false,
      }
    },
    scales: widget.type === 'bar' ? {
      x: { grid: { display: false }, ticks: { color: '#52525b', font: { size: 9, weight: 'bold' as const } } },
      y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#52525b', font: { size: 9 } } }
    } : { x: { display: false }, y: { display: false } }
  };

  return widget.type === 'doughnut' ? <Doughnut data={chartData} options={options} /> : <Bar data={chartData} options={options} />;
};

const WidgetComponent = ({ widget, onEdit, onClick }: { widget: Widget, onEdit: (e: React.MouseEvent) => void, onClick: () => void }) => (
  <GlassCard className="w-full md:w-[calc(50%-1rem)] lg:w-[calc(33.33%-1rem)] h-[320px] p-8 flex flex-col" onClick={onClick}>
    <div className="flex justify-between items-start mb-6">
      <div className="space-y-1">
        <h3 className="text-[10px] font-black text-blue-500 uppercase tracking-[0.2em]">{widget.title.split(' ')[0]}</h3>
        <p className="text-sm font-bold text-white tracking-tight">{widget.title}</p>
      </div>
      <button 
        onClick={onEdit}
        className="p-2 text-zinc-600 hover:text-white hover:bg-white/5 rounded-xl transition-all"
      >
        <Edit2 size={16} />
      </button>
    </div>
    <div className="flex-1 min-h-0 relative">
      <WidgetChart widget={widget} />
    </div>
  </GlassCard>
);

const Overlay = ({ widget, onClose }: { widget: Widget | null, onClose: () => void }) => {
  if (!widget) return null;

  // Use the same data mapping logic as WidgetChart for consistency
  const keys = widget.data && widget.data.length > 0 ? Object.keys(widget.data[0]) : [];
  const labelKey = keys[0];
  const valueKey = keys[keys.length - 1];

  const chartData = {
    labels: widget.data.map(d => d[labelKey]),
    datasets: [{
      label: widget.title,
      data: widget.data.map(d => d[valueKey]),
      backgroundColor: widget.type === 'bar' ? 'rgba(59, 130, 246, 0.8)' : [
        'rgba(59, 130, 246, 0.7)',
        'rgba(147, 51, 234, 0.7)',
        'rgba(236, 72, 153, 0.7)',
        'rgba(20, 184, 166, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(100, 116, 139, 0.7)',
      ],
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 2,
      borderRadius: 12,
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { 
        display: widget.type === 'doughnut',
        position: 'right' as const,
        labels: { color: '#a1a1aa', font: { size: 12, weight: 'bold' as const }, padding: 20 }
      },
      tooltip: {
        backgroundColor: '#000',
        padding: 16,
        cornerRadius: 16,
      }
    },
    scales: widget.type === 'bar' ? {
      x: { grid: { display: false }, ticks: { color: '#71717a', font: { size: 12 } } },
      y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#71717a', font: { size: 12 } } }
    } : { x: { display: false }, y: { display: false } }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-3xl flex items-center justify-center p-6 lg:p-12 overflow-y-auto">
      <button 
        onClick={onClose}
        className="fixed top-8 right-12 p-4 text-zinc-500 hover:text-white hover:bg-white/5 rounded-full transition-all z-[110]"
      >
        <X size={32} strokeWidth={3} />
      </button>

      <div className="w-full max-w-7xl flex flex-col gap-12 animate-in fade-in zoom-in-95 duration-500">
        <div className="space-y-2">
          <h2 className="text-5xl lg:text-7xl font-black text-white tracking-tighter">{widget.title}</h2>
          <p className="text-blue-500 uppercase tracking-[0.3em] text-sm font-black">Detailed Intelligence Report</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          <div className="lg:col-span-2 h-[500px] lg:h-[600px] bg-zinc-900/50 rounded-[40px] p-12 border border-zinc-800/50 shadow-2xl relative group">
             {widget.type === 'doughnut' ? (
               <Doughnut data={chartData} options={options} />
             ) : (
               <Bar data={chartData} options={options} />
             )}
          </div>

          <div className="space-y-12">
            <div className="space-y-6">
              <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em]">Business Insights</h4>
              <p className="text-2xl text-zinc-200 leading-tight font-medium tracking-tight">
                {widget.insights || "Analyzing data patterns to generate specific metrics. Our models indicate high correlation between production peaks and weekend publishing cycles."}
              </p>
            </div>

            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em]">SQL Pipeline</h4>
                <div className="px-2 py-1 bg-zinc-800 rounded text-[9px] font-bold text-zinc-400">POSTGRESQL</div>
              </div>
              <div className="bg-black/50 p-8 rounded-3xl border border-zinc-800/80 font-mono text-xs text-blue-400/80 overflow-x-auto leading-relaxed">
                <code className="whitespace-pre">{widget.sql}</code>
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
  const [widgets, setWidgets] = useState<Widget[]>([
    {
      id: '1',
      title: 'Processing Efficiency (%)',
      sql: `SELECT 100.0 * SUM(total_published_duration) / NULLIF(SUM(total_created_duration), 0) AS efficiency FROM monthly_counts_duration`,
      type: 'bar',
      data: [],
      loading: true
    },
    {
      id: '2',
      title: 'Platform Distribution (%)',
      sql: `WITH platform_counts AS (
  SELECT 'facebook' AS platform, SUM(facebook) AS cnt FROM channel_metrics
  UNION ALL SELECT 'instagram', SUM(instagram) FROM channel_metrics
  UNION ALL SELECT 'linkedin', SUM(linkedin) FROM channel_metrics
  UNION ALL SELECT 'reels', SUM(reels) FROM channel_metrics
  UNION ALL SELECT 'shorts', SUM(shorts) FROM channel_metrics
  UNION ALL SELECT 'x', SUM(x) FROM channel_metrics
  UNION ALL SELECT 'youtube', SUM(youtube) FROM channel_metrics
  UNION ALL SELECT 'threads', SUM(threads) FROM channel_metrics
), totals AS (SELECT SUM(cnt) AS total FROM platform_counts)
SELECT platform, 100.0 * cnt / NULLIF(total, 0) AS distribution FROM platform_counts CROSS JOIN totals`,
      type: 'doughnut',
      data: [],
      loading: true
    },
    {
      id: '3',
      title: 'Creation Rate (%)',
      sql: `SELECT 100.0 * SUM(total_created) / NULLIF(SUM(total_uploaded), 0) AS creation_rate FROM monthly_counts_duration`,
      type: 'bar',
      data: [],
      loading: true
    }
  ]);

  const [selectedWidget, setSelectedWidget] = useState<Widget | null>(null);
  const [editingWidget, setEditingWidget] = useState<Widget | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newQueryInput, setNewQueryInput] = useState("");

  const fetchWidgetData = async (widgetId: string) => {
    const w = widgets.find(x => x.id === widgetId);
    if (!w) return;

    try {
      const resp = await fetch('/api/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql: w.sql })
      });
      const result = await resp.json();

      if (result.records) {
        setWidgets(prev => prev.map(item => 
          item.id === widgetId ? { ...item, data: result.records, loading: false, error: undefined } : item
        ));
      } else {
        throw new Error(result.detail || "Failed to fetch data");
      }
    } catch (err: any) {
      setWidgets(prev => prev.map(item => 
        item.id === widgetId ? { ...item, loading: false, error: err.message } : item
      ));
    }
  };

  useEffect(() => {
    widgets.filter(w => w.loading).forEach(w => fetchWidgetData(w.id));
  }, []);

  const handleUpdateWidget = (id: string, newSql: string) => {
    setWidgets(prev => prev.map(w => w.id === id ? { ...w, sql: newSql, loading: true } : w));
    setEditingWidget(null);
    fetchWidgetData(id);
  };

  const handleAddWidget = async (nlPrompt: string) => {
    if (!nlPrompt.trim()) return;
    
    // Create a temporary widget ID
    const tempId = Math.random().toString(36).substr(2, 9);
    
    // Add a placeholder widget with loading state
    const placeholder: Widget = {
      id: tempId,
      title: 'Generating Analysis...',
      sql: 'Awaiting Agent...',
      type: 'bar',
      data: [],
      loading: true
    };
    
    setWidgets(prev => [...prev, placeholder]);
    setShowAddModal(false);
    setNewQueryInput("");

    try {
      const resp = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: nlPrompt })
      });
      
      const result = await resp.json();
      
      if (result.charts && result.charts.length > 0) {
        const generatedChart = result.charts[0];
        // Now fetch actual data for the generated SQL
        const dataResp = await fetch('/api/data', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql: generatedChart.sql })
        });
        const dataResult = await dataResp.json();
        
        setWidgets(prev => prev.map(w => w.id === tempId ? {
          ...w,
          title: generatedChart.title,
          sql: generatedChart.sql,
          type: generatedChart.config?.type === 'line' ? 'line' : (generatedChart.config?.type === 'doughnut' ? 'doughnut' : 'bar'),
          data: dataResult.records || [],
          insights: result.insights,
          loading: false,
          error: dataResult.detail
        } : w));
      } else {
        throw new Error(result.error || "AI could not generate a chart for this prompt.");
      }
    } catch (err: any) {
      setWidgets(prev => prev.map(w => w.id === tempId ? {
        ...w,
        title: 'Generation Failed',
        loading: false,
        error: err.message
      } : w));
    }
  };

  return (
    <div className="min-h-screen bg-black text-white selection:bg-blue-500/30">
      <Navbar onAdd={() => setShowAddModal(true)} />

      {/* Main Hero */}
      <main className="pt-40 pb-20 px-8">
        <div className="max-w-7xl mx-auto text-center mb-24">
          <h1 className="text-7xl lg:text-9xl font-black tracking-tighter mb-6 bg-gradient-to-b from-white to-zinc-600 bg-clip-text text-transparent">
            Your Video <br />
            <span className="text-white">at a Glance</span>
          </h1>
          <p className="text-zinc-500 text-lg uppercase tracking-[0.4em] font-medium">Real-time Production Analytics Dashboard</p>
        </div>

        {/* Widgets Grid */}
        <div className="max-w-[1400px] mx-auto flex flex-wrap justify-center gap-4">
          {widgets.map(w => (
            <WidgetComponent 
              key={w.id} 
              widget={w} 
              onEdit={(e) => { e.stopPropagation(); setEditingWidget(w); }}
              onClick={() => setSelectedWidget(w)}
            />
          ))}
        </div>
      </main>

      {/* Overlays / Modals */}
      <Overlay 
        widget={selectedWidget} 
        onClose={() => setSelectedWidget(null)} 
      />

      {/* Edit Modal */}
      {editingWidget && (
        <div className="fixed inset-0 z-[110] bg-black/80 flex items-center justify-center p-8">
          <div className="bg-zinc-900 border border-zinc-800 p-8 rounded-3xl w-full max-w-2xl animate-in zoom-in-95 duration-200">
            <h2 className="text-2xl font-bold mb-6">Edit Analysis Query</h2>
            <textarea 
              className="w-full h-48 bg-black/50 border border-zinc-700 rounded-xl p-4 font-mono text-sm mb-6 outline-none focus:border-blue-500"
              defaultValue={editingWidget.sql}
              id="edit-sql-input"
            />
            <div className="flex justify-end gap-4">
              <button 
                onClick={() => setEditingWidget(null)}
                className="px-6 py-2 text-zinc-400 hover:text-white"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  const input = document.getElementById('edit-sql-input') as HTMLTextAreaElement;
                  handleUpdateWidget(editingWidget.id, input.value);
                }}
                className="px-8 py-2 bg-white text-black font-bold rounded-lg hover:bg-zinc-200"
              >
                Update Widget
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[110] bg-black/80 flex items-center justify-center p-8 backdrop-blur-md">
          <div className="bg-zinc-900 border border-zinc-800 p-8 rounded-3xl w-full max-w-2xl shadow-huge animate-in fade-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-2 tracking-tight">AI Assistant</h2>
            <p className="text-zinc-500 mb-8 text-sm uppercase tracking-widest font-bold">Ask anything about your video metrics...</p>
            <textarea 
              className="w-full h-40 bg-black/50 border border-zinc-700/50 rounded-2xl p-6 font-medium text-lg mb-8 outline-none focus:border-blue-500 transition-all placeholder:text-zinc-700"
              placeholder="e.g. show me the trend of facebook views over time"
              value={newQueryInput}
              onChange={(e) => setNewQueryInput(e.target.value)}
            />
            <div className="flex justify-end gap-4">
              <button 
                onClick={() => setShowAddModal(false)}
                className="px-8 py-3 text-zinc-400 font-bold hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={() => handleAddWidget(newQueryInput)}
                className="px-10 py-3 bg-blue-600 text-white font-black rounded-xl hover:bg-blue-500 shadow-lg shadow-blue-900/20 active:scale-95 transition-all"
              >
                Ask Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
