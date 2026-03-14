import React, { useEffect, useRef, useState } from 'react';
import { MessageSquare, ChevronRight } from 'lucide-react';
import { API_BASE } from '../../lib/constants';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';

function StatusPill({ label, ok }) {
  const tone = ok
    ? 'border-emerald-500/30 text-emerald-300 bg-emerald-500/10'
    : 'border-amber-500/30 text-amber-300 bg-amber-500/10';
  return (
    <div className={`rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] ${tone}`}>
      {label}: {ok ? 'online' : 'offline'}
    </div>
  );
}

export default function ChatPanel({ isOpen, onClose, authToken, agentOk, databaseOk }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();

    if (agentOk === false) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'The Frammer agent is offline. Start the service to chat.',
      }]);
      return;
    }

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ message: userMsg, filters: {} }),
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(result.error || `Request failed: ${res.status}`);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: result.response || 'I processed your query but have no additional insights.',
        chartData: result.chart_data,
        actions: result.actions || [],
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: err.message || 'Sorry, I encountered an error.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`absolute top-0 right-0 h-full w-[420px] bg-[#0A0A0A] shadow-[-10px_0_30px_rgba(0,0,0,0.8)] border-l border-neutral-900 transform transition-transform duration-300 ease-in-out z-30 flex flex-col ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
      {/* Header */}
      <div className="p-5 border-b border-neutral-900 flex items-center justify-between bg-[#050505] text-white shrink-0">
        <div className="flex items-center gap-2 font-black tracking-tight text-red-500 uppercase">
          <MessageSquare size={18} /> FRAMMER AI COPILOT
        </div>
        <button onClick={onClose} className="text-neutral-500 hover:text-white transition-colors bg-[#111111] p-1 rounded hover:bg-neutral-800">
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Status */}
      <div className="px-5 py-3 border-b border-neutral-900 bg-[#080808] flex flex-wrap gap-2">
        <StatusPill label="DB" ok={Boolean(databaseOk)} />
        <StatusPill label="Agent" ok={Boolean(agentOk)} />
      </div>

      {/* Messages */}
      <div className="flex-1 p-5 overflow-y-auto space-y-6 bg-[#0A0A0A]">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} msg={msg} showThinking={false} />
        ))}
        {loading && (
          <div className="bg-[#161616] text-neutral-400 p-4 rounded-2xl rounded-tl-none text-sm w-5/6 border border-neutral-800 animate-pulse">
            Frammer AI is thinking...
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-5 border-t border-neutral-900 bg-[#050505] shrink-0">
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={send}
          disabled={loading || agentOk === false}
          placeholder={agentOk === false ? 'Agent offline.' : 'Ask Frammer AI anything...'}
        />
      </div>
    </div>
  );
}
