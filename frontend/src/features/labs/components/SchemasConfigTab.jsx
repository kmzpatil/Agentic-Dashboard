import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Play, Square, RotateCcw, Database, Settings } from 'lucide-react';

function SchemaTable({ table }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-neutral-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-[#0E0E0E] hover:bg-[#141414] transition-colors text-left"
      >
        {open ? <ChevronDown size={14} className="text-neutral-500" /> : <ChevronRight size={14} className="text-neutral-500" />}
        <Database size={14} className="text-sky-400" />
        <span className="text-sm font-bold text-neutral-200">{table.table}</span>
        <span className="text-[10px] uppercase tracking-wider text-neutral-500 ml-2">{table.stage}</span>
        <span className="ml-auto text-[11px] text-neutral-500">{table.row_count} rows · {table.columns.length} cols</span>
      </button>

      {open && (
        <div className="bg-[#0A0A0A] overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-neutral-800">
                <th className="text-left px-4 py-2 font-bold uppercase tracking-widest text-neutral-500">Column</th>
                <th className="text-left px-4 py-2 font-bold uppercase tracking-widest text-neutral-500">Type</th>
                <th className="text-left px-4 py-2 font-bold uppercase tracking-widest text-neutral-500">Constraints</th>
                <th className="text-left px-4 py-2 font-bold uppercase tracking-widest text-neutral-500">Description</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((col) => (
                <tr key={col.name} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                  <td className="px-4 py-2 font-mono font-semibold text-neutral-200">{col.name}</td>
                  <td className="px-4 py-2 text-neutral-400">{col.type}</td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1 flex-wrap">
                      {col.pk && <span className="px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 text-[9px] font-bold">PK</span>}
                      {col.notnull && <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] font-bold">NOT NULL</span>}
                      {col.fk && <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 text-[9px] font-bold">FK → {col.fk}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-neutral-500 max-w-[300px]">{col.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SimulatorControls({ dqa }) {
  const [opsPerBatch, setOpsPerBatch] = useState(5);
  const [interval, setInterval_] = useState(2);
  const isRunning = dqa.status?.running;

  return (
    <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Settings size={14} className="text-neutral-400" />
        <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400">Simulator Controls</h3>
        <span className={`ml-auto px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${
          isRunning ? 'border-emerald-500/30 text-emerald-300 bg-emerald-500/10' : 'border-neutral-600/30 text-neutral-400 bg-neutral-600/10'
        }`}>
          {isRunning ? 'Running' : 'Stopped'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest">
          Ops / Batch
          <input
            type="number"
            min="1" max="50"
            value={opsPerBatch}
            onChange={(e) => setOpsPerBatch(Number(e.target.value))}
            className="mt-1.5 w-full bg-[#111111] border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200"
          />
        </label>
        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest">
          Interval (sec)
          <input
            type="number"
            min="0.5" max="30" step="0.5"
            value={interval}
            onChange={(e) => setInterval_(Number(e.target.value))}
            className="mt-1.5 w-full bg-[#111111] border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-200"
          />
        </label>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => dqa.runAction('start', { ops_per_batch: String(opsPerBatch), interval: String(interval) })}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-400 text-black text-[11px] font-bold hover:bg-emerald-300"
        >
          <Play size={12} /> Start
        </button>
        <button
          onClick={() => dqa.runAction('stop')}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-800 text-neutral-200 text-[11px] font-bold hover:bg-neutral-700"
        >
          <Square size={12} /> Stop
        </button>
        <button
          onClick={() => dqa.runAction('reset')}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-amber-300 text-black text-[11px] font-bold hover:bg-amber-200"
        >
          <RotateCcw size={12} /> Reset
        </button>
      </div>
    </div>
  );
}

function ErrorConfigPanel({ dqa }) {
  const { errorConfig, updateErrorConfig } = dqa;
  const [localRates, setLocalRates] = useState({});
  const [dirty, setDirty] = useState(false);

  React.useEffect(() => {
    if (errorConfig && Object.keys(errorConfig).length > 0 && Object.keys(localRates).length === 0) {
      setLocalRates({ ...errorConfig });
    }
  }, [errorConfig]);

  const handleChange = (key, value) => {
    setLocalRates((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = () => {
    updateErrorConfig(localRates);
    setDirty(false);
  };

  const groups = {
    'Upload Errors': ['null_fields', 'invalid_format', 'corrupted_file', 'failed_upload', 'future_date', 'negative_value', 'duplicate_checksum'],
    'Processing Errors': ['processing_failure', 'sla_breach', 'low_quality', 'no_thumbnail', 'temporal_inversion'],
    'Publishing Errors': ['publish_failure', 'rate_limited', 'content_rejected', 'high_latency', 'schedule_drift', 'auth_failure'],
    'Distribution Errors': ['invalid_url', 'invalid_embed', 'orphan_records'],
  };

  return (
    <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400">Error Injection Rates</h3>
        {dirty && (
          <button
            onClick={handleSave}
            className="ml-auto px-3 py-1 rounded-full bg-sky-500 text-black text-[10px] font-bold hover:bg-sky-400"
          >
            Save Changes
          </button>
        )}
      </div>

      <div className="space-y-5">
        {Object.entries(groups).map(([group, keys]) => (
          <div key={group}>
            <div className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-2">{group}</div>
            <div className="space-y-2">
              {keys.map((key) => {
                const rate = localRates[key] ?? errorConfig[key] ?? 0;
                const pct = Math.round(rate * 100);
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-[11px] text-neutral-400 min-w-[150px]">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <input
                      type="range"
                      min="0" max="50" step="1"
                      value={pct}
                      onChange={(e) => handleChange(key, Number(e.target.value) / 100)}
                      className="flex-1 accent-sky-500 h-1"
                    />
                    <span className="text-[11px] font-mono text-neutral-300 min-w-[36px] text-right">{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SchemasConfigTab({ dqa }) {
  const { schemas } = dqa;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_1fr] gap-6">
      {/* Left: Schema browser */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-2">Pipeline Schemas</h3>
        {(!schemas || schemas.length === 0) && (
          <div className="text-neutral-600 text-sm py-4">Loading schemas...</div>
        )}
        {(schemas || []).map((table) => (
          <SchemaTable key={table.table} table={table} />
        ))}
      </div>

      {/* Right: Controls + Error config */}
      <div className="space-y-6">
        <SimulatorControls dqa={dqa} />
        <ErrorConfigPanel dqa={dqa} />
      </div>
    </div>
  );
}
