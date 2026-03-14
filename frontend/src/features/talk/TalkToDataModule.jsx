import React, { useEffect, useRef, useState } from 'react';
import {
  Bot, Loader2, Send, Database, Table2,
  ChevronRight, X, PanelRightOpen, BarChart3,
  Sparkles, ArrowRight, Plus, MessageSquare, Trash2,
  FileText, Clock, Activity,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_BASE } from '../../lib/constants';
import XmlChartRenderer from '../../components/charts/XmlChartRenderer';

// ── Markdown overrides ──────────────────────────────────────────────────────

const md = {
  p: ({ children }) => <p className="mb-3 last:mb-0 leading-[1.75] text-[15px]">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1.5 text-[15px]">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1.5 text-[15px]">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="text-neutral-300 italic">{children}</em>,
  code: ({ inline, children }) =>
    inline
      ? <code className="bg-neutral-800/50 text-amber-300 text-[13px] px-1.5 py-0.5 rounded font-mono">{children}</code>
      : <pre className="bg-[#111] border border-neutral-800 rounded-lg p-4 overflow-x-auto my-3 text-[13px] text-neutral-300 font-mono leading-relaxed"><code>{children}</code></pre>,
  h2: ({ children }) => <h2 className="text-[17px] font-bold text-white mt-5 mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-[16px] font-bold text-white mt-4 mb-1.5">{children}</h3>,
  table: ({ children }) => <div className="overflow-x-auto my-3 rounded-lg border border-neutral-800"><table className="text-[13px] border-collapse w-full">{children}</table></div>,
  th: ({ children }) => <th className="border-b border-neutral-700 px-3 py-2.5 text-left text-neutral-300 bg-[#111] font-semibold text-[12px] uppercase tracking-wide">{children}</th>,
  td: ({ children }) => <td className="border-b border-neutral-800/40 px-3 py-2.5 text-neutral-400 text-[13px]">{children}</td>,
};

const SUGGESTIONS = [
  { text: 'Show me uploads by channel this month', icon: <BarChart3 size={16} /> },
  { text: 'What is the conversion rate by output type?', icon: <Sparkles size={16} /> },
  { text: 'Compare top 5 clients by published duration', icon: <Table2 size={16} /> },
  { text: 'Monthly upload trend over the last year', icon: <ArrowRight size={16} /> },
];

// ── Conversation history sidebar ────────────────────────────────────────────

