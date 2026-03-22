import { useState, useMemo, useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import '../../lib/chartSetup';
import {
  ShieldCheck, AlertTriangle, Copy, Unlink, MinusCircle, CalendarX,
  HelpCircle, UserX, RouteOff, Search, ChevronDown, ChevronRight,
  LayoutDashboard, TrendingUp, Link2Off, Gauge, Loader2
} from 'lucide-react';
import { API_BASE } from '../../lib/constants';
import InfoTooltipContent from '../../components/common/InfoTooltipContent';

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
    { table: 'channels', check: 'NULL_VIOLATION', column: 'Client_Name', count: 3, severity: 'Info', message: '3 channels have NULL Client_Name - orphan channels from deprecated test environments.' },
    { table: 'raw_videos', check: 'DUPLICATE_PK', column: 'Video_ID', count: 2, severity: 'Critical', message: 'Video_ID 537 appears twice (2025-07-18, 2025-07-19), Video_ID 842 appears twice (2025-11-03). Re-upload attempts not deduplicated.' },
    { table: 'created_assets', check: 'DUPLICATE_PK', column: 'Asset_ID', count: 4, severity: 'Critical', message: '4 duplicate Asset_IDs detected: 12045, 23891, 34567, 45012. Caused by parallel pipeline runs on the same Video_ID.' },
    { table: 'published_posts', check: 'DUPLICATE_PK', column: 'Post_ID', count: 1, severity: 'Critical', message: 'Post_ID 1847 appears twice - one Facebook, one Instagram entry with identical Post_ID due to batch publish bug.' },
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
    { table: 'raw_videos', check: 'UNKNOWN_VALUE', column: 'Input_Type', count: 18, severity: 'Info', message: '18 raw_videos have Input_Type "Unknown" - content classifier returned low confidence (<0.3).' },
    { table: 'users', check: 'UNKNOWN_VALUE', column: 'Client_Name', count: 12, severity: 'Info', message: '12 users have Client_Name "Unknown". System/admin accounts not associated with specific clients.' },
    { table: 'created_assets', check: 'UNKNOWN_VALUE', column: 'Output_Type', count: 15, severity: 'Warning', message: '15 created_assets have Output_Type "Unknown". Fallback value when pipeline classification step was skipped.' },
    { table: 'post_distribution', check: 'UNKNOWN_VALUE', column: 'Published_Platform', count: 8, severity: 'Info', message: '8 post_distribution rows have Published_Platform "Unknown". Cross-posting entries where target platform was not resolved.' },
    { table: 'raw_videos', check: 'UNKNOWN_VALUE', column: 'Language', count: 7, severity: 'Info', message: '7 raw_videos have Language "Unknown". Mixed-language content where detector could not determine primary language.' },
  ],
  total: 29,
  limit: 200,
  offset: 0,
};

// ── Quality score 90-day rolling trend ──
const QUALITY_TREND_90D = [
  87.1, 87.8, 88.5, 89.6, 90.4, 91.2, 91.8, 91.5, 90.9, 90.2,
  89.6, 88.8, 87.9, 87.0, 86.0, 85.2, 84.5, 83.8, 83.4, 83.1,
  83.3, 83.6, 84.2, 85.0, 85.8, 86.6, 87.3, 87.8, 88.3, 88.8,
  89.3, 89.8, 90.3, 90.7, 91.0, 91.4, 91.8, 92.0, 91.6, 91.2,
  90.8, 90.5, 90.0, 89.6, 89.1, 88.6, 88.2, 87.9, 87.5, 87.3,
];

