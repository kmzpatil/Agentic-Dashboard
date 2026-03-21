import React from 'react';
import { Chart } from 'react-chartjs-2';
import PipelineStrip from './PipelineStrip';
import FunnelViewContextStrip from './FunnelViewContextStrip';

export default function OverviewFlowTab({
  data,
  breakdown,
  filters,
  groupedCompositionCount,
  stageSankeyData,
  stageSankeyOptions,
  stageChartRef,
  handleStageClick,
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
  const stageLinks = stageSankeyData?.datasets?.[0]?.data || [];
  const compositionLinks = compositionSankeyData?.datasets?.[0]?.data || [];
  const stageLinksCount = stageLinks.length;
  const compositionLinksCount = compositionLinks.length;
  const stageSignature = stageLinks.map((link) => `${link.from}|${link.to}|${Number(link.flow || 0).toFixed(3)}`).join('~');
  const compositionSignature = compositionLinks.map((link) => `${link.from}|${link.to}|${Number(link.flow || 0).toFixed(3)}`).join('~');
  const showCompositionControls = breakdown !== 'client';
  const sankeyCanvasClass = 'h-[310px] sm:h-[335px] [&>canvas]:!h-full [&>canvas]:!w-full';
  const stageHeaderClass = 'mb-1.5';
  const compositionHeaderClass = 'mb-2';
  return (
    <div className="space-y-4">
      <FunnelViewContextStrip breakdown={breakdown} filters={filters} />

      <PipelineStrip data={data} />

      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-neutral-500">Flow breakdown</span>
          <div className="flex-1 h-px bg-neutral-900" />
        </div>
        <div className="flex flex-wrap gap-2">
          {groupedCompositionCount > 0 && (
            <span className="rounded-full border border-neutral-700/70 bg-neutral-900/70 px-3 py-1 text-[11.5px] font-semibold text-neutral-300">
              Grouped minor links: {groupedCompositionCount}
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 xl:gap-6 items-stretch">
          <div className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-b from-emerald-950/20 via-neutral-950 to-black px-4 py-4">
            <div className="pointer-events-none absolute -top-16 right-0 h-40 w-40 rounded-full bg-emerald-400/10 blur-3xl" aria-hidden />
            <div className={stageHeaderClass}>
              <div className="flex items-center justify-between gap-3 mb-1">
                <h3 className="text-[14px] font-semibold text-neutral-100">Stage flow</h3>
              </div>
              <p className="text-[11px] text-neutral-400 mb-1.5">Upload {'→'} Processed (or Not Processed) {'→'} Created {'→'} Published {'→'} Platform</p>
            </div>

            <div className={sankeyCanvasClass} aria-label="Stage flow sankey">
              {stageLinksCount > 0 ? (
                <Chart
                  key={`stage-${breakdown}-${stageSignature}`}
                  ref={stageChartRef}
                  type="sankey"
                  data={stageSankeyData}
                  options={stageSankeyOptions}
                  onClick={handleStageClick}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-neutral-400 text-sm">No stage flow data for current filters</div>
              )}
            </div>

          </div>

          <div className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-rose-500/20 bg-gradient-to-b from-rose-950/20 via-neutral-950 to-black px-4 py-4">
            <div className="pointer-events-none absolute -top-16 left-2 h-40 w-40 rounded-full bg-rose-400/10 blur-3xl" aria-hidden />
            <div className={compositionHeaderClass}>
              <div className="flex items-center justify-between gap-3 mb-1">
                <h3 className="text-[14px] font-semibold text-neutral-100">
                  {breakdown === 'client' ? 'Client -> Outcome -> Platform' : `${breakdown.replace('_', ' ')} -> Outcome -> Platform`}
                </h3>
              </div>
              <p className="text-[11px] text-neutral-400 mb-1.5 leading-snug">
                {breakdown === 'client'
                  ? 'Client splits into published vs not-published, then into platforms'
                  : 'Selected category splits into published vs not-published, then published branches into platforms'}
              </p>
              {showCompositionControls && (
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                  <button
                    className={[
                      'px-2 py-0.5 rounded-full text-[11px] font-semibold transition-colors',
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
                      'px-2 py-0.5 rounded-full text-[11px] font-semibold transition-colors',
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
                      className="bg-neutral-950 border border-neutral-800 rounded px-2 py-0.5 text-[11px] text-neutral-300"
                    >
                      {TOP_N_OPTIONS.map((n) => (
                        <option key={n} value={n}>Top {n}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}
              <p className="text-[10.5px] text-neutral-400 mb-1.5 leading-snug">
                {breakdown === 'client'
                  ? `Showing ${totalBreakdownSources} client sources`
                  : compositionSourceMode === 'all'
                    ? `Showing all ${totalBreakdownSources} ${breakdown.replace('_', ' ')} sources`
                    : `Showing top ${compositionTopN} ${breakdown.replace('_', ' ')} sources + Other (${hiddenBreakdownSources} grouped)`}
              </p>
            </div>
            <div className={sankeyCanvasClass} aria-label="Composition outcome platform sankey">
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
                <div className="flex items-center justify-center h-full text-neutral-400 text-sm">No composition data for current filters</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
