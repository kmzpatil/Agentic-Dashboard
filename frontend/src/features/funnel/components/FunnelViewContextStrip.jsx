import React from 'react';

function formatViewLabel(value) {
  return String(value || 'channel')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default function FunnelViewContextStrip({ breakdown, filters }) {
  const viewLabel = formatViewLabel(breakdown);
  const activeFilters = Object.entries(filters || {}).filter(([, value]) => value);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="inline-flex items-center rounded-full border border-neutral-700/80 bg-neutral-900/70 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
        View by: {viewLabel}
      </span>
      {activeFilters.length > 0 && (
        <span className="inline-flex items-center rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-[11px] font-semibold text-violet-300">
          {activeFilters.length} filter{activeFilters.length > 1 ? 's' : ''} active
        </span>
      )}
    </div>
  );
}