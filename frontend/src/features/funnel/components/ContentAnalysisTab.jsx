import React, { useMemo, useState, useRef, useCallback } from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, Tooltip, Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import FunnelViewContextStrip from './FunnelViewContextStrip';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

// ─── CSS / Fonts ──────────────────────────────────────────────────────────────
const STYLES = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@500;700&display=swap');

.ca-root { font-family: 'DM Sans', system-ui, sans-serif; }
.ca-root * { box-sizing: border-box; }

.ca-card {
  background: linear-gradient(160deg, #111116 0%, #0c0c10 100%);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 18px;
  padding: 22px 24px;
  box-shadow: 0 6px 32px rgba(0,0,0,0.45);
  position: relative; overflow: hidden;
}
.ca-card--glow::before {
  content: '';
  position: absolute; top: -50px; right: -50px;
  width: 180px; height: 180px; border-radius: 50%;
  background: radial-gradient(circle, rgba(239,68,68,0.06) 0%, transparent 70%);
  pointer-events: none;
}
.ca-kpi {
  flex: 1 1 130px; min-width: 116px;
  border-radius: 14px; padding: 14px 16px;
  display: flex; flex-direction: column; gap: 2px;
}
.ca-kpi--default {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.07);
}
.ca-kpi--red {
  background: linear-gradient(140deg, rgba(239,68,68,0.1), rgba(239,68,68,0.03));
  border: 1px solid rgba(239,68,68,0.2);
}
.ca-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: 99px;
  font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
}
.ca-heat-cell {
  border-radius: 8px; padding: 8px 12px;
  text-align: center; font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px; font-weight: 700; min-width: 106px;
  cursor: default; transition: filter 0.12s ease;
}
.ca-heat-cell:hover { filter: brightness(1.2); }
.ca-perf-bar-track {
  width: 72px; height: 4px;
  background: rgba(255,255,255,0.05);
  border-radius: 99px; overflow: hidden; flex-shrink: 0;
}
.ca-spinner-btn {
  width: 16px; height: 12px; font-size: 9px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 3px; color: #9090a0; cursor: pointer; line-height: 1;
}
.ca-topn-input {
  -moz-appearance: textfield;
  appearance: textfield;
}
.ca-topn-input::-webkit-outer-spin-button,
.ca-topn-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
`;

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmtPct   = (v, d = 1) => `${(Number.isFinite(+v) ? +v : 0).toFixed(d)}%`;
const fmtLabel = (v) =>
  String(v || '').split('_').filter(Boolean)
    .map((p) => p[0].toUpperCase() + p.slice(1)).join(' ');

function heatCellStyle(v, min, max) {
  const val = Number.isFinite(+v) ? +v : 0;
  if (val <= 0.0001)
    return { bg:'rgba(20,18,28,0.85)', border:'rgba(44,40,58,0.6)', text:'#6b6b82' };
  const t   = Math.max(0, Math.min(1, (val - min) / Math.max(max - min, 1e-6)));
  const r0  = { r:176, g:24, b:56 };
  const r1  = { r:20, g:112, b:72 };
  const R   = Math.round(r0.r + (r1.r - r0.r) * t);
  const G   = Math.round(r0.g + (r1.g - r0.g) * t);
  const B   = Math.round(r0.b + (r1.b - r0.b) * t);
  const bg  = { r:12, g:12, b:16 };
  const m   = 0.72;
  const fr  = Math.round(R * m + bg.r * (1 - m));
  const fg  = Math.round(G * m + bg.g * (1 - m));
  const fb  = Math.round(B * m + bg.b * (1 - m));
  const lum = (0.299 * fr + 0.587 * fg + 0.114 * fb) / 255;
  return {
    bg:     `rgb(${fr},${fg},${fb})`,
    border: `rgb(${Math.max(fr-16,0)},${Math.max(fg-16,0)},${Math.max(fb-16,0)})`,
    text:   lum > 0.5 ? '#08080e' : '#eef0f8',
  };
}

// ─── Inline Chart.js plugins ──────────────────────────────────────────────────
// Data labels above vertical bars
const dataLabelPlugin = {
  id: 'caDataLabel',
  afterDatasetsDraw(chart) {
    const { ctx, data } = chart;
    const meta = chart.getDatasetMeta(0);
    if (!meta?.data?.length) return;
    ctx.save();
    meta.data.forEach((bar, i) => {
      const val = data.datasets[0].data[i];
      if (val == null) return;
      ctx.font         = "600 10px 'JetBrains Mono', monospace";
      ctx.fillStyle    = 'rgba(240,240,244,0.62)';
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(`${(+val).toFixed(1)}%`, bar.x, bar.y - 3);
    });
    ctx.restore();
  },
};

// Value labels right of horizontal bars
const hBarLabelPlugin = {
  id: 'caHBarLabel',
  afterDatasetsDraw(chart) {
    const { ctx, data } = chart;
    const meta = chart.getDatasetMeta(0);
    if (!meta?.data?.length) return;
    ctx.save();
    meta.data.forEach((bar, i) => {
      const val = data.datasets[0].data[i];
      if (val == null) return;
      ctx.font         = "700 11px 'JetBrains Mono', monospace";
      ctx.fillStyle    = 'rgba(240,240,244,0.72)';
      ctx.textAlign    = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${(+val).toFixed(1)}%`, bar.x + 7, bar.y);
    });
    ctx.restore();
  },
};

