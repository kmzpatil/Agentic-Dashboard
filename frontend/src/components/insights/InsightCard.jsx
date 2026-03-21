import React from 'react';
import { ArrowRight } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: {
    text: 'text-red-300',
    dot: 'bg-red-400',
  },
  warning: {
    text: 'text-amber-300',
    dot: 'bg-amber-300',
  },
  info: {
    text: 'text-sky-300',
    dot: 'bg-sky-300',
  },
};

export default function InsightCard({ insight, onNavigate }) {
  const tone = SEVERITY_STYLES[insight.severity] || SEVERITY_STYLES.info;
  const confidencePct = Math.round((insight.confidence || 0) * 100);
  const evidence = Array.isArray(insight.evidence) ? insight.evidence : [];
  const visibleEvidence = evidence.slice(0, 2);
  const extraEvidenceCount = Math.max(evidence.length - visibleEvidence.length, 0);
  const severityLabel = String(insight.severity || 'info');

  return (
    <div className="rounded-2xl border border-neutral-700/70 bg-[#111214] px-4 py-3.5 transition-colors hover:border-neutral-500/80 hover:bg-[#15171c]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
            <span className={`text-[11px] font-semibold tracking-wide uppercase ${tone.text}`}>
              {severityLabel}
            </span>
          </div>
          <h3 className="text-[14px] font-semibold text-white leading-snug line-clamp-1">
            {insight.title}
          </h3>
          <p className="mt-1.5 text-[13px] leading-[1.55] text-neutral-300 line-clamp-2">
            {insight.summary}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-neutral-600 bg-neutral-800/60 px-2 py-0.5 text-[11px] tabular-nums text-neutral-200">
          {confidencePct}% conf
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        {evidence.length > 0 ? (
          <div className="min-w-0 flex-1 text-[11px] text-neutral-400 truncate">
            <span className="text-neutral-500">Evidence:</span>{' '}
            {visibleEvidence.join(' • ')}
            {extraEvidenceCount > 0 ? ` +${extraEvidenceCount}` : ''}
          </div>
        ) : (
          <div />
        )}
        <button
          onClick={() => onNavigate?.(insight.cta?.filter_state || { view: insight.cta?.target })}
          className="shrink-0 ml-auto inline-flex items-center gap-1.5 rounded-lg border border-neutral-600 bg-neutral-800/50 px-3 py-1.5 text-[11px] font-semibold text-neutral-200 transition-colors hover:border-neutral-400 hover:text-white hover:bg-neutral-700/60"
        >
          {insight.cta?.label || 'Open'}
          <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}
