import React from 'react';

/* ── Base shimmer block ────────────────────────────────────────────────── */
export function Skeleton({ className = '', style = {} }) {
  return (
    <div
      className={`rounded bg-neutral-800/60 animate-pulse ${className}`}
      style={style}
    />
  );
}

/* ── KPI card skeleton ─────────────────────────────────────────────────── */
export function KpiSkeleton({ count = 3 }) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-${count} gap-4`}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-[#111111] rounded-xl border border-neutral-800 p-5 space-y-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

/* ── Chart area skeleton ───────────────────────────────────────────────── */
export function ChartSkeleton({ height = 380 }) {
  return (
    <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-4 rounded" />
        <Skeleton className="h-4 w-40" />
      </div>
      <div className="relative" style={{ height }}>
        {/* Y-axis ticks */}
        <div className="absolute left-0 top-0 bottom-8 w-10 flex flex-col justify-between py-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-2 w-8" />
          ))}
        </div>
        {/* Chart bars / wave */}
        <div className="ml-12 h-full flex items-end gap-1 pb-8">
          {[...Array(20)].map((_, i) => {
            const h = 30 + Math.sin(i * 0.5) * 25 + Math.random() * 20;
            return (
              <Skeleton
                key={i}
                className="flex-1 rounded-t"
                style={{ height: `${h}%`, animationDelay: `${i * 60}ms` }}
              />
            );
          })}
        </div>
        {/* X-axis ticks */}
        <div className="absolute bottom-0 left-12 right-0 flex justify-between">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-2 w-10" />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Table skeleton ────────────────────────────────────────────────────── */
export function TableSkeleton({ rows = 6, cols = 5 }) {
  return (
    <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="h-4 w-4 rounded" />
        <Skeleton className="h-4 w-48" />
      </div>
      {/* Header */}
      <div className="flex gap-4 pb-3 border-b border-neutral-800">
        {[...Array(cols)].map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" style={{ maxWidth: i === 0 ? '120px' : '80px' }} />
        ))}
      </div>
      {/* Rows */}
      {[...Array(rows)].map((_, rowIdx) => (
        <div key={rowIdx} className="flex gap-4 py-2 border-b border-neutral-800/40">
          {[...Array(cols)].map((_, colIdx) => (
            <Skeleton
              key={colIdx}
              className="h-3 flex-1"
              style={{
                maxWidth: colIdx === 0 ? '120px' : '80px',
                animationDelay: `${(rowIdx * cols + colIdx) * 40}ms`,
              }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ── Sankey / flow diagram skeleton ────────────────────────────────────── */
export function SankeySkeleton({ height = 300 }) {
  return (
    <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-4 rounded" />
        <Skeleton className="h-4 w-36" />
      </div>
      <div className="flex items-center justify-between gap-6" style={{ height }}>
        {/* Left nodes */}
        <div className="flex flex-col gap-3 w-20">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="rounded-lg" style={{ height: `${25 + i * 8}px` }} />
          ))}
        </div>
        {/* Flow lines */}
        <div className="flex-1 flex flex-col gap-4 mx-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton
              key={i}
              className="rounded-full"
              style={{ height: '6px', animationDelay: `${i * 100}ms` }}
            />
          ))}
        </div>
        {/* Right nodes */}
        <div className="flex flex-col gap-3 w-20">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="rounded-lg" style={{ height: `${20 + i * 12}px` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Overview full-page skeleton ───────────────────────────────────────── */
export function OverviewSkeleton() {
  return (
    <div className="h-full overflow-y-auto hide-scrollbar bg-[#050505] px-6 py-6 space-y-6">

      {/* Row 1: KPI horizontal scroll rail + action buttons */}
      <section>
        <div className="flex items-start gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex gap-4 overflow-hidden pb-1 pr-1">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="w-[220px] sm:w-[240px] lg:w-[260px] h-[128px] shrink-0">
                  <div className="h-full min-h-[128px] rounded-xl border border-neutral-800 bg-[#0f1218] px-4 py-4">
                    <div className="flex h-full items-start justify-between gap-3">
                      <div className="min-w-0 space-y-2">
                        <Skeleton className="h-2.5 w-16" />
                        <Skeleton className="h-9 w-24" />
                        <Skeleton className="h-3 w-20 mt-1" />
                      </div>
                      <Skeleton className="h-[64px] w-[96px] shrink-0 mt-4 rounded-lg" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="w-[140px] sm:w-[150px] lg:w-[160px] shrink-0 h-[128px] grid grid-rows-2 gap-2">
            <div className="rounded-xl border border-neutral-700 bg-[#12151b]" />
            <div className="rounded-xl border border-violet-700/50 bg-violet-950/20" />
          </div>
        </div>
      </section>

      {/* Row 2: Output Types Summary */}
      <section className="rounded-[24px] border border-neutral-800 bg-[#101216] p-5">
        <div className="mb-5 flex items-center gap-2">
          <Skeleton className="h-3.5 w-3.5 rounded" />
          <Skeleton className="h-3 w-40" />
        </div>
        <div className="flex gap-5">
          {/* Vertical tabs */}
          <div className="shrink-0 flex flex-col gap-1 w-40">
            {[...Array(4)].map((_, i) => (
              <div key={i} className={`rounded-xl px-3 py-2.5 border ${i === 0 ? 'bg-[#1a1d22] border-neutral-600' : 'bg-[#111317] border-neutral-800'}`}>
                <Skeleton className="h-3 w-16 mb-2" />
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 rounded-full bg-neutral-800/80 overflow-hidden">
                    <Skeleton className="h-1 rounded-full" style={{ width: `${30 + i * 15}%` }} />
                  </div>
                  <Skeleton className="h-2.5 w-8" />
                </div>
              </div>
            ))}
          </div>
          {/* Content: 3 stat cards + line chart */}
          <div className="flex-1 min-w-0 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="rounded-xl border border-neutral-800 bg-[#121418] p-4 text-center space-y-2">
                  <Skeleton className="h-2.5 w-16 mx-auto" />
                  <Skeleton className="h-6 w-20 mx-auto" />
                  <Skeleton className="h-2.5 w-14 mx-auto" />
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-neutral-800/70 bg-[#121418] p-4">
              <div className="flex items-center justify-between mb-3">
                <Skeleton className="h-2.5 w-32" />
                <Skeleton className="h-2.5 w-16" />
              </div>
              <div className="h-44 relative">
                <div className="absolute left-0 top-0 bottom-0 w-6 flex flex-col justify-between py-1">
                  {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-1.5 w-5" />)}
                </div>
                <div className="ml-8 h-full flex items-end gap-1 pb-4">
                  {[...Array(24)].map((_, i) => (
                    <Skeleton key={i} className="flex-1 rounded-t-sm" style={{ height: `${25 + Math.sin(i * 0.6) * 30 + 10}%`, opacity: 0.35, animationDelay: `${i * 50}ms` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Row 3: AI Insights (left) + Top Performers & Alerts (right) */}
      <section className="grid grid-cols-1 xl:grid-cols-[1.25fr_0.95fr] gap-6 xl:items-stretch">
        {/* Left: AI Insights */}
        <div className="rounded-[24px] border border-neutral-800 bg-[#101216] p-6 flex flex-col" style={{ height: '680px' }}>
          <Skeleton className="h-3.5 w-36 mb-4 shrink-0" />
          <div className="flex flex-col gap-2.5 flex-1 min-h-0">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="rounded-2xl border border-neutral-700/70 bg-[#111214] px-4 py-3.5 min-h-[108px] flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-4 w-16 rounded-md" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-3 w-8 shrink-0" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
                <div className="flex items-center justify-between mt-2.5">
                  <div className="flex gap-1.5">
                    <Skeleton className="h-4 w-20 rounded-md" />
                    <Skeleton className="h-4 w-16 rounded-md" />
                  </div>
                  <Skeleton className="h-6 w-20 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Top Performers + Alerts */}
        <div className="grid grid-rows-2 gap-6" style={{ height: '680px' }}>
          <div className="rounded-[24px] border border-neutral-800 bg-[#101216] p-5">
            <Skeleton className="h-3.5 w-32 mb-4" />
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-[#111317] px-4 py-3">
                  <Skeleton className="h-3.5 w-28 shrink-0" />
                  <div className="flex-1 h-1.5 rounded-full bg-neutral-800/80 overflow-hidden">
                    <Skeleton className="h-1.5 rounded-full" style={{ width: `${80 - i * 12}%` }} />
                  </div>
                  <Skeleton className="h-3 w-10 shrink-0" />
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-[24px] border border-amber-700/30 bg-[#15120f] p-5">
            <Skeleton className="h-3.5 w-16 mb-4" />
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="rounded-xl border border-amber-800/30 bg-[#1b1713] px-4 py-3 space-y-1.5">
                  <Skeleton className="h-3.5 w-40" />
                  <Skeleton className="h-3 w-32" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}


/* ── Usage trends skeleton ─────────────────────────────────────────────── */
/* Used as absolute inset-0 overlay on the chart body div in UsageTrendsModule */
export function UsageTrendsSkeleton() {
  return (
    <div className="h-full w-full flex flex-col">
      {/* Y-axis + chart area */}
      <div className="flex-1 relative border-b border-neutral-800/40">
        <div className="absolute left-0 top-0 bottom-0 w-8 flex flex-col justify-between py-2">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-1.5 w-6" />)}
        </div>
        <div className="ml-10 h-full flex items-end gap-1.5 pb-2">
          {[...Array(40)].map((_, i) => (
            <Skeleton
              key={i}
              className="flex-1 rounded-t-sm"
              style={{ height: `${20 + Math.sin(i * 0.4) * 25 + Math.random() * 20}%`, opacity: 0.4, animationDelay: `${i * 40}ms` }}
            />
          ))}
        </div>
      </div>
      {/* X-axis labels */}
      <div className="flex justify-between pl-10 pt-2">
        {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-2 w-12" />)}
      </div>
    </div>
  );
}

/* ── Funnel skeleton ───────────────────────────────────────────────────── */
export function FunnelSkeleton() {
  const tabLabels = ['Pipeline & Flow', 'Channel Efficiency', 'Content Analysis', 'Data Explorer', 'Publish Predictor'];
  return (
    <div className="space-y-5">
      {/* Views tab row — mirrors ANALYSIS_TABS in FunnelModule */}
      <div className="flex items-center gap-3">
        <Skeleton className="h-2 w-10" />
        <div className="flex gap-1.5">
          {tabLabels.map((_, i) => (
            <Skeleton key={i} className={`h-7 rounded-full ${i === 0 ? 'w-32' : 'w-28'}`} style={{ opacity: i === 0 ? 1 : 0.5 }} />
          ))}
        </div>
        <div className="flex-1 h-px bg-neutral-900" />
      </div>

      {/* KPI cards */}
      <KpiSkeleton count={4} />

      {/* Two Sankey / flow diagrams */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <SankeySkeleton height={360} />
        <SankeySkeleton height={360} />
      </div>

      {/* Breakdown table */}
      <TableSkeleton rows={4} cols={5} />
    </div>
  );
}

/* ── Explorer skeleton ─────────────────────────────────────────────────── */
export function ExplorerSkeleton() {
  return (
    <div className="space-y-4">
      <ChartSkeleton height={360} />
      <TableSkeleton rows={6} cols={3} />
    </div>
  );
}