// Avg reference line (vertical charts only)
function makeAvgPlugin(avg) {
  return {
    id: 'caAvgLine',
    afterDatasetsDraw(chart) {
      if (!avg) return;
      const { ctx, chartArea, scales } = chart;
      const y = scales.y?.getPixelForValue(avg);
      if (!y || y < chartArea.top || y > chartArea.bottom) return;
      ctx.save();
      ctx.beginPath();
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = 'rgba(245,158,11,0.52)';
      ctx.lineWidth   = 1.3;
      ctx.moveTo(chartArea.left, y);
      ctx.lineTo(chartArea.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font         = "600 9.5px 'JetBrains Mono', monospace";
      ctx.fillStyle    = 'rgba(245,158,11,0.72)';
      ctx.textAlign    = 'right';
      ctx.textBaseline = 'bottom';
      ctx.fillText(`avg ${(+avg).toFixed(1)}%`, chartArea.right - 4, y - 3);
      ctx.restore();
    },
  };
}

// ─── GradientBar ─────────────────────────────────────────────────────────────
function GradientBar({ chartData, avg, height = 248, horizontal = false }) {
  const chartRef = useRef(null);

  const plugins = useMemo(() => {
    if (horizontal) return [hBarLabelPlugin];
    return [dataLabelPlugin, makeAvgPlugin(avg)];
  }, [horizontal, avg]);

  const maxVal = useMemo(() => {
    const vals = chartData.datasets[0]?.data || [];
    return Math.max(...vals, 0.001);
  }, [chartData]);

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? 'y' : 'x',
    animation: { duration: 580, easing: 'easeOutCubic' },
    layout: { padding: { top: horizontal ? 4 : 24, right: horizontal ? 62 : 10, bottom: 4, left: 4 } },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#15151c',
        borderColor: 'rgba(255,255,255,0.09)',
        borderWidth: 1,
        titleColor: '#f0f0f3',
        bodyColor: '#a0a0b0',
        padding: 11,
        cornerRadius: 10,
        displayColors: false,
        callbacks: {
          label: (ctx) => ` ${(+(horizontal ? ctx.parsed.x : ctx.parsed.y)).toFixed(2)}%`,
        },
      },
    },
    scales: horizontal ? {
      x: {
        beginAtZero: true,
        max: Math.ceil(maxVal * 1.18),
        ticks: { color: '#7a7a8e', font: { size: 9 }, callback: (v) => `${v}%` },
        grid: { color: 'rgba(255,255,255,0.028)' },
        border: { display: false },
      },
      y: {
        ticks: { color: '#a0a0b0', font: { size: 11.5 }, padding: 4 },
        grid: { display: false },
        border: { display: false },
      },
    } : {
      x: {
        ticks: { color: '#7a7a8e', font: { size: 10 }, maxRotation: 34, minRotation: 0 },
        grid: { display: false },
        border: { color: 'rgba(255,255,255,0.04)' },
      },
      y: {
        beginAtZero: true,
        ticks: { color: '#7a7a8e', font: { size: 9 }, callback: (v) => `${v}%` },
        grid: { color: 'rgba(255,255,255,0.028)', drawBorder: false },
        border: { display: false },
      },
    },
  }), [horizontal, maxVal]);

  // Build gradient bg array from live canvas context
  const getEnrichedData = useCallback(() => {
    const count = chartData.datasets[0]?.data?.length || 0;
    const chart = chartRef.current;
    const ctx = chart?.ctx;
    const chartArea = chart?.chartArea;

    const bgs = Array.from({ length: count }, (_, i) => {
      const t  = count === 1 ? 0 : i / (count - 1);
      const r  = Math.round(239 + (72 - 239) * t);
      const g  = Math.round(68  + (72 - 68)  * t);
      const b  = Math.round(68  + (90 - 68)  * t);

      // First paint can happen before canvas area is measured.
      // Use a solid fallback so bars are visible immediately on tab open.
      if (!ctx || !chartArea) return `rgba(${r},${g},${b},0.82)`;

      let grad;
      if (horizontal) {
        grad = ctx.createLinearGradient(chartArea.left, 0, chartArea.right, 0);
        grad.addColorStop(0,   `rgba(${r},${g},${b},0.88)`);
        grad.addColorStop(0.7, `rgba(${r},${g},${b},0.72)`);
        grad.addColorStop(1,   `rgba(${r},${g},${b},0.3)`);
      } else {
        grad = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        grad.addColorStop(0,   `rgba(${r},${g},${b},0.95)`);
        grad.addColorStop(0.6, `rgba(${r},${g},${b},0.7)`);
        grad.addColorStop(1,   `rgba(${r},${g},${b},0.32)`);
      }
      return grad;
    });

    return {
      ...chartData,
      datasets: [{
        ...chartData.datasets[0],
        backgroundColor: bgs,
        borderRadius: horizontal
          ? { topLeft: 0, topRight: 5, bottomLeft: 0, bottomRight: 5 }
          : 6,
        borderSkipped: false,
        barPercentage: horizontal ? 0.6 : 0.68,
        categoryPercentage: 0.88,
      }],
    };
  }, [chartData, horizontal]);

  return (
    <div style={{ height }}>
      <Bar ref={chartRef} data={getEnrichedData()} options={options} plugins={plugins} />
    </div>
  );
}

