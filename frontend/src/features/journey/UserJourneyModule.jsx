import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Doughnut, Line, Bar } from 'react-chartjs-2';
import {
  X, AlertTriangle, Download, Image as ImageIcon,
  CircleDot, ChevronDown, SlidersHorizontal, History,
  Maximize2, Minimize2, RotateCcw, Zap, Settings2,
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber, formatPct } from '../../lib/formatters';
import { buildFilterParams, toOptionList, enumerateDates } from '../../lib/filterUtils';
import { detectAnomalies } from '../../lib/anomalyDetection';
import FloatingDropdown from '../../components/common/FloatingDropdown';
import DateRangeSlider from '../../components/common/DateRangeSlider';

// ─── Palettes ────────────────────────────────────────────────────────────────
const PLATFORM_COLORS = ['#ef4444','#dc2626','#b91c1c','#991b1b','#7f1d1d','#737373','#525252','#3a3a3a'];

// ─── Granularity ─────────────────────────────────────────────────────────────
const GRANULARITIES = [
  { value: 'day', label: 'D' },
  { value: 'week', label: 'W' },
  { value: 'month', label: 'M' },
  { value: 'quarter', label: 'Q' },
];

// ─── Chart tooltip / scale base ──────────────────────────────────────────────
const TOOLTIP = { backgroundColor: '#111', borderColor: '#2a2a2a', borderWidth: 1, titleColor: '#fff', bodyColor: '#737373', padding: 10 };
const SCALE_X = { ticks: { color: '#9ca3af', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.06)' } };
const SCALE_Y = { ticks: { color: '#9ca3af', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.06)' } };

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ title, value, subtitle, trendData }) {
  const isUp = trendData?.length > 1 && trendData[trendData.length - 1] >= trendData[0];
  const lineColor = isUp ? '#10b981' : '#ef4444';

  const chartData = trendData?.length ? {
    labels: trendData.map((_, i) => i),
    datasets: [{
      data: trendData, borderColor: lineColor, borderWidth: 2, tension: 0.4, pointRadius: 0, fill: true,
      backgroundColor: (ctx) => {
        const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
        g.addColorStop(0, `${lineColor}40`); g.addColorStop(1, `${lineColor}00`);
        return g;
      },
    }],
  } : null;

  const chartOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: { x: { display: false }, y: { display: false, min: trendData ? Math.min(...trendData) * 0.9 : 0 } },
    animation: { duration: 600 },
  };

  return (
    <div className="bg-[#111111] rounded-xl p-5 border border-neutral-800 flex justify-between items-start min-h-[120px]">
      <div className="flex-1 flex flex-col justify-between h-full">
        <div>
          <div className="text-xs font-bold tracking-wider text-neutral-500 mb-1">{title}</div>
          <div className="text-3xl font-black text-white tracking-tight">{value}</div>
        </div>
        <div className="text-sm text-neutral-400 mt-2">{subtitle}</div>
      </div>
      {chartData && (
        <div className="w-24 h-16 ml-4 mt-2 shrink-0">
          <Line data={chartData} options={chartOpts} />
        </div>
      )}
    </div>
  );
}

// ─── Gauge ───────────────────────────────────────────────────────────────────
function MetricGauge({ label, value, max, note }) {
  const pct = Math.min((value / max) * 100, 100);
  const data = {
    datasets: [{
      data: [pct, 100 - pct], backgroundColor: ['#ef4444', '#1c1c1c'],
      borderWidth: 0, circumference: 270, rotation: -135,
    }],
  };
  const opts = {
    responsive: true, maintainAspectRatio: false, cutout: '76%',
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    animation: { animateRotate: true, duration: 1200, easing: 'easeInOutQuart' },
  };
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: 148, height: 148 }}>
        <Doughnut data={data} options={opts} />
        <div className="absolute inset-0 flex items-center justify-center" style={{ paddingBottom: 20 }}>
          <span className="text-2xl font-black text-white">{Number(value).toFixed(1)}%</span>
        </div>
      </div>
      <div className="text-center">
        <div className="text-xs font-bold uppercase tracking-[0.18em] text-neutral-400">{label}</div>
        {note && <div className="text-[11px] text-neutral-600 mt-0.5">{note}</div>}
      </div>
    </div>
  );
}

// ─── Granularity Pills ───────────────────────────────────────────────────────
function GranularityPills({ value, onChange }) {
  return (
    <div className="flex gap-1 rounded-xl border border-neutral-800 bg-[#111111] p-1">
      {GRANULARITIES.map((item) => (
        <button key={item.value} onClick={() => onChange(item.value)} title={item.value}
          className={`h-8 w-8 rounded-lg text-xs font-bold transition-colors ${
            item.value === value ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'
          }`}
        >{item.label}</button>
      ))}
    </div>
  );
}

// ─── Top stat card definitions ───────────────────────────────────────────────
const TOP_KPIS = [
  // Row 1 — Engagement (defaults on)
  { id: 'views',          label: 'Views',                    group: 'engagement', default: true },
  { id: 'interactions',   label: 'Interactions',             group: 'engagement', default: true },
  { id: 'er',             label: 'Engagement Rate',          group: 'engagement', default: true },
  { id: 'virality',       label: 'Virality Score',           group: 'engagement', default: true },
  // Row 2 — Pipeline (defaults on)
  { id: 'uploaded',       label: 'Uploaded',                 group: 'pipeline',   default: true },
  { id: 'published',      label: 'Published',                group: 'pipeline',   default: true },
  { id: 'distributions',  label: 'Distributions',            group: 'pipeline',   default: true },
  { id: 'avgvdist',       label: 'Avg Views / Dist',         group: 'pipeline',   default: true },
  // Additional — Engagement breakdown (defaults off)
  { id: 'likes',          label: 'Likes',                    group: 'engagement', default: false },
  { id: 'comments',       label: 'Comments',                 group: 'engagement', default: false },
  { id: 'shares',         label: 'Shares',                   group: 'engagement', default: false },
  { id: 'likeRate',       label: 'Like Rate',                group: 'engagement', default: false },
  { id: 'commentRate',    label: 'Comment Rate',             group: 'engagement', default: false },
  { id: 'shareRate',      label: 'Share Rate',               group: 'engagement', default: false },
  { id: 'likeToComment',  label: 'Like-to-Comment Ratio',   group: 'engagement', default: false },
  // Additional — Pipeline & Reach (defaults off)
  { id: 'publishRate',    label: 'Publish Rate',             group: 'pipeline',   default: false },
  { id: 'distRate',       label: 'Distribution Rate',        group: 'pipeline',   default: false },
  { id: 'contentYield',   label: 'Content Yield',            group: 'pipeline',   default: false },
  { id: 'interactPerView', label: 'Interactions / View',     group: 'reach',      default: false },
  { id: 'interactPerDist', label: 'Interactions / Dist',     group: 'reach',      default: false },
  { id: 'amplification',  label: 'Amplification Potential',  group: 'reach',      default: false },
];

const TOP_GROUPS = { engagement: 'Engagement', pipeline: 'Pipeline', reach: 'Reach & Efficiency' };

// ─── Sensitivity KPI definitions (id must match computation keys) ────────────
const SENS_KPIS = [
  { id: 'engagementRate',   label: 'Engagement Rate',           group: 'engagement', default: true },
  { id: 'likeRate',         label: 'Like Rate',                  group: 'engagement', default: false },
  { id: 'commentRate',      label: 'Comment Rate',               group: 'engagement', default: false },
  { id: 'shareRate',        label: 'Share Rate',                  group: 'engagement', default: false },
  { id: 'likeToComment',    label: 'Like-to-Comment Ratio',      group: 'engagement', default: false },
  { id: 'virality',         label: 'Virality Score',              group: 'reach',      default: true },
  { id: 'avgViewsDist',     label: 'Avg Views / Distribution',    group: 'reach',      default: true },
  { id: 'amplification',    label: 'Amplification Potential',     group: 'reach',      default: false },
  { id: 'publishRate',      label: 'Publish Rate',                group: 'pipeline',   default: true },
  { id: 'contentYield',     label: 'Content Yield',               group: 'pipeline',   default: false },
  { id: 'interactPerView',  label: 'Interactions / View',         group: 'pipeline',   default: true },
  { id: 'interactPerDist',  label: 'Interactions / Distribution', group: 'pipeline',   default: false },
];

const SENS_GROUPS = { engagement: 'Engagement', reach: 'Reach & Virality', pipeline: 'Pipeline Efficiency' };

// ─── KPI Toggle Dropdown ─────────────────────────────────────────────────────
const ALL_GROUP_LABELS = { ...TOP_GROUPS, ...SENS_GROUPS };

