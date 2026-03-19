import React from "react";

export default function DateRangeSlider({ dates, startIndex, endIndex, onChange }) {
  if (!dates.length) {
    return (
      <div className="rounded-[18px] border border-neutral-800 bg-[#111111] p-4 text-sm text-neutral-500">
        Date range unavailable.
      </div>
    );
  }

  const maxIndex = dates.length - 1;
  const safeStart = Math.min(Math.max(startIndex, 0), maxIndex);
  const safeEnd = Math.min(Math.max(endIndex, safeStart), maxIndex);
  const startPct = maxIndex === 0 ? 0 : (safeStart / maxIndex) * 100;
  const endPct = maxIndex === 0 ? 100 : (safeEnd / maxIndex) * 100;

  return (
    <div className="flex flex-col justify-center h-[46px] px-4 rounded-xl border border-neutral-800 bg-[#0a0a0a]/50">
      <div className="relative h-4 mt-2">
        <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-neutral-800" />
        <div
          className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-gradient-to-r from-red-500 to-red-400"
          style={{ left: `${startPct}%`, right: `${100 - endPct}%` }}
        />
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={safeStart}
          onChange={(event) => onChange(Number(event.target.value), safeEnd)}
          className="frammer-range absolute top-1/2 -translate-y-1/2 left-0 w-full h-4 z-20 cursor-pointer"
        />
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={safeEnd}
          onChange={(event) => onChange(safeStart, Number(event.target.value))}
          className="frammer-range absolute top-1/2 -translate-y-1/2 left-0 w-full h-4 z-30 cursor-pointer"
        />
      </div>

      <div className="mt-1.5 flex items-center justify-between text-[9px] font-black uppercase tracking-[0.12em] text-neutral-500 tabular-nums">
        <span>{dates[safeStart]}</span>
        <span>{dates[safeEnd]}</span>
      </div>
    </div>
  );
}
