import React from 'react';
import { Send, Mic, MicOff } from 'lucide-react';
import useVoiceInput from '../../hooks/useVoiceInput';

const DEFAULT_PROMPTS = [
  'Top 5 channels by uploads',
  'Monthly upload trend',
  'Conversion rate by output type',
];

export default function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = 'Ask Frammer AI anything...',
  suggestions = DEFAULT_PROMPTS,
}) {
  const voice = useVoiceInput({
    onResult: (text) => {
      onChange((prev) => {
        const prevStr = typeof prev === 'string' ? prev : '';
        return prevStr ? `${prevStr} ${text}` : text;
      });
    },
  });

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div>
      <div className="relative flex items-center">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={voice.listening ? '🎙️ Listening...' : placeholder}
          disabled={disabled}
          className="w-full pl-5 pr-24 py-3.5 bg-[#111111] border border-neutral-800 rounded-full text-sm text-white focus:outline-none focus:border-red-500 transition-all disabled:opacity-50"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {voice.supported && (
            <button
              onClick={voice.toggle}
              disabled={disabled}
              type="button"
              className={`p-2 rounded-full transition-all active:scale-95 disabled:opacity-50 ${
                voice.listening
                  ? 'bg-red-500 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.6)]'
                  : 'bg-[#1A1A1A] text-neutral-400 hover:bg-neutral-700 hover:text-white'
              }`}
              title={voice.listening ? 'Stop listening' : 'Voice input'}
            >
              {voice.listening ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
          )}
          <button
            onClick={onSend}
            disabled={disabled}
            className="p-2 bg-white text-black rounded-full hover:bg-neutral-200 transition-transform active:scale-95 disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
      {suggestions && suggestions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((prompt) => (
            <span
              key={prompt}
              onClick={() => onChange(prompt)}
              className="text-xs bg-[#1A1A1A] text-neutral-400 font-bold px-3 py-1.5 rounded-full cursor-pointer hover:bg-white hover:text-black transition-colors border border-neutral-800 hover:border-white"
            >
              {prompt}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
