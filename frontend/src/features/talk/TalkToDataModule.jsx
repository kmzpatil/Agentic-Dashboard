import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Bot,
  CheckCircle2,
  ChevronRight,
  Database,
  Loader2,
  MessageSquare,
  Mic,
  MicOff,
  PanelLeft,
  PanelLeftClose,
  Plus,
  Send,
  Sparkles,
  Table2,
  Trash2,
  TrendingUp,
  Zap,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_BASE } from '../../lib/constants';
import useVoiceInput from '../../hooks/useVoiceInput';
import ArtifactCanvas from '../../components/artifacts/ArtifactCanvas';

const markdownComponents = {
  p: ({ children }) => <p className="mb-3 last:mb-0 leading-[1.75] text-[15px]">{children}</p>,
  ul: ({ children }) => <ul className="mb-3 list-disc space-y-1.5 pl-5 text-[15px]">{children}</ul>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  code: ({ inline, children }) => (
    inline
      ? <code className="rounded bg-neutral-800/60 px-1.5 py-0.5 text-[13px] text-amber-300">{children}</code>
      : <pre className="my-3 overflow-x-auto rounded-2xl border border-neutral-800 bg-[#111111] p-4 text-[13px] text-neutral-300"><code>{children}</code></pre>
  ),
};

const PHASE_LABELS = {
  planning: 'Analyzing question...',
  executing: 'Running queries...',
  repairing: 'Fixing queries...',
  synthesizing: 'Composing response...',
};

const SUGGESTIONS = [
  { icon: TrendingUp, label: 'Summarize the latest pipeline health', category: 'Overview' },
  { icon: BarChart3, label: 'Which channels are losing conversion?', category: 'Funnel' },
  { icon: Database, label: 'Show the monthly uploaded trend', category: 'Trends' },
  { icon: Sparkles, label: 'What should I investigate next?', category: 'Insight' },
];

const shouldAutoOpenCanvas = (artifacts = []) => artifacts.some(a => a.kind === 'chart');

