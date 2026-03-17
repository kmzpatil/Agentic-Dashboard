import React from 'react';
import { formatNumber, formatPct } from '../../../lib/formatters';

export default function PipelineStrip({ data }) {
  const uploaded      = Number(data?.pipelineStrip?.uploads              || data?.stageCounts?.uploaded_count       || 0);
  const created       = Number(data?.pipelineStrip?.assets_created       || data?.stageCounts?.created_count        || 0);
  const published     = Number(data?.pipelineStrip?.posts_published      || data?.stageCounts?.published_count      || 0);
  const platformPosts = Number(data?.pipelineStrip?.platform_posts       || data?.stageCounts?.platform_posts_count || 0);
  const assetsM   = Number(data?.pipelineStrip?.assets_multiplier   || 0);
  const notPubPct = Number(data?.pipelineStrip?.not_published_pct   || 0);
  const platformM = Number(data?.pipelineStrip?.platform_multiplier || 0);

  const publishConversion  = Number(data?.kpis?.publish_conversion_pct || 0);
  const avgAssetsPerUpload = Number(data?.kpis?.avg_assets_per_upload   || 0);
  const uploadFailureRate  = Number(data?.kpis?.upload_failure_rate     || 0);
  const wasteIndex         = Number(data?.kpis?.waste_index_seconds     || 0);
  const avgPublishLag      = Number(data?.kpis?.avg_lag_days            || 0);

  const stageTone = {
    neutral: 'text-neutral-100 border-neutral-700/70 bg-neutral-900/55',
    info: 'text-sky-200 border-sky-400/25 bg-sky-500/10',
    success: 'text-emerald-200 border-emerald-400/25 bg-emerald-500/10',
    amplify: 'text-indigo-200 border-indigo-400/25 bg-indigo-500/10',
  };

  const stages = [
    { label: 'Uploads',          value: uploaded, tone: stageTone.neutral },
    { label: 'Assets created',   value: created, tone: stageTone.info },
    { label: 'Posts published',  value: published, tone: stageTone.success },
    { label: 'Platform posts',   value: platformPosts, tone: stageTone.amplify },
  ];

  const notPublishedTone = notPubPct > 35
    ? 'text-rose-300'
    : notPubPct > 20
      ? 'text-amber-300'
      : 'text-emerald-300';

  const transitions = [
    {
      text: `×${assetsM.toFixed(1)} assets`,
      tone: assetsM >= 1 ? 'text-sky-300' : 'text-amber-300',
      note: assetsM >= 1 ? 'expansion' : 'weak expansion',
    },
    {
      text: `${notPubPct > 0 ? '−' : '+'}${Math.abs(notPubPct).toFixed(1)}%`,
      tone: notPublishedTone,
      note: notPubPct > 35 ? 'high loss' : notPubPct > 20 ? 'moderate loss' : 'healthy retention',
    },
    {
      text: `×${platformM.toFixed(1)} platforms`,
      tone: platformM >= 1.5 ? 'text-indigo-300' : 'text-neutral-300',
      note: platformM >= 1.5 ? 'strong distribution' : 'limited distribution',
    },
  ];

  const getKpiTone = (level) => {
    if (level === 'risk') return 'text-rose-300';
    if (level === 'watch') return 'text-amber-300';
    if (level === 'good') return 'text-emerald-300';
    return 'text-neutral-100';
  };

  const kpis = [
    {
      label: 'Publish conversion',
      value: formatPct(publishConversion),
      sub: 'posts / assets',
      level: publishConversion < 5 ? 'risk' : publishConversion < 12 ? 'watch' : 'good',
    },
    {
      label: 'Avg assets/upload',
      value: avgAssetsPerUpload.toFixed(2),
      sub: 'creation rate',
      level: avgAssetsPerUpload < 1 ? 'watch' : 'good',
    },
    {
      label: 'Upload failure rate',
      value: formatPct(uploadFailureRate),
      sub: 'cross-client avg',
      level: uploadFailureRate > 20 ? 'risk' : uploadFailureRate > 10 ? 'watch' : 'good',
    },
    {
      label: 'Waste index (avg)',
      value: `${wasteIndex.toFixed(1)}s`,
      sub: 'created not published',
      level: wasteIndex > 200 ? 'risk' : wasteIndex > 120 ? 'watch' : 'good',
    },
    {
      label: 'Avg publish lag',
      value: `${avgPublishLag.toFixed(2)} days`,
      sub: 'asset → post',
      level: avgPublishLag > 10 ? 'risk' : avgPublishLag > 5 ? 'watch' : 'good',
    },
  ];

  return (
    <div className="space-y-8">
      {/* ── Pipeline overview ── */}
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-neutral-600 mb-5 text-center">Pipeline overview</div>
        <div className="mb-4 flex items-center justify-center gap-3 text-[10px] font-medium text-neutral-500">
          <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-400" />healthy</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-400" />watch</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-rose-400" />risk</span>
        </div>
        <div className="mx-auto grid max-w-[1220px] grid-cols-1 gap-y-3 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] lg:items-end lg:gap-x-5">
          {stages.map((s, i) => (
            <React.Fragment key={s.label}>
              <div className={`text-center py-2 lg:py-2 rounded-xl border ${s.tone}`}>
                <div className="text-[12px] font-medium text-neutral-400 mb-1.5">{s.label}</div>
                <div className="text-[34px] font-bold text-white leading-none font-mono tracking-tight">
                  {formatNumber(s.value)}
                </div>
              </div>

              {i < transitions.length && (
                <div className="flex flex-col items-center justify-center py-0.5 sm:py-2 lg:py-0">
                  <span className="text-neutral-500 text-[16px] leading-none">→</span>
                  <span className={`text-[15px] font-bold mt-1 tracking-wide ${transitions[i].tone}`}>
                    {transitions[i].text}
                  </span>
                  <span className="text-[9px] uppercase tracking-wide text-neutral-600 mt-0.5">{transitions[i].note}</span>
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── KPIs ── */}
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-neutral-600 mb-5 text-center">Key performance indicators</div>
        <div className="mx-auto grid max-w-[1220px] grid-cols-1 gap-y-4 sm:grid-cols-2 xl:grid-cols-5 xl:gap-x-6">
          {kpis.map((kpi) => (
            <div key={kpi.label} className="text-center">
              <div className="text-[12px] font-medium text-neutral-400 mb-1">{kpi.label}</div>
              <div className={`text-[28px] font-bold leading-none font-mono ${getKpiTone(kpi.level)}`}>
                {kpi.value}
              </div>
              <div className="text-[11px] text-neutral-600 mt-1.5">{kpi.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
