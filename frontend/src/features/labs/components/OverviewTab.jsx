import React from 'react';
import { Upload, Cpu, Send, ArrowRight, AlertTriangle } from 'lucide-react';
import KpiCard from '../../../components/common/KpiCard';

const STAGE_ICONS = { Upload: Upload, Processing: Cpu, Publishing: Send };

function scoreTone(score) {
  if (score >= 80) return { border: 'border-emerald-500/25', bg: 'bg-emerald-500/10', text: 'text-emerald-300', dot: 'bg-emerald-400' };
  if (score >= 60) return { border: 'border-amber-500/25', bg: 'bg-amber-500/10', text: 'text-amber-300', dot: 'bg-amber-400' };
  return { border: 'border-rose-500/25', bg: 'bg-rose-500/10', text: 'text-rose-300', dot: 'bg-rose-400' };
}

function PipelineFunnel({ funnel, stageScores }) {
  const stages = funnel?.stages || [];
  const conversions = funnel?.conversions || [];
  const scores = stageScores || {};

  const stageKeys = ['upload', 'processing', 'publishing'];
  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
      <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-neutral-600 mb-5 text-center">
        Pipeline Overview
      </div>
      <div className="flex items-center gap-1.5 justify-center mb-4 text-[10px] font-medium text-neutral-500">
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-400" />healthy</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-400" />watch</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-rose-400" />critical</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-4 lg:gap-3 max-w-[1100px] mx-auto">
        {stages.map((stage, i) => {
          const key = stageKeys[i];
          const score = scores[key]?.score ?? 100;
          const tone = scoreTone(score);
          const Icon = STAGE_ICONS[stage.name] || Upload;
          const widthPct = Math.max(40, (stage.count / maxCount) * 100);

          return (
            <React.Fragment key={stage.name}>
              <div
                className={`text-center py-4 rounded-2xl border transition-all ${tone.border} ${tone.bg}`}
                style={{ width: `${widthPct}%`, margin: '0 auto', minWidth: 140 }}
              >
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Icon size={14} className={tone.text} />
                  <span className="text-[12px] font-medium text-neutral-400">{stage.name}</span>
                </div>
                <div className="text-[32px] font-bold text-white leading-none font-mono tracking-tight">
                  {stage.count.toLocaleString()}
                </div>
                <div className="mt-2 flex items-center justify-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${tone.dot}`} />
                  <span className={`text-[13px] font-bold ${tone.text}`}>{score}%</span>
                  <span className="text-[10px] text-neutral-500">quality</span>
                </div>
              </div>

              {i < conversions.length && (
                <div className="flex flex-col items-center py-1">
                  <ArrowRight size={16} className="text-neutral-600" />
                  <span className="text-[13px] font-bold text-sky-300 mt-1">
                    {conversions[i].rate}%
                  </span>
                  <span className="text-[9px] uppercase tracking-wide text-neutral-600 mt-0.5">
                    conversion
                  </span>
                  {conversions[i].drop_off > 0 && (
                    <span className="text-[9px] text-rose-400 mt-0.5">
                      −{conversions[i].drop_off}% drop
                    </span>
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function severityDot(severity) {
  if (severity === 'high') return 'bg-rose-400';
  if (severity === 'medium') return 'bg-amber-400';
  return 'bg-neutral-500';
}

export default function OverviewTab({ dqa }) {
  const { stageScores, funnel, criticalIssues, timeseries } = dqa;
  const scores = stageScores || {};
  const overall = scores.overall ?? 0;

  // Build sparkline data from timeseries
  const uploadTrend = timeseries?.upload || [];
  const processingTrend = timeseries?.processing || [];
  const publishingTrend = timeseries?.publishing || [];

  return (
    <div className="space-y-6">
      {/* Pipeline funnel */}
      <PipelineFunnel funnel={funnel} stageScores={stageScores} />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Overall Pipeline Health"
          value={`${overall}%`}
          subtitle="Weighted average across all stages"
          trendData={timeseries?.overall || []}
        />
        <KpiCard
          title="Upload Quality"
          value={`${scores.upload?.score ?? 0}%`}
          subtitle={`${scores.upload?.row_count ?? 0} uploads`}
          trendData={uploadTrend}
        />
        <KpiCard
          title="Processing Quality"
          value={`${scores.processing?.score ?? 0}%`}
          subtitle={`${scores.processing?.row_count ?? 0} assets`}
          trendData={processingTrend}
        />
        <KpiCard
          title="Publishing Quality"
          value={`${scores.publishing?.score ?? 0}%`}
          subtitle={`${scores.publishing?.row_count ?? 0} posts`}
          trendData={publishingTrend}
        />
      </div>

      {/* Critical Issues */}
      <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle size={14} className="text-amber-400" />
          <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400">
            Recent Critical Issues
          </h3>
          <span className="ml-auto text-[10px] text-neutral-600">
            {(criticalIssues || []).length} issues
          </span>
        </div>
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {(!criticalIssues || criticalIssues.length === 0) && (
            <div className="text-neutral-600 text-sm py-4 text-center">No critical issues detected.</div>
          )}
          {(criticalIssues || []).map((issue) => (
            <div key={issue.id} className="flex items-center gap-3 py-2 border-b border-neutral-900 last:border-0">
              <span className={`h-2 w-2 rounded-full flex-shrink-0 ${severityDot(issue.severity)}`} />
              <span className="text-[11px] font-mono font-bold text-sky-300 min-w-[180px]">
                {issue.error_code}
              </span>
              <span className="text-[11px] text-neutral-500 min-w-[120px]">{issue.table_name}</span>
              <span className="text-[11px] text-neutral-400 flex-1 truncate">{issue.error_message}</span>
              <span className="text-[10px] text-neutral-600 flex-shrink-0">
                {issue.timestamp?.substring(11, 19)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