function ThinkingTrace({ actions }) {
  const [open, setOpen] = useState(false);
  if (!actions?.length) return null;
  return (
    <div className="mb-3 rounded-xl border border-neutral-800/60 bg-[#0D0D0D] overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-[#111111]"
      >
        <Zap size={12} className="text-amber-400 shrink-0" />
        <span className="text-[12px] font-semibold text-neutral-500">
          {actions.length} reasoning step{actions.length !== 1 ? 's' : ''}
        </span>
        <ChevronRight size={12} className={`ml-auto text-neutral-600 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-neutral-800/60 px-3 py-2 space-y-1">
          {actions.map((action, i) => (
            <div key={i} className="flex gap-2 text-[12px] font-mono text-neutral-500">
              <span className="text-neutral-700 shrink-0">·</span>
              <span>{action}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InlineKpiCards({ artifact }) {
  const items = artifact?.spec?.items || [];
  if (!items.length) return null;
  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      {items.map(item => (
        <div key={item.label} className="rounded-xl border border-neutral-800 bg-[#0D0D0D] p-3">
          <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-500">{item.label}</div>
          <div className="mt-1.5 text-xl font-black tracking-tight text-white">{item.value ?? '-'}</div>
        </div>
      ))}
    </div>
  );
}

function InlineTablePreview({ artifact, datasets }) {
  const dataset = (datasets || []).find(d => d.id === artifact?.dataset_id);
  const rows = dataset?.rows || [];
  const columns = dataset?.schema || [];
  const PREVIEW_ROWS = 3;
  const extra = rows.length - PREVIEW_ROWS;
  if (!rows.length || !columns.length) return null;
  return (
    <div className="mt-3 rounded-xl border border-neutral-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className="bg-[#0F0F0F]">
            <tr>
              {columns.map(col => (
                <th key={col.key} className="px-3 py-2 text-left text-[10px] font-bold uppercase tracking-[0.18em] text-neutral-500">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, PREVIEW_ROWS).map((row, i) => (
              <tr key={i} className="border-t border-neutral-900">
                {columns.map(col => (
                  <td key={col.key} className="px-3 py-2 text-neutral-300 whitespace-nowrap">
                    {String(row?.[col.key] ?? '-')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {extra > 0 && (
        <div className="border-t border-neutral-900 bg-[#0A0A0A] px-3 py-2 text-[11px] text-neutral-500">
          +{extra} more rows — open workbench to see all
        </div>
      )}
    </div>
  );
}

function ErrorBanner({ error }) {
  if (!error) return null;
  return (
    <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-red-900/40 bg-red-950/20 px-3 py-2.5">
      <AlertTriangle size={14} className="text-red-400 shrink-0 mt-0.5" />
      <span className="text-[13px] text-red-300">{error}</span>
    </div>
  );
}

function AssistantMessageItem({ message, onOpenCanvas, onNavigate }) {
  const artifacts = message.artifacts || [];
  const hasChart = artifacts.some(a => a.kind === 'chart');
  const kpiArtifact = !hasChart ? artifacts.find(a => a.kind === 'kpi-grid') : null;
  const tableArtifact = !hasChart && !kpiArtifact ? artifacts.find(a => a.kind === 'table') : null;
  const hasAnyArtifact = artifacts.length > 0;
  const chartCount = artifacts.filter(a => a.kind === 'chart').length;
  const workbenchLabel = hasChart
    ? (chartCount > 1 ? `Open Workbench (${chartCount} charts)` : 'Open Workbench')
    : kpiArtifact ? 'View Full Data' : 'Explore Data';
  const intentBadge = message.intent && message.intent !== 'analytics'
    ? <span className="ml-2 rounded-full bg-neutral-800 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-neutral-400">{message.intent}</span>
    : null;

  return (
    <div className="max-w-[780px]">
      <div className="mb-2.5 flex items-center gap-2.5">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-500/10">
          <Bot size={13} className="text-red-400" />
        </div>
        <span className="text-[12px] font-semibold text-neutral-600">Frammer Copilot</span>
        {intentBadge}
      </div>
      <div className="pl-[34px] text-[15px] leading-[1.75] text-neutral-300">
        <ThinkingTrace actions={message.actions} />
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {message.markdown || message.content || ''}
        </ReactMarkdown>
        {kpiArtifact && <InlineKpiCards artifact={kpiArtifact} />}
        {tableArtifact && <InlineTablePreview artifact={tableArtifact} datasets={message.datasets} />}
        <ErrorBanner error={message.error} />
        {hasAnyArtifact && (
          <button
            onClick={() => onOpenCanvas(message)}
            className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-neutral-800 bg-[#111111] px-4 py-2.5 text-[13px] font-semibold text-neutral-400 transition-colors hover:border-neutral-700 hover:bg-[#171717] hover:text-neutral-200"
          >
            <Table2 size={14} />
            {workbenchLabel}
          </button>
        )}
        {!!message.suggested_actions?.length && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.suggested_actions.map(action => (
              <button
                key={`${action.label}-${action.target}`}
                onClick={() => onNavigate?.(action.filter_state || { view: action.target })}
                className="rounded-full border border-neutral-800 bg-[#0E0E0E] px-3 py-1.5 text-xs font-semibold text-neutral-400 transition-colors hover:border-neutral-700 hover:text-neutral-200"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ message }) {
  return (
    <div className="max-w-[780px]">
      <div className="text-[15px] font-medium leading-[1.75] text-white">{message.content}</div>
    </div>
  );
}

function StreamingIndicator({ phase, planSteps, completedSteps }) {
  const phaseLabel = PHASE_LABELS[phase] || 'Working...';

  return (
    <div className="max-w-[780px]">
      <div className="mb-2.5 flex items-center gap-2.5">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-500/10">
          <Loader2 size={13} className="animate-spin text-red-400" />
        </div>
        <span className="text-[12px] font-semibold text-neutral-600">Frammer Copilot</span>
      </div>
      <div className="pl-[34px]">
        <div className="flex items-center gap-2.5 text-sm text-neutral-500 mb-3">
          <span className="dot-flow" />
          <span className="transition-all duration-300">{phaseLabel}</span>
        </div>

        {planSteps.length > 0 && (
          <div className="rounded-xl border border-neutral-800/60 bg-[#0D0D0D] overflow-hidden">
            <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-600 border-b border-neutral-800/60">
              Execution Plan
            </div>
            <div className="px-3 py-2 space-y-1.5">
              {planSteps.map((step) => {
                const isComplete = completedSteps.has(step.id);
                const isFailed = completedSteps.get(step.id) === 'error';
                return (
                  <div key={step.id} className="flex items-center gap-2 text-[12px] font-mono">
                    {isComplete ? (
                      isFailed ? (
                        <AlertTriangle size={11} className="text-red-400 shrink-0" />
                      ) : (
                        <CheckCircle2 size={11} className="text-emerald-400 shrink-0" />
                      )
                    ) : (
                      <div className="h-[11px] w-[11px] rounded-full border border-neutral-700 shrink-0" />
                    )}
                    <span className={isComplete ? (isFailed ? 'text-red-400' : 'text-neutral-400') : 'text-neutral-600'}>
                      {step.description || step.action}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onSelect }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 py-12">
      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-red-500/20 bg-gradient-to-br from-red-500/20 to-red-500/5 shadow-[0_0_40px_rgba(239,68,68,0.12)]">
        <Bot size={32} className="text-red-400" />
      </div>
      <h2 className="mt-6 text-2xl font-bold text-white">Data Workbench</h2>
      <p className="mt-2 max-w-sm text-center text-[14px] leading-relaxed text-neutral-500">
        Ask a question in plain English. The agent writes SQL, executes it, and returns charts, KPIs, and tables.
      </p>
      <div className="mt-5 flex items-center gap-4 text-[12px] font-semibold text-neutral-600">
        {[
          { icon: BarChart3, label: 'Charts' },
          { icon: Table2, label: 'Tables' },
          { icon: Database, label: 'SQL' },
          { icon: Sparkles, label: 'AI Insights' },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <Icon size={12} className="text-neutral-600" />
            {label}
          </div>
        ))}
      </div>
      <div className="mt-8 grid w-full max-w-2xl grid-cols-1 gap-3 md:grid-cols-2">
        {SUGGESTIONS.map(({ icon: Icon, label, category }) => (
          <button
            key={label}
            onClick={() => onSelect(label)}
            className="group relative rounded-2xl border border-neutral-800 bg-[#0E0E0E] p-4 text-left transition-colors hover:border-neutral-700 hover:bg-[#111111]"
          >
            <div className="mb-2 flex items-start justify-between">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-800/60 text-neutral-500 group-hover:text-neutral-300 transition-colors">
                <Icon size={13} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-600">{category}</span>
            </div>
            <p className="text-[13px] leading-relaxed text-neutral-400 group-hover:text-neutral-200 transition-colors">{label}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function HistorySidebar({ conversations, activeId, onSelect, onNew, onDelete, collapsed, onToggle }) {
  return (
    <div className={`flex h-full shrink-0 flex-col border-r border-neutral-800 bg-[#0A0A0A] transition-all duration-200 ${collapsed ? 'w-[48px]' : 'w-[260px]'}`}>
      {collapsed ? (
        <div className="flex flex-col items-center gap-2 pt-3">
          <button
            onClick={onToggle}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-500 transition-colors hover:bg-[#171717] hover:text-neutral-300"
            title="Expand sidebar"
          >
            <PanelLeft size={16} />
          </button>
          <button
            onClick={onNew}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-500 transition-colors hover:bg-[#171717] hover:text-neutral-300"
            title="New conversation"
          >
            <Plus size={14} />
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 border-b border-neutral-800 p-3">
            <button
              onClick={onNew}
              className="flex flex-1 items-center gap-2 rounded-2xl border border-neutral-800 bg-[#111111] px-3 py-3 text-[13px] font-semibold text-neutral-300 transition-colors hover:bg-[#171717]"
            >
              <Plus size={14} />
              New conversation
            </button>
            <button
              onClick={onToggle}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-neutral-600 transition-colors hover:bg-[#171717] hover:text-neutral-300"
              title="Collapse sidebar"
            >
              <PanelLeftClose size={15} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {conversations.map(conversation => (
              <div
                key={conversation.id}
                className={`group flex cursor-pointer items-center gap-2 rounded-2xl px-3 py-3 transition-colors ${
                  conversation.id === activeId
                    ? 'bg-[#171717] text-white'
                    : 'text-neutral-500 hover:bg-[#111111] hover:text-neutral-300'
                }`}
                onClick={() => onSelect(conversation.id)}
              >
                <MessageSquare size={13} className="shrink-0" />
                <span className="flex-1 truncate text-[13px]">{conversation.title || 'New conversation'}</span>
                <button
                  onClick={e => { e.stopPropagation(); onDelete(conversation.id); }}
                  className="opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function TalkToDataModule({ authToken, routeState, onNavigate }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [canvasMessage, setCanvasMessage] = useState(null);
  // Streaming state
  const [streamPhase, setStreamPhase] = useState('');
  const [planSteps, setPlanSteps] = useState([]);
  const [completedSteps, setCompletedSteps] = useState(new Map());
  const endRef = useRef(null);

  const voice = useVoiceInput({
    onResult: text => setInput(prev => (prev ? `${prev} ${text}` : text)),
  });

  useEffect(() => {
    if (routeState?.prompt) setInput(routeState.prompt);
  }, [routeState?.prompt]);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, streamPhase, completedSteps]);

  useEffect(() => { fetchConversations(); }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (!res.ok) return;
      const payload = await res.json();
      setConversations(payload.conversations || []);
    } catch { /* keep UI resilient */ }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setCanvasMessage(null);
    setInput(routeState?.prompt || '');
  };

  const handleSelectConversation = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (!res.ok) return;
      const payload = await res.json();
      setConversationId(id);
      setCanvasMessage(null);
      setMessages(payload.messages || []);
    } catch { /* ignore */ }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await fetch(`${API_BASE}/conversations/${id}`, {
        method: 'DELETE',
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      setConversations(curr => curr.filter(c => c.id !== id));
      if (id === conversationId) handleNewConversation();
    } catch { /* ignore */ }
  };

  const send = async (overrideValue) => {
    const text = (overrideValue || input).trim();
    if (!text || loading) return;

    setInput('');
    setMessages(curr => [...curr, { role: 'user', content: text }]);
    setLoading(true);
    setStreamPhase('');
    setPlanSteps([]);
    setCompletedSteps(new Map());

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ message: text, filters: {}, conversation_id: conversationId }),
      });

      if (!res.ok) {
        const errPayload = await res.json().catch(() => ({}));
        throw new Error(errPayload.detail || errPayload.error || `Request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') continue;

          try {
            const event = JSON.parse(data);

            switch (event.type) {
              case 'init':
                if (event.conversation_id) setConversationId(event.conversation_id);
                break;

              case 'phase':
                setStreamPhase(event.phase);
                break;

              case 'plan':
                setPlanSteps(event.steps || []);
                break;

              case 'step_complete':
                setCompletedSteps(prev => {
                  const next = new Map(prev);
                  next.set(event.step_id, event.status);
                  return next;
                });
                break;

              case 'complete': {
                const msg = event.message || {};
                const assistantMessage = {
                  role: 'assistant',
                  content: msg.markdown || event.response || '',
                  markdown: msg.markdown || event.response || '',
                  artifacts: msg.artifacts || [],
                  datasets: msg.datasets || [],
                  suggested_actions: msg.suggested_actions || [],
                  actions: msg.actions || event.actions || [],
                  intent: msg.intent || 'analytics',
                  sql: msg.sql || '',
                  error: msg.error || '',
                  report_xml: msg.report_xml || event.report_xml || '',
                };
                setMessages(curr => [...curr, assistantMessage]);
                if (shouldAutoOpenCanvas(assistantMessage.artifacts)) {
                  setCanvasMessage(assistantMessage);
                }
                // Reset streaming state
                setStreamPhase('');
                setPlanSteps([]);
                setCompletedSteps(new Map());
                fetchConversations();
                break;
              }

              case 'error':
                setMessages(curr => [...curr, {
                  role: 'assistant',
                  markdown: `Something went wrong: ${event.error}`,
                  content: `Something went wrong: ${event.error}`,
                  artifacts: [],
                  datasets: [],
                  suggested_actions: [],
                  actions: [],
                  intent: 'error',
                  sql: '',
                  error: event.error,
                }]);
                setStreamPhase('');
                setPlanSteps([]);
                setCompletedSteps(new Map());
                break;

              default:
                break;
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }
    } catch (err) {
      // Fallback: if streaming fails, try the non-streaming endpoint
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
          },
          body: JSON.stringify({ message: text, filters: {}, conversation_id: conversationId }),
        });
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.detail || payload.error || `Request failed: ${res.status}`);

        if (payload.conversation_id) setConversationId(payload.conversation_id);

        const assistantMessage = {
          role: 'assistant',
          content: payload.response || '',
          markdown: payload.message?.markdown || payload.response || '',
          artifacts: payload.message?.artifacts || [],
          datasets: payload.message?.datasets || [],
          suggested_actions: payload.message?.suggested_actions || [],
          actions: payload.actions || [],
          intent: payload.message?.intent || payload.intent || 'analytics',
          sql: payload.message?.sql || payload.sql || '',
          error: payload.message?.error || payload.error || '',
          report_xml: payload.message?.report_xml || payload.report_xml || '',
        };
        setMessages(curr => [...curr, assistantMessage]);
        if (shouldAutoOpenCanvas(assistantMessage.artifacts)) {
          setCanvasMessage(assistantMessage);
        }
        fetchConversations();
      } catch (fallbackErr) {
        setMessages(curr => [...curr, {
          role: 'assistant',
          markdown: `Something went wrong: ${fallbackErr.message}`,
          content: `Something went wrong: ${fallbackErr.message}`,
          artifacts: [],
          datasets: [],
          suggested_actions: [],
          actions: [],
          intent: 'error',
          sql: '',
          error: fallbackErr.message,
        }]);
      }
    } finally {
      setLoading(false);
      setStreamPhase('');
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
        collapsed={!sidebarOpen}
        onToggle={() => setSidebarOpen(o => !o)}
      />

      <div className={`flex min-w-0 flex-col transition-all duration-300 ${canvasMessage ? 'w-[44%]' : 'flex-1'}`}>
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !loading ? (
            <EmptyState onSelect={text => send(text)} />
          ) : (
            <div className="mx-auto max-w-4xl space-y-8 px-6 py-6">
              {messages.map((message, index) => (
                <div key={`${message.role}-${index}`}>
                  {message.role === 'user'
                    ? <UserMessage message={message} />
                    : <AssistantMessageItem message={message} onOpenCanvas={setCanvasMessage} onNavigate={onNavigate} />}
                </div>
              ))}
              {loading && (
                <StreamingIndicator
                  phase={streamPhase}
                  planSteps={planSteps}
                  completedSteps={completedSteps}
                />
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <div className="border-t border-neutral-800/40 bg-[#080808] px-4 py-4">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-center rounded-2xl border border-neutral-800 bg-[#111111] focus-within:border-neutral-600">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={voice.listening ? 'Listening...' : 'Ask Copilot about your data...'}
                disabled={loading}
                className="flex-1 bg-transparent px-5 py-4 text-[15px] text-white placeholder-neutral-600 focus:outline-none disabled:opacity-50"
              />
              {voice.supported && (
                <button
                  onClick={voice.toggle}
                  disabled={loading}
                  type="button"
                  className={`mr-2 rounded-xl p-2.5 transition-all ${
                    voice.listening
                      ? 'bg-red-500 text-white'
                      : 'bg-[#1A1A1A] text-neutral-400 hover:bg-neutral-700 hover:text-white'
                  }`}
                >
                  {voice.listening ? <MicOff size={15} /> : <Mic size={15} />}
                </button>
              )}
              <button
                onClick={() => send()}
                disabled={loading || !input.trim()}
                className="mr-2 rounded-xl bg-white p-2.5 text-black transition-colors hover:bg-neutral-200 disabled:opacity-30"
              >
                <Send size={15} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {canvasMessage && (
        <div className="flex flex-1 flex-col border-l border-neutral-800/50 bg-[#0B0B0B]">
          <ArtifactCanvas
            artifacts={canvasMessage.artifacts || []}
            datasets={canvasMessage.datasets || []}
            sql={canvasMessage.sql || ''}
            reportXml={canvasMessage.report_xml || ''}
            onClose={() => setCanvasMessage(null)}
          />
        </div>
      )}
    </div>
  );
}
