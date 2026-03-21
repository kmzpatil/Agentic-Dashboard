import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ChevronLeft, ChevronRight, Share2, Target, Zap,
  TrendingUp, Users, Star, Award, Flame, X,
} from 'lucide-react';
import { API_BASE } from '../../lib/constants';

/* ─────────────────────────────────────────────────────────────────────────────
   Utility helpers
───────────────────────────────────────────────────────────────────────────── */
const fmt = (n) => {
  if (n == null) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(Math.round(n));
};

const PLATFORM_COLORS = {
  instagram: '#E1306C',
  reels:     '#E1306C',
  youtube:   '#FF0000',
  shorts:    '#FF0000',
  tiktok:    '#69C9D0',
  facebook:  '#1877F2',
  linkedin:  '#0A66C2',
  twitter:   '#1DA1F2',
  x:         '#FFFFFF',
  threads:   '#AAAAAA',
  other:     '#555555',
};

function platformColor(name = '') {
  const key = name.toLowerCase().replace(/\s+/g, '');
  for (const [k, v] of Object.entries(PLATFORM_COLORS)) {
    if (key.includes(k)) return v;
  }
  return '#6366f1';
}

/* ─────────────────────────────────────────────────────────────────────────────
   Circular progress gauge (SVG, no Chart.js)
───────────────────────────────────────────────────────────────────────────── */
function CircularGauge({ value = 0, max = 100, size = 280, color = '#6366f1', label = 'EFFICIENCY' }) {
  const r       = (size / 2) * 0.78;
  const cx      = size / 2;
  const cy      = size / 2;
  const circumference = 2 * Math.PI * r;
  const pct     = Math.min(Math.max(value / max, 0), 1);
  const offset  = circumference * (1 - pct);
  const display = typeof value === 'number' ? `${Math.round(value)}%` : value;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e1e1e" strokeWidth={size * 0.075} />
      {/* Progress */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={color}
        strokeWidth={size * 0.075}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 1s ease' }}
      />
      {/* Center text */}
      <text x={cx} y={cy - 6} textAnchor="middle" fill="white" fontSize={size * 0.145} fontWeight="900" fontFamily="system-ui">
        {display}
      </text>
      <text x={cx} y={cy + size * 0.1} textAnchor="middle" fill="#888" fontSize={size * 0.055} fontWeight="700" fontFamily="system-ui" letterSpacing="2">
        {label}
      </text>
    </svg>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Donut chart for platform distribution (canvas / Chart.js)
───────────────────────────────────────────────────────────────────────────── */
function PlatformDonut({ platforms = [] }) {
  const canvasRef = useRef(null);
  const chartRef  = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !platforms.length) return;
    import('chart.js').then(({ Chart, ArcElement, Tooltip, DoughnutController }) => {
      Chart.register(ArcElement, Tooltip, DoughnutController);
      if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null; }
      chartRef.current = new Chart(canvasRef.current, {
        type: 'doughnut',
        data: {
          labels: platforms.map((p) => p.platform),
          datasets: [{
            data:            platforms.map((p) => p.cnt || p.count || 0),
            backgroundColor: platforms.map((p) => platformColor(p.platform)),
            borderWidth:     2,
            borderColor:     '#0d0d0d',
          }],
        },
        options: {
          cutout: '70%',
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          animation: { duration: 1200 },
        },
      });
    });
    return () => { if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null; } };
  }, [platforms]);

  return <canvas ref={canvasRef} style={{ width: 280, height: 280 }} />;
}

/* ─────────────────────────────────────────────────────────────────────────────
   REI tier helper
───────────────────────────────────────────────────────────────────────────── */
function reiTier(score) {
  if (score >= 1.5) return { tier: 'PLATINUM', color: '#e2e8f0', glow: 'rgba(226,232,240,0.4)' };
  if (score >= 1.2) return { tier: 'GOLD',     color: '#f59e0b', glow: 'rgba(245,158,11,0.4)'  };
  if (score >= 0.9) return { tier: 'SILVER',   color: '#94a3b8', glow: 'rgba(148,163,184,0.4)' };
  return               { tier: 'BRONZE',   color: '#b45309', glow: 'rgba(180,83,9,0.4)'   };
}