// ─── Small UI primitives ──────────────────────────────────────────────────────
function Chip({ children, tone = 'neutral', dot = false }) {
  const T = {
    neutral: { bg:'rgba(28,28,36,0.9)',    border:'rgba(255,255,255,0.08)', text:'#8b8b9a' },
    red:     { bg:'rgba(239,68,68,0.08)',  border:'rgba(239,68,68,0.22)',   text:'#f87171' },
    green:   { bg:'rgba(34,197,94,0.08)',  border:'rgba(34,197,94,0.22)',   text:'#4ade80' },
    amber:   { bg:'rgba(245,158,11,0.08)', border:'rgba(245,158,11,0.22)',  text:'#fbbf24' },
    violet:  { bg:'rgba(139,92,246,0.08)', border:'rgba(139,92,246,0.22)', text:'#a78bfa' },
  }[tone] || { bg:'rgba(28,28,36,0.9)', border:'rgba(255,255,255,0.08)', text:'#8b8b9a' };
  return (
    <span className="ca-chip" style={{ background:T.bg, border:`1px solid ${T.border}`, color:T.text }}>
      {dot && <span style={{ width:5, height:5, borderRadius:'50%', background:T.text, opacity:0.75, flexShrink:0 }} />}
      {children}
    </span>
  );
}