function KpiToggle({ items, active, onToggle, className = '' }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Group items if they have a group property
  const hasGroups = items.some(i => i.group);
  const groups = hasGroups
    ? [...new Set(items.map(i => i.group))].map(g => ({ key: g, label: ALL_GROUP_LABELS[g] || g, items: items.filter(i => i.group === g) }))
    : [{ key: 'all', label: null, items }];

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button type="button" onClick={() => setOpen(o => !o)}
        className={`inline-flex h-7 w-7 items-center justify-center rounded-lg border transition-colors ${open ? 'border-red-500/40 bg-red-500/10 text-red-400' : 'border-neutral-800 text-neutral-500 hover:text-white hover:border-neutral-600'}`}
        title="Configure visible KPIs">
        <Settings2 size={14} />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-64 max-h-[400px] overflow-y-auto rounded-xl border border-neutral-800 bg-[#0d0d0d] backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[100] p-1"
          style={{ scrollbarWidth: 'thin', scrollbarColor: '#333 #0d0d0d' }}>
          {groups.map(g => (
            <div key={g.key}>
              {g.label && <div className="px-3 py-1.5 text-[9px] font-black uppercase tracking-[0.2em] text-neutral-600 bg-neutral-900/50">{g.label}</div>}
              {g.items.map(item => {
                const isOn = active.includes(item.id);
                return (
                  <button key={item.id} onClick={() => onToggle(item.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all flex items-center gap-2.5 ${isOn ? 'text-white' : 'text-neutral-500 hover:text-neutral-300'}`}>
                    <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${isOn ? 'bg-red-500 border-red-500' : 'border-neutral-700 bg-neutral-900'}`}>
                      {isOn && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                    </div>
                    {item.label}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Sensitivity Slider ──────────────────────────────────────────────────────
function SensSlider({ label, value, onChange, icon }) {
  const pct = value;
  const color = pct > 0 ? '#10b981' : pct < 0 ? '#ef4444' : '#525252';
  return (
    <div className="group">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          {icon}
          <span className="text-sm font-semibold text-neutral-300">{label}</span>
        </div>
        <span className="text-sm font-black tabular-nums" style={{ color }}>
          {pct > 0 ? '+' : ''}{pct}%
        </span>
      </div>
      <input
        type="range" min={-50} max={100} step={1} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, #ef4444 0%, #525252 33%, #10b981 100%)`,
          accentColor: color,
        }}
      />
    </div>
  );
}

// ─── Sensitivity Effect Row ──────────────────────────────────────────────────
function EffectRow({ label, oldVal, newVal, format = 'number', inverse = false }) {
  const delta = oldVal !== 0 ? ((newVal - oldVal) / oldVal) * 100 : 0;
  const improved = inverse ? delta < 0 : delta > 0;
  const color = Math.abs(delta) < 0.5 ? 'text-neutral-400' : improved ? 'text-emerald-400' : 'text-red-400';
  const fmt = (v) => {
    if (format === 'pct') return `${Number(v).toFixed(2)}%`;
    if (format === 'ratio') return Number(v).toFixed(2);
    return formatNumber(Math.round(v));
  };
  return (
    <div className="flex items-center justify-between py-3 border-b border-neutral-800/40 last:border-0">
      <div>
        <div className="text-sm font-semibold text-neutral-300">{label}</div>
        {Math.abs(delta) >= 0.5 && <div className="text-xs text-neutral-600">was {fmt(oldVal)}</div>}
      </div>
      <div className="text-right">
        <div className="text-lg font-black text-white">{fmt(newVal)}</div>
        {Math.abs(delta) >= 0.5 && (
          <div className={`text-xs font-bold ${color}`}>
            {delta > 0 ? '+' : ''}{delta.toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// ─── Main ────────────────────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════════════
export default function UserJourneyModule({ authUser }) {
  // ── Core state ──────────────────────────────────────────────────────────────
  const [granularity, setGranularity] = useState('week');
  const [activeChart, setActiveChart] = useState('engagement');
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [pipelineTab, setPipelineTab] = useState('conversion'); // 'conversion' | 'sensitivity'

  // ── KPI visibility state ────────────────────────────────────────────────────
  const [visibleTopKpis, setVisibleTopKpis] = useState(() => TOP_KPIS.filter(k => k.default).map(k => k.id));
  const [visibleSensKpis, setVisibleSensKpis] = useState(() => SENS_KPIS.filter(k => k.default).map(k => k.id));

  const toggleTopKpi = (id) => setVisibleTopKpis(prev => prev.includes(id) ? prev.filter(k => k !== id) : [...prev, id]);
  const toggleSensKpi = (id) => setVisibleSensKpis(prev => prev.includes(id) ? prev.filter(k => k !== id) : [...prev, id]);

  // ── Filter state ────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState({
    company: authUser?.role === 'client_admin' ? [authUser.clientName] : ['All'],
    channel: ['All'], user: ['All'], language: ['All'],
    inputType: ['All'], outputType: ['All'], dateFrom: '', dateTo: '',
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [isFiltersOpen, setIsFiltersOpen] = useState(true);

  // ── Time-series feature state ───────────────────────────────────────────────
  const [showComparison, setShowComparison] = useState(false);
  const [comparisonOffset, setComparisonOffset] = useState(1);
  const [showPoints, setShowPoints] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const chartRef = useRef(null);

  // ── Sensitivity state ───────────────────────────────────────────────────────
  const [sens, setSens] = useState({ views: 0, likes: 0, comments: 0, shares: 0, uploaded: 0, published: 0, distributions: 0 });
  const updateSens = (key, val) => setSens(prev => ({ ...prev, [key]: val }));

  // ── Maximize side-effects ───────────────────────────────────────────────────
  useEffect(() => {
    if (isMaximized) { document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = ''; }; }
    document.body.style.overflow = '';
  }, [isMaximized]);

  useEffect(() => {
    const t = setTimeout(() => { if (chartRef.current?.resize) chartRef.current.resize(); window.dispatchEvent(new Event('resize')); }, 80);
    return () => clearTimeout(t);
  }, [isMaximized]);

  // ── Filter helpers ──────────────────────────────────────────────────────────
  const appliedFiltersQuery = useMemo(() => buildFilterParams(appliedFilters), [appliedFilters]);
  const appliedSuffix = appliedFiltersQuery ? `&${appliedFiltersQuery}` : '';

  const workingFiltersQuery = useMemo(() => buildFilterParams(filters), [filters]);

  const activeFilterCount = useMemo(() => (
    Object.entries(filters).reduce((count, [key, value]) => {
      if (key === 'dateFrom' || key === 'dateTo') return value ? count + 1 : count;
      if (Array.isArray(value)) return count + value.filter(v => v !== 'All').length;
      return value && value !== 'All' ? count + 1 : count;
    }, 0)
  ), [filters]);

  // ── Filter options API ──────────────────────────────────────────────────────
  const effectiveCompany = filters.company?.[0] !== 'All' ? filters.company[0] : '';
  const filterOptionsUrl = `${API_BASE}/usage-trends/v1/filters/options${effectiveCompany ? `?company=${encodeURIComponent(effectiveCompany)}` : ''}`;
  const { data: filterOptionsData, loading: filterOptionsLoading, error: filterOptionsError } = useApi(filterOptionsUrl, [filterOptionsUrl]);

  const filterOptions = useMemo(() => {
    const base = { company: ['All'], channel: ['All'], user: ['All'], language: ['All'], input_type: ['All'], output_type: ['All'] };
    const api = filterOptionsData?.filters || {};
    return {
      company: api.company || base.company, channel: api.channel || base.channel,
      user: api.user || base.user, language: api.language || base.language,
      input_type: api.input_type || base.input_type, output_type: api.output_type || base.output_type,
    };
  }, [filterOptionsData]);

  // ── Date range for slider ───────────────────────────────────────────────────
  const dateRangeUrl = `${API_BASE}/usage-trends/v1/filters/date-range`;
  const { data: dateRangeData } = useApi(dateRangeUrl, [dateRangeUrl]);

  const validateUrl = workingFiltersQuery ? `${API_BASE}/usage-trends/v1/filters/validate?${workingFiltersQuery}` : null;
  const { data: validateData } = useApi(validateUrl, [validateUrl]);

  const minDate = dateRangeData?.min_date || filterOptionsData?.date_range?.min_date || '';
  const maxDate = dateRangeData?.max_date || filterOptionsData?.date_range?.max_date || '';
  const sliderDates = useMemo(() => enumerateDates(minDate, maxDate), [minDate, maxDate]);

  const dateStartIndex = useMemo(() => {
    if (!sliderDates.length) return 0;
    const idx = filters.dateFrom ? sliderDates.indexOf(filters.dateFrom) : 0;
    return idx >= 0 ? idx : 0;
  }, [sliderDates, filters.dateFrom]);

  const dateEndIndex = useMemo(() => {
    if (!sliderDates.length) return 0;
    const fallback = sliderDates.length - 1;
    const idx = filters.dateTo ? sliderDates.indexOf(filters.dateTo) : fallback;
    return idx >= 0 ? idx : fallback;
  }, [sliderDates, filters.dateTo]);

  const handleDateRangeChange = (nextStart, nextEnd) => {
    if (!sliderDates.length) return;
    const max = sliderDates.length - 1;
    const s = Math.min(Math.max(Math.min(nextStart, nextEnd), 0), max);
    const e = Math.min(Math.max(Math.max(nextStart, nextEnd), 0), max);
    setFilters(prev => ({ ...prev, dateFrom: s === 0 ? '' : sliderDates[s], dateTo: e === max ? '' : sliderDates[e] }));
  };

  const hasDataForFilters = validateData?.has_data;

  // ── Main data API ───────────────────────────────────────────────────────────
  const apiQuery = `${API_BASE}/user-journey?granularity=${granularity}${appliedSuffix}`;
  const { data, loading, error } = useApi(apiQuery, [apiQuery]);

  const timeseries  = data?.timeseries            || [];
  const summary     = data?.summary               || {};
  const platformBD  = data?.platform_breakdown    || [];
  const outputBD    = data?.output_type_breakdown || [];
  const recent      = data?.recent_journey        || [];

  // ── Derived totals ──────────────────────────────────────────────────────────
  const totalViews    = Number(summary.views    || 0);
  const totalLikes    = Number(summary.likes    || 0);
  const totalComments = Number(summary.comments || 0);
  const totalShares   = Number(summary.shares   || 0);
  const totalInteract = totalLikes + totalComments + totalShares;
  const virality      = totalViews > 0 ? (totalShares / totalViews) * 100 : 0;
  const avgViewsDist  = (summary.distributions || 0) > 0 ? totalViews / summary.distributions : 0;

  // ── Sparklines ──────────────────────────────────────────────────────────────
  const spkViews    = useMemo(() => timeseries.map(r => r.views || 0), [timeseries]);
  const spkInteract = useMemo(() => timeseries.map(r => (r.likes||0)+(r.comments||0)+(r.shares||0)), [timeseries]);
  const spkER       = useMemo(() => timeseries.map(r => r.engagement_rate_pct || 0), [timeseries]);
  const spkViral    = useMemo(() => timeseries.map(r => (r.views||0) > 0 ? (r.shares/r.views)*100 : 0), [timeseries]);
  const spkUploaded = useMemo(() => timeseries.map(r => r.uploaded_videos || 0), [timeseries]);
  const spkPublish  = useMemo(() => timeseries.map(r => r.published_posts || 0), [timeseries]);
  const spkDist     = useMemo(() => timeseries.map(r => r.distributions || 0), [timeseries]);
  const spkAvgV     = useMemo(() => timeseries.map(r => (r.distributions||0) > 0 ? r.views/r.distributions : 0), [timeseries]);
  const spkLikes    = useMemo(() => timeseries.map(r => r.likes || 0), [timeseries]);
  const spkComments = useMemo(() => timeseries.map(r => r.comments || 0), [timeseries]);
  const spkShares   = useMemo(() => timeseries.map(r => r.shares || 0), [timeseries]);
  const spkLikeRate = useMemo(() => timeseries.map(r => (r.views||0) > 0 ? ((r.likes||0)/(r.views))*100 : 0), [timeseries]);
  const spkCommentRate = useMemo(() => timeseries.map(r => (r.views||0) > 0 ? ((r.comments||0)/(r.views))*100 : 0), [timeseries]);
  const spkShareRate = useMemo(() => timeseries.map(r => (r.views||0) > 0 ? ((r.shares||0)/(r.views))*100 : 0), [timeseries]);
  const spkPubRate  = useMemo(() => timeseries.map(r => (r.uploaded_videos||0) > 0 ? ((r.published_posts||0)/(r.uploaded_videos))*100 : 0), [timeseries]);
  const spkIPV      = useMemo(() => timeseries.map(r => (r.views||0) > 0 ? ((r.likes||0)+(r.comments||0)+(r.shares||0))/(r.views) : 0), [timeseries]);
  const spkIPD      = useMemo(() => timeseries.map(r => (r.distributions||0) > 0 ? ((r.likes||0)+(r.comments||0)+(r.shares||0))/(r.distributions) : 0), [timeseries]);

  // ── Platform drill-down ─────────────────────────────────────────────────────
  const platformStats = useMemo(() => {
    if (!selectedPlatform) return null;
    const rows = recent.filter(r => r.platform === selectedPlatform);
    const v = rows.reduce((s, r) => s + (r.views||0), 0);
    const l = rows.reduce((s, r) => s + (r.likes||0), 0);
    const c = rows.reduce((s, r) => s + (r.comments||0), 0);
    const sh= rows.reduce((s, r) => s + (r.shares||0), 0);
    const int = l + c + sh;
    return { views: v, likes: l, comments: c, shares: sh, er: v > 0 ? (int/v*100).toFixed(2) : '0.00', count: rows.length };
  }, [selectedPlatform, recent]);

  // ── Language breakdown ──────────────────────────────────────────────────────
  const langBD = useMemo(() => {
    const m = {};
    recent.forEach(r => { const k = r.language || 'Unknown'; m[k] = (m[k]||0) + (r.views||0); });
    return Object.entries(m).sort(([,a],[,b]) => b-a).slice(0,6);
  }, [recent]);
  const maxLang = Math.max(...langBD.map(([,v]) => v), 1);

  // ── Input type breakdown ────────────────────────────────────────────────────
  const inputBD = useMemo(() => {
    const m = {};
    recent.forEach(r => { const k = r.input_type || 'Unknown'; m[k] = (m[k]||0) + (r.views||0); });
    return Object.entries(m).sort(([,a],[,b]) => b-a).slice(0,6);
  }, [recent]);
  const maxInput = Math.max(...inputBD.map(([,v]) => v), 1);

  // ── Quick insights ──────────────────────────────────────────────────────────
  const topByViews = platformBD.reduce((b, p) => !b || p.views > b.views ? p : b, null);
  const topByER    = platformBD.reduce((b, p) => !b || p.engagement_rate_pct > b.engagement_rate_pct ? p : b, null);
  const topOutput  = outputBD.reduce((b, o) => !b || o.views_per_post > b.views_per_post ? o : b, null);

  // ── Anomaly detection (client-side) ─────────────────────────────────────────
  const anomalies = useMemo(() => {
    const points = timeseries.map(r => {
      let value = 0;
      if (activeChart === 'engagement') value = r.views || 0;
      else if (activeChart === 'rate') value = r.engagement_rate_pct || 0;
      else if (activeChart === 'virality') value = (r.views||0) > 0 ? (r.shares/r.views)*100 : 0;
      else value = r.views || 0;
      return { period: r.period, value };
    });
    return detectAnomalies(points);
  }, [timeseries, activeChart]);

  const anomalyDates = useMemo(() => new Map(anomalies.map(a => [String(a.period).slice(0, 10), a.direction])), [anomalies]);

  // ── Chart tabs ──────────────────────────────────────────────────────────────
  const TABS = [
    { id: 'engagement', label: 'Views & Interactions' },
    { id: 'rate',       label: 'Engagement Rate' },
    { id: 'platforms',  label: 'Platforms' },
    { id: 'virality',   label: 'Virality' },
  ];

  // ── Chart data with anomalies and comparison ────────────────────────────────
  const engagementData = useMemo(() => {
    const labels = timeseries.map(r => r.period);
    const mainData = timeseries.map(r => r.views || 0);
    const datasets = [
      {
        label: 'Views', data: mainData,
        borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', tension: 0.4, fill: true, borderWidth: 2,
        pointRadius: (ctx) => { const d = labels[ctx.dataIndex]; return anomalyDates.has(d) ? 6 : showPoints ? 3 : 0; },
        pointHoverRadius: (ctx) => anomalyDates.has(labels[ctx.dataIndex]) ? 9 : 5,
        pointBackgroundColor: (ctx) => { const d = labels[ctx.dataIndex]; if (!anomalyDates.has(d)) return '#ef4444'; return anomalyDates.get(d) === 'drop' ? '#F59E0B' : '#34D399'; },
        pointBorderColor: (ctx) => { const d = labels[ctx.dataIndex]; if (!anomalyDates.has(d)) return '#ef4444'; return anomalyDates.get(d) === 'drop' ? '#92400E' : '#065F46'; },
        pointBorderWidth: (ctx) => anomalyDates.has(labels[ctx.dataIndex]) ? 2 : 0,
      },
      {
        label: 'Interactions', data: timeseries.map(r => (r.likes||0)+(r.comments||0)+(r.shares||0)),
        borderColor: 'rgba(255,255,255,0.25)', backgroundColor: 'transparent', tension: 0.4, fill: false,
        pointRadius: 0, pointHoverRadius: 5, borderDash: [4, 4],
      },
    ];
    if (showComparison) {
      datasets.push({
        label: `Views (${comparisonOffset}p Lag)`,
        data: labels.map((_, idx) => idx >= comparisonOffset ? mainData[idx - comparisonOffset] : null),
        borderColor: '#A855F7', backgroundColor: 'transparent', borderWidth: 2, tension: 0.4,
        borderDash: [3, 3], fill: false, pointRadius: 0, pointHoverRadius: 4,
      });
    }
    return { labels, datasets };
  }, [timeseries, anomalyDates, showPoints, showComparison, comparisonOffset]);

  const rateData = useMemo(() => {
    const labels = timeseries.map(r => r.period);
    const mainData = timeseries.map(r => r.engagement_rate_pct || 0);
    const datasets = [{
      label: 'Engagement Rate %', data: mainData,
      borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', tension: 0.4, fill: true, borderWidth: 2,
      pointRadius: (ctx) => { const d = labels[ctx.dataIndex]; return anomalyDates.has(d) ? 6 : showPoints ? 3 : 0; },
      pointHoverRadius: (ctx) => anomalyDates.has(labels[ctx.dataIndex]) ? 9 : 5,
      pointBackgroundColor: (ctx) => { const d = labels[ctx.dataIndex]; if (!anomalyDates.has(d)) return '#ef4444'; return anomalyDates.get(d) === 'drop' ? '#F59E0B' : '#34D399'; },
      pointBorderColor: (ctx) => { const d = labels[ctx.dataIndex]; if (!anomalyDates.has(d)) return '#ef4444'; return anomalyDates.get(d) === 'drop' ? '#92400E' : '#065F46'; },
      pointBorderWidth: (ctx) => anomalyDates.has(labels[ctx.dataIndex]) ? 2 : 0,
    }];
    if (showComparison) {
      datasets.push({
        label: `Engagement Rate (${comparisonOffset}p Lag)`,
        data: labels.map((_, idx) => idx >= comparisonOffset ? mainData[idx - comparisonOffset] : null),
        borderColor: '#A855F7', backgroundColor: 'transparent', borderWidth: 2, tension: 0.4,
        borderDash: [3, 3], fill: false, pointRadius: 0, pointHoverRadius: 4,
      });
    }
    return { labels, datasets };
  }, [timeseries, anomalyDates, showPoints, showComparison, comparisonOffset]);

  const viralityData = useMemo(() => {
    const labels = timeseries.map(r => r.period);
    const mainData = timeseries.map(r => (r.views||0) > 0 ? (r.shares/r.views)*100 : 0);
    const datasets = [{
      label: 'Virality %', data: mainData,
      borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', tension: 0.4, fill: true, borderWidth: 2,
      pointRadius: (ctx) => { const d = labels[ctx.dataIndex]; return anomalyDates.has(d) ? 6 : showPoints ? 3 : 0; },
      pointHoverRadius: (ctx) => anomalyDates.has(labels[ctx.dataIndex]) ? 9 : 5,
      pointBackgroundColor: (ctx) => { const d = labels[ctx.dataIndex]; if (!anomalyDates.has(d)) return '#ef4444'; return anomalyDates.get(d) === 'drop' ? '#F59E0B' : '#34D399'; },
      pointBorderColor: (ctx) => { const d = labels[ctx.dataIndex]; if (!anomalyDates.has(d)) return '#ef4444'; return anomalyDates.get(d) === 'drop' ? '#92400E' : '#065F46'; },
      pointBorderWidth: (ctx) => anomalyDates.has(labels[ctx.dataIndex]) ? 2 : 0,
    }];
    if (showComparison) {
      datasets.push({
        label: `Virality (${comparisonOffset}p Lag)`,
        data: labels.map((_, idx) => idx >= comparisonOffset ? mainData[idx - comparisonOffset] : null),
        borderColor: '#A855F7', backgroundColor: 'transparent', borderWidth: 2, tension: 0.4,
        borderDash: [3, 3], fill: false, pointRadius: 0, pointHoverRadius: 4,
      });
    }
    return { labels, datasets };
  }, [timeseries, anomalyDates, showPoints, showComparison, comparisonOffset]);

  const platformData = useMemo(() => ({
    labels: platformBD.map(r => r.platform),
    datasets: [
      { label: 'Views', data: platformBD.map(r => r.views||0), backgroundColor: 'rgba(239,68,68,0.65)', borderRadius: 6, borderSkipped: false },
      { label: 'Likes', data: platformBD.map(r => r.likes||0), backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 6, borderSkipped: false },
    ],
  }), [platformBD]);

  const doughnutData = useMemo(() => ({
    labels: ['Likes', 'Comments', 'Shares'],
    datasets: [{
      data: [totalLikes, totalComments, totalShares],
      backgroundColor: ['#ef4444', '#525252', '#262626'], borderWidth: 0, hoverOffset: 8,
    }],
  }), [totalLikes, totalComments, totalShares]);

  const platformDoughnutData = useMemo(() => ({
    labels: platformBD.map(p => p.platform),
    datasets: [{
      data: platformBD.map(p => p.views),
      backgroundColor: PLATFORM_COLORS.slice(0, platformBD.length),
      borderColor: '#111111', borderWidth: 2, hoverOffset: 8,
    }],
  }), [platformBD]);

  const platformDoughnutOpts = useMemo(() => ({
    responsive: true, maintainAspectRatio: false, cutout: '48%',
    plugins: {
      legend: { position: 'right', labels: { color: '#737373', font: { size: 11 }, boxWidth: 10, padding: 12 } },
      tooltip: { ...TOOLTIP, callbacks: { label: ctx => ` ${ctx.label}: ${formatNumber(ctx.raw)} views` } },
    },
    onClick: (_evt, elements) => {
      if (elements.length > 0) {
        const platform = platformBD[elements[0].index]?.platform;
        if (platform) setSelectedPlatform(prev => prev === platform ? null : platform);
      }
    },
    animation: { duration: 700 },
  }), [platformBD]);

  const baseOpts = {
    responsive: true, maintainAspectRatio: false, animation: { duration: 600 },
    plugins: { legend: { labels: { color: '#525252', font: { size: 11 }, boxWidth: 12, padding: 16 } }, tooltip: TOOLTIP },
    scales: { x: SCALE_X, y: SCALE_Y },
  };
  const rateOpts  = { ...baseOpts, scales: { x: SCALE_X, y: { ...SCALE_Y, ticks: { ...SCALE_Y.ticks, callback: v => `${v}%` } } } };
  const doughOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'right', labels: { color: '#737373', font: { size: 11 }, boxWidth: 10, padding: 12 } },
      tooltip: { ...TOOLTIP, callbacks: { label: ctx => ` ${ctx.label}: ${formatNumber(ctx.raw)}${totalInteract > 0 ? ` · ${((ctx.raw/totalInteract)*100).toFixed(1)}%` : ''}` } },
    },
    animation: { duration: 900 },
  };

  // ── Active chart renderer ───────────────────────────────────────────────────
  const chartEl = (() => {
    if (activeChart === 'engagement') return <Line ref={chartRef} data={engagementData} options={baseOpts} />;
    if (activeChart === 'rate')       return <Line ref={chartRef} data={rateData}       options={rateOpts} />;
    if (activeChart === 'virality')   return <Line ref={chartRef} data={viralityData}   options={rateOpts} />;
    if (activeChart === 'platforms')  return <Bar  ref={chartRef} data={platformData}   options={baseOpts} />;
    return null;
  })();

  // ── Export handlers ─────────────────────────────────────────────────────────
  const handleExportCsv = () => {
    let csv = 'Date,Views,Likes,Comments,Shares,Engagement_Rate,Virality\n';
    timeseries.forEach(r => {
      const vir = (r.views||0) > 0 ? ((r.shares||0)/(r.views)*100).toFixed(2) : '0';
      csv += `${r.period},${r.views||0},${r.likes||0},${r.comments||0},${r.shares||0},${r.engagement_rate_pct||0},${vir}\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `metrics_${granularity}.csv`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExportImage = () => {
    if (chartRef.current?.canvas) {
      const url = chartRef.current.canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url; a.download = 'metrics_chart.png'; a.click();
    }
  };

  // ── Sensitivity analysis computations ───────────────────────────────────────
  const uploaded   = Number(summary.uploaded_videos || 0);
  const published  = Number(summary.published_posts || 0);
  const distCount  = Number(summary.distributions || 0);

  const simViews    = totalViews    * (1 + sens.views / 100);
  const simLikes    = totalLikes    * (1 + sens.likes / 100);
  const simComments = totalComments * (1 + sens.comments / 100);
  const simShares   = totalShares   * (1 + sens.shares / 100);
  const simUploaded = uploaded  * (1 + sens.uploaded / 100);
  const simPublished= published * (1 + sens.published / 100);
  const simDist     = distCount * (1 + sens.distributions / 100);

  const simInteract = simLikes + simComments + simShares;
  const simER       = simViews > 0 ? (simInteract / simViews) * 100 : 0;
  const simVirality = simViews > 0 ? (simShares / simViews) * 100 : 0;
  const simAvgVDist = simDist > 0 ? simViews / simDist : 0;
  const simPubRate  = simUploaded > 0 ? (simPublished / simUploaded) * 100 : 0;
  const simLikeRate = simViews > 0 ? (simLikes / simViews) * 100 : 0;
  const simCommentRate = simViews > 0 ? (simComments / simViews) * 100 : 0;
  const simShareRate = simViews > 0 ? (simShares / simViews) * 100 : 0;
  const simLikeToComment = simComments > 0 ? simLikes / simComments : 0;
  const simCPV      = simViews > 0 ? simInteract / simViews : 0; // cost-per-view analogue
  const simDistEfficiency = simDist > 0 ? simInteract / simDist : 0;
  const simContentYield   = simUploaded > 0 ? simDist / simUploaded : 0;
  const simAmplification  = simViews > 0 ? (simShares * simAvgVDist) : 0;

  // Originals for delta display
  const origER           = totalViews > 0 ? (totalInteract / totalViews) * 100 : 0;
  const origVirality     = virality;
  const origAvgVDist     = avgViewsDist;
  const origPubRate      = uploaded > 0 ? (published / uploaded) * 100 : 0;
  const origLikeRate     = totalViews > 0 ? (totalLikes / totalViews) * 100 : 0;
  const origCommentRate  = totalViews > 0 ? (totalComments / totalViews) * 100 : 0;
  const origShareRate    = totalViews > 0 ? (totalShares / totalViews) * 100 : 0;
  const origLikeToComment = totalComments > 0 ? totalLikes / totalComments : 0;
  const origCPV          = totalViews > 0 ? totalInteract / totalViews : 0;
  const origDistEfficiency = distCount > 0 ? totalInteract / distCount : 0;
  const origContentYield   = uploaded > 0 ? distCount / uploaded : 0;
  const origAmplification  = totalViews > 0 ? (totalShares * origAvgVDist) : 0;

  const sensHasChanges = Object.values(sens).some(v => v !== 0);

  // ── Sensitivity KPI value map (keyed by SENS_KPIS id) ──────────────────────
  const sensKpiMap = {
    engagementRate:  { oldVal: origER,              newVal: simER,              format: 'pct' },
    likeRate:        { oldVal: origLikeRate,         newVal: simLikeRate,        format: 'pct' },
    commentRate:     { oldVal: origCommentRate,      newVal: simCommentRate,     format: 'pct' },
    shareRate:       { oldVal: origShareRate,        newVal: simShareRate,       format: 'pct' },
    likeToComment:   { oldVal: origLikeToComment,    newVal: simLikeToComment,   format: 'ratio' },
    virality:        { oldVal: origVirality,         newVal: simVirality,        format: 'pct' },
    avgViewsDist:    { oldVal: origAvgVDist,         newVal: simAvgVDist,        format: 'number' },
    amplification:   { oldVal: origAmplification,    newVal: simAmplification,   format: 'number' },
    publishRate:     { oldVal: origPubRate,           newVal: simPubRate,         format: 'pct' },
    contentYield:    { oldVal: origContentYield,      newVal: simContentYield,    format: 'ratio' },
    interactPerView: { oldVal: origCPV,              newVal: simCPV,             format: 'ratio' },
    interactPerDist: { oldVal: origDistEfficiency,    newVal: simDistEfficiency,  format: 'number' },
  };

  // Group visible sensitivity KPIs by their group
  const visibleSensGrouped = useMemo(() => {
    const grouped = {};
    SENS_KPIS.filter(k => visibleSensKpis.includes(k.id)).forEach(k => {
      if (!grouped[k.group]) grouped[k.group] = [];
      grouped[k.group].push(k);
    });
    return grouped;
  }, [visibleSensKpis]);

  // ── Loading / error ─────────────────────────────────────────────────────────
  if (loading) return <div className="h-full flex items-center justify-center text-sm text-neutral-500">Loading engagement metrics...</div>;
  if (error)   return <div className="p-6 text-sm text-red-400">{error}</div>;

  // ═══════════════════════════════════════════════════════════════════════════
  // ─── Render ────────────────────────────────────────────────────────────────
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div className={`h-full bg-[#050505] text-white ${isMaximized ? 'fixed inset-0 z-50 overflow-hidden p-8 bg-[#0a0a0a]' : 'overflow-hidden flex'}`}>

      {/* ── Shared range-slider styles ── */}
      <style>{`
        .frammer-scrollbar::-webkit-scrollbar { width: 4px; }
        .frammer-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .frammer-scrollbar::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 9999px; }
        .frammer-scrollbar::-webkit-scrollbar-thumb:hover { background: #333333; }
        .frammer-scrollbar { scrollbar-width: thin; scrollbar-color: #333333 transparent; }
        .frammer-range { -webkit-appearance: none; appearance: none; pointer-events: none; background: transparent; }
        .frammer-range:focus { outline: none; }
        .frammer-range::-webkit-slider-runnable-track { height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; }
        .frammer-range::-moz-range-track { height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; }
        .frammer-range::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; pointer-events: auto; width: 18px; height: 18px; border-radius: 9999px; background: #fafafa; border: 2px solid #ef4444; box-shadow: 0 0 0 4px rgba(239,68,68,0.15); cursor: pointer; margin-top: -6px; }
        .frammer-range::-moz-range-thumb { pointer-events: auto; width: 18px; height: 18px; border-radius: 9999px; background: #fafafa; border: 2px solid #ef4444; box-shadow: 0 0 0 4px rgba(239,68,68,0.15); cursor: pointer; }
        .comparison-slider::-webkit-slider-thumb { background: #A855F7 !important; border: 2px solid #000 !important; box-shadow: 0 0 10px rgba(168,85,247,0.4) !important; }
        .comparison-slider::-webkit-slider-runnable-track { background: rgba(168,85,247,0.1) !important; }
        .comparison-slider::-moz-range-thumb { background: #fafafa !important; border: 2px solid #A855F7 !important; box-shadow: 0 0 0 4px rgba(168,85,247,0.15) !important; }
        .comparison-slider { pointer-events: auto !important; }
        .sens-slider::-webkit-slider-thumb { width: 14px; height: 14px; border-radius: 9999px; background: #fff; border: 2px solid #ef4444; cursor: pointer; margin-top: -5px; }
        .sens-slider::-webkit-slider-runnable-track { height: 4px; border-radius: 2px; }
      `}</style>

      {/* Sidebar + content sit side by side; sidebar is fixed, content scrolls */}

        {/* ══════════════════════════════════════════════════════════════════════
            FILTER SIDEBAR
           ══════════════════════════════════════════════════════════════════════ */}
        {!isMaximized && (
          <aside className={`shrink-0 border-r border-neutral-800/60 bg-[#0a0a0a] flex flex-col h-full overflow-hidden transition-all duration-300 ${isFiltersOpen ? 'w-[220px]' : 'w-[52px]'}`}>
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between border-b border-neutral-800/60 bg-[#0e0e0e] px-3 py-3 gap-2">
              {isFiltersOpen && (
                <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                  <SlidersHorizontal size={14} className={activeFilterCount > 0 ? 'text-red-400' : 'text-neutral-500'} />
                  <div className="min-w-0 overflow-hidden">
                    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-300 leading-none truncate">Filters</div>
                    <div className={`mt-0.5 text-[10px] font-semibold leading-none ${activeFilterCount > 0 ? 'text-red-400' : 'text-neutral-600'}`}>
                      {activeFilterCount > 0 ? `${activeFilterCount} applied` : 'None applied'}
                    </div>
                  </div>
                </div>
              )}
              <button type="button" onClick={() => setIsFiltersOpen(p => !p)}
                className="flex-shrink-0 inline-flex h-7 w-7 items-center justify-center rounded-full border border-neutral-800 bg-[#0f0f0f] text-neutral-400 transition-colors hover:border-neutral-700 hover:text-white"
                title={isFiltersOpen ? 'Collapse' : 'Expand filters'}>
                <ChevronDown size={13} className={`transition-transform duration-200 ${isFiltersOpen ? 'rotate-0' : '-rotate-90'}`} />
              </button>
            </div>

            {/* Collapsed badge */}
            {!isFiltersOpen && (
              <div className="flex flex-col items-center gap-3 pt-4 pb-3">
                <div className="relative">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full border transition-colors ${activeFilterCount > 0 ? 'border-red-500/30 bg-red-500/10' : 'border-neutral-800'}`}>
                    <SlidersHorizontal size={14} className={activeFilterCount > 0 ? 'text-red-400' : 'text-neutral-600'} />
                  </div>
                  {activeFilterCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-black text-white leading-none">{activeFilterCount}</span>
                  )}
                </div>
              </div>
            )}

            {/* Expanded filters */}
            {isFiltersOpen && (
              <>
                <div className="flex-1 overflow-y-auto frammer-scrollbar min-h-0">
                  <div className="space-y-3 p-3">
                    {authUser?.role !== 'client_admin' && authUser?.role !== 'user' && (
                      <div>
                        <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">Client</label>
                        <FloatingDropdown value={filters.company}
                          onChange={(v) => setFilters(p => ({ ...p, company: v, channel: ['All'], user: ['All'], language: ['All'], inputType: ['All'], outputType: ['All'] }))}
                          options={toOptionList(filterOptions.company)} minWidth="100%" multiSelect />
                      </div>
                    )}
                    <div>
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">Channel</label>
                      <FloatingDropdown value={filters.channel} onChange={(v) => setFilters(p => ({ ...p, channel: v }))} options={toOptionList(filterOptions.channel)} minWidth="100%" multiSelect />
                    </div>
                    {authUser?.role !== 'user' && (
                      <div>
                        <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">User</label>
                        <FloatingDropdown value={filters.user} onChange={(v) => setFilters(p => ({ ...p, user: v }))} options={toOptionList(filterOptions.user)} minWidth="100%" multiSelect />
                      </div>
                    )}
                    <div>
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">Language</label>
                      <FloatingDropdown value={filters.language} onChange={(v) => setFilters(p => ({ ...p, language: v }))} options={toOptionList(filterOptions.language)} minWidth="100%" multiSelect />
                    </div>
                    <div>
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">Input Type</label>
                      <FloatingDropdown value={filters.inputType} onChange={(v) => setFilters(p => ({ ...p, inputType: v }))} options={toOptionList(filterOptions.input_type)} minWidth="100%" multiSelect />
                    </div>
                    <div>
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">Output Type</label>
                      <FloatingDropdown value={filters.outputType} onChange={(v) => setFilters(p => ({ ...p, outputType: v }))} options={toOptionList(filterOptions.output_type)} minWidth="100%" multiSelect />
                    </div>

                    <DateRangeSlider dates={sliderDates} startIndex={dateStartIndex} endIndex={dateEndIndex} onChange={handleDateRangeChange} />

                    {/* Validation */}
                    <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] px-3 py-2 text-[10px]">
                      {filterOptionsLoading && <span className="text-neutral-600">Loading options...</span>}
                      {filterOptionsError && <span className="text-amber-400">Failed to load options.</span>}
                      {!filterOptionsLoading && workingFiltersQuery && hasDataForFilters === false && <span className="text-red-400">No data for this combination.</span>}
                      {!filterOptionsLoading && workingFiltersQuery && hasDataForFilters === true && <span className="text-emerald-400">Filters validated.</span>}
                      {!filterOptionsLoading && !workingFiltersQuery && <span className="text-neutral-600">Using full dataset.</span>}
                    </div>
                  </div>
                </div>

                {/* Apply / Reset */}
                <div className="flex-shrink-0 border-t border-neutral-800/60 p-3 space-y-2">
                  <button type="button" onClick={() => setAppliedFilters(filters)}
                    className="w-full rounded-xl bg-red-500 px-3 py-2.5 text-[11px] font-bold uppercase tracking-[0.15em] text-white transition-all hover:bg-red-400 shadow-lg shadow-red-500/20">
                    Apply Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
                  </button>
                  <button type="button"
                    onClick={() => {
                      const r = { company: authUser?.role === 'client_admin' ? [authUser.clientName] : ['All'], channel: ['All'], user: ['All'], language: ['All'], inputType: ['All'], outputType: ['All'], dateFrom: '', dateTo: '' };
                      setFilters(r); setAppliedFilters(r);
                    }}
                    className="w-full rounded-xl border border-neutral-800 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.15em] text-neutral-500 transition-all hover:border-red-500/30 hover:text-red-400">
                    Reset
                  </button>
                </div>
              </>
            )}
          </aside>
        )}

        {/* ══════════════════════════════════════════════════════════════════════
            MAIN CONTENT
           ══════════════════════════════════════════════════════════════════════ */}
        <div className={`overflow-y-auto frammer-scrollbar ${isMaximized ? 'h-full' : 'flex-1 min-w-0 h-full px-6 py-6 space-y-6'}`}>

          {!isMaximized && (
            <>
              {/* ── Header ── */}
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Analytics</div>
                  <h2 className="mt-1 text-2xl font-black tracking-tight">Engagement Metrics</h2>
                  <p className="mt-1 text-sm text-neutral-500">End-to-end content performance — upload to audience engagement.</p>
                </div>
                <div className="flex items-center gap-3">
                  <KpiToggle items={TOP_KPIS} active={visibleTopKpis} onToggle={toggleTopKpi} />
                  <GranularityPills value={granularity} onChange={setGranularity} />
                </div>
              </div>

              {/* ── KPI Cards (dynamically filtered) ── */}
              {(() => {
                const topCardData = {
                  // Engagement
                  views:          { title: 'VIEWS',                  value: formatNumber(totalViews),                                        subtitle: `${formatPct(summary.interaction_rate_pct||0)} engagement rate`,                    trendData: spkViews },
                  interactions:   { title: 'INTERACTIONS',           value: formatNumber(totalInteract),                                     subtitle: `${formatNumber(totalLikes)} likes · ${formatNumber(totalShares)} shares`,           trendData: spkInteract },
                  er:             { title: 'ENGAGEMENT RATE',        value: `${Number(summary.interaction_rate_pct||0).toFixed(2)}%`,         subtitle: '(likes + comments + shares) / views',                                             trendData: spkER },
                  virality:       { title: 'VIRALITY SCORE',         value: `${virality.toFixed(2)}%`,                                       subtitle: `${formatNumber(totalShares)} shares total`,                                       trendData: spkViral },
                  likes:          { title: 'LIKES',                  value: formatNumber(totalLikes),                                        subtitle: `${formatPct(origLikeRate)} like rate`,                                            trendData: spkLikes },
                  comments:       { title: 'COMMENTS',               value: formatNumber(totalComments),                                     subtitle: `${formatPct(origCommentRate)} comment rate`,                                      trendData: spkComments },
                  shares:         { title: 'SHARES',                 value: formatNumber(totalShares),                                       subtitle: `${formatPct(origShareRate)} share rate`,                                          trendData: spkShares },
                  likeRate:       { title: 'LIKE RATE',              value: `${origLikeRate.toFixed(2)}%`,                                    subtitle: 'likes / views',                                                                   trendData: spkLikeRate },
                  commentRate:    { title: 'COMMENT RATE',           value: `${origCommentRate.toFixed(2)}%`,                                 subtitle: 'comments / views',                                                                trendData: spkCommentRate },
                  shareRate:      { title: 'SHARE RATE',             value: `${origShareRate.toFixed(2)}%`,                                   subtitle: 'shares / views',                                                                  trendData: spkShareRate },
                  likeToComment:  { title: 'LIKE-TO-COMMENT',        value: origLikeToComment.toFixed(1),                                     subtitle: 'likes per comment',                                                               trendData: spkLikes },
                  // Pipeline
                  uploaded:       { title: 'UPLOADED',               value: formatNumber(summary.uploaded_videos||0),                         subtitle: 'raw videos',                                                                      trendData: spkUploaded },
                  published:      { title: 'PUBLISHED',              value: formatNumber(summary.published_posts||0),                         subtitle: `${formatPct(summary.publish_from_upload_pct||0)} of uploads`,                      trendData: spkPublish },
                  distributions:  { title: 'DISTRIBUTIONS',          value: formatNumber(summary.distributions||0),                           subtitle: `${formatPct(summary.distribution_from_publish_pct||0)} from published`,            trendData: spkDist },
                  avgvdist:       { title: 'AVG VIEWS / DIST',       value: formatNumber(Math.round(avgViewsDist)),                           subtitle: 'reach per distribution',                                                          trendData: spkAvgV },
                  publishRate:    { title: 'PUBLISH RATE',           value: `${origPubRate.toFixed(1)}%`,                                     subtitle: 'published / uploaded',                                                            trendData: spkPubRate },
                  distRate:       { title: 'DISTRIBUTION RATE',      value: `${Number(summary.distribution_from_publish_pct||0).toFixed(1)}%`, subtitle: 'distributed / published',                                                         trendData: spkDist },
                  contentYield:   { title: 'CONTENT YIELD',          value: origContentYield.toFixed(2),                                      subtitle: 'distributions per upload',                                                        trendData: spkDist },
                  // Reach & Efficiency
                  interactPerView: { title: 'INTERACTIONS / VIEW',   value: origCPV.toFixed(2),                                               subtitle: 'engagement density',                                                              trendData: spkIPV },
                  interactPerDist: { title: 'INTERACTIONS / DIST',   value: formatNumber(Math.round(origDistEfficiency)),                     subtitle: 'engagement per placement',                                                        trendData: spkIPD },
                  amplification:  { title: 'AMPLIFICATION',          value: formatNumber(Math.round(origAmplification)),                      subtitle: 'shares × avg views/dist',                                                         trendData: spkShares },
                };
                const visible = TOP_KPIS.filter(k => visibleTopKpis.includes(k.id));
                const cols = Math.min(visible.length, 4);
                return visible.length > 0 && (
                  <section className={`grid gap-4`} style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
                    {visible.map(k => {
                      const d = topCardData[k.id];
                      return d ? <StatCard key={k.id} {...d} /> : null;
                    })}
                  </section>
                );
              })()}

              {/* ── Pipeline Conversion / Sensitivity (tabbed) ── */}
              <section className="rounded-[28px] border border-neutral-800 bg-[#111111]">
                {/* Sub-tabs */}
                <div className="flex items-center justify-between border-b border-neutral-800 px-6 pt-4 pb-0">
                  <div className="flex gap-1">
                    <button onClick={() => setPipelineTab('conversion')}
                      className={`px-5 py-2.5 text-sm font-semibold tracking-wide transition-colors ${pipelineTab === 'conversion' ? 'text-white border-b-2 border-red-500' : 'text-neutral-500 hover:text-neutral-300'}`}>
                      Pipeline Conversion
                    </button>
                    <button onClick={() => setPipelineTab('sensitivity')}
                      className={`px-5 py-2.5 text-sm font-semibold tracking-wide transition-colors flex items-center gap-2 ${pipelineTab === 'sensitivity' ? 'text-white border-b-2 border-red-500' : 'text-neutral-500 hover:text-neutral-300'}`}>
                      <Zap size={14} /> Sensitivity Analysis
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    {pipelineTab === 'sensitivity' && (
                      <KpiToggle items={SENS_KPIS} active={visibleSensKpis} onToggle={toggleSensKpi} />
                    )}
                    {pipelineTab === 'sensitivity' && sensHasChanges && (
                      <button onClick={() => setSens({ views: 0, likes: 0, comments: 0, shares: 0, uploaded: 0, published: 0, distributions: 0 })}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-neutral-700 text-xs font-bold text-neutral-400 hover:text-white hover:border-neutral-500 transition-colors">
                        <RotateCcw size={12} /> Reset All
                      </button>
                    )}
                  </div>
                </div>

                <div className="p-6">
                  {/* ── Tab 1: Pipeline Conversion ── */}
                  {pipelineTab === 'conversion' && (
                    <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-8">
                      <div className="flex flex-wrap justify-around gap-6 items-start">
                        <MetricGauge label="Publish Rate"      value={Number(summary.publish_from_upload_pct||0)}       max={100} note="% of uploads published" />
                        <MetricGauge label="Distribution Rate" value={Number(summary.distribution_from_publish_pct||0)} max={100} note="% posts distributed" />
                        <MetricGauge label="Engagement Rate"   value={Number(summary.interaction_rate_pct||0)}          max={100} note="% interactions per view" />
                      </div>
                      <div className="flex flex-col justify-center divide-y divide-neutral-800/60">
                        {[
                          { label: 'Top Platform by Views',  main: topByViews?.platform || '—',    sub: topByViews ? formatNumber(topByViews.views) + ' views' : '' },
                          { label: 'Best Engagement Rate',   main: topByER?.platform || '—',       sub: topByER ? formatPct(topByER.engagement_rate_pct) + ' ER' : '' },
                          { label: 'Top Output Type',        main: topOutput?.output_type || '—',  sub: topOutput ? formatNumber(topOutput.views_per_post) + ' views/post' : '' },
                          { label: 'Virality',               main: `${virality.toFixed(2)}% share rate`, sub: formatNumber(totalShares) + ' shares' },
                        ].map(({ label, main, sub }) => (
                          <div key={label} className="flex items-center justify-between py-3">
                            <div>
                              <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-neutral-600">{label}</div>
                              <div className="mt-0.5 font-semibold text-white">{main}</div>
                            </div>
                            <div className="text-sm text-neutral-500 text-right">{sub}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* ── Tab 2: Sensitivity Analysis ── */}
                  {pipelineTab === 'sensitivity' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                      {/* Sliders */}
                      <div className="space-y-5">
                        <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-600 mb-3">Adjust Inputs</div>
                        <SensSlider label="Views" value={sens.views} onChange={(v) => updateSens('views', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-red-500" />} />
                        <SensSlider label="Likes" value={sens.likes} onChange={(v) => updateSens('likes', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-red-400" />} />
                        <SensSlider label="Comments" value={sens.comments} onChange={(v) => updateSens('comments', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-neutral-400" />} />
                        <SensSlider label="Shares" value={sens.shares} onChange={(v) => updateSens('shares', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-neutral-500" />} />
                        <div className="border-t border-neutral-800/40 pt-4" />
                        <SensSlider label="Uploaded Videos" value={sens.uploaded} onChange={(v) => updateSens('uploaded', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-blue-400" />} />
                        <SensSlider label="Published Posts" value={sens.published} onChange={(v) => updateSens('published', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />} />
                        <SensSlider label="Distributions" value={sens.distributions} onChange={(v) => updateSens('distributions', v)}
                          icon={<div className="w-2.5 h-2.5 rounded-full bg-amber-400" />} />
                      </div>

                      {/* Cascading effects — dynamic grouped KPIs */}
                      <div className="space-y-4">
                        {Object.entries(visibleSensGrouped).map(([group, kpis]) => (
                          <div key={group}>
                            <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-600 mb-2">{SENS_GROUPS[group]}</div>
                            <div className="rounded-xl border border-neutral-800 bg-[#0d0d0d] p-4">
                              {kpis.map(k => {
                                const v = sensKpiMap[k.id];
                                return v ? <EffectRow key={k.id} label={k.label} oldVal={v.oldVal} newVal={v.newVal} format={v.format} /> : null;
                              })}
                            </div>
                          </div>
                        ))}

                        {/* Simulated Totals — always shown */}
                        <div>
                          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-600 mb-2">Simulated Totals</div>
                          <div className="rounded-xl border border-neutral-800 bg-[#0d0d0d] p-4">
                            <div className="grid grid-cols-2 gap-4">
                              {[
                                ['Views', simViews], ['Likes', simLikes],
                                ['Comments', simComments], ['Shares', simShares],
                              ].map(([label, val]) => (
                                <div key={label} className="text-center py-1">
                                  <div className="text-xl font-black text-white">{formatNumber(Math.round(val))}</div>
                                  <div className="text-xs text-neutral-500 uppercase">{label}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              CHART SECTION with anomaly panel
             ═══════════════════════════════════════════════════════════════════ */}
          <section className={isMaximized ? 'h-full flex flex-col' : 'grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-6'}>

            {/* Chart card */}
            <div className={`rounded-[28px] border border-neutral-800 bg-[#111111] flex flex-col overflow-hidden ${isMaximized ? 'flex-1 h-full' : ''}`}>
              {/* Tab bar + toolbar */}
              <div className="flex items-center justify-between border-b border-neutral-800 px-5 py-2">
                <div className="flex gap-1">
                  {TABS.map(tab => (
                    <button key={tab.id} onClick={() => setActiveChart(tab.id)}
                      className={`px-4 py-2 text-sm font-medium tracking-wide transition-colors ${
                        activeChart === tab.id
                          ? 'text-white border-b-2 border-[#ef4444]'
                          : 'text-neutral-500 hover:text-neutral-300'
                      }`}
                    >{tab.label}</button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  {/* Comparison toggle */}
                  <button onClick={() => setShowComparison(!showComparison)}
                    className={`p-1.5 rounded-lg transition-all ${showComparison
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]'
                      : 'text-neutral-500 hover:text-neutral-300 border border-transparent'}`}
                    title="Compare with Past Period">
                    <History size={16} />
                  </button>
                  {showComparison && (
                    <div className="flex items-center gap-2">
                      <input type="range" min="1" max="12" value={comparisonOffset}
                        onChange={(e) => setComparisonOffset(parseInt(e.target.value))}
                        className="w-20 accent-purple-500 comparison-slider frammer-range cursor-pointer" />
                      <span className="text-[10px] font-black text-purple-400/80 tabular-nums w-8">{comparisonOffset}P</span>
                    </div>
                  )}
                  <div className="h-4 w-px bg-neutral-800" />
                  <button onClick={() => setShowPoints(!showPoints)} className={`text-neutral-500 hover:text-white transition-colors ${showPoints ? 'text-white' : ''}`} title="Toggle Points">
                    <CircleDot size={16} />
                  </button>
                  <button onClick={handleExportCsv} className="text-neutral-500 hover:text-white transition-colors" title="Export CSV">
                    <Download size={16} />
                  </button>
                  <button onClick={handleExportImage} className="text-neutral-500 hover:text-white transition-colors" title="Export PNG">
                    <ImageIcon size={16} />
                  </button>
                  <div className="h-4 w-px bg-neutral-800" />
                  <button onClick={() => setIsMaximized(!isMaximized)} className="text-neutral-500 hover:text-white transition-colors" title={isMaximized ? 'Minimize' : 'Maximize'}>
                    {isMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                  </button>
                </div>
              </div>
              <div className={`flex-1 min-h-0 p-5 ${isMaximized ? '' : 'h-[300px]'}`}>
                {chartEl}
              </div>
            </div>

            {/* Anomaly panel */}
            {!isMaximized && (
              <div className="rounded-[28px] border border-neutral-800 bg-[#111111] flex flex-col overflow-hidden h-[380px]">
                <div className="flex-shrink-0 flex items-center gap-2 border-b border-neutral-800/60 bg-[#0e0e0e] px-5 py-3">
                  <AlertTriangle size={14} className="text-amber-500" />
                  <h3 className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-300">Anomalies</h3>
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto frammer-scrollbar p-4 space-y-3">
                  {anomalies.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-neutral-800 rounded-xl">
                      <AlertTriangle size={24} className="text-emerald-500/20 mb-2" />
                      <div className="text-sm font-semibold text-neutral-300 mb-1">System Normal</div>
                      <div className="text-xs text-neutral-500">No anomalies detected.</div>
                    </div>
                  ) : anomalies.map((a) => (
                    <div key={`${a.period}-${a.direction}`}
                      className="group relative overflow-hidden rounded-xl border border-neutral-800 bg-[#0d0d0d] p-4 transition-all hover:border-neutral-600">
                      <div className={`absolute top-0 left-0 w-1 h-full ${a.direction === 'drop' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="text-sm font-bold text-white capitalize">{a.direction === 'drop' ? 'Significant Drop' : 'Abnormal Spike'}</div>
                          <div className="mt-0.5 text-xs text-neutral-400">{a.period}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-base font-black text-white">{formatNumber(a.value)}</div>
                          <div className="text-[10px] uppercase font-bold text-neutral-500">Z {Number(a.zScore).toFixed(1)}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {!isMaximized && (
            <>
              {/* ── Platform + Interaction Breakdown ── */}
              <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Platform Performance</div>
                    {selectedPlatform && (
                      <button onClick={() => setSelectedPlatform(null)} className="flex items-center gap-1 text-xs text-neutral-500 hover:text-white transition-colors">
                        <X size={12} /> Clear
                      </button>
                    )}
                  </div>
                  {platformStats && (
                    <div className="mb-4 rounded-xl border border-neutral-800 bg-[#0d0d0d] px-4 py-3">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-600 mb-2">{selectedPlatform}</div>
                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div><div className="text-lg font-black text-white">{formatNumber(platformStats.views)}</div><div className="text-[10px] text-neutral-600 uppercase tracking-wider">Views</div></div>
                        <div><div className="text-lg font-black text-[#ef4444]">{platformStats.er}%</div><div className="text-[10px] text-neutral-600 uppercase tracking-wider">ER</div></div>
                        <div><div className="text-lg font-black text-white">{formatNumber(platformStats.shares)}</div><div className="text-[10px] text-neutral-600 uppercase tracking-wider">Shares</div></div>
                      </div>
                    </div>
                  )}
                  <div className="flex-1 min-h-0" style={{ height: platformStats ? 260 : 320 }}>
                    <Doughnut data={platformDoughnutData} options={platformDoughnutOpts} />
                  </div>
                </div>

                <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5 flex flex-col">
                  <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Interaction Breakdown</div>
                  {totalInteract > 0 ? (
                    <>
                      <div className="flex-1 min-h-0" style={{ minHeight: 200 }}><Doughnut data={doughnutData} options={doughOpts} /></div>
                      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-neutral-800 pt-4">
                        {[['Likes', totalLikes, '#ef4444'], ['Comments', totalComments, '#737373'], ['Shares', totalShares, '#525252']].map(([l, v, c]) => (
                          <div key={l} className="text-center">
                            <div className="text-xs font-bold uppercase tracking-wider" style={{ color: c }}>{l}</div>
                            <div className="text-xl font-black text-white mt-1">{formatNumber(v)}</div>
                            <div className="text-[11px] text-neutral-600">{formatPct((v/totalInteract)*100)}</div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="flex flex-1 items-center justify-center text-sm text-neutral-700">No interaction data</div>
                  )}
                </div>
              </section>

              {/* ── Output Type Cards ── */}
              <section className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
                <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Output Type Performance</div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                  {outputBD.map(row => (
                    <div key={row.output_type}
                      className="group relative rounded-xl border border-neutral-800 bg-[#0d0d0d] p-4 overflow-hidden cursor-default hover:border-neutral-600 transition-colors">
                      <div className="transition-opacity duration-200 group-hover:opacity-0">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-500">{row.output_type}</div>
                        <div className="mt-3 text-2xl font-black text-white">{formatNumber(row.views_per_post)}</div>
                        <div className="mt-1 text-[11px] text-neutral-600">views per post</div>
                      </div>
                      <div className="absolute inset-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-between">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-[#ef4444]">{row.output_type}</div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs"><span className="text-neutral-500">Views</span><span className="font-bold text-white">{formatNumber(row.views)}</span></div>
                          <div className="flex justify-between text-xs"><span className="text-neutral-500">Posts</span><span className="font-bold text-white">{formatNumber(row.posts_distributed)}</span></div>
                          <div className="flex justify-between text-xs"><span className="text-neutral-500">Interactions</span><span className="font-bold text-white">{formatNumber(row.interactions)}</span></div>
                          <div className="flex justify-between text-xs border-t border-neutral-800 pt-2"><span className="text-neutral-500">Views/Post</span><span className="font-black text-[#ef4444]">{formatNumber(row.views_per_post)}</span></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* ── Language + Input Type Breakdown ── */}
              <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
                  <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Views by Language</div>
                  <div className="space-y-4">
                    {langBD.map(([lang, views]) => (
                      <div key={lang}>
                        <div className="flex justify-between text-sm mb-1.5">
                          <span className="font-medium text-neutral-300">{lang}</span>
                          <span className="text-neutral-500 tabular-nums text-xs">{formatNumber(views)}</span>
                        </div>
                        <div className="h-1.5 bg-neutral-900 rounded-full overflow-hidden">
                          <div className="h-full bg-[#ef4444] rounded-full" style={{ width: `${Math.max((views / maxLang) * 100, 2)}%`, opacity: 0.6 }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[28px] border border-neutral-800 bg-[#111111] p-5">
                  <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mb-4">Views by Input Type</div>
                  <div className="space-y-4">
                    {inputBD.map(([type, views]) => (
                      <div key={type}>
                        <div className="flex justify-between text-sm mb-1.5">
                          <span className="font-medium text-neutral-300">{type}</span>
                          <span className="text-neutral-500 tabular-nums text-xs">{formatNumber(views)}</span>
                        </div>
                        <div className="h-1.5 bg-neutral-900 rounded-full overflow-hidden">
                          <div className="h-full bg-[#ef4444] rounded-full" style={{ width: `${Math.max((views / maxInput) * 100, 2)}%`, opacity: 0.6 }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              {/* Old standalone sensitivity section removed — merged into pipeline tab above */}
            </>
          )}
        </div>
    </div>
  );
}
