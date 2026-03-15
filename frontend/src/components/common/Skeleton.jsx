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
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      <KpiSkeleton count={5} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TableSkeleton rows={4} cols={2} />
        <TableSkeleton rows={3} cols={1} />
      </div>
      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-5 flex items-start gap-4">
        <Skeleton className="w-10 h-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      </div>
    </div>
  );
}

/* ── Usage trends skeleton ─────────────────────────────────────────────── */
export function UsageTrendsSkeleton() {
  return (
    <div className="space-y-6">
      <KpiSkeleton count={3} />
      <ChartSkeleton height={380} />
      <TableSkeleton rows={3} cols={3} />
    </div>
  );
}

/* ── Funnel skeleton ───────────────────────────────────────────────────── */
export function FunnelSkeleton() {
  return (
    <div className="space-y-6">
      <KpiSkeleton count={4} />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <SankeySkeleton />
        <SankeySkeleton />
      </div>
      <TableSkeleton rows={5} cols={6} />
      <TableSkeleton rows={4} cols={8} />
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