function SectionHead({ title, badge, desc, right }) {
  return (
    <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:12, marginBottom:18 }}>
      <div>
        <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom: desc ? 5 : 0 }}>
          <span style={{ fontSize:13.5, fontWeight:700, color:'#f0f0f3', letterSpacing:'-0.015em' }}>{title}</span>
          {badge && (
            <span style={{
              fontSize:9.5, fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase',
              color:'#8b8b9a', background:'rgba(255,255,255,0.04)',
              border:'1px solid rgba(255,255,255,0.07)', borderRadius:6, padding:'2px 7px',
            }}>{badge}</span>
          )}
        </div>
        {desc && <p style={{ margin:0, fontSize:11.5, color:'#9090a0', lineHeight:1.6, maxWidth:530 }}>{desc}</p>}
      </div>
      {right && <div style={{ flexShrink:0, marginTop:1 }}>{right}</div>}
    </div>
  );
}

function KpiCard({ label, value, sub, tone = 'default' }) {
  return (
    <div className={`ca-kpi ca-kpi--${tone === 'red' ? 'red' : 'default'}`}>
      <span style={{ fontSize:9.5, fontWeight:700, color:'#8b8b9a', letterSpacing:'0.08em', textTransform:'uppercase' }}>{label}</span>
      <span style={{
        fontSize:22, fontWeight:700, letterSpacing:'-0.04em', lineHeight:1.1,
        fontFamily:"'JetBrains Mono', monospace",
        color: tone === 'red' ? '#f87171' : '#f0f0f3', marginTop:5,
      }}>{value}</span>
      {sub && (
        <span style={{
          fontSize:11, color:'#6b6b82', marginTop:2,
          overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap',
        }} title={sub}>{sub}</span>
      )}
    </div>
  );
}

