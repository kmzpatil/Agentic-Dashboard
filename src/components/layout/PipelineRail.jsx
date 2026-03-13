import React from 'react';
import { formatHours, formatNumber } from '../../lib/formatters';

function PipelineStage({ title, count, hours, status }) {
  const borderColors = {
    brand: 'border-red-500',
    warning: 'border-amber-500',
    neutral: 'border-neutral-700',
  };

  return (
    <div className={`flex flex-col items-center bg-[#111111] border-b-4 ${borderColors[status]} rounded-t-lg p-3 w-40 hover:bg-[#1A1A1A] transition-colors`}>
      <span className="text-xs font-bold tracking-wider text-neutral-400 mb-1">{title}</span>
      <span className="text-xl font-black tracking-tight">{count}</span>
      <span className="text-xs text-neutral-500">{hours}</span>
    </div>
  );
}

function FlowConnector() {
  return (
    <div className="flex items-center justify-center w-16 relative">
      <div className="h-0.5 w-full bg-neutral-800 absolute"></div>
      <div className="flex space-x-1 z-10">
        <div className="w-1.5 h-1.5 bg-red-500 rounded-full dot-flow"></div>
        <div className="w-1.5 h-1.5 bg-red-500 rounded-full dot-flow"></div>
        <div className="w-1.5 h-1.5 bg-red-500 rounded-full dot-flow"></div>
      </div>
    </div>
  );
}

export default function PipelineRail({ overview }) {
  const kpis = overview?.kpis;

  return (
    <div className="flex items-center justify-between w-full bg-[#050505] text-white p-4 overflow-x-auto hide-scrollbar border-b border-neutral-900">
      <div className="flex items-center space-x-2 min-w-max">
        <PipelineStage title="UPLOADED" count={formatNumber(kpis?.uploaded_count || 0)} hours={formatHours(kpis?.uploaded_duration || 0)} status="neutral" />
        <FlowConnector />
        <PipelineStage title="PROCESSED" count={formatNumber(kpis?.processed_count || 0)} hours={formatHours(kpis?.created_duration || 0)} status="brand" />
        <FlowConnector />
        <PipelineStage title="CREATED" count={formatNumber(kpis?.created_count || 0)} hours={formatHours(kpis?.created_duration || 0)} status="brand" />
        <FlowConnector />
        <PipelineStage title="PUBLISHED" count={formatNumber(kpis?.published_count || 0)} hours={formatHours(kpis?.published_duration || 0)} status="warning" />
      </div>
    </div>
  );
}
