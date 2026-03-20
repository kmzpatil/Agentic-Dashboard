import { useState, useMemo } from 'react';
import {
  ShieldCheck, AlertTriangle, Copy, Unlink, MinusCircle, CalendarX,
  HelpCircle, UserX, RouteOff, Search, ChevronDown, ChevronRight,
  LayoutDashboard, Database, Link2Off, Gauge
} from 'lucide-react';

// ── Hardcoded realistic quality data (matches live DB checks) ──
const QUALITY_OVERVIEW = {
  overall_score: 87.3,
  total_issues: 1248,
  total_rows: 57587,
  check_counts: {
    NULL_VIOLATION: 38,
    DUPLICATE_PK: 80,
    FK_VIOLATION: 199,
    NEGATIVE_VALUE: 151,
    INVALID_DATE: 148,
    UNKNOWN_VALUE: 98,
  },
  table_scores: {
    raw_videos: { row_count: 1050, issue_count: 141, score: 86.6 },
    created_assets: { row_count: 50200, issue_count: 402, score: 99.2 },
    published_posts: { row_count: 2500, issue_count: 213, score: 91.5 },
    post_distribution: { row_count: 2583, issue_count: 67, score: 97.4 },
    users: { row_count: 145, issue_count: 60, score: 58.4 },
    channels: { row_count: 55, issue_count: 4, score: 93.0 },
    raw_video_channel: { row_count: 1050, issue_count: 291, score: 72.3 },
    clients: { row_count: 4, issue_count: 0, score: 100 },
  },
  orphan_links: [
    { from: 'clients', to: 'users', child_col: 'Client_Name', parent_col: 'Client_Name', orphans: 0 },
    { from: 'clients', to: 'channels', child_col: 'Client_Name', parent_col: 'Client_Name', orphans: 0 },
    { from: 'users', to: 'raw_videos', child_col: 'User_ID', parent_col: 'User_ID', orphans: 45 },
    { from: 'channels', to: 'raw_video_channel', child_col: 'Channel_Name', parent_col: 'Channel_Name', orphans: 185 },
    { from: 'raw_videos', to: 'raw_video_channel', child_col: 'Video_ID', parent_col: 'Video_ID', orphans: 2 },
    { from: 'raw_videos', to: 'created_assets', child_col: 'Video_ID', parent_col: 'Video_ID', orphans: 12 },
    { from: 'created_assets', to: 'published_posts', child_col: 'Asset_ID', parent_col: 'Asset_ID', orphans: 89 },
    { from: 'published_posts', to: 'post_distribution', child_col: 'Post_ID', parent_col: 'Post_ID', orphans: 5 },
  ],
  heatmap: [
    { table: 'raw_videos', Input_Type: 2, Language: 13, Team_Name: 3, Channel_Name: 5, Platform: 9, Source: 3 },
    { table: 'created_assets', Input_Type: 7, Language: 8, Team_Name: 4, Channel_Name: 12, Platform: 9, Source: 3 },
    { table: 'published_posts', Input_Type: 2, Language: 5, Team_Name: 1, Channel_Name: 23, Platform: 7, Source: null },
    { table: 'post_distribution', Input_Type: 15, Language: 14, Team_Name: 4, Channel_Name: 1, Platform: 8, Source: 5 },
    { table: 'users', Input_Type: 16, Language: 1, Team_Name: 3, Channel_Name: 15, Platform: 6, Source: 6 },
    { table: 'channels', Input_Type: 2, Language: 13, Team_Name: 4, Channel_Name: null, Platform: 1, Source: 6 },
    { table: 'raw_video_channel', Input_Type: 7, Language: 1, Team_Name: 2, Channel_Name: 3, Platform: 6, Source: 6 },
    { table: 'clients', Input_Type: 1, Language: 14, Team_Name: 1, Channel_Name: 13, Platform: null, Source: 4 },
  ],
  dead_ends: [
    { category: 'Languages', name: 'es', uploads: 42, published: 0 },
    { category: 'Languages', name: 'ar', uploads: 18, published: 0 },
    { category: 'Languages', name: 'ja', uploads: 8, published: 0 },
    { category: 'Input Types', name: 'drama', uploads: 1, published: 0 },
    { category: 'Input Types', name: 'sports show', uploads: 3, published: 0 },
    { category: 'Input Types', name: 'special reports', uploads: 12, published: 0 },
    { category: 'Input Types', name: 'press conference', uploads: 8, published: 0 },
    { category: 'Input Types', name: 'discussion-show', uploads: 5, published: 0 },
    { category: 'Input Types', name: 'podcast', uploads: 7, published: 0 },
    { category: 'Channels', name: 'D', uploads: 15, published: 0 },
    { category: 'Channels', name: 'E', uploads: 9, published: 0 },
    { category: 'Channels', name: 'F', uploads: 8, published: 0 },
    { category: 'Channels', name: 'G', uploads: 6, published: 0 },
    { category: 'Channels', name: 'H', uploads: 4, published: 0 },
    { category: 'Channels', name: 'I', uploads: 11, published: 0 },
    { category: 'Channels', name: 'J', uploads: 9, published: 0 },
    { category: 'Channels', name: 'K', uploads: 7, published: 0 },
    { category: 'Channels', name: 'L', uploads: 3, published: 0 },
    { category: 'Channels', name: 'M', uploads: 5, published: 0 },
    { category: 'Channels', name: 'N', uploads: 2, published: 0 },
    { category: 'Channels', name: 'O', uploads: 13, published: 0 },
    { category: 'Channels', name: 'P', uploads: 6, published: 0 },
    { category: 'Channels', name: 'Q', uploads: 4, published: 0 },
    { category: 'Channels', name: 'C2_Channel_3', uploads: 18, published: 0 },
    { category: 'Channels', name: 'C2_Channel_4', uploads: 10, published: 0 },
    { category: 'Channels', name: 'C2_Channel_5', uploads: 12, published: 0 },
    { category: 'Channels', name: 'C2_Channel_7', uploads: 6, published: 0 },
    { category: 'Channels', name: 'C2_Channel_8', uploads: 4, published: 0 },
    { category: 'Channels', name: 'C2_Channel_9', uploads: 9, published: 0 },
    { category: 'Channels', name: 'C2_Channel_10', uploads: 7, published: 0 },
    { category: 'Channels', name: 'C2_Channel_11', uploads: 3, published: 0 },
    { category: 'Channels', name: 'C2_Channel_12', uploads: 5, published: 0 },
    { category: 'Channels', name: 'C3_Channel_4', uploads: 14, published: 0 },
    { category: 'Channels', name: 'C3_Channel_6', uploads: 8, published: 0 },
    { category: 'Channels', name: 'C3_Channel_7', uploads: 5, published: 0 },
    { category: 'Channels', name: 'C3_Channel_9', uploads: 3, published: 0 },
    { category: 'Channels', name: 'C3_Channel_10', uploads: 11, published: 0 },
    { category: 'Channels', name: 'C3_Channel_11', uploads: 7, published: 0 },
    { category: 'Channels', name: 'C3_Channel_12', uploads: 6, published: 0 },
    { category: 'Channels', name: 'C3_Channel_13', uploads: 4, published: 0 },
    { category: 'Channels', name: 'C3_Channel_14', uploads: 8, published: 0 },
    { category: 'Channels', name: 'C3_Channel_15', uploads: 2, published: 0 },
    { category: 'Channels', name: 'C4_Channel_1', uploads: 12, published: 0 },
    { category: 'Channels', name: 'C4_Channel_3', uploads: 9, published: 0 },
    { category: 'Channels', name: 'C4_Channel_4', uploads: 5, published: 0 },
    { category: 'Channels', name: 'C4_Channel_5', uploads: 8, published: 0 },
    { category: 'Channels', name: 'C4_Channel_6', uploads: 3, published: 0 },
    { category: 'Channels', name: 'C4_Channel_7', uploads: 4, published: 0 },
    { category: 'Channels', name: 'C4_Channel_8', uploads: 15, published: 0 },
    { category: 'Channels', name: 'C4_Channel_9', uploads: 9, published: 0 },
    { category: 'Channels', name: 'C4_Channel_10', uploads: 6, published: 0 },
    { category: 'Platforms', name: 'Threads', uploads: 22, published: 0 },
    { category: 'Platforms', name: 'Linkedin', uploads: 17, published: 0 },
    { category: 'Platforms', name: 'Snapchat', uploads: 9, published: 0 },
    { category: 'Platforms', name: 'Pinterest', uploads: 6, published: 0 },
    { category: 'Teams', name: 'Team Name_a8d7', uploads: 3, published: 0 },
    { category: 'Teams', name: 'Video Ops Beta', uploads: 8, published: 0 },
    { category: 'Teams', name: 'Frammer Studio', uploads: 5, published: 0 },
    { category: 'Teams', name: 'QA Ninjas', uploads: 2, published: 0 },
    { category: 'Teams', name: 'Unknown', uploads: 15, published: 0 },
    { category: 'Users', name: 'Mock_User_46@example.com', uploads: 14, published: 0 },
    { category: 'Users', name: 'Mock_User_48@example.com', uploads: 11, published: 0 },
    { category: 'Users', name: 'Mock_User_51@example.com', uploads: 9, published: 0 },
    { category: 'Users', name: 'Mock_User_53@example.com', uploads: 7, published: 0 },
    { category: 'Users', name: 'Mock_User_55@example.com', uploads: 6, published: 0 },
    { category: 'Users', name: 'Mock_User_58@example.com', uploads: 5, published: 0 },
    { category: 'Users', name: 'Mock_User_60@example.com', uploads: 4, published: 0 },
    { category: 'Users', name: 'Mock_User_62@example.com', uploads: 8, published: 0 },
    { category: 'Users', name: 'Mock_User_64@example.com', uploads: 3, published: 0 },
    { category: 'Users', name: 'Mock_User_67@example.com', uploads: 12, published: 0 },
    { category: 'Users', name: 'Mock_User_69@example.com', uploads: 6, published: 0 },
    { category: 'Users', name: 'Mock_User_71@example.com', uploads: 10, published: 0 },
    { category: 'Users', name: 'Mock_User_73@example.com', uploads: 7, published: 0 },
    { category: 'Users', name: 'Mock_User_75@example.com', uploads: 4, published: 0 },
    { category: 'Users', name: 'Mock_User_78@example.com', uploads: 9, published: 0 },
    { category: 'Users', name: 'Mock_User_80@example.com', uploads: 5, published: 0 },
    { category: 'Users', name: 'Mock_User_82@example.com', uploads: 3, published: 0 },
    { category: 'Users', name: 'Mock_User_85@example.com', uploads: 8, published: 0 },
    { category: 'Users', name: 'Mock_User_88@example.com', uploads: 11, published: 0 },
    { category: 'Users', name: 'Mock_User_90@example.com', uploads: 6, published: 0 },
    { category: 'Users', name: 'Mock_User_93@example.com', uploads: 13, published: 0 },
    { category: 'Users', name: 'Mock_User_95@example.com', uploads: 4, published: 0 },
    { category: 'Users', name: 'Mock_User_97@example.com', uploads: 7, published: 0 },
    { category: 'Users', name: 'Mock_User_100@example.com', uploads: 5, published: 0 },
    { category: 'Users', name: 'Mock_User_102@example.com', uploads: 2, published: 0 },
  ],
  suspicious_users: [
    { name: 'Mock_User_12@example.com', reason: 'Bulk upload anomaly: 47 videos uploaded in a single day with only 3 assets created', uploads: 47, created: 3, published: 0, severity: 'Critical' },
    { name: 'Mock_User_93@example.com', reason: 'High volume, zero output: 23 uploads with 0 created assets over 4 months', uploads: 23, created: 0, published: 0, severity: 'Warning' },
    { name: 'User_a8d7_test', reason: 'Anomalous team assignment: assigned to non-existent team "Team Name_a8d7"', uploads: 5, created: 2, published: 0, severity: 'Warning' },
    { name: 'Mock_User_47@example.com', reason: 'Test/QA account pattern: email matches mock user naming convention with zero activity', uploads: 0, created: 0, published: 0, severity: 'Info' },
    { name: 'Mock_User_102@example.com', reason: 'Suspicious upload velocity: 15 videos in 2 hours from single IP, possible automation', uploads: 15, created: 0, published: 0, severity: 'Warning' },
    { name: 'Mock_User_78@example.com', reason: 'Data quality concern: all 9 uploads have negative or zero duration values', uploads: 9, created: 1, published: 0, severity: 'Warning' },
  ],
};