function TopNSpinner({ value, max, onChange }) {
  return (
    <div style={{
      display:'inline-flex', alignItems:'center', gap:7,
      background:'rgba(0,0,0,0.45)', border:'1px solid rgba(255,255,255,0.07)',
      borderRadius:10, padding:'5px 11px',
    }}>
      <span style={{ fontSize:9.5, color:'#8b8b9a', fontWeight:700, letterSpacing:'0.07em', textTransform:'uppercase' }}>Top</span>
      <input
        className="ca-topn-input"
        type="number" min={1} max={max} value={value}
        onChange={(e) => onChange(Math.min(max, Math.max(1, +e.target.value)))}
        style={{
          width:32, border:'none', background:'transparent', outline:'none',
          color:'#f0f0f3', fontWeight:700, fontSize:13.5,
          textAlign:'center', fontFamily:"'JetBrains Mono', monospace",
        }}
      />
      <div style={{ display:'flex', flexDirection:'column', gap:2 }}>
        {[['+',1],['−',-1]].map(([s,d]) => (
          <button key={s} className="ca-spinner-btn"
            onClick={() => onChange(Math.min(max, Math.max(1, value + d)))}>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function PerfRow({ rank, label, value, maxValue, tone }) {
  const pct   = Math.min(100, (value / Math.max(maxValue, 0.001)) * 100);
  const color = tone === 'green' ? '#22c55e' : '#ef4444';
  return (
    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
      <span style={{ fontSize:10, color:'#6b6b82', fontFamily:"'JetBrains Mono',monospace", minWidth:16, textAlign:'right' }}>{rank}</span>
      <span style={{ fontSize:12.5, color:'#a0a0b0', flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{label}</span>
      <div className="ca-perf-bar-track">
        <div style={{ height:'100%', width:`${pct}%`, background:color, borderRadius:99, opacity:0.68 }} />
      </div>
      <span style={{
        fontSize:11.5, fontWeight:700, color, fontFamily:"'JetBrains Mono',monospace",
        minWidth:48, textAlign:'right',
      }}>{fmtPct(value)}</span>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
const DEFAULT_TOP_N = 15;

export default function ContentAnalysisTab({ authUser, data, breakdown = 'channel', filters }) {
  const isAdmin   = authUser?.role === 'website_admin';
  const [topN, setTopN] = useState(DEFAULT_TOP_N);

  const breakdownRows = data?.breakdown || [];
  const maxN          = Math.max(1, breakdownRows.length);
  const clampedN      = Math.min(maxN, Math.max(1, Math.floor(topN)));
  const updateN       = (v) => setTopN(Math.min(maxN, Math.max(1, Math.floor(+v || DEFAULT_TOP_N))));

  const showHeatmap   = isAdmin && breakdown === 'client';
  const viewLabel     = fmtLabel(breakdown || 'channel');
  const heatmapRows   = data?.inputTypeClientHeatmap || [];

  // Summary stats
  const summary = useMemo(() => {
    if (!breakdownRows.length) return null;
    const convs = breakdownRows.map((r) => +r.conversion || 0);
    const avg   = convs.reduce((a, b) => a + b, 0) / convs.length;
    const best  = breakdownRows.reduce((a, r) => (+r.conversion > +a.conversion ? r : a), breakdownRows[0]);
    const worst = breakdownRows.reduce((a, r) => (+r.conversion < +a.conversion ? r : a), breakdownRows[0]);
    return { avg, best, worst, total: breakdownRows.length };
  }, [breakdownRows]);

  // Performer lists
  const [topPerfs, bottomPerfs] = useMemo(() => {
    const s = [...breakdownRows].sort((a, b) => +b.conversion - +a.conversion);
    return [s.slice(0, 5), [...s].reverse().slice(0, 5)];
  }, [breakdownRows]);

  // Heatmap range
  const heatRange = useMemo(() => {
    const vals = heatmapRows
      .flatMap((r) => (r.clients || []).map((c) => +c.conversion_pct))
      .filter((n) => Number.isFinite(n) && n > 0);
    return { min: vals.length ? Math.min(...vals) : 0, max: vals.length ? Math.max(...vals) : 1 };
  }, [heatmapRows]);

  // Main bar data
  const mainBarData = useMemo(() => {
    const rows = breakdownRows.slice(0, clampedN);
    return {
      labels:   rows.map((r) => r.label),
      datasets: [{ label: 'Conversion %', data: rows.map((r) => +r.conversion || 0) }],
    };
  }, [breakdownRows, clampedN]);

  // Client bar data — sorted descending
  const clientBarData = useMemo(() => {
    const raw    = data?.publishByClient || [];
    const sorted = [...raw].sort((a, b) => (+b.conversion_pct || 0) - (+a.conversion_pct || 0));
    return {
      labels:   sorted.map((r) => r.client_name),
      datasets: [{ label: 'Conversion %', data: sorted.map((r) => +r.conversion_pct || 0) }],
    };
  }, [data?.publishByClient]);

  const clientAvg = useMemo(() => {
    const d = clientBarData.datasets[0]?.data || [];
    return d.length ? d.reduce((a, b) => a + b, 0) / d.length : 0;
  }, [clientBarData]);

  // Hbar height: enough rows to breathe
  const clientChartH = Math.max(180, (clientBarData.labels.length || 0) * 36 + 28);

  return (
    <div className="ca-root" style={{ display:'flex', flexDirection:'column', gap:14 }}>
      <style>{STYLES}</style>

      <FunnelViewContextStrip breakdown={breakdown} filters={filters} />

      {/* KPI strip */}
      {summary && (
        <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
          <KpiCard label="Tracked" value={summary.total} sub={`${viewLabel}s in current view`} />
          <KpiCard label="Avg conversion" value={fmtPct(summary.avg)} />
          <KpiCard label="Best" value={fmtPct(summary.best?.conversion)} sub={summary.best?.label} />
          <KpiCard label="Lowest" value={fmtPct(summary.worst?.conversion)} sub={summary.worst?.label} />
          <KpiCard
            label="Spread"
            value={fmtPct((+summary.best?.conversion || 0) - (+summary.worst?.conversion || 0))}
            sub="best − worst"
          />
        </div>
      )}

      {/* Main: heatmap or bar */}
      {showHeatmap ? (
        <div className="ca-card">
          <SectionHead
            title="Input type × client conversion"
            desc="Published ÷ created per input type and client. Hover cells for raw counts."
          />
          <div style={{ overflowX:'auto' }}>
            <table style={{
              width:'100%', minWidth:880,
              borderCollapse:'separate', borderSpacing:'3px 3px', fontSize:12,
            }}>
              <thead>
                <tr>
                  <th style={{
                    position:'sticky', left:0, zIndex:20, background:'#0c0c10',
                    padding:'5px 18px 5px 0', textAlign:'left',
                    fontSize:9.5, fontWeight:700, color:'#8b8b9a',
                    letterSpacing:'0.07em', textTransform:'uppercase',
                  }}>Input type</th>
                  {(data?.heatmapClients || []).map((c) => (
                    <th key={c} style={{
                      padding:'5px 10px', textAlign:'center',
                      fontSize:10.5, fontWeight:600, color:'#6b6b82', whiteSpace:'nowrap',
                    }}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapRows.map((row) => (
                  <tr key={row.input_type}>
                    <td style={{
                      position:'sticky', left:0, zIndex:10, background:'#0c0c10',
                      padding:'3px 18px 3px 0', fontSize:12, fontWeight:500,
                      color:'#8b8b9a', maxWidth:210,
                      overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap',
                    }} title={row.input_type}>{row.input_type}</td>
                    {(row.clients || []).map((cell, i) => {
                      const conv = Number.isFinite(+cell.conversion_pct) ? +cell.conversion_pct : 0;
                      const s = heatCellStyle(conv, heatRange.min, heatRange.max);
                      return (
                        <td key={i}
                          className="ca-heat-cell"
                          title={`Created: ${cell.assets_created||0}  ·  Published: ${cell.posts_published||0}`}
                          style={{ background:s.bg, border:`1px solid ${s.border}`, color:s.text }}
                        >{fmtPct(conv)}</td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Legend */}
          <div style={{ marginTop:16, display:'flex', alignItems:'center', gap:10 }}>
            <span style={{ fontSize:10.5, color:'#8b8b9a' }}>Low</span>
            <div style={{ height:5, width:130, borderRadius:99, background:'linear-gradient(to right,#631828,#0f4f38)', border:'1px solid rgba(255,255,255,0.04)' }} />
            <span style={{ fontSize:10.5, color:'#8b8b9a' }}>High conversion</span>
            <span style={{ fontSize:10.5, color:'rgba(255,255,255,0.35)', marginLeft:8 }}>· hover for raw counts</span>
          </div>
        </div>
      ) : (
        <div className="ca-card ca-card--glow">
          <SectionHead
            title={`${viewLabel} publish conversion`}
            badge={`${clampedN} of ${maxN}`}
            desc={
              `Top ${clampedN} ${viewLabel.toLowerCase()} entries by publish conversion rate (published ÷ created). Dashed line = average.`
            }
            right={(
              <TopNSpinner value={clampedN} max={maxN} onChange={updateN} />
            )}
          />
          <GradientBar chartData={mainBarData} avg={summary?.avg} height={252} />
        </div>
      )}

      {/* Client bar — sorted, horizontal */}
      {isAdmin && clientBarData.labels.length > 0 && (
        <div className="ca-card">
          <SectionHead
            title="Publish conversion by client"
            desc={`Overall average: ${fmtPct(clientAvg)}.`}
          />
          <GradientBar chartData={clientBarData} avg={clientAvg} horizontal height={clientChartH} />
        </div>
      )}

      {/* Top / bottom performers */}
      {breakdownRows.length >= 4 && !showHeatmap && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14 }}>
          {[
            { title:'Top performers',  rows: topPerfs,    tone:'green' },
            { title:'Needs attention', rows: bottomPerfs, tone:'red'   },
          ].map(({ title, rows, tone }) => {
            const maxVal = Math.max(...rows.map((r) => +r.conversion || 0), 0.001);
            const dotColor = tone === 'green' ? '#22c55e' : '#ef4444';
            return (
              <div className="ca-card" key={title} style={{ padding:'18px 20px' }}>
                <div style={{ display:'flex', alignItems:'center', gap:7, marginBottom:14 }}>
                  <span style={{
                    width:6, height:6, borderRadius:'50%', flexShrink:0,
                    background: dotColor,
                    boxShadow: `0 0 7px ${dotColor}88`,
                  }} />
                  <span style={{ fontSize:10.5, fontWeight:700, color:'#8b8b9a', letterSpacing:'0.07em', textTransform:'uppercase' }}>{title}</span>
                </div>
                <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
                  {rows.map((r, i) => (
                    <PerfRow key={r.label} rank={i+1} label={r.label} value={+r.conversion||0} maxValue={maxVal} tone={tone} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}