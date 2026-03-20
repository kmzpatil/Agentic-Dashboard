import React from 'react';
import { ArrowRight, AlertTriangle, Sparkles, Info } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: {
    badge: 'bg-red-500/10 text-red-400 border-red-500/20',
    accent: 'border-l-red-500',
    icon: <AlertTriangle size={13} />,
  },
  warning: {
    badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    accent: 'border-l-amber-500',
    icon: <Sparkles size={13} />,
  },
  info: {
    badge: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    accent: 'border-l-sky-500',
    icon: <Info size={13} />,
  },
};

export default function InsightCard({ insight, onNavigate }) {
  const tone = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;

  return (
    <div className={`rounded-2xl border border-neutral-800/60 bg-[#0C0C0C] border-l-[3px] ${tone.accent} px-4 py-3.5 transition-colors hover:bg-[#111111] h-full flex flex-col justify-between`}>
      <div>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.15em] shrink-0 ${tone.badge}`}>
              {tone.icon}
              {insight.severity}
            </div>
            <h3 className="text-[13px] font-semibold text-white truncate">{insight.title}</h3>
          </div>
          <span className="text-[10px] tabular-nums text-neutral-600 shrink-0">
            {Math.round((insight.confidence || 0) * 100)}%
          </span>
        </div>
        <p className="mt-1.5 text-xs leading-[1.6] text-neutral-500 line-clamp-2">{insight.summary}</p>
      </div>
      <div className="mt-2.5 flex items-center justify-between gap-3">
        {!!insight.evidence?.length ? (
          <div className="flex flex-wrap gap-1.5 min-w-0">
            {insight.evidence.slice(0, 3).map((item) => (
              <span key={item} className="rounded-md bg-neutral-800/50 px-2 py-0.5 text-[10px] font-medium text-neutral-500 truncate max-w-[120px]">
                {item}
              </span>
            ))}
          </div>
        ) : <div />}
        <button
          onClick={() => onNavigate?.(insight.cta?.filter_state || { view: insight.cta?.target })}
          className="inline-flex items-center gap-1 rounded-lg bg-white/5 border border-neutral-700/50 px-2.5 py-1 text-[11px] font-semibold text-neutral-300 transition-colors hover:bg-white/10 hover:text-white shrink-0"
        >
          {insight.cta?.label || 'Open'}
          <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}