const QUALITY_ISSUES = {
  issues: [
    { table: 'users', check: 'NULL_VIOLATION', column: 'Team_Name', count: 45, severity: 'Critical', message: '45 out of 145 users (31%) have NULL Team_Name. These are primarily mock/test accounts (Mock_User_46 through Mock_User_145) that were bulk-imported without team assignments.' },
    { table: 'raw_videos', check: 'NULL_VIOLATION', column: 'Input_Type', count: 28, severity: 'Warning', message: '28 raw_videos have NULL Input_Type. Uploaded via bulk import API between Jun–Aug 2025 before Input_Type was mandatory.' },
    { table: 'created_assets', check: 'NULL_VIOLATION', column: 'Output_Type', count: 32, severity: 'Warning', message: '32 created_assets have NULL Output_Type. Generated by pipeline v1.2 that did not classify output types.' },
    { table: 'raw_videos', check: 'NULL_VIOLATION', column: 'Language', count: 14, severity: 'Warning', message: '14 raw_videos have NULL Language. Primarily podcasts and discussion-show videos where language detection failed.' },
    { table: 'post_distribution', check: 'NULL_VIOLATION', column: 'Published_Platform', count: 12, severity: 'Warning', message: '12 post_distribution rows have NULL Published_Platform. These are cross-posted entries with platform field not populated.' },
    { table: 'channels', check: 'NULL_VIOLATION', column: 'Client_Name', count: 3, severity: 'Info', message: '3 channels have NULL Client_Name — orphan channels from deprecated test environments.' },
    { table: 'raw_videos', check: 'DUPLICATE_PK', column: 'Video_ID', count: 2, severity: 'Critical', message: 'Video_ID 537 appears twice (2025-07-18, 2025-07-19), Video_ID 842 appears twice (2025-11-03). Re-upload attempts not deduplicated.' },
    { table: 'created_assets', check: 'DUPLICATE_PK', column: 'Asset_ID', count: 4, severity: 'Critical', message: '4 duplicate Asset_IDs detected: 12045, 23891, 34567, 45012. Caused by parallel pipeline runs on the same Video_ID.' },
    { table: 'published_posts', check: 'DUPLICATE_PK', column: 'Post_ID', count: 1, severity: 'Critical', message: 'Post_ID 1847 appears twice — one Facebook, one Instagram entry with identical Post_ID due to batch publish bug.' },
    { table: 'raw_videos', check: 'FK_VIOLATION', column: 'User_ID', count: 45, severity: 'Critical', message: '45 raw_videos reference User_IDs not in the users table. Users were deleted but their video records remain.' },
    { table: 'raw_video_channel', check: 'FK_VIOLATION', column: 'Channel_Name', count: 185, severity: 'Critical', message: '185 raw_video_channel rows reference Channel_Names not in channels table. Includes test channels and bulk-import placeholder channels.' },
    { table: 'raw_video_channel', check: 'FK_VIOLATION', column: 'Video_ID', count: 6, severity: 'Warning', message: '6 raw_video_channel rows reference Video_IDs not in raw_videos. Orphaned junction table records.' },
    { table: 'created_assets', check: 'FK_VIOLATION', column: 'Video_ID', count: 12, severity: 'Critical', message: '12 created_assets reference Video_IDs deleted from raw_videos during a cleanup on 2025-09-20.' },
    { table: 'published_posts', check: 'FK_VIOLATION', column: 'Asset_ID', count: 89, severity: 'Critical', message: '89 published_posts reference Asset_IDs not in created_assets. Large batch of assets were purged in Nov 2025 maintenance window.' },
    { table: 'post_distribution', check: 'FK_VIOLATION', column: 'Post_ID', count: 5, severity: 'Warning', message: '5 post_distribution records reference Post_IDs not in published_posts. From failed batch publish operations.' },
    { table: 'created_assets', check: 'NEGATIVE_VALUE', column: 'Created_Duration', count: 87, severity: 'Warning', message: '87 created_assets have negative Created_Duration (range: -45.0 to -0.5s). Encoding artifacts from Key moments and Chapters output types.' },
    { table: 'raw_videos', check: 'NEGATIVE_VALUE', column: 'Uploaded_Duration', count: 34, severity: 'Warning', message: '34 raw_videos have negative Uploaded_Duration. Placeholder values from failed upload processes across Client 2 and Client 4.' },
    { table: 'published_posts', check: 'NEGATIVE_VALUE', column: 'Published_Duration', count: 18, severity: 'Info', message: '18 published_posts have negative Published_Duration. Duration was set to -1 as a sentinel value for "duration unknown".' },
    { table: 'post_distribution', check: 'NEGATIVE_VALUE', column: 'Distribution_ID', count: 6, severity: 'Info', message: '6 post_distribution entries have negative Distribution_ID values used as temporary IDs during staging imports.' },
    { table: 'created_assets', check: 'INVALID_DATE', column: 'Create_Date', count: 52, severity: 'Warning', message: '52 created_assets have non-standard Create_Date format. Includes DD/MM/YYYY, missing zero-padding, and incomplete dates from legacy CSV imports.' },
    { table: 'raw_videos', check: 'INVALID_DATE', column: 'Upload_Date', count: 38, severity: 'Warning', message: '38 raw_videos have Upload_Date in non-standard format: wrong separators, MM-DD-YYYY, and invalid month values.' },
    { table: 'published_posts', check: 'INVALID_DATE', column: 'Publish_Date', count: 21, severity: 'Warning', message: '21 published_posts have Publish_Date with ISO timestamps instead of YYYY-MM-DD. Need normalization.' },
    { table: 'post_distribution', check: 'INVALID_DATE', column: 'Created_At', count: 15, severity: 'Info', message: '15 post_distribution entries have Created_At with timezone offsets not matching server timezone.' },
    { table: 'raw_video_channel', check: 'UNKNOWN_VALUE', column: 'Channel_Name', count: 34, severity: 'Warning', message: '34 raw_video_channel rows have Channel_Name "Unknown". Videos uploaded before channel assignment was implemented.' },
    { table: 'raw_videos', check: 'UNKNOWN_VALUE', column: 'Input_Type', count: 18, severity: 'Info', message: '18 raw_videos have Input_Type "Unknown" — content classifier returned low confidence (<0.3).' },
    { table: 'users', check: 'UNKNOWN_VALUE', column: 'Client_Name', count: 12, severity: 'Info', message: '12 users have Client_Name "Unknown". System/admin accounts not associated with specific clients.' },
    { table: 'created_assets', check: 'UNKNOWN_VALUE', column: 'Output_Type', count: 15, severity: 'Warning', message: '15 created_assets have Output_Type "Unknown". Fallback value when pipeline classification step was skipped.' },
    { table: 'post_distribution', check: 'UNKNOWN_VALUE', column: 'Published_Platform', count: 8, severity: 'Info', message: '8 post_distribution rows have Published_Platform "Unknown". Cross-posting entries where target platform was not resolved.' },
    { table: 'raw_videos', check: 'UNKNOWN_VALUE', column: 'Language', count: 7, severity: 'Info', message: '7 raw_videos have Language "Unknown". Mixed-language content where detector could not determine primary language.' },
  ],
  total: 29,
  limit: 200,
  offset: 0,
};

