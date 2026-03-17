import React from 'react';
import { Chart } from 'react-chartjs-2';
import PipelineStrip from './PipelineStrip';

export default function OverviewFlowTab({
  data,
  breakdown,
  filters,
  groupedCompositionCount,
  stageSankeyData,
  stageSankeyOptions,
  compositionSankeyData,
  compositionSankeyOptions,
  compositionChartRef,
  handleCompositionClick,
  handleCompositionChartHover,
  compositionSourceMode,
  onCompositionSourceModeChange,
  compositionTopN,
  onCompositionTopNChange,
  totalBreakdownSources,
  hiddenBreakdownSources,
}) {
  const TOP_N_OPTIONS = [5, 8, 10, 12, 15, 20, 30, 50];
  const activeFilters = Object.entries(filters || {}).filter(([, v]) => v);
  const stageLinks = stageSankeyData?.datasets?.[0]?.data || [];
  const compositionLinks = compositionSankeyData?.datasets?.[0]?.data || [];
  const stageLinksCount = stageLinks.length;
  const compositionLinksCount = compositionLinks.length;
  const stageSignature = stageLinks.map((link) => `${link.from}|${link.to}|${Number(link.flow || 0).toFixed(3)}`).join('~');
  const compositionSignature = compositionLinks.map((link) => `${link.from}|${link.to}|${Number(link.flow || 0).toFixed(3)}`).join('~');
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center rounded-full border border-neutral-700/80 bg-neutral-900/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          View by: {breakdown.replace('_', ' ')}
        </span>
        {activeFilters.length > 0 && (
          <span className="inline-flex items-center rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-[10px] font-semibold text-violet-300">
            {activeFilters.length} filter{activeFilters.length > 1 ? 's' : ''} active
          </span>
        )}
      </div>

      <PipelineStrip data={data} />

      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <span className="text-[9.5px] font-bold uppercase tracking-[0.2em] text-neutral-600">Flow breakdown</span>
          <div className="flex-1 h-px bg-neutral-900" />
        </div>
        <div className="flex flex-wrap gap-2">
          {groupedCompositionCount > 0 && (
            <span className="rounded-full border border-neutral-700/70 bg-neutral-900/70 px-3 py-1 text-[10.5px] font-semibold text-neutral-300">
              Grouped minor links: {groupedCompositionCount}
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 xl:gap-10 items-start">
          <div className="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-b from-emerald-950/20 via-neutral-950 to-black px-4 py-4 sm:px-5 sm:py-5">
            <div className="pointer-events-none absolute -top-16 right-0 h-40 w-40 rounded-full bg-emerald-400/10 blur-3xl" aria-hidden />
            <div className="flex items-center justify-between gap-3 mb-1">
              <h3 className="text-[13px] font-semibold text-neutral-100">Stage flow</h3>
            </div>
            <p className="text-[11.5px] text-neutral-400 mb-3.5">Upload {'->'} Processed {'->'} Created {'->'} Published</p>
            <div className="h-[360px] sm:h-[390px]" aria-label="Stage flow sankey">
              {stageLinksCount > 0 ? (
                <Chart key={`stage-${breakdown}-${stageSignature}`} type="sankey" data={stageSankeyData} options={stageSankeyOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-neutral-600 text-sm">No stage flow data for current filters</div>
              )}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-2xl border border-rose-500/20 bg-gradient-to-b from-rose-950/20 via-neutral-950 to-black px-4 py-4 sm:px-5 sm:py-5">
            <div className="pointer-events-none absolute -top-16 left-2 h-40 w-40 rounded-full bg-rose-400/10 blur-3xl" aria-hidden />
            <div className="flex items-center justify-between gap-3 mb-1">
              <h3 className="text-[13px] font-semibold text-neutral-100">
                {breakdown === 'client' ? 'Client -> Outcome -> Platform' : `${breakdown.replace('_', ' ')} -> Outcome -> Platform`}
              </h3>
            </div>
            <p className="text-[11.5px] text-neutral-400 mb-1.5">
              {breakdown === 'client'
                ? 'Client splits into published vs not-published, then into platforms'
                : 'Selected category splits into published vs not-published, then published branches into platforms'}
            </p>
            {breakdown !== 'client' && (
              <div className="mb-3.5 flex flex-wrap items-center gap-2">
                <button
                  className={[
                    'px-2.5 py-1 rounded-full text-[10.5px] font-semibold transition-colors',
                    compositionSourceMode === 'top'
                      ? 'bg-white/10 text-white ring-1 ring-white/15'
                      : 'bg-neutral-900 text-neutral-400 hover:text-neutral-200',
                  ].join(' ')}
                  onClick={() => onCompositionSourceModeChange?.('top')}
                >
                  Top N + Other
                </button>
                <button
                  className={[
                    'px-2.5 py-1 rounded-full text-[10.5px] font-semibold transition-colors',
                    compositionSourceMode === 'all'
                      ? 'bg-white/10 text-white ring-1 ring-white/15'
                      : 'bg-neutral-900 text-neutral-400 hover:text-neutral-200',
                  ].join(' ')}
                  onClick={() => onCompositionSourceModeChange?.('all')}
                >
                  Show all
                </button>
                {compositionSourceMode === 'top' && (
                  <select
                    value={compositionTopN}
                    onChange={(event) => onCompositionTopNChange?.(Number(event.target.value) || compositionTopN)}
                    className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-[10.5px] text-neutral-300"
                  >
                    {TOP_N_OPTIONS.map((n) => (
                      <option key={n} value={n}>Top {n}</option>
                    ))}
                  </select>
                )}
              </div>
            )}
            <p className="text-[10px] text-neutral-600 mb-3">
              {breakdown === 'client'
                ? `Showing ${totalBreakdownSources} client sources`
                : compositionSourceMode === 'all'
                  ? `Showing all ${totalBreakdownSources} ${breakdown.replace('_', ' ')} sources`
                  : `Showing top ${compositionTopN} ${breakdown.replace('_', ' ')} sources + Other (${hiddenBreakdownSources} grouped)`}
            </p>
            <div className="h-[360px] sm:h-[390px]" aria-label="Composition outcome platform sankey">
              {compositionLinksCount > 0 ? (
                <Chart
                  key={`composition-${breakdown}-${compositionSignature}`}
                  ref={compositionChartRef}
                  type="sankey"
                  data={compositionSankeyData}
                  options={compositionSankeyOptions}
                  onClick={handleCompositionClick}
                  onHover={handleCompositionChartHover}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-neutral-600 text-sm">No composition data for current filters</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
