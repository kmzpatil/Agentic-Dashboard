import React from 'react';
import { ArrowRight, AlertTriangle, Sparkles } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: {
    badge: 'bg-red-500/10 text-red-300 border-red-500/20',
    icon: <AlertTriangle size={14} />,
  },
  warning: {
    badge: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    icon: <Sparkles size={14} />,
  },
  info: {
    badge: 'bg-sky-500/10 text-sky-300 border-sky-500/20',
    icon: <Sparkles size={14} />,
  },
};

export default function InsightCard({ insight, onNavigate }) {
  const tone = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;

  return (
    <div className="rounded-3xl border border-neutral-800 bg-[#111111] p-5">
      <div className="flex items-start justify-between gap-4">
        <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] ${tone.badge}`}>
          {tone.icon}
          {insight.severity}
        </div>
        <div className="text-[11px] uppercase tracking-[0.18em] text-neutral-600">
          {Math.round((insight.confidence || 0) * 100)}% confidence
        </div>
      </div>
      <h3 className="mt-4 text-lg font-bold tracking-tight text-white">{insight.title}</h3>
      <p className="mt-2 text-sm leading-6 text-neutral-400">{insight.summary}</p>
      {!!insight.evidence?.length && (
        <div className="mt-4 flex flex-wrap gap-2">
          {insight.evidence.map((item) => (
            <span key={item} className="rounded-full bg-[#171717] px-3 py-1 text-[11px] font-medium text-neutral-500">
              {item}
            </span>
          ))}
        </div>
      )}
      <button
        onClick={() => onNavigate?.(insight.cta?.filter_state || { view: insight.cta?.target })}
        className="mt-5 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-bold text-black transition-colors hover:bg-neutral-200"
      >
        {insight.cta?.label || 'Open'}
        <ArrowRight size={15} />
      </button>
    </div>
  );
}