function HistorySidebar({ conversations, activeId, onSelect, onNew, onDelete }) {
  return (
    <div className="w-[260px] shrink-0 bg-[#0A0A0A] border-r border-neutral-800/50 flex flex-col h-full">
      <div className="p-3 border-b border-neutral-800/50">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2.5 text-[13px] font-semibold text-neutral-300 bg-[#111] hover:bg-[#1A1A1A] border border-neutral-800 rounded-lg transition-colors"
        >
          <Plus size={14} /> New conversation
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${conv.id === activeId
                ? 'bg-[#1A1A1A] text-white'
                : 'text-neutral-500 hover:bg-[#111] hover:text-neutral-300'
              }`}
            onClick={() => onSelect(conv.id)}
          >
            <MessageSquare size={13} className="shrink-0" />
            <span className="text-[13px] truncate flex-1">{conv.title || 'New conversation'}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
        {conversations.length === 0 && (
          <div className="px-3 py-8 text-center">
            <Clock size={20} className="mx-auto text-neutral-700 mb-2" />
            <div className="text-[12px] text-neutral-600">No conversations yet</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Canvas panel (right, >=50% width) ───────────────────────────────────────

function CanvasPanel({ artifact, onClose }) {
  const [tab, setTab] = useState('chart');

  if (!artifact) return null;

  const { chartData, actions, chartXml } = artifact;
  const datasets = chartData ? Object.entries(chartData) : [];
  const hasChart = Boolean(chartXml);
  const hasData = datasets.length > 0;
  const hasActivity = actions && actions.length > 0;

  const tabs = [
    ...(hasChart ? [{ id: 'chart', label: 'Chart', icon: <BarChart3 size={13} /> }] : []),
    ...(hasData ? [{ id: 'data', label: 'Data', icon: <Table2 size={13} /> }] : []),
    ...(hasActivity ? [{ id: 'activity', label: 'Activity', icon: <Activity size={13} /> }] : []),
  ];

  const validTab = tabs.find(t => t.id === tab) ? tab : tabs[0]?.id || 'data';

  return (
    <div className="flex-1 min-w-0 bg-[#0C0C0C] border-l border-neutral-800/50 flex flex-col h-full">
      <div className="px-5 py-3.5 border-b border-neutral-800/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-red-500/10 flex items-center justify-center">
            <FileText size={14} className="text-red-400" />
          </div>
          <span className="text-[13px] font-bold text-neutral-200 uppercase tracking-wider">Analysis</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-neutral-800 text-neutral-500 hover:text-neutral-300 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {tabs.length > 1 && (
        <div className="px-5 pt-2 flex gap-1 border-b border-neutral-800/40 shrink-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-3.5 py-2.5 text-[12px] font-semibold rounded-t-lg transition-colors ${validTab === t.id
                  ? 'text-white bg-[#161616] border border-neutral-800/60 border-b-transparent -mb-px'
                  : 'text-neutral-500 hover:text-neutral-300'
                }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-5">
        {validTab === 'chart' && hasChart && (
          <XmlChartRenderer xmlString={chartXml} data={chartData} />
        )}

        {validTab === 'data' && hasData && (
          <div className="space-y-5">
            {datasets.map(([name, rows], idx) => (
              <DatasetTable key={idx} name={name} rows={rows} />
            ))}
          </div>
        )}

        {validTab === 'activity' && hasActivity && (
          <div>
            <div className="text-[12px] font-semibold text-neutral-500 uppercase tracking-wide mb-4">Agent Activity</div>
            <div className="space-y-2">
              {actions.map((action, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-neutral-800 text-neutral-500 flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5">
                    {i + 1}
                  </div>
                  <div className="flex-1 text-[13px] text-neutral-400 leading-relaxed py-0.5">
                    {action}
                  </div>
                  <ChevronRight size={12} className="text-neutral-700 shrink-0 mt-1.5" />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DatasetTable({ name, rows }) {
  const [expanded, setExpanded] = useState(false);
  if (!Array.isArray(rows) || rows.length === 0) return null;

  const cols = Object.keys(rows[0]);
  const displayRows = expanded ? rows.slice(0, 50) : rows.slice(0, 10);

  return (
    <div className="rounded-lg border border-neutral-800 overflow-hidden">
      <div className="px-4 py-2.5 bg-[#111] flex items-center justify-between">
        <span className="text-[12px] font-semibold text-neutral-400 truncate">{name}</span>
        <span className="text-[11px] text-neutral-600 font-mono">{rows.length} rows</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr>
              {cols.map((col) => (
                <th key={col} className="px-3 py-2 text-left text-neutral-500 bg-[#0E0E0E] font-semibold border-b border-neutral-800/50 whitespace-nowrap text-[11px]">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr key={i} className="hover:bg-neutral-800/20 transition-colors">
                {cols.map((col) => (
                  <td key={col} className="px-3 py-2 text-neutral-400 border-b border-neutral-800/30 whitespace-nowrap">
                    {String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 10 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full py-2 text-[11px] font-semibold text-neutral-500 hover:text-neutral-300 bg-[#0E0E0E] border-t border-neutral-800/50 transition-colors"
        >
          {expanded ? 'Show less' : `Show all ${rows.length} rows`}
        </button>
      )}
    </div>
  );
}

// ── Chat messages ───────────────────────────────────────────────────────────

function AssistantMessage({ msg, onOpenCanvas }) {
  const hasArtifact = (msg.chartData && Object.keys(msg.chartData).length > 0) || msg.chartXml;

  return (
    <div className="max-w-[760px]">
      <div className="flex items-center gap-2.5 mb-2.5">
        <div className="w-6 h-6 rounded-lg bg-red-500/10 flex items-center justify-center">
          <Bot size={13} className="text-red-400" />
        </div>
        <span className="text-[12px] font-semibold text-neutral-600">Frammer AI</span>
      </div>

      <div className="text-[15px] text-neutral-300 leading-[1.75] pl-[34px]">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>
          {msg.content || ''}
        </ReactMarkdown>

        {hasArtifact && (
          <button
            onClick={() => onOpenCanvas(msg)}
            className="mt-4 inline-flex items-center gap-2.5 text-[13px] font-semibold text-neutral-400 bg-[#111] hover:bg-[#1A1A1A] border border-neutral-800 hover:border-neutral-600 px-4 py-2.5 rounded-lg transition-all group"
          >
            <PanelRightOpen size={15} className="text-neutral-500 group-hover:text-red-400 transition-colors" />
            View analysis
            {msg.chartData && (
              <span className="text-[11px] text-neutral-600 font-mono">
                {Object.values(msg.chartData).reduce((sum, r) => sum + (Array.isArray(r) ? r.length : 0), 0)} rows
              </span>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

function UserMessage({ msg }) {
  return (
    <div className="max-w-[760px]">
      <div className="text-[15px] text-white leading-[1.75] font-medium">
        {msg.content}
      </div>
    </div>
  );
}

function LoadingIndicator() {
  return (
    <div className="max-w-[760px]">
      <div className="flex items-center gap-2.5 mb-2.5">
        <div className="w-6 h-6 rounded-lg bg-red-500/10 flex items-center justify-center">
          <Loader2 size={13} className="text-red-400 animate-spin" />
        </div>
        <span className="text-[12px] font-semibold text-neutral-600">Frammer AI</span>
      </div>
      <div className="pl-[34px] flex items-center gap-3">
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full bg-neutral-600 animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 rounded-full bg-neutral-600 animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 rounded-full bg-neutral-600 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-[14px] text-neutral-600">Analyzing your data...</span>
      </div>
    </div>
  );
}

// ── Empty state ─────────────────────────────────────────────────────────────

function EmptyState({ onSelect }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-red-500/20 to-red-500/5 border border-red-500/20 flex items-center justify-center mb-6">
        <Bot size={28} className="text-red-400" />
      </div>
      <h2 className="text-2xl font-bold text-white mb-2">Talk to Your Data</h2>
      <p className="text-neutral-500 text-[14px] text-center max-w-md mb-10 leading-relaxed">
        Ask questions in plain English. I'll query the database, analyze results,
        and generate charts and reports for you.
      </p>
      <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
        {SUGGESTIONS.map(({ text, icon }) => (
          <button
            key={text}
            onClick={() => onSelect(text)}
            className="group text-left text-[14px] bg-[#0E0E0E] text-neutral-500 p-4 rounded-xl border border-neutral-800/60 hover:border-neutral-700 hover:text-neutral-300 hover:bg-[#111] transition-all flex items-start gap-3"
          >
            <span className="mt-0.5 text-neutral-600 group-hover:text-red-400 transition-colors shrink-0">{icon}</span>
            <span className="leading-snug">{text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main module ─────────────────────────────────────────────────────────────

export default function TalkToDataModule({ authToken }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [canvasArtifact, setCanvasArtifact] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data.conversations || []);
      }
    } catch {
      /* agent offline */
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setCanvasArtifact(null);
    setInput('');
  };

  const handleSelectConversation = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (!res.ok) return;
      const data = await res.json();
      setConversationId(id);
      setCanvasArtifact(null);
      setMessages(
        (data.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          actions: m.metadata?.actions || [],
          chartData: null,
          chartXml: '',
        }))
      );
    } catch {
      /* ignore */
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await fetch(`${API_BASE}/conversations/${id}`, {
        method: 'DELETE',
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === conversationId) handleNewConversation();
    } catch {
      /* ignore */
    }
  };

  const send = async (overrideMsg) => {
    const text = (overrideMsg || input).trim();
    if (!text || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          filters: {},
          conversation_id: conversationId,
        }),
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(result.error || `Request failed: ${res.status}`);

      if (result.conversation_id) {
        setConversationId(result.conversation_id);
      }

      const assistantMsg = {
        role: 'assistant',
        content: result.response || 'No response generated.',
        chartData: result.chart_data,
        chartXml: result.chart_xml || '',
        actions: result.actions || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);

      const hasData = result.chart_data && Object.keys(result.chart_data).length > 0;
      if (hasData || result.chart_xml) {
        setCanvasArtifact(assistantMsg);
      }

      fetchConversations();
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `Something went wrong: ${err.message}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-full bg-[#080808]">
      <HistorySidebar
        conversations={conversations}
        activeId={conversationId}
        onSelect={handleSelectConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      <div className={`flex flex-col min-w-0 ${canvasArtifact ? 'w-[45%]' : 'flex-1'} transition-all duration-300`}>
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState onSelect={(text) => send(text)} />
          ) : (
            <div className="max-w-3xl mx-auto px-6 py-6 space-y-8">
              {messages.map((msg, idx) => (
                <div key={idx}>
                  {msg.role === 'user'
                    ? <UserMessage msg={msg} />
                    : <AssistantMessage msg={msg} onOpenCanvas={setCanvasArtifact} />
                  }
                </div>
              ))}
              {loading && <LoadingIndicator />}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <div className="shrink-0 border-t border-neutral-800/40 bg-[#080808] px-4 py-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-center bg-[#111] border border-neutral-800 rounded-xl focus-within:border-neutral-600 transition-colors">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your data..."
                disabled={loading}
                className="flex-1 bg-transparent pl-5 pr-3 py-3.5 text-[15px] text-white placeholder-neutral-600 focus:outline-none disabled:opacity-50"
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim()}
                className="mr-2 p-2.5 rounded-lg bg-white text-black hover:bg-neutral-200 transition-all active:scale-95 disabled:opacity-30 disabled:hover:bg-white"
              >
                <Send size={15} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {canvasArtifact && (
        <CanvasPanel
          artifact={canvasArtifact}
          onClose={() => setCanvasArtifact(null)}
        />
      )}
    </div>
  );
}
