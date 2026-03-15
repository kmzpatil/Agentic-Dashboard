import React, { useEffect, useRef, useState } from 'react';
import {
  Bot,
  Loader2,
  MessageSquare,
  Mic,
  MicOff,
  PanelRightOpen,
  Plus,
  Send,
  Trash2,
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

const SUGGESTIONS = [
  'Summarize the latest pipeline health',
  'Which channels are losing conversion?',
  'Show the monthly uploaded trend',
  'What should I investigate next?',
];

function HistorySidebar({ conversations, activeId, onSelect, onNew, onDelete }) {
  return (
    <div className="flex h-full w-[260px] shrink-0 flex-col border-r border-neutral-800 bg-[#0A0A0A]">
      <div className="border-b border-neutral-800 p-3">
        <button
          onClick={onNew}
          className="flex w-full items-center gap-2 rounded-2xl border border-neutral-800 bg-[#111111] px-3 py-3 text-[13px] font-semibold text-neutral-300 transition-colors hover:bg-[#171717]"
        >
          <Plus size={14} />
          New conversation
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {conversations.map((conversation) => (
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
              onClick={(event) => {
                event.stopPropagation();
                onDelete(conversation.id);
              }}
              className="opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function AssistantMessage({ message, onOpenCanvas, onNavigate }) {
  const hasArtifacts = (message.artifacts || []).length > 0;

  return (
    <div className="max-w-[780px]">
      <div className="mb-2.5 flex items-center gap-2.5">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-500/10">
          <Bot size={13} className="text-red-400" />
        </div>
        <span className="text-[12px] font-semibold text-neutral-600">Frammer Copilot</span>
      </div>

      <div className="pl-[34px] text-[15px] leading-[1.75] text-neutral-300">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {message.markdown || message.content || ''}
        </ReactMarkdown>

        {hasArtifacts && (
          <button
            onClick={() => onOpenCanvas(message)}
            className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-neutral-800 bg-[#111111] px-4 py-2.5 text-[13px] font-semibold text-neutral-400 transition-colors hover:border-neutral-700 hover:bg-[#171717] hover:text-neutral-200"
          >
            <PanelRightOpen size={14} />
            View analysis
          </button>
        )}

        {!!message.suggested_actions?.length && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.suggested_actions.map((action) => (
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

function LoadingIndicator() {
  return (
    <div className="max-w-[780px]">
      <div className="mb-2.5 flex items-center gap-2.5">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-500/10">
          <Loader2 size={13} className="animate-spin text-red-400" />
        </div>
        <span className="text-[12px] font-semibold text-neutral-600">Frammer Copilot</span>
      </div>
      <div className="pl-[34px] text-sm text-neutral-500">Analyzing your data and building artifacts...</div>
    </div>
  );
}

function EmptyState({ onSelect }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-red-500/20 bg-gradient-to-br from-red-500/20 to-red-500/5">
        <Bot size={28} className="text-red-400" />
      </div>
      <h2 className="mt-6 text-2xl font-bold text-white">Copilot</h2>
      <p className="mt-2 max-w-md text-center text-[14px] leading-relaxed text-neutral-500">
        Ask a question in plain English and Copilot will query the backend, return typed artifacts, and suggest where to drill next.
      </p>
      <div className="mt-8 grid w-full max-w-2xl grid-cols-1 gap-3 md:grid-cols-2">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            onClick={() => onSelect(text)}
            className="rounded-2xl border border-neutral-800 bg-[#0E0E0E] p-4 text-left text-[14px] text-neutral-400 transition-colors hover:border-neutral-700 hover:bg-[#111111] hover:text-neutral-200"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function TalkToDataModule({ authToken, routeState, onNavigate }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [canvasMessage, setCanvasMessage] = useState(null);
  const endRef = useRef(null);

  const voice = useVoiceInput({
    onResult: (text) => setInput((previous) => (previous ? `${previous} ${text}` : text)),
  });

  useEffect(() => {
    if (routeState?.prompt) {
      setInput(routeState.prompt);
    }
  }, [routeState?.prompt]);

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
      if (!res.ok) return;
      const payload = await res.json();
      setConversations(payload.conversations || []);
    } catch {
      // Keep UI resilient if the assistant runtime is unavailable.
    }
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
    } catch {
      // Ignore and keep the current panel stable.
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await fetch(`${API_BASE}/conversations/${id}`, {
        method: 'DELETE',
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      setConversations((current) => current.filter((conversation) => conversation.id !== id));
      if (id === conversationId) handleNewConversation();
    } catch {
      // Ignore.
    }
  };

  const send = async (overrideValue) => {
    const text = (overrideValue || input).trim();
    if (!text || loading) return;

    setInput('');
    setMessages((current) => [...current, { role: 'user', content: text }]);
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
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.detail || payload.error || `Request failed: ${res.status}`);

      if (payload.conversation_id) {
        setConversationId(payload.conversation_id);
      }

      const assistantMessage = {
        role: 'assistant',
        content: payload.response || '',
        markdown: payload.message?.markdown || payload.response || '',
        artifacts: payload.message?.artifacts || [],
        datasets: payload.message?.datasets || [],
        suggested_actions: payload.message?.suggested_actions || [],
        intent: payload.message?.intent || 'analytics',
        error: payload.error || '',
      };
      setMessages((current) => [...current, assistantMessage]);
      if ((assistantMessage.artifacts || []).length) {
        setCanvasMessage(assistantMessage);
      }
      fetchConversations();
    } catch (error) {
      setMessages((current) => [...current, {
        role: 'assistant',
        markdown: `Something went wrong: ${error.message}`,
        content: `Something went wrong: ${error.message}`,
        artifacts: [],
        datasets: [],
        suggested_actions: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
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

      <div className={`flex min-w-0 flex-col transition-all duration-300 ${canvasMessage ? 'w-[48%]' : 'flex-1'}`}>
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState onSelect={(text) => send(text)} />
          ) : (
            <div className="mx-auto max-w-4xl space-y-8 px-6 py-6">
              {messages.map((message, index) => (
                <div key={`${message.role}-${index}`}>
                  {message.role === 'user'
                    ? <UserMessage message={message} />
                    : <AssistantMessage message={message} onOpenCanvas={setCanvasMessage} onNavigate={onNavigate} />}
                </div>
              ))}
              {loading && <LoadingIndicator />}
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
                onChange={(event) => setInput(event.target.value)}
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
        <div className="flex-1 border-l border-neutral-800/50 bg-[#0C0C0C]">
          <div className="border-b border-neutral-800/50 px-5 py-4">
            <div className="text-[12px] font-bold uppercase tracking-[0.2em] text-neutral-500">Artifact Canvas</div>
          </div>
          <div className="h-[calc(100%-57px)] overflow-y-auto p-5">
            <ArtifactCanvas artifacts={canvasMessage.artifacts || []} datasets={canvasMessage.datasets || []} />
          </div>
        </div>
      )}
    </div>
  );
}