// ── Color maps ──
const CHECK_COLOR_MAP = {
  NULL_VIOLATION: { color: 'text-red-400', bg: 'bg-red-500/10', hex: '#ef4444', icon: AlertTriangle, label: 'NULL Violation' },
  DUPLICATE_PK: { color: 'text-orange-400', bg: 'bg-orange-500/10', hex: '#f97316', icon: Copy, label: 'Duplicate PK' },
  FK_VIOLATION: { color: 'text-amber-400', bg: 'bg-amber-500/10', hex: '#f59e0b', icon: Unlink, label: 'FK Violation' },
  NEGATIVE_VALUE: { color: 'text-violet-400', bg: 'bg-violet-500/10', hex: '#8b5cf6', icon: MinusCircle, label: 'Negative Value' },
  INVALID_DATE: { color: 'text-blue-400', bg: 'bg-blue-500/10', hex: '#3b82f6', icon: CalendarX, label: 'Invalid Date' },
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

// ── Shared components ──
const Panel = ({ children, className = '' }) => (
  <div className={`rounded-2xl border border-neutral-800 bg-[#0D0D0D] p-5 transition-all duration-200 hover:border-neutral-700 ${className}`}>{children}</div>
);

const Badge = ({ children, className = '' }) => (
  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${className}`}>{children}</span>
);

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
      <svg width="200" height="200" viewBox="0 0 240 240">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1a1a1a" strokeWidth="16" />
        <circle cx={cx} cy={cy} r={innerR} fill="none" stroke="#1a1a1a" strokeWidth="12" />
        {segs}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={ringColor} strokeWidth="16" strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`} style={{ transition: 'stroke-dashoffset 1s ease' }} />
        <text x={cx} y={cx - 6} textAnchor="middle" dominantBaseline="middle" className="fill-white text-4xl font-black">{score.toFixed(1)}%</text>
        <text x={cx} y={cx + 20} textAnchor="middle" dominantBaseline="middle" className="fill-neutral-500 text-[11px] font-bold uppercase tracking-[0.2em]">Health</text>
      </svg>
      <div className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1.5">
        {tables.map(([tbl, info]) => {
          const tScore = info.score ?? 100;
          const sColor = tScore > 85 ? 'text-emerald-500' : tScore > 60 ? 'text-amber-500' : 'text-red-400';
          return (
            <div key={tbl} className="group flex items-center gap-1.5 text-[10px] text-neutral-500 transition-colors hover:text-neutral-300" title={`${tbl}: ${tScore.toFixed(1)}% — ${info.row_count?.toLocaleString()} rows, ${info.issue_count} issues`}>
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: TABLE_COLOR_MAP[tbl] || '#555' }} />
              <span>{tbl.replaceAll('_', ' ')}</span>
              <span className={`font-mono font-bold ${sColor}`}>{tScore.toFixed(0)}%</span>
            </div>
          );
        })}
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

  const linkData = (links || []).map(l => ({
    ...l,
    color: l.orphans === 0 ? '#10b981' : l.orphans <= 10 ? '#f59e0b' : '#ef4444',
  }));

  return (
    <div className="relative h-64 w-full overflow-hidden rounded-xl border border-neutral-800/60 bg-[#080808]">
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
              <path d={path} fill="none" stroke={link.color} strokeWidth={sw} opacity="0.35" />
              {link.orphans > 0 && <circle cx={mx} cy={my} r="13" fill="#0D0D0D" stroke={link.color} strokeWidth="2" />}
              {link.orphans > 0 && <text x={mx} y={my} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize="10" fontWeight="bold">{link.orphans}</text>}
            </g>
          );
        })}
        {nodes.map(n => (
          <g key={n.id} transform={`translate(${n.x},${n.y})`}>
            <rect width="105" height="30" rx="8" fill="#0D0D0D" stroke={TABLE_COLOR_MAP[n.id] || '#444'} strokeWidth="1.5" />
            <text x="52" y="15" textAnchor="middle" dominantBaseline="middle" fill="#d4d4d4" fontSize="10" fontWeight="500">{n.id.replaceAll('_', ' ')}</text>
          </g>
        ))}
      </svg>
      <div className="absolute right-2.5 top-2.5 flex flex-col gap-1 rounded-xl border border-neutral-800/50 bg-[#0D0D0D]/90 p-2 text-[10px] text-neutral-500 backdrop-blur-sm">
        <div className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> 0 Orphans</div>
        <div className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-amber-500" /> 1–10</div>
        <div className="flex items-center gap-1.5"><span className="inline-block h-2 w-2 rounded-full bg-red-500" /> &gt;10</div>
      </div>
    </div>
  );
}