// ── Color maps ──
const CHECK_COLOR_MAP = {
  NULL_VIOLATION: { color: 'text-red-400', bg: 'bg-red-500/10', hex: '#ef4444', icon: AlertTriangle, label: 'NULL Violation', description: 'Required fields (IDs, dates, durations) that are empty. Every mandatory column is scanned per table.' },
  DUPLICATE_PK: { color: 'text-orange-400', bg: 'bg-orange-500/10', hex: '#f97316', icon: Copy, label: 'Duplicate PK', description: 'Same primary key appearing more than once - usually from parallel pipeline runs or failed dedup.' },
  FK_VIOLATION: { color: 'text-amber-400', bg: 'bg-amber-500/10', hex: '#f59e0b', icon: Unlink, label: 'FK Violation', description: 'Records referencing a parent row that no longer exists - e.g. a video linked to a deleted user.' },
  NEGATIVE_VALUE: { color: 'text-violet-400', bg: 'bg-violet-500/10', hex: '#8b5cf6', icon: MinusCircle, label: 'Negative Value', description: 'Duration or count columns with values below zero - bad entries from failed uploads or encoding errors.' },
  INVALID_DATE: { color: 'text-blue-400', bg: 'bg-blue-500/10', hex: '#3b82f6', icon: CalendarX, label: 'Invalid Date', description: 'Dates not matching YYYY-MM-DD, before 2020, or in the future. Often from legacy CSV imports.' },
  UNKNOWN_VALUE: { color: 'text-neutral-400', bg: 'bg-neutral-500/10', hex: '#9ca3af', icon: HelpCircle, label: 'Unknown Value', description: 'Dimension fields containing "Unknown", "N/A", "None", or empty strings - unclassified content.' },
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

const QUALITY_FORMULA_REFERENCE = [
  {
    id: '1',
    title: 'Health Score (Overview Ring)',
    formula: 'Health Score = (1 - (Total Issues / Total Rows Across All Tables)) x 100',
    details: [
      'Total Issues = NULL Violations + Duplicate PKs + FK Violations + Negative Values + Invalid Dates + Unknown Values + Suspicious Users + Dead Ends',
      'Total Rows = COUNT(raw_videos) + COUNT(created_assets) + COUNT(published_posts) + COUNT(post_distribution) + COUNT(users) + COUNT(channels) + COUNT(raw_video_channel) + COUNT(clients)',
    ],
  },
  {
    id: '2',
    title: 'Per-Table Health (Inner Ring)',
    formula: 'Table Health = (1 - (Issues in Table / Rows in Table)) x 100',
    details: [
      'Example: raw_videos Health = (1 - (issues in raw_videos / COUNT(raw_videos))) x 100',
    ],
  },
  {
    id: '3',
    title: 'NULL Violation Count',
    formula: 'For each required column: COUNT(*) WHERE column IS NULL',
    details: [
      'Required columns: raw_videos(Video_ID, User_ID, Uploaded_Date, Uploaded_Duration), created_assets(Asset_ID, Video_ID, Created_Date, Created_Duration), published_posts(Post_ID, Asset_ID, Published_Date, Published_Duration), post_distribution(Distribution_ID, Post_ID, Platform), users(User_ID, Name, Email, Team_Name), channels(Channel_Name), raw_video_channel(Video_ID, Channel_Name), clients(Client_ID)',
    ],
  },
  {
    id: '4',
    title: 'Duplicate PK Count',
    formula: 'Duplicate PKs = COUNT(*) - COUNT(DISTINCT primary_key)',
    details: [
      'Applied per table (Video_ID, Asset_ID, Post_ID, Distribution_ID, User_ID).',
    ],
  },
  {
    id: '5',
    title: 'FK Violation Count (Orphans)',
    formula: 'LEFT JOIN child to parent; count rows WHERE parent PK IS NULL AND child FK IS NOT NULL',
    details: [
      'users -> raw_videos, raw_videos -> created_assets, created_assets -> published_posts, published_posts -> post_distribution, channels -> raw_video_channel, raw_videos -> raw_video_channel',
      'Total Orphans = sum of all relationship-level orphan counts.',
    ],
  },
  {
    id: '6',
    title: 'Negative Value Count',
    formula: 'For each numeric column: COUNT(*) WHERE column < 0',
    details: [
      'Columns tracked: Uploaded_Duration/Count, Created_Duration/Count, Published_Duration/Count.',
    ],
  },
  {
    id: '7',
    title: 'Invalid Date Count',
    formula: "COUNT(*) WHERE date NOT matching 'YYYY-MM-DD' OR date < '2020-01-01' OR date > CURRENT_DATE + 1 day",
    details: [
      'Applied on Uploaded_Date, Created_Date, Published_Date.',
    ],
  },
  {
    id: '8',
    title: 'Unknown Value Count',
    formula: "COUNT(*) WHERE LOWER(column) IN ('unknown', 'n/a', 'none', 'null', '')",
    details: [
      'Dimension columns: raw_videos(Input_Type, Language), users(Team_Name, Email), channels(Channel_Name), post_distribution(Platform).',
    ],
  },
  {
    id: '9',
    title: 'Contamination Rate',
    formula: 'Contamination % = (Unknown Values + NULL Violations in dimension columns) / Total Dimension Cell Count x 100',
    details: [
      'Total Dimension Cell Count = (rows raw_videos x 2) + (rows users x 2) + (rows post_distribution x 1) + (rows channels x 1).',
    ],
  },
  {
    id: '10',
    title: 'Contamination Heatmap Cell',
    formula: "Cell % = COUNT(NULL or unknown-like values in table.column) / COUNT(*) from table x 100",
    details: [
      "Unknown-like values include: 'unknown', 'n/a', 'none', ''.",
    ],
  },
  {
    id: '11',
    title: 'Dead End Detection',
    formula: 'Dead End if SUM(Uploaded_Count) > 0 AND SUM(Published_Count) = 0 for a dimension value',
    details: [
      'Applied across dimensions such as Language, Input_Type, Channel, Platform.',
    ],
  },
  {
    id: '12',
    title: 'Suspicious User Detection',
    formula: "Flag user if any rule matches: risky email keyword OR Created_Count > Uploaded_Count OR Uploaded_Count > 50 with Published_Count = 0 OR non-company email domain",
    details: [
      "Keywords: test, delete, mock, qa, dummy. Allowed domains: '@frammer.com', '@frammer.ai'.",
    ],
  },
  {
    id: '13',
    title: 'Quality Score Trend (90-Day)',
    formula: 'Daily Score = (1 - (issues detected that day / total rows that day)) x 100',
    details: [
      'Plot the last 90 daily values with a fixed 90% target line.',
    ],
  },
  {
    id: '14',
    title: 'Activity Logger Metrics (1h)',
    formula: "Total Ops = COUNT(*) where timestamp > NOW() - 1 hour; Inserts/Updates/Deletes/Errors are operation-level filtered counts in same window",
    details: [
      "Inserts: operation='INSERT', Updates: operation='UPDATE', Deletes: operation='DELETE', Errors: status='ERROR'.",
    ],
  },
  {
    id: '15',
    title: 'Broken Reference Chain Visual Severity',
    formula: 'Link color: green(0), amber(1-10), red(>10); line thickness = MIN(12, MAX(2, orphan_count / 5))',
    details: [
      'Badge value shows exact orphan count per FK relationship.',
    ],
  },
  {
    id: '16',
    title: 'Issue Severity Classification',
    formula: 'Critical = duplicate PK or critical FK/suspicious-user conditions; Warning = NULL-required/negative/FK non-critical; Info = unknown, parseable invalid date, low-volume dead ends',
    details: [],
  },
];

const QUALITY_FORMULA_GUIDE = {
  '1': {
    math: 'Health % = (1 - issues/rows) x 100',
    definition: 'This is the overall data quality score.',
    instruction: 'If this drops, open issue types and see what increased.',
  },
  '2': {
    math: 'Table Health % = (1 - table_issues/table_rows) x 100',
    definition: 'This shows quality score for each table.',
    instruction: 'Find the lowest table score first and fix that table.',
  },
  '3': {
    math: 'NULL count = number of required blank cells',
    definition: 'Counts required fields that are blank.',
    instruction: 'Fix these first so records are complete.',
  },
  '4': {
    math: 'Duplicate IDs = total IDs - unique IDs',
    definition: 'Counts duplicate IDs that should be unique.',
    instruction: 'Treat this as high priority to avoid wrong reporting.',
  },
  '5': {
    math: 'Orphans = child rows with missing parent row',
    definition: 'Counts broken links between related tables.',
    instruction: 'Start with red links because they are the most severe.',
  },
  '6': {
    math: 'Negative count = values < 0',
    definition: 'Counts negative numbers where they should not exist.',
    instruction: 'Check data input and calculations for those fields.',
  },
  '7': {
    math: 'Invalid date count = wrong format or out-of-range date',
    definition: 'Counts dates that look wrong or out of range.',
    instruction: 'Standardize date format and block bad dates at input.',
  },
  '8': {
    math: 'Unknown count = blank/unknown/n-a/none values',
    definition: 'Counts placeholder values like Unknown or N/A.',
    instruction: 'Replace placeholders with real values where possible.',
  },
  '9': {
    math: 'Contamination % = bad dimension cells/total dimension cells x 100',
    definition: 'Shows how much key text data is blank or placeholder.',
    instruction: 'Lower contamination to improve dashboard trust.',
  },
  '10': {
    math: 'Cell % = bad cells in this column/table rows x 100',
    definition: 'Shows contamination by table and column.',
    instruction: 'Start cleanup from the darkest cells.',
  },
  '11': {
    math: 'Dead end = uploads > 0 and published = 0',
    definition: 'Finds paths where uploads happen but nothing gets published.',
    instruction: 'Use this to find workflow bottlenecks.',
  },
  '12': {
    math: 'Flag if any rule is true (rule1 OR rule2 OR rule3 OR rule4)',
    definition: 'Flags accounts with unusual behavior.',
    instruction: 'Review critical accounts first.',
  },
  '13': {
    math: 'Daily quality % = (1 - daily_issues/daily_rows) x 100',
    definition: 'Shows quality trend over the last 90 days.',
    instruction: 'Watch long-term direction, not single-day spikes.',
  },
  '14': {
    math: '1h counts = operations in last 1 hour',
    definition: 'Shows recent system activity and errors.',
    instruction: 'Use this during monitoring and troubleshooting.',
  },
  '15': {
    math: 'Line width = min(12, max(2, orphans/5))',
    definition: 'Visual style (color/thickness) shows how bad broken links are.',
    instruction: 'Use color and thickness to prioritize quickly.',
  },
  '16': {
    math: 'Priority order = Critical > Warning > Info',
    definition: 'Groups issues by importance: Critical, Warning, Info.',
    instruction: 'Fix in this order: Critical, then Warning, then Info.',
  },
};

function FormulaReferenceTooltip() {
  return (
    <div className="space-y-2.5">
      <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber-400">Data Quality Help Guide</div>
      <p className="text-[11px] leading-relaxed text-neutral-300">
        Quick explanation of each metric in simple language.
      </p>
      <div className="space-y-2">
        {QUALITY_FORMULA_REFERENCE.map((item) => (
          <div key={item.id} className="rounded-lg border border-neutral-800/70 bg-[#090909] p-2.5">
            <div className="text-[10px] font-bold uppercase tracking-[0.08em] text-neutral-200">
              {item.id}. {item.title}
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-amber-300">
              <span className="font-semibold text-amber-200">Math:</span>{' '}
              {QUALITY_FORMULA_GUIDE[item.id]?.math}
            </p>
            <p className="mt-1.5 text-[10px] leading-relaxed text-neutral-300">
              <span className="font-semibold text-neutral-200">Definition:</span>{' '}
              {QUALITY_FORMULA_GUIDE[item.id]?.definition}
            </p>
            <p className="mt-1 text-[10px] leading-relaxed text-neutral-400">
              <span className="font-semibold text-neutral-300">Instruction:</span>{' '}
              {QUALITY_FORMULA_GUIDE[item.id]?.instruction}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Shared components ──
const Panel = ({ children, className = '' }) => (
  <div className={`rounded-2xl border border-neutral-800 bg-[#0D0D0D] p-5 transition-all duration-200 hover:border-neutral-700 ${className}`}>{children}</div>
);

const Badge = ({ children, className = '' }) => (
  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${className}`}>{children}</span>
);

function FormulaInfoButton({
  tooltip,
  ariaLabel = 'Formula details',
  align = 'right',
  widthClass = 'w-[min(22rem,calc(100vw-2rem))]',
  buttonClassName = '',
  tooltipClassName = '',
}) {
  const [open, setOpen] = useState(false);
  const closeTimerRef = useRef(null);
  const alignmentClass = align === 'left'
    ? 'left-0'
    : align === 'center'
      ? 'left-1/2 -translate-x-1/2'
      : 'right-0';

  const clearCloseTimer = () => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  };

  const openTooltip = () => {
    clearCloseTimer();
    setOpen(true);
  };

  const closeTooltipWithDelay = () => {
    clearCloseTimer();
    closeTimerRef.current = setTimeout(() => setOpen(false), 160);
  };

  useEffect(() => {
    return () => clearCloseTimer();
  }, []);

  return (
    <div
      className="relative inline-flex"
      onFocusCapture={openTooltip}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        onMouseEnter={openTooltip}
        onMouseLeave={closeTooltipWithDelay}
        onFocus={openTooltip}
        className={`inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-700 bg-neutral-900 text-[9px] font-black tracking-tight text-neutral-300 transition-colors duration-200 hover:border-amber-500/60 hover:text-amber-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/20 ${buttonClassName}`}
      >
        <span className="leading-none">fx</span>
      </button>
      <div
        onMouseEnter={openTooltip}
        onMouseLeave={closeTooltipWithDelay}
        className={`absolute top-full z-50 mt-2 max-w-[calc(100vw-2rem)] rounded-xl border border-neutral-700 bg-[#0d0d0d] p-4 shadow-2xl transition-all duration-150 ${alignmentClass} ${widthClass} break-words whitespace-normal text-[11px] leading-relaxed text-neutral-300 ${tooltipClassName} ${
          open ? 'pointer-events-auto translate-y-0 opacity-100' : 'pointer-events-none translate-y-1 opacity-0'
        }`}
      >
        {tooltip}
      </div>
    </div>
  );
}

function FlipCard({ front, back, className = '' }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <div
      className={`relative overflow-hidden ${className}`}
      style={{ perspective: '900px' }}
      onMouseEnter={() => setFlipped(true)}
      onMouseLeave={() => setFlipped(false)}
    >
      {/* Invisible spacer - keeps the card's natural height in the grid */}
      <div aria-hidden className="invisible pointer-events-none">{front}</div>
      {/* Flip wrapper - absolutely fills the card */}
      <div style={{ transformStyle: 'preserve-3d', transition: 'transform 0.42s cubic-bezier(0.4,0,0.2,1)', transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)', position: 'absolute', inset: 0 }}>
        <div style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden', position: 'absolute', inset: 0 }}>
          {front}
        </div>
        <div style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden', transform: 'rotateY(180deg)', position: 'absolute', inset: 0 }}>
          {back}
        </div>
      </div>
    </div>
  );
}

// ── Quality Score Trend - Chart.js area chart ──
const TREND_LABELS = QUALITY_TREND_90D.map((_, i) => {
  const daysAgo = QUALITY_TREND_90D.length - 1 - i;
  return daysAgo === 0 ? 'Today' : daysAgo % 15 === 0 ? `${daysAgo}d ago` : '';
});

const TREND_CHART_DATA = {
  labels: TREND_LABELS,
  datasets: [{
    label: 'Quality Score',
    data: QUALITY_TREND_90D,
    borderColor: '#10b981',
    backgroundColor: (ctx) => {
      const canvas = ctx.chart.ctx;
      const { chartArea } = ctx.chart;
      if (!chartArea) return 'rgba(16,185,129,0.15)';
      const gradient = canvas.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
      gradient.addColorStop(0, 'rgba(16,185,129,0.35)');
      gradient.addColorStop(1, 'rgba(16,185,129,0.01)');
      return gradient;
    },
    borderWidth: 2,
    tension: 0.4,
    fill: true,
    pointRadius: 0,
    pointHoverRadius: 4,
    pointHoverBackgroundColor: '#10b981',
    pointHoverBorderColor: '#fff',
    pointHoverBorderWidth: 2,
  }],
};

const TREND_CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 600 },
  interaction: { mode: 'index', intersect: false },
  hover: { mode: 'index', intersect: false },
  layout: { padding: { top: 20 } },
  plugins: {
    legend: { display: false },
    tooltip: {
      enabled: true,
      backgroundColor: 'rgba(15,15,15,0.97)',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      titleColor: '#a3a3a3',
      bodyColor: '#ffffff',
      padding: 12,
      boxPadding: 4,
      displayColors: false,
      callbacks: {
        title: (items) => items[0]?.label || '',
        label: (ctx) => `Quality Score: ${ctx.parsed.y.toFixed(1)}%`,
        afterLabel: (ctx) => {
          const v = ctx.parsed.y;
          if (v >= 90) return '  ✓ Above target';
          return `  ↓ ${(90 - v).toFixed(1)}% below target`;
        },
      },
    },
    annotation: {
      annotations: {
        targetLine: {
          type: 'line',
          yMin: 90,
          yMax: 90,
          borderColor: '#f59e0b',
          borderWidth: 1.5,
          borderDash: [8, 5],
          label: {
            display: true,
            content: '90% Target',
            position: 'start',
            xAdjust: 6,
            yAdjust: -12,
            backgroundColor: 'transparent',
            color: '#f59e0b',
            font: { size: 11, weight: 'bold' },
            padding: 0,
          },
        },
      },
    },
  },
  scales: {
    x: {
      ticks: { color: '#525252', font: { size: 10 }, maxRotation: 0 },
      grid: { color: 'rgba(255,255,255,0.03)' },
      border: { display: false },
    },
    y: {
      min: 78,
      max: 97,
      ticks: { color: '#525252', font: { size: 10 }, callback: (v) => `${v}%`, stepSize: 2 },
      grid: { color: 'rgba(255,255,255,0.04)' },
      border: { display: false },
    },
  },
};

function QualityTrendsChart() {
  return (
    <div className="flex flex-col h-full">
      <div className="mb-3 flex items-center gap-2">
        <TrendingUp className="h-3.5 w-3.5 text-emerald-400" strokeWidth={2.5} />
        <span className="text-sm font-bold text-white">Quality Score Trend</span>
        <FormulaInfoButton
          ariaLabel="Quality score trend formula"
          align="left"
          widthClass="w-[min(24rem,calc(100vw-2rem))]"
          tooltip={
            <InfoTooltipContent
              eyebrow="How This Works"
              summary="This chart shows whether data quality is getting better or worse."
              bullets={[
                { label: 'Simple math', text: 'Quality % = (1 - issues/rows) x 100' },
                { label: 'Higher is better', text: 'A higher score means fewer data issues.' },
                { label: 'Time range', text: 'You are seeing the last 90 days.' },
                { label: 'Target', text: 'The dashed line is the quality goal (90%).' },
              ]}
            />
          }
        />
        <span className="ml-1 text-[10px] text-neutral-500">90-day rolling average against 90% target</span>
      </div>
      <div className="flex-1 min-h-0" style={{ minHeight: 200 }}>
        <Line data={TREND_CHART_DATA} options={TREND_CHART_OPTIONS} />
      </div>
    </div>
  );
}

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
            <div key={tbl} className="group flex items-center gap-1.5 text-[12px] text-neutral-500 transition-colors hover:text-neutral-300" title={`${tbl}: ${tScore.toFixed(1)}% - ${info.row_count?.toLocaleString()} rows, ${info.issue_count} issues`}>
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
const FK_DESCRIPTIONS = {
  'users→raw_videos': { key: 'User_ID', desc: 'Raw videos referencing a User_ID that no longer exists in the users table.' },
  'raw_videos→created_assets': { key: 'Video_ID', desc: 'Created assets referencing a Video_ID that no longer exists in raw_videos.' },
  'created_assets→published_posts': { key: 'Asset_ID', desc: 'Published posts referencing an Asset_ID that no longer exists in created_assets.' },
  'published_posts→post_distribution': { key: 'Post_ID', desc: 'Post distributions referencing a Post_ID that no longer exists in published_posts.' },
  'channels→raw_video_channel': { key: 'Channel_Name', desc: 'Video-channel mappings referencing a Channel_Name not found in channels.' },
  'raw_videos→raw_video_channel': { key: 'Video_ID', desc: 'Video-channel mappings referencing a Video_ID not found in raw_videos.' },
  'clients→users': { key: 'Client_ID', desc: 'Users referencing a Client_ID that no longer exists in the clients table.' },
};

function OrphanFlowDiagram({ links }) {
  const [tooltip, setTooltip] = useState(null);

  const nodes = [
    { id: 'clients', x: 20, y: 35 },
    { id: 'users', x: 20, y: 135 },
    { id: 'channels', x: 20, y: 235 },
    { id: 'raw_videos', x: 180, y: 85 },
    { id: 'raw_video_channel', x: 180, y: 235 },
    { id: 'created_assets', x: 340, y: 85 },
    { id: 'published_posts', x: 500, y: 85 },
    { id: 'post_distribution', x: 500, y: 185 },
  ];

  const linkData = (links || []).map(l => ({
    ...l,
    color: l.orphans === 0 ? '#10b981' : l.orphans <= 10 ? '#f59e0b' : '#ef4444',
  }));

  const handleBadgeEnter = (e, link, mx, my) => {
    const svg = e.target.closest('svg');
    const pt = svg.createSVGPoint();
    pt.x = mx; pt.y = my;
    const screenPt = pt.matrixTransform(svg.getScreenCTM());
    const container = svg.parentElement.getBoundingClientRect();
    const fkKey = `${link.from}→${link.to}`;
    const info = FK_DESCRIPTIONS[fkKey];
    setTooltip({
      x: screenPt.x - container.left,
      y: screenPt.y - container.top,
      from: link.from.replaceAll('_', ' '),
      to: link.to.replaceAll('_', ' '),
      orphans: link.orphans,
      joinKey: info?.key || 'FK',
      desc: info?.desc || `${link.orphans} orphan records between ${link.from} and ${link.to}.`,
      color: link.color,
    });
  };

  return (
    <div className="relative h-full min-h-[256px] w-full overflow-hidden rounded-xl border border-neutral-800/60 bg-[#080808]">
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
              {link.orphans > 0 && (
                <g
                  className="cursor-pointer"
                  onMouseEnter={(e) => handleBadgeEnter(e, link, mx, my)}
                  onMouseLeave={() => setTooltip(null)}
                >
                  <circle cx={mx} cy={my} r="13" fill="#0D0D0D" stroke={link.color} strokeWidth="2" />
                  <text x={mx} y={my} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize="10" fontWeight="bold">{link.orphans}</text>
                  {/* Invisible larger hit area */}
                  <circle cx={mx} cy={my} r="20" fill="transparent" />
                </g>
              )}
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

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-50 w-56 rounded-xl border border-neutral-700 bg-[#111111] p-3 shadow-xl shadow-black/50"
          style={{ left: tooltip.x, top: tooltip.y - 8, transform: 'translate(-50%, -100%)' }}
        >
          <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold text-neutral-200">
            <span className="inline-block h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: tooltip.color }} />
            {tooltip.from} &rarr; {tooltip.to}
          </div>
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded-md bg-neutral-800 px-1.5 py-0.5 text-[10px] font-mono text-neutral-400">FK: {tooltip.joinKey}</span>
            <span className="text-[11px] font-bold" style={{ color: tooltip.color }}>{tooltip.orphans} orphan{tooltip.orphans !== 1 ? 's' : ''}</span>
          </div>
          <p className="text-[10px] leading-relaxed text-neutral-400">{tooltip.desc}</p>
          <div className="absolute left-1/2 bottom-0 -translate-x-1/2 translate-y-full">
            <div className="h-0 w-0 border-l-[6px] border-r-[6px] border-t-[6px] border-transparent border-t-neutral-700" />
          </div>
        </div>
      )}

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
    if (val === null || val === undefined) return 'bg-neutral-900/20 text-neutral-400';
    if (val === 0) return 'bg-emerald-900/25 text-emerald-400';
    if (val < 10) return 'bg-amber-900/25 text-amber-400';
    return 'bg-red-900/30 text-red-400 font-bold';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="p-2 text-left text-[10px] font-bold uppercase tracking-wider text-neutral-400">Table \ Column</th>
            {cols.map(c => <th key={c} className="p-2 text-center text-[10px] font-bold uppercase tracking-wider text-neutral-400">{c}</th>)}
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
        <td className="p-3"><ChevronRight className={`h-4 w-4 text-neutral-400 transition-transform duration-200 ${open ? 'rotate-90' : ''}`} /></td>
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
export default function DataQualityModule({ authUser }) {
  const role = authUser?.role || 'website_admin';
  const isUser         = role === 'user';
  const isClientAdmin  = role === 'client_admin';
  const isAdmin        = role === 'website_admin';
  const [subTab, setSubTab] = useState('overview');
  const [filterTable, setFilterTable] = useState('');
  const [filterCheck, setFilterCheck] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [useLiveData, setUseLiveData] = useState(false);
  const [liveOverview, setLiveOverview] = useState(null);
  const [liveIssues, setLiveIssues] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState(null);

  useEffect(() => {
    if (!useLiveData) return;
    setLiveLoading(true);
    setLiveError(null);
    const token = localStorage.getItem('frammer_auth_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    Promise.all([
      fetch(`${API_BASE}/data-quality`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/data-quality/issues?limit=200`, { headers }).then(r => r.json()),
    ])
      .then(([overview, issues]) => {
        setLiveOverview(overview);
        setLiveIssues(issues);
      })
      .catch(err => setLiveError(err.message || 'Failed to load live data'))
      .finally(() => setLiveLoading(false));
  }, [useLiveData]);

  const data = (useLiveData && liveOverview) ? liveOverview : QUALITY_OVERVIEW;
  const issuesSource = (useLiveData && liveIssues) ? liveIssues.issues : QUALITY_ISSUES.issues;
  const issuesTotal = (useLiveData && liveIssues) ? liveIssues.total : QUALITY_ISSUES.total;

  const filteredIssues = useMemo(() => {
    let items = issuesSource;
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
  }, [issuesSource, filterTable, filterCheck, searchTerm]);

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
    { label: 'Total Issues', value: (data.total_issues ?? 0).toLocaleString(), sub: `across ${Object.keys(data.table_scores || {}).length} tables`, icon: AlertTriangle, iconBg: 'bg-red-500/10', iconColor: 'text-red-400', valueColor: 'text-red-400', accentColor: 'bg-red-500', description: 'Sum of all data problems - NULLs, duplicates, broken FKs, negatives, bad dates, and unknowns across all tables.' },
    { label: 'Orphan Records', value: totalOrphans.toLocaleString(), sub: 'broken FK references', icon: Link2Off, iconBg: 'bg-amber-500/10', iconColor: 'text-amber-400', valueColor: 'text-amber-400', accentColor: 'bg-amber-500', description: 'Child records whose parent row was deleted - broken links from users to videos to assets down the chain.' },
    { label: 'Contamination', value: `${avgContam}%`, sub: 'NULL & Unknown values', icon: Gauge, iconBg: 'bg-violet-500/10', iconColor: 'text-violet-400', valueColor: 'text-violet-400', accentColor: 'bg-violet-500', description: 'Share of dimension fields containing NULL or placeholders like "Unknown" and "N/A" across type, language, team, and platform.' },
    { label: 'Dead Ends', value: totalDeadEnds, sub: 'zero-publish paths', icon: RouteOff, iconBg: 'bg-neutral-500/10', iconColor: 'text-neutral-400', valueColor: 'text-neutral-300', accentColor: 'bg-neutral-500', description: 'Content paths where uploads happened but nothing was published - segments stuck in the pipeline.' },
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
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white">Data Quality & Governance</h2>
              <FormulaInfoButton
                ariaLabel="Complete data quality formula reference"
                align="left"
                widthClass="w-[min(34rem,calc(100vw-2rem))]"
                buttonClassName="h-5 w-5"
                tooltipClassName="max-h-[72vh] overflow-y-auto"
                tooltip={<FormulaReferenceTooltip />}
              />
            </div>
            <p className="text-[11px] text-neutral-500">Monitor integrity, debug pipelines, and ensure clean analytics.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Live data toggle */}
          <button
            onClick={() => setUseLiveData(v => !v)}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold transition-all duration-200 ${
              useLiveData
                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                : 'border-neutral-700 bg-[#0D0D0D] text-neutral-500 hover:border-neutral-600 hover:text-neutral-300'
            }`}
          >
            {liveLoading
              ? <Loader2 size={11} className="animate-spin" />
              : <span className={`h-1.5 w-1.5 rounded-full ${useLiveData ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-neutral-600'}`} />
            }
            {useLiveData ? 'Live' : 'Demo'}
          </button>

          <div className="flex gap-1 rounded-full border border-neutral-800 bg-[#0D0D0D] p-1">
            {[
              { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={13} /> },
              ...(!isUser ? [{ id: 'issues', label: 'Issue Explorer', icon: <Search size={13} /> }] : []),
            ].map(t => (
              <button key={t.id} onClick={() => setSubTab(t.id)} className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all duration-200 ${subTab === t.id ? 'bg-[#1a1a1a] text-white shadow-sm' : 'text-neutral-500 hover:text-neutral-200'}`}>
                {t.icon}{t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Role-scoped notice */}
      {isUser && (
        <div className="border-b border-indigo-900/40 bg-indigo-950/20 px-6 py-2 text-xs text-indigo-400">
          Showing data quality metrics scoped to your uploads.
        </div>
      )}
      {isClientAdmin && (
        <div className="border-b border-neutral-900/40 bg-[#080808] px-6 py-2 text-xs text-neutral-500">
          Showing data quality for your client workspace.
        </div>
      )}

      {/* Live data error banner */}
      {useLiveData && liveError && (
        <div className="border-b border-red-900/40 bg-red-950/20 px-6 py-2 text-xs text-red-400">
          Failed to load live data: {liveError}. Showing demo data.
        </div>
      )}

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

            {/* Health ring + KPI cards - flat 5-col grid, ring spans 2 rows */}
            <div className="grid gap-3 lg:grid-cols-5" style={{ gridTemplateColumns: 'repeat(5, minmax(0,1fr))', gridAutoRows: '1fr' }}>
              {/* Health ring - 1 col wide, spans 2 rows */}
              <FlipCard
                className="row-span-2 rounded-2xl border border-neutral-800 bg-[#0D0D0D]"
                front={
                  <div className="flex h-full items-center justify-center p-3">
                    <HealthRing score={data.overall_score ?? 0} tableScores={data.table_scores || {}} />
                  </div>
                }
                back={
                  <div className="flex h-full flex-col justify-center rounded-2xl bg-[#0D0D0D] p-5">
                    <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.15em] text-emerald-400">Health Score</div>
                    <p className="text-[14px] leading-relaxed text-neutral-400">
                      Share of clean rows across all 8 tables - issues divided by row count, subtracted from 100%.
                    </p>
                    <p className="mt-2 text-[14px] leading-relaxed text-neutral-400">
                      Inner ring shows per-table scores based on the same formula.
                    </p>
                  </div>
                }
              />

              {/* Row 1: 4 summary KPI cards */}
              {kpiCards.map(kpi => {
                const KpiIcon = kpi.icon;
                return (
                  <FlipCard
                    key={kpi.label}
                    className="rounded-2xl border border-neutral-800 bg-[#0D0D0D]"
                    front={
                      <div className="relative h-full p-3">
                        <div className={`absolute left-0 top-0 h-0.5 w-full ${kpi.accentColor} opacity-40`} />
                        <div className="flex h-full items-start justify-between">
                          <div className="min-w-0">
                            <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-neutral-500">{kpi.label}</div>
                            <div className={`mt-1.5 text-[40px] font-black tracking-tight leading-none ${kpi.valueColor}`}>{kpi.value}</div>
                            <div className="mt-1.5 text-[14px] text-neutral-400">{kpi.sub}</div>
                          </div>
                          <div className={`shrink-0 rounded-lg ${kpi.iconBg} p-2`}>
                            <KpiIcon className={`h-4 w-4 ${kpi.iconColor} opacity-60`} />
                          </div>
                        </div>
                      </div>
                    }
                    back={
                      <div className="flex h-full flex-col justify-center rounded-2xl bg-[#0D0D0D] p-4">
                        <div className={`mb-2 text-[11px] font-bold uppercase tracking-[0.15em] ${kpi.valueColor}`}>{kpi.label}</div>
                        <p className="text-[14px] leading-relaxed text-neutral-400 line-clamp-3">{kpi.description}</p>
                      </div>
                    }
                  />
                );
              })}

              {/* Row 2: 4 check-type cards */}
              {['NULL_VIOLATION', 'NEGATIVE_VALUE', 'INVALID_DATE', 'UNKNOWN_VALUE'].map(key => {
                const conf = CHECK_COLOR_MAP[key];
                const Icon = conf.icon;
                const cnt = checks[key] || 0;
                return (
                  <FlipCard
                    key={key}
                    className="rounded-2xl border border-neutral-800 bg-[#0D0D0D]"
                    front={
                      <div className="flex h-full items-start justify-between p-3">
                        <div className="min-w-0">
                          <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-neutral-500">{conf.label}</div>
                          <div className={`mt-1.5 text-[40px] font-black tracking-tight leading-none ${conf.color}`}>{cnt}</div>
                          <div className="mt-1.5 text-[13px] text-neutral-400">issues detected</div>
                        </div>
                        <div className={`shrink-0 rounded-lg ${conf.bg} p-2`}>
                          <Icon className={`h-4 w-4 ${conf.color} opacity-60`} />
                        </div>
                      </div>
                    }
                    back={
                      <div className="flex h-full flex-col justify-center rounded-2xl bg-[#0D0D0D] p-4">
                        <div className={`mb-2 text-[11px] font-bold uppercase tracking-[0.15em] ${conf.color}`}>{conf.label}</div>
                        <p className="text-[14px] leading-relaxed text-neutral-400 line-clamp-3">{conf.description}</p>
                      </div>
                    }
                  />
                );
              })}
            </div>

            {/* Heatmap + Orphan flow - admin/client_admin only */}
            {!isUser && <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.4fr_1fr] xl:items-stretch">
              <Panel>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-white">
                    <div className="rounded-lg bg-violet-500/10 p-1.5"><HelpCircle className="h-3.5 w-3.5 text-violet-400" /></div>
                    Value Contamination Matrix
                    <FormulaInfoButton
                      ariaLabel="Contamination formulas"
                      align="left"
                      widthClass="w-[min(24rem,calc(100vw-2rem))]"
                      tooltip={
                        <InfoTooltipContent
                          eyebrow="How This Works"
                          summary="Contamination means important text fields are blank or generic values."
                          bullets={[
                            { label: 'Simple math', text: 'Contamination % = bad cells/total cells x 100' },
                            { label: 'Examples', text: "Blank, Unknown, N/A, None." },
                            { label: 'Cell value', text: 'Shows what percent of rows are bad in that column.' },
                            { label: 'What to do', text: 'Start cleaning columns with the highest percentages.' },
                          ]}
                        />
                      }
                    />
                  </h3>
                  <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">% of "Unknown" or NULL values</span>
                </div>
                <ContaminationHeatmap rows={data.heatmap} />
              </Panel>
              <Panel className="flex flex-col">
                <div className="mb-4 flex items-center justify-between shrink-0">
                  <h3 className="flex items-center gap-2 text-sm font-bold text-white">
                    <div className="rounded-lg bg-amber-500/10 p-1.5"><Unlink className="h-3.5 w-3.5 text-amber-400" /></div>
                    Broken Reference Chains
                    <FormulaInfoButton
                      ariaLabel="Foreign key orphan formulas"
                      align="left"
                      widthClass="w-[min(24rem,calc(100vw-2rem))]"
                      tooltip={
                        <InfoTooltipContent
                          eyebrow="How This Works"
                          summary="This map shows broken parent-child links (orphans)."
                          bullets={[
                            { label: 'Simple math', text: 'Orphans = child rows with missing parent rows' },
                            { label: 'Broken link', text: 'A child row points to a parent row that does not exist.' },
                            { label: 'Colors', text: 'Green is good, amber needs attention, red is urgent.' },
                            { label: 'Thickness', text: 'Thicker lines mean more broken records.' },
                          ]}
                        />
                      }
                    />
                  </h3>
                  <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">Foreign Key Violations</span>
                </div>
                <div className="flex flex-1 items-center">
                  <OrphanFlowDiagram links={data.orphan_links} />
                </div>
              </Panel>
            </div>}

            {/* Check breakdown + Dead Ends + Suspicious Users */}

            <div className={`grid grid-cols-1 gap-5 xl:h-[500px] ${isAdmin ? 'xl:grid-cols-[1.2fr_0.9fr_0.9fr]' : 'xl:grid-cols-[1.2fr_0.9fr]'}`}>

              {/* Column 1: Quality Score Trends */}
              <Panel className="flex flex-col overflow-hidden">
                <QualityTrendsChart />
              </Panel>

              <Panel className="flex flex-col overflow-hidden !border-amber-900/20 !bg-[#0d0b08]">
                <div className="mb-3 flex items-center gap-2">
                  <div className="rounded-lg bg-amber-500/10 p-1.5"><RouteOff className="h-3.5 w-3.5 text-amber-400" /></div>
                  <h3 className="text-sm font-bold text-white">Dead End Paths</h3>
                  <FormulaInfoButton
                    ariaLabel="Dead end detection formula"
                    align="left"
                    widthClass="w-[min(24rem,calc(100vw-2rem))]"
                    tooltip={
                      <InfoTooltipContent
                        eyebrow="How This Works"
                        summary="Dead ends are paths where content gets uploaded but never published."
                        bullets={[
                          { label: 'Simple math', text: 'Dead end = uploads > 0 and published = 0' },
                          { label: 'Meaning', text: 'Work started, but no output reached publish.' },
                          { label: 'Where checked', text: 'Language, input type, channel, platform, and more.' },
                          { label: 'Card count', text: 'Total number of blocked paths.' },
                        ]}
                      />
                    }
                  />
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
                            <span className="shrink-0 text-[11px] text-neutral-400">{item.uploads}↑</span>
                            <span className="shrink-0 rounded-md bg-red-500/10 px-1.5 py-0.5 text-[10px] font-bold text-red-400">0 pub</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {Object.keys(deadEndGroups).length === 0 && (
                    <p className="py-4 text-center text-sm text-neutral-400">No dead ends found.</p>
                  )}
                </div>
              </Panel>

              {/*Suspicious Users - website_admin only */}
              {isAdmin && <Panel className="flex flex-col overflow-hidden !border-red-900/20 !bg-[#0d0808]">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
                  <div className="rounded-lg bg-pink-500/10 p-1.5"><UserX className="h-3.5 w-3.5 text-pink-400" /></div>
                  Suspicious Accounts
                  <FormulaInfoButton
                    ariaLabel="Suspicious user detection formulas"
                    align="left"
                    widthClass="w-[min(24rem,calc(100vw-2rem))]"
                    tooltip={
                      <InfoTooltipContent
                        eyebrow="How This Works"
                        summary="An account is flagged when any suspicious pattern is detected."
                        bullets={[
                          { label: 'Simple math', text: 'Flagged if any rule is true (rule1 OR rule2 OR rule3 OR rule4)' },
                          { label: 'Test-like account', text: 'Email looks like test or dummy usage.' },
                          { label: 'Impossible activity', text: 'Created count is higher than uploaded count.' },
                          { label: 'High effort, no result', text: 'Many uploads but no published output.' },
                          { label: 'Unapproved email', text: 'Email is outside allowed company domains.' },
                        ]}
                      />
                    }
                  />
                  <Badge className="ml-auto border border-red-500/20 bg-red-500/10 text-red-400">{(data.suspicious_users || []).length}</Badge>
                </h3>
                <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                  {(data.suspicious_users || []).map((user, i) => {
                    const sevClass = user.severity === 'Critical'
                      ? 'border-red-500/20 bg-red-500/10 text-red-400'
                      : user.severity === 'Warning'
                        ? 'border-amber-500/20 bg-amber-500/10 text-amber-400'
                        : 'border-blue-500/20 bg-blue-500/10 text-blue-400';
                    const cardBorder = user.severity === 'Critical'
                      ? 'border-red-900/30'
                      : user.severity === 'Warning'
                        ? 'border-amber-900/30'
                        : '';
                    return (
                      <div key={i} className={`rounded-xl border border-neutral-800/40 bg-[#0a0a0a] p-3 transition-all duration-200 hover:bg-[#111111] ${cardBorder}`}>
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
              </Panel>}
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
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
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
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
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
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-400">Table</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
                        <div className="flex items-center gap-1.5">
                          <span>Check Type</span>
                          <FormulaInfoButton
                            ariaLabel="Check type counting formulas"
                            align="left"
                            widthClass="w-[min(24rem,calc(100vw-2rem))]"
                            buttonClassName="h-4 w-4 border-neutral-600 bg-neutral-900/90 text-[8px]"
                            tooltip={
                              <InfoTooltipContent
                                eyebrow="How Counts Are Made"
                                summary="Each issue type has a simple rule."
                                bullets={[
                                  { label: 'Simple math', text: 'Count = number of rows matching that issue rule' },
                                  { label: 'NULL', text: 'Required field is blank.' },
                                  { label: 'Duplicate ID', text: 'An ID appears more than once.' },
                                  { label: 'Broken link', text: 'A related record is missing.' },
                                  { label: 'Negative value', text: 'A number is below zero when it should not be.' },
                                  { label: 'Invalid date', text: 'Date format or date range is not valid.' },
                                  { label: 'Unknown value', text: "Value is generic text like 'unknown' or 'n/a'." },
                                ]}
                              />
                            }
                          />
                        </div>
                      </th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-400">Column</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-400">Count</th>
                      <th className="border-b border-neutral-800/60 p-3 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
                        <div className="flex items-center gap-1.5">
                          <span>Severity</span>
                          <FormulaInfoButton
                            ariaLabel="Issue severity classification formula"
                            align="left"
                            widthClass="w-[min(24rem,calc(100vw-2rem))]"
                            buttonClassName="h-4 w-4 border-neutral-600 bg-neutral-900/90 text-[8px]"
                            tooltip={
                              <InfoTooltipContent
                                eyebrow="How Severity Is Set"
                                summary="Severity helps prioritize what to fix first."
                                bullets={[
                                  { label: 'Simple rule', text: 'Priority order is Critical > Warning > Info' },
                                  { label: 'Critical', text: 'High impact. Fix immediately.' },
                                  { label: 'Warning', text: 'Important issue. Fix soon.' },
                                  { label: 'Info', text: 'Low impact cleanup item.' },
                                ]}
                              />
                            }
                          />
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredIssues.map((issue, idx) => <IssueRow key={idx} issue={issue} />)}
                    {filteredIssues.length === 0 && (
                      <tr><td colSpan="6" className="p-8 text-center text-neutral-400">No issues found matching filters.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-neutral-800/60 bg-[#0a0a0a] px-4 py-3 text-sm text-neutral-500">
                <span>Showing <span className="font-semibold text-neutral-300">{filteredIssues.length}</span> of {issuesTotal} issues</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
