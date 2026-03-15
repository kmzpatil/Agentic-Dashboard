import React, { useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE } from '../../lib/constants';
import KpiCard from '../../components/common/KpiCard';

const REFRESH_MS = 5000;

function formatCount(value) {
  if (value === null || value === undefined) return '0';
  return new Intl.NumberFormat().format(value);
}

export default function SimulatorModule() {
  const [status, setStatus] = useState(null);
  const [tables, setTables] = useState([]);
  const [logs, setLogs] = useState([]);
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [opsPerBatch, setOpsPerBatch] = useState(5);
  const [intervalSeconds, setIntervalSeconds] = useState(2);
  const syncedDefaults = useRef(false);

  const logCounts = status?.log_counts || {};
  const totalLogs = Object.values(logCounts).reduce((sum, count) => sum + Number(count || 0), 0);

  const loadAll = async () => {
    try {
      setError('');
      const [statusRes, tablesRes, logsRes, qualityRes] = await Promise.all([
        fetch(`${API_BASE}/simulator/status`),
        fetch(`${API_BASE}/simulator/tables`),
        fetch(`${API_BASE}/simulator/logs?limit=20`),
        fetch(`${API_BASE}/simulator/quality`),
      ]);

      if (!statusRes.ok) throw new Error('Failed to load simulator status');
      if (!tablesRes.ok) throw new Error('Failed to load simulator tables');
      if (!logsRes.ok) throw new Error('Failed to load simulator logs');
      if (!qualityRes.ok) throw new Error('Failed to load quality report');

      const statusPayload = await statusRes.json();
      const tablesPayload = await tablesRes.json();
      const logsPayload = await logsRes.json();
      const qualityPayload = await qualityRes.json();

      setStatus(statusPayload);
      setTables(tablesPayload);
      setLogs(logsPayload);
      setQuality(qualityPayload);

      if (!syncedDefaults.current && statusPayload?.settings) {
        setOpsPerBatch(statusPayload.settings.ops_per_batch ?? 5);
        setIntervalSeconds(statusPayload.settings.interval ?? 2);
        syncedDefaults.current = true;
      }
    } catch (err) {
      setError(err.message || 'Failed to load simulator data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    const id = setInterval(loadAll, REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  const runAction = async (action) => {
    setLoading(true);
    setError('');
    try {
      let url = `${API_BASE}/simulator/${action}`;
      if (action === 'start') {
        const params = new URLSearchParams({
          ops_per_batch: String(opsPerBatch),
          interval: String(intervalSeconds),
        });
        url += `?${params.toString()}`;
      }
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) throw new Error(`Failed to ${action} simulator`);
      await loadAll();
    } catch (err) {
      setError(err.message || 'Simulator action failed');
    } finally {
      setLoading(false);
    }
  };

  const tableRows = useMemo(() => {
    return (tables || []).map((table) => (
      <div key={table.name} className="flex items-center justify-between py-2 border-b border-neutral-900 text-sm">
        <div className="text-neutral-300 font-semibold">{table.name}</div>
        <div className="text-neutral-500">{formatCount(table.row_count)}</div>
      </div>
    ));
  }, [tables]);

  return (
    <div className="h-full w-full overflow-y-auto px-8 py-6 text-white">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-black tracking-tight">Data Simulator</h2>
          <p className="text-sm text-neutral-500 mt-1">In-memory data generator with logging and quality checks.</p>
        </div>
        <button
          onClick={loadAll}
          className="px-4 py-2 rounded-full bg-neutral-900 border border-neutral-800 text-xs font-bold tracking-widest uppercase text-neutral-400 hover:text-white hover:border-neutral-600"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Running" value={status?.running ? 'Yes' : 'No'} subtitle="Simulator thread" />
        <KpiCard title="Total Tables" value={formatCount(tables.length)} subtitle="In-memory schema" />
        <KpiCard title="Total Logs" value={formatCount(totalLogs)} subtitle="Recorded operations" />
        <KpiCard
          title="Quality Score"
          value={quality?.overall_score ? `${quality.overall_score}%` : '0%'}
          subtitle={`${quality?.total_issues || 0} issues detected`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-6 mb-6">
        <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400">Controls</h3>
            <div className="text-xs text-neutral-600">Auto-refreshes every 5s</div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <label className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
              Ops per batch
              <input
                type="number"
                min="1"
                max="50"
                value={opsPerBatch}
                onChange={(e) => setOpsPerBatch(Number(e.target.value))}
                className="mt-2 w-full bg-[#111111] border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200"
              />
            </label>
            <label className="text-xs font-bold text-neutral-500 uppercase tracking-widest">
              Interval (sec)
              <input
                type="number"
                min="0.5"
                max="30"
                step="0.5"
                value={intervalSeconds}
                onChange={(e) => setIntervalSeconds(Number(e.target.value))}
                className="mt-2 w-full bg-[#111111] border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => runAction('start')}
              disabled={loading}
              className="px-5 py-2 rounded-full bg-emerald-400 text-black text-sm font-bold hover:bg-emerald-300 disabled:opacity-50"
            >
              Start
            </button>
            <button
              onClick={() => runAction('stop')}
              disabled={loading}
              className="px-5 py-2 rounded-full bg-neutral-800 text-neutral-200 text-sm font-bold hover:bg-neutral-700 disabled:opacity-50"
            >
              Stop
            </button>
            <button
              onClick={() => runAction('reset')}
              disabled={loading}
              className="px-5 py-2 rounded-full bg-amber-300 text-black text-sm font-bold hover:bg-amber-200 disabled:opacity-50"
            >
              Reset
            </button>
          </div>
        </div>

        <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
          <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">Log Status</h3>
          <div className="space-y-3 text-sm text-neutral-300">
            {Object.keys(logCounts).length === 0 && <div className="text-neutral-600">No logs yet.</div>}
            {Object.entries(logCounts).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="uppercase text-[11px] tracking-widest text-neutral-500">{key}</span>
                <span className="font-semibold">{formatCount(value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.3fr] gap-6">
        <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
          <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">Tables</h3>
          <div className="divide-y divide-neutral-900">{tableRows}</div>
        </div>

        <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5 overflow-hidden">
          <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">Recent Logs</h3>
          <div className="space-y-3 max-h-[360px] overflow-y-auto pr-2">
            {logs.length === 0 && <div className="text-neutral-600">No log entries yet.</div>}
            {logs.map((log) => (
              <div key={log.id} className="border border-neutral-900 rounded-xl p-3">
                <div className="flex items-center justify-between text-xs uppercase tracking-widest text-neutral-500">
                  <span>{log.operation}</span>
                  <span>{log.status}</span>
                </div>
                <div className="mt-2 text-sm text-neutral-200 font-semibold">
                  {log.table_name} {log.row_id ? `#${log.row_id}` : ''}
                </div>
                {log.error_message && (
                  <div className="mt-1 text-xs text-red-300">{log.error_message}</div>
                )}
                <div className="mt-2 text-[11px] text-neutral-600">{log.timestamp}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
