import React, { useCallback, useEffect, useRef, useState } from 'react';

const STATUS_COLORS = {
  SUCCESS: { bar: 'bg-emerald-500', badge: 'border-emerald-500/30 text-emerald-300 bg-emerald-500/10' },
  ERROR: { bar: 'bg-rose-500', badge: 'border-rose-500/30 text-rose-300 bg-rose-500/10' },
  QUALITY_ISSUE: { bar: 'bg-amber-500', badge: 'border-amber-500/30 text-amber-300 bg-amber-500/10' },
  PENDING: { bar: 'bg-neutral-600', badge: 'border-neutral-600/30 text-neutral-400 bg-neutral-600/10' },
  INFO: { bar: 'bg-sky-500', badge: 'border-sky-500/30 text-sky-300 bg-sky-500/10' },
};

function getColors(status) {
  return STATUS_COLORS[status] || STATUS_COLORS.PENDING;
}

function EventLogEntry({ log }) {
  const [expanded, setExpanded] = useState(false);
  const colors = getColors(log.status);

  return (
    <div
      className="flex gap-0 border border-neutral-900 rounded-xl overflow-hidden cursor-pointer hover:border-neutral-700 transition-colors"
      onClick={() => setExpanded((prev) => !prev)}
    >
      <div className={`w-1 flex-shrink-0 ${colors.bar}`} />
      <div className="flex-1 px-3 py-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-bold font-mono text-neutral-300 uppercase">{log.operation}</span>
          <span className="text-[11px] font-semibold text-neutral-200">{log.table_name}</span>
          {log.row_id && <span className="text-[10px] text-neutral-600">#{log.row_id}</span>}
          <span className={`ml-auto px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${colors.badge}`}>
            {log.status}
          </span>
        </div>

        {log.error_code && (
          <div className="mt-1 text-[10px] font-mono text-sky-400">{log.error_code}</div>
        )}

        {log.error_message && (
          <div className="mt-1 text-[11px] text-rose-300">{log.error_message}</div>
        )}

        <div className="mt-1.5 text-[10px] font-mono text-neutral-600">{log.timestamp}</div>

        {expanded && (
          <div className="mt-3 space-y-2 text-[10px] font-mono">
            {log.old_values && (
              <div>
                <span className="text-neutral-500">old: </span>
                <span className="text-neutral-400">{JSON.stringify(log.old_values, null, 2)}</span>
              </div>
            )}
            {log.new_values && (
              <div>
                <span className="text-neutral-500">new: </span>
                <span className="text-neutral-400">{JSON.stringify(log.new_values, null, 2)}</span>
              </div>
            )}
            {!log.old_values && !log.new_values && (
              <div className="text-neutral-600">No additional details.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function EventLoggerTab({ dqa }) {
  const { logs, status } = dqa;
  const [stageFilter, setStageFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const containerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    setAutoScroll(atBottom);
  }, []);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = 0; // logs are reverse-chronological
    }
  }, [logs, autoScroll]);

  const stageTableMap = {
    upload: ['raw_videos', 'raw_video_channel'],
    processing: ['created_assets'],
    publishing: ['published_posts', 'post_distribution'],
  };

  const filtered = (logs || []).filter((log) => {
    if (statusFilter !== 'all' && log.status !== statusFilter) return false;
    if (stageFilter !== 'all') {
      const tables = stageTableMap[stageFilter] || [];
      if (!tables.includes(log.table_name)) return false;
    }
    return true;
  });

  const logCounts = {};
  (logs || []).forEach((l) => {
    logCounts[l.status] = (logCounts[l.status] || 0) + 1;
  });

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="bg-[#0E0E0E] border border-neutral-800 rounded-lg px-3 py-1.5 text-[11px] text-neutral-300"
        >
          <option value="all">All Stages</option>
          <option value="upload">Upload</option>
          <option value="processing">Processing</option>
          <option value="publishing">Publishing</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-[#0E0E0E] border border-neutral-800 rounded-lg px-3 py-1.5 text-[11px] text-neutral-300"
        >
          <option value="all">All Statuses</option>
          <option value="SUCCESS">Success</option>
          <option value="ERROR">Error</option>
          <option value="QUALITY_ISSUE">Quality Issue</option>
          <option value="PENDING">Pending</option>
        </select>

        <div className="flex-1" />

        {/* Live counts */}
        <div className="flex gap-2">
          {Object.entries(logCounts).map(([key, count]) => {
            const colors = getColors(key);
            return (
              <span key={key} className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${colors.badge}`}>
                {key}: {count}
              </span>
            );
          })}
        </div>
      </div>

      {/* Log list */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="space-y-2 max-h-[calc(100vh-340px)] overflow-y-auto pr-1"
      >
        {filtered.length === 0 && (
          <div className="text-neutral-600 text-sm py-8 text-center">No log entries match your filters.</div>
        )}
        {filtered.map((log) => (
          <EventLogEntry key={log.id} log={log} />
        ))}
      </div>
    </div>
  );
}
