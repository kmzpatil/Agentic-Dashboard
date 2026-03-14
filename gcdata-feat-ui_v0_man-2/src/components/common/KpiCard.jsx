import React from 'react';

export default function KpiCard({ title, value, subtitle }) {
  return (
    <div className="bg-[#111111] rounded-xl p-5 border border-neutral-800 hover:border-neutral-600 transition-colors">
      <div className="text-xs font-bold tracking-wider text-neutral-500 mb-1">{title}</div>
      <div className="text-3xl font-black text-white tracking-tight">{value}</div>
      <div className="text-sm text-neutral-400 mt-2">{subtitle}</div>
    </div>
  );
}