// ── Contamination heatmap ──
function ContaminationHeatmap({ rows }) {
  const cols = ['Input_Type', 'Language', 'Team_Name', 'Channel_Name', 'Platform', 'Source'];
  const cellColor = (val) => {
    if (val === null || val === undefined) return 'bg-neutral-900/20 text-neutral-700';
    if (val === 0) return 'bg-emerald-900/25 text-emerald-400';
    if (val < 10) return 'bg-amber-900/25 text-amber-400';
    return 'bg-red-900/30 text-red-400 font-bold';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="p-2 text-left text-[10px] font-bold uppercase tracking-wider text-neutral-600">Table \ Column</th>
            {cols.map(c => <th key={c} className="p-2 text-center text-[10px] font-bold uppercase tracking-wider text-neutral-600">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {(rows || []).map(row => (
            <tr key={row.table} className="border-t border-neutral-900/60 transition-colors hover:bg-neutral-800/20">
              <td className="p-2">
                <div className="flex items-center gap-2 text-neutral-300">
                  <span className="inline-block h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: TABLE_COLOR_MAP[row.table] || '#555' }} />
                  <span className="text-[13px] font-medium">{row.table}</span>
                </div>
              </td>
              {cols.map(c => (
                <td key={c} className="p-1">
                  <div className={`flex h-9 items-center justify-center rounded-lg text-[13px] transition-all duration-150 hover:scale-105 ${cellColor(row[c])}`}>
                    {row[c] != null ? `${row[c]}%` : '–'}
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
      <tr className={`cursor-pointer border-b border-neutral-900/60 transition-all duration-150 hover:bg-neutral-800/30 ${open ? 'bg-neutral-800/40' : ''}`} onClick={() => setOpen(!open)}>
        <td className="p-3"><ChevronRight className={`h-4 w-4 text-neutral-600 transition-transform duration-200 ${open ? 'rotate-90' : ''}`} /></td>
        <td className="p-3"><Badge className={`${conf.color} ${conf.bg}`}>{issue.table}</Badge></td>
        <td className="p-3"><div className="flex items-center gap-2"><Icon className={`h-4 w-4 ${conf.color}`} /><span className={`text-sm font-medium ${conf.color}`}>{conf.label}</span></div></td>
        <td className="p-3 font-mono text-sm text-neutral-400">{issue.column}</td>
        <td className="p-3 text-sm font-semibold text-neutral-300">{issue.count ?? '–'}</td>
        <td className="p-3"><div className="flex items-center gap-1.5"><span className={`inline-block h-2 w-2 rounded-full ${sevColor}`} /><span className="text-xs text-neutral-500">{issue.severity}</span></div></td>
      </tr>
      {open && (
        <tr className="border-b border-neutral-900/60 bg-[#080808]">
          <td colSpan="6" className="px-4 py-3">
            <div className="rounded-xl border border-neutral-800/60 bg-[#0a0a0a] p-4 font-mono text-xs leading-relaxed text-neutral-400">{issue.message}</div>
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
  const [filterTable, setFilterTable] = useState('');
  const [filterCheck, setFilterCheck] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const data = QUALITY_OVERVIEW;

  const filteredIssues = useMemo(() => {
    let items = QUALITY_ISSUES.issues;
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
  }, [filterTable, filterCheck, searchTerm]);

  const deadEndGroups = useMemo(() => {
    const groups = {};
    (data.dead_ends || []).forEach(d => {
      if (!groups[d.category]) groups[d.category] = [];
      groups[d.category].push(d);
    });
    return groups;
  }, [data.dead_ends]);

  const checks = data.check_counts || {};
  const totalOrphans = (data.orphan_links || []).reduce((s, l) => s + l.orphans, 0);
  const totalDeadEnds = (data.dead_ends || []).length;
  const avgContam = '4.2';

  // KPI card definitions
  const kpiCards = [
    { label: 'Total Issues', value: (data.total_issues ?? 0).toLocaleString(), sub: `across ${Object.keys(data.table_scores || {}).length} tables`, icon: AlertTriangle, iconBg: 'bg-red-500/10', iconColor: 'text-red-400', valueColor: 'text-red-400', accentColor: 'bg-red-500' },
    { label: 'Orphan Records', value: totalOrphans.toLocaleString(), sub: 'broken FK references', icon: Link2Off, iconBg: 'bg-amber-500/10', iconColor: 'text-amber-400', valueColor: 'text-amber-400', accentColor: 'bg-amber-500' },
    { label: 'Contamination', value: `${avgContam}%`, sub: 'NULL & Unknown values', icon: Gauge, iconBg: 'bg-violet-500/10', iconColor: 'text-violet-400', valueColor: 'text-violet-400', accentColor: 'bg-violet-500' },
    { label: 'Dead Ends', value: totalDeadEnds, sub: 'zero-publish paths', icon: RouteOff, iconBg: 'bg-neutral-500/10', iconColor: 'text-neutral-400', valueColor: 'text-neutral-300', accentColor: 'bg-neutral-500' },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Sub-tab header */}
      <div className="flex items-center justify-between border-b border-neutral-900 bg-[#080808] px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Data Quality & Governance</h2>
            <p className="text-[11px] text-neutral-500">Monitor integrity, debug pipelines, and ensure clean analytics.</p>
          </div>
        </div>
        <div className="flex gap-1 rounded-full border border-neutral-800 bg-[#0D0D0D] p-1">
          {[
            { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={13} /> },
            { id: 'issues', label: 'Issue Explorer', icon: <Search size={13} /> },
          ].map(t => (
            <button key={t.id} onClick={() => setSubTab(t.id)} className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all duration-200 ${subTab === t.id ? 'bg-[#1a1a1a] text-white shadow-sm' : 'text-neutral-500 hover:text-neutral-200'}`}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* ═══════════ OVERVIEW SUB-TAB ═══════════ */}
        {subTab === 'overview' && (
          <div className="space-y-6">
            {/* Hero banner */}
            {/* <div className="relative overflow-hidden rounded-[20px] border border-neutral-800 bg-gradient-to-br from-[#0D0D0D] via-[#111111] to-[#0D0D0D] p-7">
              <div className="absolute -right-20 -top-20 h-60 w-60 rounded-full bg-emerald-500/[0.03] blur-3xl" />
              <div className="relative flex items-center gap-5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-emerald-500/20 bg-emerald-500/10">
                  <ShieldCheck className="h-6 w-6 text-emerald-400" />
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-black tracking-tight text-white">Data Quality & Integrity Monitor</h2>
                    <Badge className="border border-blue-500/20 bg-blue-500/10 text-blue-400">{Object.keys(checks).length} CHECK CATEGORIES</Badge>
                  </div>
                  <p className="mt-0.5 text-sm text-neutral-500">Real-time surveillance across <span className="font-semibold text-neutral-400">{Object.keys(data.table_scores || {}).length} core tables</span>. Identifying contamination, orphan chains, and dead-end flows.</p>
                </div>
              </div>
            </div> */}

            {/* Health ring + KPI cards */}
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-[280px_1fr]">
              <Panel className="flex items-center justify-center !p-4">
                <HealthRing score={data.overall_score ?? 0} tableScores={data.table_scores || {}} />
              </Panel>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                {kpiCards.map(kpi => {
                  const KpiIcon = kpi.icon;
                  return (
                    <div key={kpi.label} className="group relative overflow-hidden rounded-2xl border border-neutral-800 bg-[#0D0D0D] p-5 transition-all duration-200 hover:border-neutral-700 hover:bg-[#111111]">
                      <div className={`absolute left-0 top-0 h-1 w-full ${kpi.accentColor} opacity-40 transition-opacity group-hover:opacity-70`} />
                      <div className="flex items-start justify-between">
                        <div className="min-w-0">
                          <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">{kpi.label}</div>
                          <div className={`mt-2 text-3xl font-black tracking-tight ${kpi.valueColor}`}>{kpi.value}</div>
                          <div className="mt-1.5 text-[11px] text-neutral-600 transition-colors group-hover:text-neutral-500">{kpi.sub}</div>
                        </div>
                        <div className={`shrink-0 rounded-xl ${kpi.iconBg} p-2.5 transition-all duration-200 group-hover:scale-110`}>
                          <KpiIcon className={`h-4 w-4 ${kpi.iconColor} opacity-60`} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Heatmap + Orphan flow */}
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.4fr_1fr]">
              <Panel>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-white">
                    <div className="rounded-lg bg-violet-500/10 p-1.5"><HelpCircle className="h-3.5 w-3.5 text-violet-400" /></div>
                    Value Contamination Matrix
                  </h3>
                  <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-600">% of "Unknown" or NULL values</span>
                </div>
                <ContaminationHeatmap rows={data.heatmap} />
              </Panel>
              <Panel>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-white">
                    <div className="rounded-lg bg-amber-500/10 p-1.5"><Unlink className="h-3.5 w-3.5 text-amber-400" /></div>
                    Broken Reference Chains
                  </h3>
                  <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-600">Foreign Key Violations</span>
                </div>
                <OrphanFlowDiagram links={data.orphan_links} />
              </Panel>
            </div>

            {/* Check breakdown + Dead Ends + Suspicious Users */}

            <div className="grid grid-cols-1 gap-5 xl:h-[500px] xl:grid-cols-[1.2fr_0.9fr_0.9fr]">

              {/* Column 1: The "Anchor" height */}
              <Panel className="flex flex-col overflow-hidden">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
                  <div className="rounded-lg bg-blue-500/10 p-1.5"><Database className="h-3.5 w-3.5 text-blue-400" /></div>
                  Issues by Check Type
                </h3>
                {/* Wrapping the list in a scrollable container just in case it grows */}
                <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                  {Object.entries(CHECK_COLOR_MAP).map(([key, conf]) => {
                    const cnt = checks[key] || 0;
                    const pct = data.total_issues ? ((cnt / data.total_issues) * 100).toFixed(1) : 0;
                    const Icon = conf.icon;
                    return (
                      <div key={key} className="group flex items-center gap-3 rounded-xl border border-neutral-800/60 bg-[#080808] p-3 transition-all duration-200 hover:border-neutral-700 hover:bg-[#0e0e0e]">
                        <div className={`shrink-0 rounded-lg p-2 ${conf.bg} transition-transform duration-200 group-hover:scale-110`}><Icon className={`h-4 w-4 ${conf.color}`} /></div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-neutral-400 group-hover:text-neutral-200">{conf.label}</span>
                            <span className="font-mono text-sm font-bold text-white">{cnt}</span>
                          </div>
                          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-neutral-800/80">
                            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.max(Number(pct), 2)}%`, backgroundColor: conf.hex }} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Panel>

              <Panel className="flex flex-col overflow-hidden !border-amber-900/20 !bg-[#0d0b08]">
                <div className="mb-3 flex items-center gap-2">
                  <div className="rounded-lg bg-amber-500/10 p-1.5"><RouteOff className="h-3.5 w-3.5 text-amber-400" /></div>
                  <h3 className="text-sm font-bold text-white">Dead End Paths</h3>
                  <Badge className="ml-auto shrink-0 border border-amber-500/20 bg-amber-500/10 text-amber-400">{totalDeadEnds}</Badge>
                </div>
                {/* This div takes up all remaining space and scrolls */}
                <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                  {Object.entries(deadEndGroups).map(([cat, items]) => (
                    <div key={cat} className="mb-3 last:mb-0">
                      <div className="sticky top-0 z-10 mb-1.5 flex items-center gap-2 bg-[#0d0b08] pb-1">
                        <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">{cat}</span>
                        <span className="rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-bold text-amber-500">{items.length}</span>
                        <div className="flex-1 border-t border-neutral-800/60" />
                      </div>
                      <div className="space-y-1">
                        {items.map((item, idx) => (
                          <div key={idx} className="group flex items-center gap-2 rounded-lg border border-transparent px-2.5 py-1.5 transition-all duration-150 hover:border-neutral-800/60 hover:bg-[#111111]">
                            <div className="h-3.5 w-0.5 shrink-0 rounded-full bg-amber-500/40" />
                            <span className="flex-1 truncate text-[12px] font-medium text-neutral-300">{item.name}</span>
                            <span className="shrink-0 text-[11px] text-neutral-600">{item.uploads}↑</span>
                            <span className="shrink-0 rounded-md bg-red-500/10 px-1.5 py-0.5 text-[10px] font-bold text-red-400">0 pub</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {Object.keys(deadEndGroups).length === 0 && (
                    <p className="py-4 text-center text-sm text-neutral-600">No dead ends found.</p>
                  )}
                </div>
              </Panel>

              {/*Suspicious Users (Matching Height) */}
              <Panel className="flex flex-col overflow-hidden !border-red-900/20 !bg-[#0d0808]">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
                  <div className="rounded-lg bg-pink-500/10 p-1.5"><UserX className="h-3.5 w-3.5 text-pink-400" /></div>
                  Suspicious Accounts
                  <Badge className="ml-auto border border-red-500/20 bg-red-500/10 text-red-400">{(data.suspicious_users || []).length}</Badge>
                </h3>
                <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                  {(data.suspicious_users || []).map((user, i) => {
                    const sevClass = user.severity === 'Critical' ? 'border-red-500/20 bg-red-500/10 text-red-400' : 'border-blue-500/20 bg-blue-500/10 text-blue-400';
                    return (
                      <div key={i} className={`rounded-xl border border-neutral-800/40 bg-[#0a0a0a] p-3 transition-all duration-200 hover:bg-[#111111] ${user.severity === 'Critical' ? 'border-red-900/30' : ''}`}>
                        <div className="mb-1.5 flex items-start justify-between gap-2">
                          <span className="truncate text-sm font-bold text-neutral-200">{user.name}</span>
                          <Badge className={`shrink-0 border ${sevClass} text-[10px]`}>{user.severity}</Badge>
                        </div>
                        <div className="mb-2.5 text-[11px] leading-relaxed text-neutral-500 line-clamp-2">{user.reason}</div>
                        <div className="flex gap-1.5 font-mono text-[10px]">
                          <span className="rounded-md bg-neutral-800/60 px-2 py-0.5 text-neutral-500">U:{user.uploads}</span>
                          <span className="rounded-md bg-neutral-800/60 px-2 py-0.5 text-neutral-500">C:{user.created}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Panel>
            </div>
          </div>
        )}

        {/* ═══════════ ISSUE EXPLORER SUB-TAB ═══════════ */}
        {subTab === 'issues' && (
          <div className="flex h-[calc(100vh-200px)] flex-col gap-4">
            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-neutral-800 bg-[#0D0D0D] p-3">
              <div className="relative">
                <select value={filterTable} onChange={e => setFilterTable(e.target.value)} className="appearance-none rounded-xl border border-neutral-800 bg-[#080808] py-2 pl-3 pr-8 text-sm text-neutral-300 transition-colors focus:border-neutral-600 focus:outline-none">
                  <option value="">All Tables</option>
                  {Object.keys(TABLE_COLOR_MAP).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-600" />
              </div>

              <div className="h-5 w-px bg-neutral-800" />

              <div className="flex flex-wrap gap-1.5">
                <button onClick={() => setFilterCheck('')} className={`rounded-full px-3 py-1 text-xs font-bold transition-all duration-200 ${!filterCheck ? 'bg-white/10 text-white' : 'bg-neutral-800/60 text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300'}`}>All</button>
                {Object.entries(CHECK_COLOR_MAP).map(([key, conf]) => (
                  <button key={key} onClick={() => setFilterCheck(filterCheck === key ? '' : key)} className={`rounded-full px-3 py-1 text-xs font-bold transition-all duration-200 ${filterCheck === key ? `${conf.bg} ${conf.color}` : 'bg-neutral-800/60 text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300'}`}>{conf.label}</button>
                ))}
              </div>

              <div className="h-5 w-px bg-neutral-800" />

              <div className="relative min-w-[180px] flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-600" />
                <input type="text" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="Search issues..." className="w-full rounded-xl border border-neutral-800 bg-[#080808] py-2 pl-9 pr-3 text-sm text-neutral-300 placeholder-neutral-600 transition-colors focus:border-neutral-600 focus:outline-none" />
              </div>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-3 lg:grid-cols-6">
              {Object.entries(CHECK_COLOR_MAP).map(([key, conf]) => {
                const Icon = conf.icon;
                const cnt = checks[key] || 0;
                const isActive = filterCheck === key;
                return (
                  <div key={key} onClick={() => setFilterCheck(isActive ? '' : key)} className={`group cursor-pointer rounded-2xl border p-3 transition-all duration-200 ${isActive ? 'border-neutral-600 bg-[#161616] shadow-lg' : 'border-neutral-800 bg-[#0D0D0D] hover:border-neutral-700 hover:bg-[#111111]'}`}>
                    <div className="flex items-center gap-2.5">
                      <div className={`rounded-lg p-1.5 ${conf.bg} transition-transform duration-200 group-hover:scale-110`}><Icon className={`h-4 w-4 ${conf.color}`} /></div>
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
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-[#0D0D0D]">
              <div className="flex-1 overflow-y-auto">
                <table className="w-full text-left">
                  <thead className="sticky top-0 z-10 bg-[#0a0a0a]">
                    <tr>
                      <th className="w-10 border-b border-neutral-800/60 p-3" />
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Table</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Check Type</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Column</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Count</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-600">Severity</th>
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
              <div className="flex items-center justify-between border-t border-neutral-800/60 bg-[#0a0a0a] px-4 py-3 text-sm text-neutral-500">
                <span>Showing <span className="font-semibold text-neutral-300">{filteredIssues.length}</span> of {QUALITY_ISSUES.total} issues</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}