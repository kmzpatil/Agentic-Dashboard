import React, { useState, useMemo } from 'react';
import {
  ShieldCheck, AlertTriangle, Copy, Unlink, MinusCircle, CalendarX,
  HelpCircle, UserX, RouteOff, Search, ChevronDown, ChevronRight,
  LayoutDashboard
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';

// ── Color maps ──
const CHECK_COLOR_MAP = {
  NULL_VIOLATION: { color: 'text-red-500', bg: 'bg-red-500/10', hex: '#ef4444', icon: AlertTriangle, label: 'NULL Violation' },
  DUPLICATE_PK: { color: 'text-orange-500', bg: 'bg-orange-500/10', hex: '#f97316', icon: Copy, label: 'Duplicate PK' },
  FK_VIOLATION: { color: 'text-amber-500', bg: 'bg-amber-500/10', hex: '#f59e0b', icon: Unlink, label: 'FK Violation' },
  NEGATIVE_VALUE: { color: 'text-violet-500', bg: 'bg-violet-500/10', hex: '#8b5cf6', icon: MinusCircle, label: 'Negative Value' },
  INVALID_DATE: { color: 'text-blue-500', bg: 'bg-blue-500/10', hex: '#3b82f6', icon: CalendarX, label: 'Invalid Date' },
  UNKNOWN_VALUE: { color: 'text-neutral-400', bg: 'bg-neutral-500/10', hex: '#9ca3af', icon: HelpCircle, label: 'Unknown Value' },
};

const TABLE_COLOR_MAP = {
  raw_videos: '#3b82f6',
  created_assets: '#10b981',
  published_posts: '#8b5cf6',
  post_distribution: '#f59e0b',
  users: '#ec4899',
  channels: '#06b6d4',
  raw_video_channel: '#f97316',
  clients: '#a3a3a3',
};

// ── Shared tiny components ──
const Panel = ({ children, className = '' }) => (
  <div className={`rounded-2xl border border-neutral-800 bg-[#111111] p-5 ${className}`}>{children}</div>
);

const Badge = ({ children, className = '' }) => (
  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}>{children}</span>
);