/* ─────────────────────────────────────────────────────────────────────────────
   Navigation arrows
───────────────────────────────────────────────────────────────────────────── */
function NavArrow({ direction, onClick, disabled }) {
  const isLeft = direction === 'left';
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="absolute"
      style={{
        [isLeft ? 'left' : 'right']: '24px',
        bottom: '32px',
        width: 52,
        height: 52,
        borderRadius: '50%',
        background: disabled ? '#1a1a1a' : (isLeft ? '#1e1e1e' : '#6366f1'),
        border: '1px solid #2a2a2a',
        color: disabled ? '#444' : 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'background 0.2s',
        zIndex: 10,
      }}
    >
      {isLeft ? <ChevronLeft size={22} /> : <ChevronRight size={22} />}
    </button>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Dot pagination
───────────────────────────────────────────────────────────────────────────── */
function DotNav({ total, current, onSelect }) {
  return (
    <div style={{ position: 'absolute', bottom: 44, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 8, zIndex: 10 }}>
      {Array.from({ length: total }).map((_, i) => (
        <button
          key={i}
          onClick={() => onSelect(i)}
          style={{
            width: i === current ? 24 : 8,
            height: 8,
            borderRadius: 4,
            background: i === current ? '#6366f1' : '#333',
            border: 'none',
            cursor: 'pointer',
            transition: 'all 0.3s',
            padding: 0,
          }}
        />
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   CLIENT SCENES
───────────────────────────────────────────────────────────────────────────── */

/* Scene C1: The Momentum */
function ClientMomentum({ data }) {
  const uploaded  = fmt(data.uploaded_count);
  const created   = fmt(data.created_count);
  const published = fmt(data.published_count);
  const spike     = data.best_month_pct > 0 ? `+${Math.round(data.best_month_pct)}%` : null;

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden"
         style={{ background: 'linear-gradient(135deg, #0a0a0a 0%, #0f0f0f 100%)' }}>
      {/* Decorative SVG curves */}
      <svg style={{ position: 'absolute', top: 0, right: 0, opacity: 0.18, pointerEvents: 'none' }}
           width="520" height="320" viewBox="0 0 520 320">
        <path d="M520,0 Q300,80 260,160 Q220,240 0,320" fill="none" stroke="#6366f1" strokeWidth="2" strokeDasharray="8 6"/>
        <path d="M520,40 Q320,100 280,200 Q240,280 40,320" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 8"/>
        <path d="M520,80 Q340,120 300,220" fill="none" stroke="#6366f1" strokeWidth="1" strokeDasharray="4 10"/>
      </svg>

      {/* Main card */}
      <div style={{
        background: '#111111',
        border: '1px solid #1e1e1e',
        borderRadius: 24,
        padding: '48px 56px',
        maxWidth: 680,
        width: '90%',
        position: 'relative',
      }}>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.22em', color: '#ef4444', marginBottom: 16 }}>
          THE MOMENTUM
        </div>
        <div style={{ fontSize: 88, fontWeight: 900, color: 'white', lineHeight: 1, marginBottom: 20, letterSpacing: '-2px' }}>
          {fmt(data.uploaded_count)}
        </div>
        <div style={{ color: '#888', fontSize: 15, lineHeight: 1.7, marginBottom: 32 }}>
          This year, your content engine never stopped. You hit the ground running
          and finished the year with a massive archive of assets.
        </div>
        {/* Engagement row */}
        <div style={{ display: 'flex', gap: 32, marginBottom: 28 }}>
          {[
            { icon: <TrendingUp size={16}/>, val: created,   label: 'Created'   },
            { icon: <Zap size={16}/>,        val: published, label: 'Published' },
          ].map(({ icon, val, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: '#6366f1' }}>{icon}</span>
              <span style={{ color: 'white', fontWeight: 800, fontSize: 18 }}>{val}</span>
              <span style={{ color: '#666', fontSize: 13 }}>{label}</span>
            </div>
          ))}
        </div>
        {/* Spike badge */}
        {spike && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#ef4444', color: 'white',
            borderRadius: 999, padding: '8px 20px', fontWeight: 700, fontSize: 14,
          }}>
            <Flame size={16} />
            Usage spiked by {spike} in {data.best_month}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Team Series (shared by both roles) ─────────────────────────────────── */
function TeamSeries({ data }) {
  const canvasRef = useRef(null);
  const chartRef  = useRef(null);
  const timeline  = data.monthly_timeline || [];

  useEffect(() => {
    if (!canvasRef.current || !timeline.length) return;

    // Chart.js is registered globally via chartSetup
    import('chart.js').then((mod) => {
      const Chart = mod.Chart || mod.default;
      if (!Chart) return;
      if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null; }

      chartRef.current = new Chart(canvasRef.current, {
        type: 'line',
        data: {
          labels: timeline.map((p) => p.label),
          datasets: [
            {
              label: 'Uploaded',
              data: timeline.map((p) => p.uploaded),
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99,102,241,0.12)',
              fill: true, tension: 0.4, borderWidth: 2,
              pointRadius: 4, pointBackgroundColor: '#6366f1',
            },
            {
              label: 'Created',
              data: timeline.map((p) => p.created),
              borderColor: '#a855f7',
              backgroundColor: 'rgba(168,85,247,0.08)',
              fill: true, tension: 0.4, borderWidth: 2,
              pointRadius: 4, pointBackgroundColor: '#a855f7',
            },
            {
              label: 'Published',
              data: timeline.map((p) => p.published),
              borderColor: '#ef4444',
              backgroundColor: 'rgba(239,68,68,0.08)',
              fill: true, tension: 0.4, borderWidth: 2,
              pointRadius: 4, pointBackgroundColor: '#ef4444',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#111',
              borderColor: '#2a2a2a',
              borderWidth: 1,
              titleColor: '#aaa',
              bodyColor: '#eee',
              padding: 10,
              callbacks: {
                labelColor: (ctx) => ({
                  borderColor: ctx.dataset.borderColor,
                  backgroundColor: ctx.dataset.borderColor,
                }),
              },
            },
          },
          scales: {
            x: {
              grid: { color: '#1a1a1a' },
              ticks: { color: '#555', font: { size: 11 } },
            },
            y: {
              grid: { color: '#1a1a1a' },
              ticks: { color: '#555', font: { size: 11 } },
              beginAtZero: true,
            },
          },
          animation: { duration: 900 },
        },
      });
    });

    return () => { if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null; } };
  }, [timeline]);

  const SERIES = [
    { label: 'Uploaded',  color: '#6366f1' },
    { label: 'Created',   color: '#a855f7' },
    { label: 'Published', color: '#ef4444' },
  ];

  const peak = timeline.reduce((best, m) => m.uploaded > (best?.uploaded ?? 0) ? m : best, null);

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ maxWidth: 820, width: '90%' }}>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.22em', color: '#6366f1', marginBottom: 8 }}>
          THE TIMELINE
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <h2 style={{ fontSize: 34, fontWeight: 900, color: 'white', lineHeight: 1.1 }}>
              Your Year in Motion
            </h2>
            {peak && (
              <p style={{ color: '#555', fontSize: 13, marginTop: 6 }}>
                Peak month: <span style={{ color: '#aaa', fontWeight: 700 }}>{peak.label}</span>
                {' '}— {fmt(peak.uploaded)} uploads
              </p>
            )}
          </div>
          {/* Legend */}
          <div style={{ display: 'flex', gap: 20 }}>
            {SERIES.map(({ label, color }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 22, height: 2, background: color, borderRadius: 2 }} />
                <span style={{ color: '#666', fontSize: 12, fontWeight: 600 }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Chart canvas */}
        <div style={{
          height: 260, background: '#0d0d0d',
          borderRadius: 16, padding: '16px 20px',
          border: '1px solid #1a1a1a',
        }}>
          {timeline.length > 0
            ? <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
            : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#333', fontSize: 14 }}>
                No timeline data available
              </div>
            )}
        </div>
      </div>
    </div>
  );
}

