import React from 'react';
import { ArrowRight, AlertTriangle, Info, Sparkles } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: {
    badge: 'bg-red-500/10 text-red-300 border-red-500/20',
    accent: 'border-l-red-500',
    icon: <AlertTriangle size={12} />,
  },
  warning: {
    badge: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    accent: 'border-l-amber-400',
    icon: <Sparkles size={12} />,
  },
  info: {
    badge: 'bg-sky-500/10 text-sky-300 border-sky-500/20',
    accent: 'border-l-sky-500',
    icon: <Info size={12} />,
  },
};

export default function InsightCard({ insight, onNavigate }) {
  const tone = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;

  return (
    <div className={`rounded-2xl border border-neutral-800/60 bg-[#0C0C0C] border-l-[3px] ${tone.accent} px-4 py-3.5 h-full flex flex-col justify-between transition-colors hover:bg-[#111111]`}>
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
            {insight.evidence.map((item) => (
              <span key={item} className="rounded-md bg-neutral-800/60 px-2 py-0.5 text-[10px] font-medium text-neutral-500 truncate max-w-[120px]">
                {item}
              </span>
            ))}
          </div>
        ) : <div />}
        <button
          onClick={() => onNavigate?.(insight.cta?.filter_state || { view: insight.cta?.target })}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-neutral-700 bg-neutral-800/50 px-3 py-1.5 text-[11px] font-bold text-neutral-300 transition-colors hover:border-neutral-500 hover:text-white hover:bg-neutral-700"
        >
          {insight.cta?.label || 'Open'}
          <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}
