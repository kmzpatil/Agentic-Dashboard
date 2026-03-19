import React from 'react';
import { formatNumber, formatPct } from '../../../lib/formatters';

const FLOW_STYLES = `
@keyframes pipelineFlowShift {
  0% { transform: translateX(-16px); opacity: 0; }
  15% { opacity: 1; }
  100% { transform: translateX(calc(100% + 16px)); opacity: 0; }
}

@keyframes pipelineFlowPulse {
  0%, 100% { opacity: 0.42; }
  50% { opacity: 0.9; }
}

.pipeline-flow-wrap {
  width: 100%;
  position: relative;
  height: 12px;
}

.pipeline-flow-line {
  position: relative;
  height: 4px;
  width: 100%;
  border-radius: 9999px;
  background: linear-gradient(90deg, rgba(82,82,91,0.28), rgba(232,232,236,0.86), rgba(82,82,91,0.28));
  box-shadow: 0 0 0 1px rgba(255,255,255,0.04) inset, 0 0 12px rgba(212,212,216,0.22);
  overflow: hidden;
}

.pipeline-flow-line::before {
  content: '';
  position: absolute;
  left: 7%;
  right: 7%;
  top: 50%;
  height: 1px;
  background: rgba(255,255,255,0.38);
  transform: translateY(-50%);
  animation: pipelineFlowPulse 2.1s ease-in-out infinite;
}

.pipeline-flow-line::after {
  content: '';
  position: absolute;
  right: -2px;
  top: 50%;
  width: 9px;
  height: 9px;
  border-top: 2px solid rgba(245,245,245,0.82);
  border-right: 2px solid rgba(245,245,245,0.82);
  transform: translateY(-50%) rotate(45deg);
}

.pipeline-flow-dot {
  position: absolute;
  top: 50%;
  left: 0;
  width: 7px;
  height: 7px;
  border-radius: 9999px;
  background: rgba(250, 250, 250, 0.95);
  box-shadow: 0 0 12px rgba(250, 250, 250, 0.85), 0 0 18px rgba(180,180,190,0.45);
  transform: translate(-16px, -50%);
  animation: pipelineFlowShift 1.8s ease-out infinite;
}

.pipeline-flow-dot--slow {
  width: 5px;
  height: 5px;
  opacity: 0.68;
  animation-duration: 2.45s;
  animation-delay: 0.52s;
}

.pipeline-flow-dot--third {
  width: 4px;
  height: 4px;
  opacity: 0.55;
  animation-duration: 2.95s;
  animation-delay: 0.92s;
}
`;

function FlowConnector({ text, note, compact = false, alignToValue = false }) {
  const layoutClass = compact
    ? 'min-h-[64px] justify-center'
    : alignToValue
      ? 'lg:min-h-[92px] justify-start lg:pt-[34px]'
      : 'lg:min-h-[92px] justify-center';

  return (
    <div className={`flex flex-col items-center px-1 ${layoutClass}`}>
      {text && (
        <span className="mb-2 text-[18px] font-semibold leading-none tracking-tight whitespace-nowrap text-neutral-300">
          {text}
        </span>
      )}
      <div className="pipeline-flow-wrap">
        <div className="pipeline-flow-line" />
        <span className="pipeline-flow-dot" />
        <span className="pipeline-flow-dot pipeline-flow-dot--slow" />
        <span className="pipeline-flow-dot pipeline-flow-dot--third" />
      </div>
      {note && (
        <span className="text-[10px] uppercase tracking-[0.08em] text-neutral-600 mt-1 whitespace-nowrap">
          {note}
        </span>
      )}
    </div>
  );
}

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

  const stages = [
    { label: 'Uploads',          value: uploaded },
    { label: 'Assets created',   value: created },
    { label: 'Posts published',  value: published },
    { label: 'Platform posts',   value: platformPosts },
  ];

  const transitions = [
    {
      text: `×${assetsM.toFixed(1)} assets`,
      note: assetsM >= 1 ? 'expansion' : 'weak expansion',
    },
    {
      text: `${notPubPct > 0 ? '−' : '+'}${Math.abs(notPubPct).toFixed(1)}%`,
      note: notPubPct > 35 ? 'high loss' : notPubPct > 20 ? 'moderate loss' : 'healthy retention',
    },
    {
      text: `×${platformM.toFixed(1)} platforms`,
      note: platformM >= 1.5 ? 'strong distribution' : 'limited distribution',
    },
  ];

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
    <div className="space-y-5">
      <style>{FLOW_STYLES}</style>

      {/* ── Pipeline overview ── */}
      <div>
        <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-neutral-500 mb-3 text-center">Pipeline overview</div>
        <div className="mx-auto grid max-w-[1260px] grid-cols-1 gap-y-3 sm:grid-cols-2 lg:grid-cols-[1fr_132px_1fr_132px_1fr_132px_1fr] lg:items-center lg:gap-x-2">
          {stages.map((s, i) => (
            <React.Fragment key={s.label}>
              <div className="text-center py-0.5 lg:min-h-[92px] flex flex-col justify-end">
                <div className="text-[12px] font-medium text-neutral-400 mb-1">{s.label}</div>
                <div className="text-[46px] font-semibold leading-none font-mono tracking-tight text-neutral-200">
                  {formatNumber(s.value)}
                </div>
              </div>

              {i < transitions.length && (
                <FlowConnector text={transitions[i].text} note={transitions[i].note} alignToValue />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── KPIs ── */}
      <div>
        <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-neutral-500 mb-3 text-center">Key performance indicators</div>
        <div className="mx-auto grid max-w-[1220px] grid-cols-1 gap-y-3 sm:grid-cols-2 xl:grid-cols-5 xl:gap-x-5">
          {kpis.map((kpi) => (
            <div key={kpi.label} className="text-center">
              <div className="text-[13px] font-medium text-neutral-400 mb-1">{kpi.label}</div>
              <div className="text-[28px] font-bold leading-none font-mono text-neutral-300">
                {kpi.value}
              </div>
              <div className="text-[12px] text-neutral-500 mt-1.5">{kpi.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