const Sparkline = ({ data, color }) => {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((d, i) => `${(i / (data.length - 1)) * 100},${100 - ((d - min) / range) * 100}`).join(' ');
  return (
    <svg viewBox="0 -10 100 120" className="h-8 w-20">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// ── Health ring (SVG) ──
function HealthRing({ score, tableScores }) {
  const r = 90, cx = 120, cy = 120;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const ringColor = score > 85 ? '#10b981' : score > 60 ? '#f59e0b' : '#ef4444';

  const tables = Object.entries(tableScores || {});
  const segAngle = tables.length ? 360 / tables.length : 0;

  let cur = 0;
  const innerR = 65;
  const segs = tables.map(([tbl, info]) => {
    const rad1 = ((cur - 90) * Math.PI) / 180;
    const rad2 = ((cur + segAngle - 92) * Math.PI) / 180;
    const x1 = cx + innerR * Math.cos(rad1), y1 = cy + innerR * Math.sin(rad1);
    const x2 = cx + innerR * Math.cos(rad2), y2 = cy + innerR * Math.sin(rad2);
    const lg = segAngle > 180 ? 1 : 0;
    cur += segAngle;
    const tScore = info.score ?? 100;
    const op = tScore > 85 ? 1 : tScore > 60 ? 0.5 : 0.2;
    return <path key={tbl} d={`M ${x1} ${y1} A ${innerR} ${innerR} 0 ${lg} 1 ${x2} ${y2}`} fill="none" stroke={TABLE_COLOR_MAP[tbl] || '#555'} strokeWidth="12" strokeOpacity={op} strokeLinecap="round" />;
  });

  return (
    <div className="flex flex-col items-center">
      <svg width="220" height="220" viewBox="0 0 240 240">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#262626" strokeWidth="16" />
        <circle cx={cx} cy={cy} r={innerR} fill="none" stroke="#262626" strokeWidth="12" />
        {segs}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={ringColor} strokeWidth="16" strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`} />
        <text x={cx} y={cx - 4} textAnchor="middle" dominantBaseline="middle" className="fill-white text-4xl font-black">{score.toFixed(1)}%</text>
        <text x={cx} y={cx + 22} textAnchor="middle" dominantBaseline="middle" className="fill-neutral-500 text-[11px] font-bold uppercase tracking-[0.2em]">Health</text>
      </svg>
      <div className="mt-3 flex flex-wrap justify-center gap-3">
        {tables.map(([tbl]) => (
          <div key={tbl} className="flex items-center gap-1.5 text-[11px] text-neutral-400">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: TABLE_COLOR_MAP[tbl] || '#555' }} />
            {tbl}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Orphan flow diagram ──
function OrphanFlowDiagram({ links }) {
  const nodes = [
    { id: 'clients', x: 20, y: 50 },
    { id: 'users', x: 20, y: 150 },
    { id: 'channels', x: 20, y: 250 },
    { id: 'raw_videos', x: 180, y: 100 },
    { id: 'raw_video_channel', x: 180, y: 250 },
    { id: 'created_assets', x: 340, y: 100 },
    { id: 'published_posts', x: 500, y: 100 },
    { id: 'post_distribution', x: 500, y: 200 },
  ];

  const linkData = (links || []).map(l => {
    const color = l.orphans === 0 ? '#10b981' : l.orphans <= 10 ? '#f59e0b' : '#ef4444';
    return { ...l, color };
  });

  return (
    <div className="relative h-64 w-full overflow-hidden rounded-xl border border-neutral-800 bg-[#0A0A0A]">
      <svg width="100%" height="100%" viewBox="0 0 620 300" preserveAspectRatio="xMidYMid meet">
        {linkData.map((link, i) => {
          const from = nodes.find(n => n.id === link.from);
          const to = nodes.find(n => n.id === link.to);
          if (!from || !to) return null;
          const sw = Math.max(2, Math.min(12, link.orphans / 5));
          const path = `M ${from.x + 85} ${from.y + 15} C ${from.x + 135} ${from.y + 15}, ${to.x - 50} ${to.y + 15}, ${to.x} ${to.y + 15}`;
          const mx = (from.x + to.x + 85) / 2, my = (from.y + to.y + 30) / 2;
          return (
            <g key={i}>
              <path d={path} fill="none" stroke={link.color} strokeWidth={sw} opacity="0.45" />
              {link.orphans > 0 && <circle cx={mx} cy={my} r="12" fill="#111" stroke={link.color} strokeWidth="2" />}
              {link.orphans > 0 && <text x={mx} y={my} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize="10" fontWeight="bold">{link.orphans}</text>}
            </g>
          );
        })}
        {nodes.map(n => (
          <g key={n.id} transform={`translate(${n.x},${n.y})`}>
            <rect width="105" height="30" rx="6" fill="#0A0A0A" stroke={TABLE_COLOR_MAP[n.id] || '#444'} strokeWidth="1.5" />
            <text x="52" y="15" textAnchor="middle" dominantBaseline="middle" fill="#d4d4d4" fontSize="11" fontWeight="500">{n.id.replace(/_/g, ' ')}</text>
          </g>
        ))}
      </svg>
      <div className="absolute right-2 top-2 flex flex-col gap-1 rounded-lg bg-[#111]/80 p-2 text-[10px] text-neutral-500 backdrop-blur">
        <div className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> 0 Orphans</div>
        <div className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-amber-500" /> 1-10</div>
        <div className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-red-500" /> &gt;10</div>
      </div>
    </div>
  );
}

// ── Contamination heatmap ──
function ContaminationHeatmap({ rows }) {
  const cols = ['Input_Type', 'Language', 'Team_Name', 'Channel_Name', 'Published_Platform'];
  const cellColor = (val) => {
    if (val === null || val === undefined) return 'bg-neutral-900/30 text-neutral-700';
    if (val === 0) return 'bg-emerald-900/20 text-emerald-500';
    if (val < 10) return 'bg-amber-900/30 text-amber-400';
    return 'bg-red-900/40 text-red-400 font-bold';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="p-2 text-left text-xs font-medium text-neutral-500">Table</th>
            {cols.map(c => <th key={c} className="p-2 text-center text-xs font-medium text-neutral-500">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {(rows || []).map(row => (
            <tr key={row.table} className="border-t border-neutral-900">
              <td className="p-2 text-neutral-300 flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: TABLE_COLOR_MAP[row.table] || '#555' }} />
                {row.table}
              </td>
              {cols.map(c => (
                <td key={c} className="p-1">
                  <div className={`flex h-9 items-center justify-center rounded-md ${cellColor(row[c])}`}>
                    {row[c] != null ? `${row[c]}%` : '-'}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Issue row (expandable) ──
function IssueRow({ issue }) {
  const [open, setOpen] = useState(false);
  const conf = CHECK_COLOR_MAP[issue.check] || CHECK_COLOR_MAP.UNKNOWN_VALUE;
  const Icon = conf.icon;
  const sevColor = issue.severity === 'Critical' ? 'bg-red-500' : issue.severity === 'Warning' ? 'bg-amber-500' : 'bg-blue-500';

  return (
    <>
      <tr className={`cursor-pointer border-b border-neutral-900 transition-colors hover:bg-neutral-900/50 ${open ? 'bg-neutral-900/60' : ''}`} onClick={() => setOpen(!open)}>
        <td className="p-3"><ChevronRight className={`h-4 w-4 text-neutral-600 transition-transform ${open ? 'rotate-90' : ''}`} /></td>
        <td className="p-3"><Badge className={`${conf.color} ${conf.bg}`}>{issue.table}</Badge></td>
        <td className="p-3"><div className="flex items-center gap-2"><Icon className={`h-4 w-4 ${conf.color}`} /><span className={`text-sm font-medium ${conf.color}`}>{conf.label}</span></div></td>
        <td className="p-3 font-mono text-sm text-neutral-400">{issue.column}</td>
        <td className="p-3 text-sm text-neutral-300">{issue.count ?? '-'}</td>
        <td className="p-3"><div className="flex items-center gap-1.5"><span className={`inline-block h-2 w-2 rounded-full ${sevColor}`} /><span className="text-xs text-neutral-500">{issue.severity}</span></div></td>
      </tr>
      {open && (
        <tr className="border-b border-neutral-900 bg-[#0A0A0A]">
          <td colSpan="6" className="p-4">
            <div className="rounded-xl border border-neutral-800 bg-[#0d0d0d] p-4 font-mono text-xs text-neutral-400">{issue.message}</div>
          </td>
        </tr>
      )}
    </>
  );
}


// ═══════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════
export default function DataQualityModule() {
  const [subTab, setSubTab] = useState('overview');

  // API calls
  const overview = useApi(`${API_BASE}/quality`, []);
  const issuesApi = useApi(`${API_BASE}/quality/issues?limit=200`, []);

  // Issue explorer filters
  const [filterTable, setFilterTable] = useState('');
  const [filterCheck, setFilterCheck] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const data = overview.data || {};
  const loading = overview.loading;
  const error = overview.error;

  // Filtered issues
  const filteredIssues = useMemo(() => {
    let items = issuesApi.data?.issues || [];
    if (filterTable) items = items.filter(i => i.table === filterTable);
    if (filterCheck) items = items.filter(i => i.check === filterCheck);
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      items = items.filter(i =>
        (i.table || '').toLowerCase().includes(q) ||
        (i.column || '').toLowerCase().includes(q) ||
        (i.message || '').toLowerCase().includes(q)
      );
    }
    return items;
  }, [issuesApi.data, filterTable, filterCheck, searchTerm]);

  // Group dead ends by category
  const deadEndGroups = useMemo(() => {
    const groups = {};
    (data.dead_ends || []).forEach(d => {
      if (!groups[d.category]) groups[d.category] = [];
      groups[d.category].push(d);
    });
    return groups;
  }, [data.dead_ends]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-neutral-500">
        <div className="flex flex-col items-center gap-3">
          <ShieldCheck className="h-8 w-8 animate-pulse text-neutral-600" />
          <span className="text-sm">Running quality checks...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-400">{error}</div>;
  }

  const checks = data.check_counts || {};
  const totalOrphans = (data.orphan_links || []).reduce((s, l) => s + l.orphans, 0);
  const totalDeadEnds = (data.dead_ends || []).length;

  // Contamination rate
  const contamRows = data.heatmap || [];
  const contamVals = contamRows.flatMap(r => ['Input_Type', 'Language', 'Team_Name', 'Channel_Name', 'Published_Platform'].map(c => r[c]).filter(v => v != null));
  const avgContam = contamVals.length ? (contamVals.reduce((a, b) => a + b, 0) / contamVals.length).toFixed(1) : '0.0';

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Sub-tab header */}
      <div className="flex items-center justify-between border-b border-neutral-900 bg-[#090909] px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-blue-500/30 bg-blue-600/10">
            <ShieldCheck className="h-4 w-4 text-blue-500" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Data Quality & Governance</h2>
            <p className="text-[11px] text-neutral-500">Monitor integrity, debug pipelines, and ensure clean analytics.</p>
          </div>
        </div>
        <div className="flex gap-1 rounded-full border border-neutral-800 bg-[#111111] p-1">
          {[
            { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={14} /> },
            { id: 'issues', label: 'Issue Explorer', icon: <Search size={14} /> },
          ].map(t => (
            <button key={t.id} onClick={() => setSubTab(t.id)} className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors ${subTab === t.id ? 'bg-[#171717] text-white' : 'text-neutral-500 hover:text-neutral-200'}`}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* ═══════════ OVERVIEW SUB-TAB ═══════════ */}
        {subTab === 'overview' && (
          <div className="space-y-6">
            {/* Row 1: Hero banner */}
            <div className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-gradient-to-r from-[#111111] to-[#171717] p-8">
              <div className="flex items-center gap-6">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_30px_rgba(16,185,129,0.15)]">
                  <ShieldCheck className="h-7 w-7 text-emerald-400" />
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-black text-white">Data Quality & Integrity Monitor</h2>
                    <Badge className="border border-blue-500/30 bg-blue-500/10 text-blue-400">{Object.keys(checks).length} CHECK CATEGORIES</Badge>
                  </div>
                  <p className="mt-1 text-sm text-neutral-500">Real-time surveillance across {Object.keys(data.table_scores || {}).length} core tables. Identifying contamination, orphan chains, and dead-end dimensional flows.</p>
                </div>
              </div>
            </div>

            {/* Row 2: Health ring + KPI cards */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[300px_1fr]">
              <Panel className="flex items-center justify-center">
                <HealthRing score={data.overall_score ?? 0} tableScores={data.table_scores || {}} />
              </Panel>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <Panel>
                  <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500">Total Issues</div>
                  <div className="mt-2 text-3xl font-black text-red-400">{(data.total_issues ?? 0).toLocaleString()}</div>
                </Panel>
                <Panel>
                  <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500">Orphan Records</div>
                  <div className="mt-2 text-3xl font-black text-amber-400">{totalOrphans.toLocaleString()}</div>
                </Panel>
                <Panel>
                  <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500">Contamination</div>
                  <div className="mt-2 text-3xl font-black text-violet-400">{avgContam}%</div>
                </Panel>
                <Panel>
                  <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500">Dead Ends</div>
                  <div className="mt-2 text-3xl font-black text-neutral-400">{totalDeadEnds}</div>
                </Panel>
              </div>
            </div>

            {/* Row 3: Heatmap + Orphan flow */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_1fr]">
              <Panel>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-base font-bold text-white"><HelpCircle className="h-4 w-4 text-violet-500" /> Value Contamination Matrix</h3>
                  <span className="text-[11px] text-neutral-500">% of "Unknown" or NULL values</span>
                </div>
                <ContaminationHeatmap rows={data.heatmap} />
              </Panel>
              <Panel>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-base font-bold text-white"><Unlink className="h-4 w-4 text-amber-500" /> Broken Reference Chains</h3>
                  <span className="text-[11px] text-neutral-500">Foreign Key Violations</span>
                </div>
                <OrphanFlowDiagram links={data.orphan_links} />
              </Panel>
            </div>

            {/* Row 4: Check breakdown + Dead Ends + Suspicious Users */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.9fr_0.9fr]">
              {/* Check breakdown */}
              <Panel>
                <h3 className="mb-4 text-base font-bold text-white">Issues by Check Type</h3>
                <div className="space-y-2">
                  {Object.entries(CHECK_COLOR_MAP).map(([key, conf]) => {
                    const cnt = checks[key] || 0;
                    const Icon = conf.icon;
                    const pct = data.total_issues ? ((cnt / data.total_issues) * 100).toFixed(1) : 0;
                    return (
                      <div key={key} className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-[#0A0A0A] p-3">
                        <div className={`rounded-lg p-2 ${conf.bg}`}><Icon className={`h-4 w-4 ${conf.color}`} /></div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-neutral-300">{conf.label}</span>
                            <span className="font-mono text-sm font-bold text-white">{cnt}</span>
                          </div>
                          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-neutral-800">
                            <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: conf.hex }} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Panel>

              {/* Dead Ends */}
              <Panel className="border-amber-900/30 bg-amber-950/10">
                <h3 className="mb-3 flex items-center gap-2 text-base font-bold text-white"><RouteOff className="h-4 w-4 text-amber-500" /> Dead End Paths</h3>
                <div className="max-h-[280px] space-y-3 overflow-y-auto pr-1">
                  {Object.entries(deadEndGroups).map(([cat, items]) => (
                    <div key={cat}>
                      <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-neutral-600">{cat} ({items.length})</div>
                      <div className="space-y-1">
                        {items.map((item, idx) => (
                          <div key={idx} className="flex items-center justify-between rounded-lg border border-neutral-800/50 bg-[#0d0d0d] p-2 text-sm">
                            <span className="font-medium text-neutral-300">{item.name}</span>
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-neutral-500">{item.uploads} uploads</span>
                              <span className="rounded bg-red-500/10 px-1.5 py-0.5 font-bold text-red-400">0 published</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {Object.keys(deadEndGroups).length === 0 && <p className="text-sm text-neutral-600">No dead ends found.</p>}
                </div>
              </Panel>

              {/* Suspicious Users */}
              <Panel className="border-red-900/30 bg-red-950/10">
                <h3 className="mb-3 flex items-center gap-2 text-base font-bold text-white"><UserX className="h-4 w-4 text-pink-500" /> Suspicious Accounts</h3>
                <div className="max-h-[280px] space-y-2 overflow-y-auto pr-1">
                  {(data.suspicious_users || []).map((user, i) => (
                    <div key={i} className="rounded-xl border border-red-900/30 bg-[#0d0d0d] p-3">
                      <div className="mb-1 flex items-start justify-between">
                        <span className="truncate pr-2 text-sm font-bold text-neutral-200">{user.name}</span>
                        <Badge className={user.severity === 'Critical' ? 'border border-red-500/30 bg-red-500/10 text-red-400' : user.severity === 'Warning' ? 'border border-amber-500/30 bg-amber-500/10 text-amber-400' : 'border border-blue-500/30 bg-blue-500/10 text-blue-400'}>{user.severity}</Badge>
                      </div>
                      <div className="mb-2 text-[11px] text-neutral-500">{user.reason}</div>
                      <div className="flex gap-2 font-mono text-[10px]">
                        <span className="rounded bg-[#0A0A0A] px-1.5 py-0.5 text-neutral-600">U:{user.uploads}</span>
                        <span className="rounded bg-[#0A0A0A] px-1.5 py-0.5 text-neutral-600">C:{user.created}</span>
                        <span className="rounded bg-[#0A0A0A] px-1.5 py-0.5 text-neutral-600">P:{user.published}</span>
                      </div>
                    </div>
                  ))}
                  {(data.suspicious_users || []).length === 0 && <p className="text-sm text-neutral-600">No suspicious accounts found.</p>}
                </div>
              </Panel>
            </div>
          </div>
        )}

        {/* ═══════════ ISSUE EXPLORER SUB-TAB ═══════════ */}
        {subTab === 'issues' && (
          <div className="flex h-[calc(100vh-200px)] flex-col gap-4">
            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-neutral-800 bg-[#111111] p-3">
              <div className="relative">
                <select value={filterTable} onChange={e => setFilterTable(e.target.value)} className="appearance-none rounded-xl border border-neutral-800 bg-[#0A0A0A] py-2 pl-3 pr-8 text-sm text-neutral-300 focus:border-red-500 focus:outline-none">
                  <option value="">All Tables</option>
                  {Object.keys(TABLE_COLOR_MAP).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-600" />
              </div>

              <div className="h-5 w-px bg-neutral-800" />

              <div className="flex flex-wrap gap-1.5">
                <button onClick={() => setFilterCheck('')} className={`rounded-full px-2.5 py-1 text-xs font-bold ${!filterCheck ? 'bg-red-500/20 text-red-400' : 'bg-neutral-800 text-neutral-500 hover:text-neutral-300'}`}>All Checks</button>
                {Object.entries(CHECK_COLOR_MAP).map(([key, conf]) => (
                  <button key={key} onClick={() => setFilterCheck(filterCheck === key ? '' : key)} className={`rounded-full px-2.5 py-1 text-xs font-bold ${filterCheck === key ? `${conf.bg} ${conf.color}` : 'bg-neutral-800 text-neutral-500 hover:text-neutral-300'}`}>{conf.label}</button>
                ))}
              </div>

              <div className="h-5 w-px bg-neutral-800" />

              <div className="relative min-w-[180px] flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-600" />
                <input type="text" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="Search..." className="w-full rounded-xl border border-neutral-800 bg-[#0A0A0A] py-2 pl-9 pr-3 text-sm text-neutral-300 placeholder-neutral-600 focus:border-red-500 focus:outline-none" />
              </div>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-3 lg:grid-cols-6">
              {Object.entries(CHECK_COLOR_MAP).map(([key, conf]) => {
                const Icon = conf.icon;
                const cnt = checks[key] || 0;
                return (
                  <div key={key} onClick={() => setFilterCheck(filterCheck === key ? '' : key)} className={`cursor-pointer rounded-2xl border p-3 transition-colors ${filterCheck === key ? 'border-neutral-600 bg-[#171717]' : 'border-neutral-800 bg-[#111111] hover:border-neutral-700'}`}>
                    <div className="flex items-center gap-2.5">
                      <div className={`rounded-lg p-1.5 ${conf.bg}`}><Icon className={`h-4 w-4 ${conf.color}`} /></div>
                      <div>
                        <div className="text-lg font-black text-white">{cnt}</div>
                        <div className="text-[9px] font-bold uppercase tracking-wider text-neutral-500">{conf.label}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Issues table */}
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-[#111111]">
              <div className="flex-1 overflow-y-auto">
                <table className="w-full text-left">
                  <thead className="sticky top-0 z-10 bg-[#0d0d0d]">
                    <tr>
                      <th className="w-10 border-b border-neutral-800 p-3" />
                      <th className="border-b border-neutral-800 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Table</th>
                      <th className="border-b border-neutral-800 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Check Type</th>
                      <th className="border-b border-neutral-800 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Column</th>
                      <th className="border-b border-neutral-800 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Count</th>
                      <th className="border-b border-neutral-800 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredIssues.map((issue, idx) => <IssueRow key={idx} issue={issue} />)}
                    {filteredIssues.length === 0 && (
                      <tr><td colSpan="6" className="p-8 text-center text-neutral-600">No issues found matching filters.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-neutral-800 bg-[#0d0d0d] p-3 text-sm text-neutral-500">
                <span>Showing {filteredIssues.length} of {issuesApi.data?.total ?? 0} issues</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