/* Scene C2: The Efficiency Engine */
function ClientEfficiency({ data }) {
  const eff   = Math.round(data.processing_efficiency);
  const dfs  = Math.round(data.dfs_score);

  return (
    <div className="relative w-full h-full flex items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 64, maxWidth: 860, width: '90%' }}>
        {/* Gauge */}
        <div style={{ flexShrink: 0 }}>
          <CircularGauge value={eff} color="#6366f1" size={260} label="EFFICIENCY" />
        </div>

        {/* Text column */}
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 36, fontWeight: 900, color: 'white', marginBottom: 20, lineHeight: 1.15 }}>
            The Efficiency Engine
          </h2>
          <p style={{ color: '#888', fontSize: 15, lineHeight: 1.7, marginBottom: 32 }}>
            Your average published video is significantly shorter than your created
            videos. You are mastering the art of the hook! Your Clip Duration
            Alignment shows incredible precision.
          </p>
          {/* DFS card */}
          <div style={{
            background: '#151515',
            border: '1px solid #222',
            borderRadius: 16,
            padding: '20px 24px',
            display: 'flex',
            alignItems: 'center',
            gap: 20,
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: '50%',
              background: '#1a1a3a',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Target size={22} style={{ color: '#6366f1' }} />
            </div>
            <div>
              <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.2em', color: '#888', marginBottom: 4 }}>
                DURATION FIT SCORE (DFS)
              </div>
              <div style={{ fontSize: 32, fontWeight: 900, color: 'white' }}>{dfs}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Scene C3: Content DNA — Omnichannel Explorer */
function ClientContentDNA({ data }) {
  const platforms = data.platforms || [];
  const score     = data.entropy_score || 0;
  const total     = platforms.reduce((s, p) => s + (p.cnt || p.count || 0), 0) || 1;

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      {/* Donut + personality */}
      <div style={{ position: 'relative', marginBottom: 24 }}>
        <PlatformDonut platforms={platforms} />
        {/* Center overlay label */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.2em', color: '#888', marginBottom: 4 }}>
            PERSONALITY
          </div>
          <div style={{ fontSize: 18, fontWeight: 900, color: 'white', textAlign: 'center', maxWidth: 140 }}>
            {data.personality}
          </div>
        </div>
      </div>

      {/* Platform legend */}
      {platforms.length > 0 && (
        <div style={{ display: 'flex', gap: 20, marginBottom: 28, flexWrap: 'wrap', justifyContent: 'center' }}>
          {platforms.slice(0, 5).map((p) => (
            <div key={p.platform} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: platformColor(p.platform) }} />
              <span style={{ color: '#ccc', fontSize: 13, fontWeight: 600 }}>{p.platform}</span>
              <span style={{ color: '#555', fontSize: 12 }}>
                {Math.round((p.cnt || p.count || 0) / total * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Score */}
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 64, fontWeight: 900, color: '#6366f1', lineHeight: 1 }}>
          {score.toFixed(1)}
          <span style={{ fontSize: 28, color: '#555' }}>/10</span>
        </div>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.2em', color: '#888', marginTop: 8 }}>
          CONTENT DIVERSITY SCORE
        </div>
        <div style={{ color: '#666', fontSize: 14, marginTop: 8, maxWidth: 420, textAlign: 'center' }}>
          Your Content Diversity Score is off the charts, successfully distributing
          your message across multiple platforms.
        </div>
      </div>
    </div>
  );
}

/* Scene C4: The Funnel of Success */
function ClientFunnel({ data }) {
  const conv        = Math.round(data.publish_conversion_rate);
  const created     = data.created_count  || 1;
  const published   = data.published_count || 0;
  const maxBar      = Math.max(created, published);
  const createdH    = 200;
  const publishedH  = Math.round((published / maxBar) * 200);
  const lift        = data.best_lift_score;

  return (
    <div className="relative w-full h-full flex items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40, maxWidth: 720, width: '90%' }}>
        {/* Bars */}
        <div style={{ display: 'flex', gap: 80, alignItems: 'flex-end' }}>
          {[
            { label: 'Created',   h: createdH,   color: '#6366f1' },
            { label: 'Published', h: publishedH, color: '#ef4444' },
          ].map(({ label, h, color }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 90, height: h,
                background: color,
                borderRadius: '8px 8px 0 0',
                transition: 'height 1s ease',
              }} />
              <span style={{ color: '#888', fontSize: 14, fontWeight: 600 }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Conversion card */}
        <div style={{
          background: '#111', border: '1px solid #1e1e1e',
          borderRadius: 20, padding: '28px 40px', width: '100%',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={20} color="white" />
            </div>
            <div style={{ fontSize: 28, fontWeight: 900, color: 'white' }}>{conv}% Conversion</div>
          </div>
          <p style={{ color: '#888', fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
            Your production pipeline is blazing fast. But here is your secret weapon:{' '}
            <strong style={{ color: 'white' }}>{data.best_lift_input} → {data.best_lift_output}</strong>{' '}
            yielded your highest Interaction Lift Score of the year.
          </p>
          {lift > 0 && (
            <div style={{ background: '#0d0d0d', borderRadius: 12, padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#666', fontSize: 14 }}>Lift Score</span>
              <span style={{ color: '#ef4444', fontWeight: 900, fontSize: 22 }}>{lift.toFixed(1)}x</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* Scene C5: The Champions */
function ClientChampions({ data, onShare }) {
  const channels = data.top_channels || [];

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ maxWidth: 700, width: '90%' }}>
        <h2 style={{ fontSize: 40, fontWeight: 900, color: 'white', textAlign: 'center', marginBottom: 12 }}>
          The Champions
        </h2>
        <p style={{ color: '#666', textAlign: 'center', fontSize: 15, marginBottom: 36, lineHeight: 1.6 }}>
          A great platform needs great talent. These are your most aligned channels
          and your highest-potential creators.
        </p>

        {/* Channel list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 32 }}>
          {channels.slice(0, 5).map((ch, i) => (
            <div key={ch.name} style={{
              background: i === 0 ? '#0e0e1e' : '#111',
              border: `1px solid ${i === 0 ? '#6366f1' : '#1e1e1e'}`,
              borderRadius: 16,
              padding: '18px 24px',
              display: 'flex',
              alignItems: 'center',
              gap: 20,
            }}>
              <span style={{ color: '#555', fontSize: 20, fontWeight: 900, minWidth: 32 }}>#{i + 1}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 800, fontSize: 17, color: 'white', display: 'flex', alignItems: 'center', gap: 8 }}>
                  {ch.name}
                  {i === 0 && <Award size={16} style={{ color: '#f59e0b' }} />}
                </div>
                {ch.top_creator && (
                  <div style={{ color: '#666', fontSize: 13, marginTop: 2 }}>
                    Top Creator: <strong style={{ color: '#999' }}>{ch.top_creator}</strong>
                  </div>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', color: '#555', marginBottom: 2 }}>
                  ALIGNMENT
                </div>
                <div style={{ fontSize: 26, fontWeight: 900, color: '#6366f1' }}>{ch.score}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ color: '#555', fontSize: 13, fontStyle: 'italic', maxWidth: 360 }}>
            Shoutout to your top 10% of users who drove the majority of your published success!
          </p>
          <button
            onClick={onShare}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: '#6366f1', color: 'white',
              border: 'none', borderRadius: 999,
              padding: '12px 24px', fontWeight: 700, fontSize: 14,
              cursor: 'pointer',
            }}
          >
            <Share2 size={16} />
            Share Results
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   USER SCENES
───────────────────────────────────────────────────────────────────────────── */

/* Scene U1: The Creator's Spark */
function UserSpark({ data }) {
  const spike = data.best_month_pct > 0 ? `+${Math.round(data.best_month_pct)}%` : null;

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden"
         style={{ background: 'linear-gradient(135deg, #0a0a0a 0%, #0f0f0f 100%)' }}>
      <svg style={{ position: 'absolute', top: 0, right: 0, opacity: 0.15, pointerEvents: 'none' }}
           width="480" height="300" viewBox="0 0 480 300">
        <path d="M480,0 Q280,60 240,130 Q200,200 0,300" fill="none" stroke="#6366f1" strokeWidth="2" strokeDasharray="8 6"/>
        <path d="M480,40 Q300,90 260,170 Q220,240 40,300" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 8"/>
      </svg>

      <div style={{
        background: '#111', border: '1px solid #1e1e1e',
        borderRadius: 24, padding: '48px 56px',
        maxWidth: 660, width: '90%',
      }}>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.22em', color: '#6366f1', marginBottom: 16 }}>
          THE CREATOR'S SPARK
        </div>
        <div style={{ fontSize: 80, fontWeight: 900, color: 'white', lineHeight: 1, marginBottom: 20, letterSpacing: '-2px' }}>
          {fmt(data.uploaded_count)}
        </div>
        <p style={{ color: '#888', fontSize: 15, lineHeight: 1.7, marginBottom: 32 }}>
          You were a relentless creator this year. You personally fueled the
          channel's engine, uploading <strong style={{ color: 'white' }}>{fmt(data.uploaded_count)}</strong> raw
          videos and transforming them into{' '}
          <strong style={{ color: 'white' }}>{fmt(data.published_count)}</strong> publish-ready assets.
        </p>
        <div style={{ display: 'flex', gap: 32, marginBottom: 28 }}>
          {[
            { val: fmt(data.created_count),  label: 'Created'   },
            { val: fmt(data.published_count), label: 'Published' },
          ].map(({ val, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: 'white', fontWeight: 800, fontSize: 18 }}>{val}</span>
              <span style={{ color: '#666', fontSize: 13 }}>{label}</span>
            </div>
          ))}
        </div>
        {spike && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#ef4444', color: 'white',
            borderRadius: 999, padding: '8px 20px', fontWeight: 700, fontSize: 14,
          }}>
            <Flame size={16} />
            Your creative output spiked {spike} in {data.best_month}
          </div>
        )}
      </div>
    </div>
  );
}

/* Scene U2: The Efficiency Master */
function UserEfficiency({ data }) {
  const conv = Math.round(data.publish_conversion_rate);
  const dfs = Math.round(data.dfs_score);

  return (
    <div className="relative w-full h-full flex items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 64, maxWidth: 860, width: '90%' }}>
        <div style={{ flexShrink: 0 }}>
          <CircularGauge value={conv} color="#6366f1" size={260} label="CONVERSION" />
        </div>
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 36, fontWeight: 900, color: 'white', marginBottom: 20, lineHeight: 1.15 }}>
            The Efficiency Master
          </h2>
          <p style={{ color: '#888', fontSize: 15, lineHeight: 1.7, marginBottom: 32 }}>
            You know exactly what your audience wants. With a personal Publish
            Conversion Rate of <strong style={{ color: 'white' }}>{conv}%</strong>, your content
            doesn't just sit in the drafts — it goes live. Your Clip Duration
            Alignment shows you've mastered the perfect cut.
          </p>
          <div style={{
            background: '#151515', border: '1px solid #222',
            borderRadius: 16, padding: '20px 24px',
            display: 'flex', alignItems: 'center', gap: 20,
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: '50%', background: '#1a1a3a',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Target size={22} style={{ color: '#6366f1' }} />
            </div>
            <div>
              <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.2em', color: '#888', marginBottom: 4 }}>
                DURATION FIT SCORE (DFS)
              </div>
              <div style={{ fontSize: 32, fontWeight: 900, color: 'white' }}>{dfs}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Scene U3: Content DNA (User) */
function UserContentDNA({ data }) {
  return <ClientContentDNA data={data} />;
}

/* Scene U4: The Hidden Gem — REI */
function UserHiddenGem({ data }) {
  const rei   = data.rei_score || 0;
  const tier  = reiTier(rei);

  return (
    <div className="relative w-full h-full flex items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ textAlign: 'center', maxWidth: 520 }}>
        {/* Trading card */}
        <div style={{
          background: 'linear-gradient(145deg, #111 0%, #181818 100%)',
          border: `2px solid ${tier.color}`,
          borderRadius: 24,
          padding: '48px 56px',
          marginBottom: 32,
          boxShadow: `0 0 60px ${tier.glow}`,
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Glow layer */}
          <div style={{
            position: 'absolute', inset: 0,
            background: `radial-gradient(circle at 50% 30%, ${tier.glow} 0%, transparent 70%)`,
            pointerEvents: 'none',
          }} />

          <div style={{ position: 'relative' }}>
            <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.25em', color: tier.color, marginBottom: 12 }}>
              {tier.tier} CREATOR
            </div>
            <Star size={48} style={{ color: tier.color, marginBottom: 16 }} />
            <div style={{ fontSize: 72, fontWeight: 900, color: 'white', lineHeight: 1, letterSpacing: '-2px' }}>
              {rei.toFixed(2)}x
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.18em', color: '#888', marginTop: 8 }}>
              CREATOR QUALITY SCORE (REI)
            </div>
          </div>
        </div>

        <p style={{ color: '#666', fontSize: 15, lineHeight: 1.7 }}>
          You bring pure quality to the table. Based on your Relative Efficiency
          Index, you consistently output high-potential content, punching above
          your weight class even when tackling the toughest video formats.
        </p>
      </div>
    </div>
  );
}

/* Scene U5: The Team Pillar */
function UserTeamPillar({ data }) {
  const share  = data.share_pct || 0;
  const topPct = data.top_pct   || 0;

  return (
    <div className="relative w-full h-full flex items-center justify-center"
         style={{ background: '#0a0a0a' }}>
      <div style={{ maxWidth: 680, width: '90%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 64 }}>
          {/* Circular share gauge */}
          <div style={{ flexShrink: 0 }}>
            <CircularGauge value={share} color="#6366f1" size={240} label="YOUR SHARE" />
          </div>

          <div style={{ flex: 1 }}>
            <h2 style={{ fontSize: 36, fontWeight: 900, color: 'white', marginBottom: 20, lineHeight: 1.15 }}>
              The Team Pillar
            </h2>
            <p style={{ color: '#888', fontSize: 15, lineHeight: 1.7, marginBottom: 28 }}>
              You are a pillar of your team. You personally drove{' '}
              <strong style={{ color: 'white' }}>{share.toFixed(1)}%</strong> of your channel's
              total uploads this year, cementing your status as a top-tier creator
              and a vital part of the operation.
            </p>

            {/* Top-n% badge */}
            {topPct > 0 && (
              <div style={{
                background: '#0e0e1e', border: '1px solid #6366f1',
                borderRadius: 16, padding: '18px 24px',
                display: 'flex', alignItems: 'center', gap: 16,
              }}>
                <div style={{
                  width: 44, height: 44, borderRadius: '50%', background: '#1a1a3a',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Users size={20} style={{ color: '#6366f1' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.2em', color: '#888', marginBottom: 2 }}>
                    YOUR POWER RANKING
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 900, color: 'white' }}>
                    Top <span style={{ color: '#6366f1' }}>{topPct.toFixed(0)}%</span> of creators
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main WrappedModule
───────────────────────────────────────────────────────────────────────────── */
export default function WrappedModule({ onNavigate }) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [scene,   setScene]   = useState(0);

  const exit = useCallback(() => {
    if (onNavigate) onNavigate({ view: 'mission-control' });
  }, [onNavigate]);

  /* Fetch wrapped data — stale-while-revalidate with localStorage cache */
  useEffect(() => {
    const CACHE_KEY = 'frammer_wrapped_v1';
    const token = localStorage.getItem('frammer_auth_token');
    if (!token) { setError('Not authenticated'); setLoading(false); return; }

    // Load from cache immediately (skip spinner if cache hit)
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      try {
        setData(JSON.parse(cached));
        setLoading(false);
      } catch (_) { /* ignore corrupt cache */ }
    }

    // Always fetch fresh in background
    fetch(`${API_BASE}/wrapped`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((fresh) => {
        const freshStr = JSON.stringify(fresh);
        // Only update state + cache if data actually changed
        if (freshStr !== cached) {
          localStorage.setItem(CACHE_KEY, freshStr);
          setData(fresh);
        }
        setLoading(false);
      })
      .catch((e) => {
        // Only show error if there's no cached data to fall back on
        if (!cached) { setError(e.message); setLoading(false); }
      });
  }, []);

  /* Build scene list */
  const scenes = data
    ? data.role_type === 'client'
      ? [
          <ClientMomentum    key="c1" data={data} />,
          <TeamSeries        key="ts" data={data} />,
          <ClientEfficiency  key="c2" data={data} />,
          <ClientContentDNA  key="c3" data={data} />,
          <ClientFunnel      key="c4" data={data} />,
          <ClientChampions   key="c5" data={data} onShare={() => {}} />,
        ]
      : [
          <UserSpark      key="u1" data={data} />,
          <TeamSeries     key="ts" data={data} />,
          <UserEfficiency key="u2" data={data} />,
          <UserContentDNA key="u3" data={data} />,
          <UserHiddenGem  key="u4" data={data} />,
          <UserTeamPillar key="u5" data={data} />,
        ]
    : [];

  const total   = scenes.length;
  const isLast  = scene === total - 1;
  const canBack = scene > 0;

  const go = useCallback((dir) => {
    setScene((s) => Math.min(Math.max(s + dir, 0), total - 1));
  }, [total]);

  /* Keyboard navigation */
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'ArrowRight') { if (isLast) exit(); else go(1); }
      if (e.key === 'ArrowLeft')  go(-1);
      if (e.key === 'Escape')     exit();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, isLast, exit]);

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center" style={{ background: '#0a0a0a' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 48, height: 48, border: '3px solid #1e1e1e',
            borderTopColor: '#6366f1', borderRadius: '50%',
            animation: 'spin 0.9s linear infinite', margin: '0 auto 16px',
          }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          <div style={{ color: '#555', fontSize: 14 }}>Loading your year in review…</div>
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center" style={{ background: '#0a0a0a' }}>
        <div style={{ color: '#ef4444', textAlign: 'center' }}>
          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Failed to load Wrapped</div>
          <div style={{ color: '#666', fontSize: 13 }}>{error}</div>
          <button
            onClick={exit}
            style={{
              marginTop: 20, padding: '8px 20px', borderRadius: 999,
              background: '#1e1e1e', border: '1px solid #333', color: '#888',
              fontSize: 13, cursor: 'pointer',
            }}
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  /* ── Slides ── */
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: '#0a0a0a' }}>

      {/* ✕ Exit button — top-right, always visible */}
      <button
        onClick={exit}
        title="Exit (Esc)"
        style={{
          position: 'absolute', top: 20, right: 20, zIndex: 20,
          width: 36, height: 36, borderRadius: '50%',
          background: '#1a1a1a', border: '1px solid #2a2a2a',
          color: '#555', display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', transition: 'color 0.15s, border-color 0.15s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = '#ccc'; e.currentTarget.style.borderColor = '#444'; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = '#555'; e.currentTarget.style.borderColor = '#2a2a2a'; }}
      >
        <X size={16} />
      </button>

      {/* Scene */}
      <div style={{ width: '100%', height: '100%' }}>
        {scenes[scene]}
      </div>

      {/* Dot nav */}
      {total > 1 && (
        <DotNav total={total} current={scene} onSelect={setScene} />
      )}

      {/* Back arrow */}
      <NavArrow direction="left" onClick={() => go(-1)} disabled={!canBack} />

      {/* Forward: Continue button on last scene, arrow otherwise */}
      {isLast ? (
        <button
          onClick={exit}
          style={{
            position: 'absolute', right: 24, bottom: 32, zIndex: 10,
            display: 'flex', alignItems: 'center', gap: 8,
            background: '#6366f1', color: 'white', border: 'none',
            borderRadius: 999, padding: '13px 28px',
            fontWeight: 700, fontSize: 15, cursor: 'pointer',
            boxShadow: '0 0 24px rgba(99,102,241,0.35)',
            transition: 'background 0.2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = '#4f46e5'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = '#6366f1'; }}
        >
          Continue
          <ChevronRight size={18} />
        </button>
      ) : (
        <NavArrow direction="right" onClick={() => go(1)} disabled={false} />
      )}
    </div>
  );
}
