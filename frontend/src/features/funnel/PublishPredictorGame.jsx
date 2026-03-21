import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { Target, Info, ChevronDown } from 'lucide-react';
import { API_BASE } from '../../lib/constants';

// ── SVG Gauge ────────────────────────────────────────────────────────────────

function ProbabilityGauge({ value }) {
  const r = 80;
  const cx = 100, cy = 100;
  const circumference = Math.PI * r;
  const v = Math.max(0, Math.min(100, value));
  const offset = circumference * (1 - v / 100);

  const color =
    v < 25 ? '#ef4444' :
    v < 50 ? '#f59e0b' :
    v < 75 ? '#22c55e' : '#10b981';

  const label =
    v < 15 ? 'Very Unlikely' :
    v < 35 ? 'Unlikely' :
    v < 55 ? 'Possible' :
    v < 75 ? 'Likely' : 'Very Likely';

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" width={240} height={144}>
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke="#1a1a1a" strokeWidth="14" strokeLinecap="round"
        />
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease-out, stroke 0.5s' }}
        />
        <text x={cx} y={cy - 18} textAnchor="middle" fill="white" fontSize="34" fontWeight="900" fontFamily="system-ui">
          {v.toFixed(1)}%
        </text>
        <text x={cx} y={cy + 5} textAnchor="middle" fill="#525252" fontSize="9" fontWeight="700" letterSpacing="0.18em">
          PUBLISH PROBABILITY
        </text>
      </svg>
      <div className="mt-1 text-sm font-bold uppercase tracking-wider" style={{ color, transition: 'color 0.5s' }}>
        {label}
      </div>
    </div>
  );
}

// ── Timeline bar ─────────────────────────────────────────────────────────────

function TimelineBar({ label, value }) {
  const w = Math.max(0, Math.min(100, value));
  const barColor =
    w < 25 ? 'bg-red-500' :
    w < 50 ? 'bg-amber-500' :
    w < 75 ? 'bg-green-500' : 'bg-emerald-400';

  return (
    <div className="flex items-center gap-3">
      <div className="w-24 text-xs text-neutral-400 font-medium text-right shrink-0">{label}</div>
      <div className="flex-1 h-5 rounded-full bg-neutral-800/50 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-700 ease-out`}
          style={{ width: `${w}%` }}
        />
      </div>
      <div className="w-14 text-sm font-bold text-white text-right tabular-nums">{value.toFixed(1)}%</div>
    </div>
  );
}

// ── Select ───────────────────────────────────────────────────────────────────

function Select({ label, value, onChange, options, disabled }) {
  return (
    <div>
      <label className="block mb-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="w-full appearance-none rounded-xl border border-neutral-800 bg-[#0a0a0a] px-4 py-3 pr-8 text-sm text-white font-semibold
                     focus:outline-none focus:border-red-500/50 transition-colors disabled:opacity-40"
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
        <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 pointer-events-none" />
      </div>
    </div>
  );
}

// ── Slider ───────────────────────────────────────────────────────────────────

function DurationSlider({ label, value, onChange, max, unit = 's' }) {
  const display = unit === 's'
    ? value >= 3600 ? `${(value / 3600).toFixed(1)}h` : value >= 60 ? `${Math.round(value / 60)}m` : `${value}s`
    : `${value} day${value !== 1 ? 's' : ''}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">{label}</label>
        <span className="text-xs font-bold text-white tabular-nums">{display}</span>
      </div>
      <input
        type="range" min={0} max={max} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none bg-neutral-800 cursor-pointer
                   [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                   [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2
                   [&::-webkit-slider-thumb]:border-red-500 [&::-webkit-slider-thumb]:cursor-pointer
                   [&::-webkit-slider-thumb]:shadow-[0_0_6px_rgba(239,68,68,0.4)]"
      />
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function PublishPredictorGame({ authUser }) {
  const role = authUser?.role || 'user';
  const isAdmin = role === 'website_admin';
  const lockedClient = !isAdmin ? (authUser?.clientName || '') : '';

  const [options, setOptions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showInfo, setShowInfo] = useState(false);

  // form
  const [client, setClient] = useState('');
  const [channel, setChannel] = useState('');
  const [inputType, setInputType] = useState('');
  const [language, setLanguage] = useState('');
  const [outputType, setOutputType] = useState('');
  const [uploadedDuration, setUploadedDuration] = useState(3000);
  const [createdDuration, setCreatedDuration] = useState(1500);
  const [uploadToCreateDays, setUploadToCreateDays] = useState(1);

  const debounceRef = useRef(null);

  const token = localStorage.getItem('frammer_auth_token');
  const headers = useMemo(() => ({
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }), [token]);

  // ── fetch options (triggers model training on first ever call) ──────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const controller = new AbortController();
        // First call may train the model — allow up to 3 minutes
        const timeout = setTimeout(() => controller.abort(), 180_000);
        const res = await fetch(`${API_BASE}/publish-predictor/options`, {
          headers,
          signal: controller.signal,
        });
        clearTimeout(timeout);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setOptions(data);
        if (isAdmin) {
          if (data.clients?.length) setClient(data.clients[0]);
        } else {
          setClient(lockedClient || data.clients?.[0] || '');
        }
        if (data.input_types?.length)  setInputType(data.input_types[0]);
        if (data.languages?.length)    setLanguage(data.languages[0]);
        if (data.output_types?.length) setOutputType(data.output_types[0]);
        setUploadedDuration(Math.round((data.max_uploaded_duration || 15000) / 3));
        setCreatedDuration(Math.round((data.max_created_duration || 10000) / 3));
      } catch (err) {
        if (!cancelled) {
          const msg = err.name === 'AbortError'
            ? 'Model training timed out — refresh to retry (model may be cached now)'
            : err.message;
          setError(msg);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [headers, isAdmin, lockedClient]);

  useEffect(() => {
    if (!isAdmin && lockedClient && client !== lockedClient) {
      setClient(lockedClient);
    }
  }, [isAdmin, lockedClient, client]);

  // auto-set channel when client changes
  const selectedClient = isAdmin ? client : (lockedClient || client);
  const availableChannels = useMemo(() => {
    if (!options?.channel_by_client || !selectedClient) return [];
    return options.channel_by_client[selectedClient] || [];
  }, [options, selectedClient]);

  useEffect(() => {
    if (availableChannels.length > 0 && !availableChannels.includes(channel)) {
      setChannel(availableChannels[0]);
    }
  }, [availableChannels]);

  // ── predict (debounced) ────────────────────────────────────────────────
  const predict = useCallback(async () => {
    if (!selectedClient || !channel || !inputType || !language || !outputType) return;
    try {
      const res = await fetch(`${API_BASE}/publish-predictor/predict`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          client_name: selectedClient,
          assigned_channel: channel,
          input_type: inputType,
          language,
          output_type: outputType,
          uploaded_duration: uploadedDuration,
          created_duration: createdDuration,
          upload_to_create_days: uploadToCreateDays,
        }),
      });
      if (!res.ok) throw new Error('Prediction failed');
      setResult(await res.json());
    } catch (err) {
      console.error('predict:', err);
    }
  }, [selectedClient, channel, inputType, language, outputType, uploadedDuration, createdDuration, uploadToCreateDays, headers]);

  useEffect(() => {
    if (!options || loading) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(predict, 350);
    return () => clearTimeout(debounceRef.current);
  }, [selectedClient, channel, inputType, language, outputType, uploadedDuration, createdDuration, uploadToCreateDays, options, loading]);

  // ── loading / error ────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <style>{`
          @keyframes oracleDot { 0%,100%{transform:translateY(0);opacity:.35} 50%{transform:translateY(-8px);opacity:1} }
        `}</style>
        <div className="flex gap-2 mb-4">
          {[0,1,2,3,4].map(i => (
            <span key={i} className="block w-2.5 h-2.5 rounded-full bg-red-500"
              style={{ animation: `oracleDot 1.2s ease-in-out ${i * 0.15}s infinite` }} />
          ))}
        </div>
        <p className="text-sm font-black uppercase tracking-[0.2em] text-neutral-300">Initialising ML Model</p>
        <p className="mt-2 text-xs text-neutral-400">Training RandomForest classifier on first load — this is a one-time operation…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-6 py-4 text-sm text-red-400">{error}</div>
      </div>
    );
  }

  // ── render ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-500/10 border border-red-500/20">
            <Target size={18} className="text-red-500" />
          </div>
          <div>
            <h3 className="text-sm font-black uppercase tracking-[0.12em] text-white">Publish Oracle</h3>
            <p className="text-[11px] text-neutral-500 mt-0.5">
              Interactive what-if simulation — tweak asset attributes and watch publish probability change in real time
            </p>
          </div>
        </div>

        {isAdmin && (
          <div className="flex items-center gap-2">
            {options?.accuracy != null && (
              <div className="rounded-lg border border-neutral-800 bg-[#111] px-3 py-1.5 text-[10px] font-bold text-neutral-400 tracking-wider">
                ACCURACY <span className="text-emerald-400 ml-1">{(options.accuracy * 100).toFixed(1)}%</span>
              </div>
            )}
            {options?.total_samples > 0 && (
              <div className="rounded-lg border border-neutral-800 bg-[#111] px-3 py-1.5 text-[10px] font-bold text-neutral-400 tracking-wider">
                {(options.total_samples / 1000).toFixed(0)}K <span className="text-neutral-500">SAMPLES</span>
              </div>
            )}
            <button
              onClick={() => setShowInfo(v => !v)}
              className={`p-2 rounded-lg border transition-colors ${showInfo ? 'border-red-500/40 bg-red-500/10 text-red-400' : 'border-neutral-800 text-neutral-500 hover:text-white'}`}
            >
              <Info size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Info panel */}
      {isAdmin && showInfo && (
        <div className="rounded-xl border border-neutral-800 bg-[#0d0d0d] p-5 space-y-4">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-red-400">How it works</h4>
          <p className="text-xs text-neutral-400 leading-relaxed">
            A <strong className="text-white">RandomForest classifier</strong> (1000 decision trees, balanced class weights) is trained on
            the full historical pipeline data. It learns patterns across <strong className="text-neutral-200">client, channel, content type,
            language, and duration</strong> to predict whether an asset will be published — and how quickly.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              ['1000', 'Decision Trees'],
              [`${options?.total_samples ? (options.total_samples / 1000).toFixed(0) + 'K' : '—'}`, 'Training Rows'],
              ['8', 'Feature Dims'],
              [`${options?.classes?.length || '—'}`, 'Output Classes'],
              [`${options?.accuracy ? (options.accuracy * 100).toFixed(1) + '%' : '—'}`, 'Test Accuracy'],
            ].map(([val, lbl]) => (
              <div key={lbl} className="rounded-lg bg-neutral-900 p-3 text-center">
                <div className="text-lg font-black text-white">{val}</div>
                <div className="text-[9px] text-neutral-500 uppercase tracking-wider">{lbl}</div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-neutral-400">
            Target classes: <span className="text-neutral-400">Never</span> · <span className="text-neutral-400">Within 1 Day</span> ·{' '}
            <span className="text-neutral-400">Within 2 Days</span> · <span className="text-neutral-400">Within 3 Days</span> ·{' '}
            <span className="text-neutral-400">More than 3 Days</span>
          </p>
        </div>
      )}

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── Left: Configure ── */}
        <div className="lg:col-span-2 rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6 space-y-5">
          <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">Configure Asset</h4>

          {isAdmin ? (
            <Select label="Client" value={client} onChange={setClient} options={options?.clients || []} />
          ) : (
            <div>
              <label className="block mb-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">Client</label>
              <div className="w-full rounded-xl border border-neutral-800 bg-[#0a0a0a] px-4 py-3 text-sm text-neutral-300 font-semibold">
                {selectedClient || 'N/A'}
              </div>
            </div>
          )}
          <Select label="Channel" value={channel} onChange={setChannel} options={availableChannels} />

          <div className="grid grid-cols-2 gap-4">
            <Select label="Input Type" value={inputType} onChange={setInputType} options={options?.input_types || []} />
            <Select label="Language" value={language} onChange={setLanguage} options={options?.languages || []} />
          </div>

          <Select label="Output Type" value={outputType} onChange={setOutputType} options={options?.output_types || []} />

          <div className="pt-3 border-t border-neutral-800/50 space-y-5">
            <DurationSlider label="Upload Duration" value={uploadedDuration} onChange={setUploadedDuration} max={options?.max_uploaded_duration || 15000} />
            <DurationSlider label="Created Duration" value={createdDuration} onChange={setCreatedDuration} max={options?.max_created_duration || 10000} />
            <DurationSlider label="Days to Create" value={uploadToCreateDays} onChange={setUploadToCreateDays} max={10} unit="d" />
          </div>
        </div>

        {/* ── Right: Prediction ── */}
        <div className="lg:col-span-3 space-y-5">
          {/* Gauge */}
          <div className="rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6 flex flex-col items-center">
            {result ? (
              <ProbabilityGauge value={result.publish_probability} />
            ) : (
              <div className="py-12 text-xs text-neutral-500">Waiting for first prediction…</div>
            )}

            {/* Predicted class pill */}
            {result && (
              <div className="mt-4 flex items-center gap-2">
                <span className="text-[10px] text-neutral-500 font-bold uppercase tracking-wider">Most likely:</span>
                <span className="rounded-md bg-red-500/10 border border-red-500/30 px-3 py-1 text-xs font-bold text-red-300">
                  {result.predicted_class.replace(/^\d_/, '').replace(/_/g, ' ')}
                </span>
              </div>
            )}
          </div>

          {/* Timeline */}
          {result && (
            <div className="rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6">
              <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500 mb-5">Cumulative Publish Timeline</h4>
              <div className="space-y-3">
                <TimelineBar label="Within 1 Day"  value={result.cumulative.within_1_day} />
                <TimelineBar label="Within 2 Days" value={result.cumulative.within_2_days} />
                <TimelineBar label="Within 3 Days" value={result.cumulative.within_3_days} />
                <TimelineBar label="Eventually"    value={result.cumulative.eventually} />
              </div>

              <div className="mt-4 pt-4 border-t border-neutral-800/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500" />
                  <span className="text-xs text-neutral-400">Never Published</span>
                </div>
                <span className="text-sm font-bold text-red-400 tabular-nums">{result.never.toFixed(1)}%</span>
              </div>
            </div>
          )}

          {/* Class breakdown */}
          {result && (
            <div className="rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6">
              <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500 mb-4">Raw Class Probabilities</h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {Object.entries(result.class_probabilities).map(([cls, prob]) => {
                  const lbl = cls.replace(/^\d_/, '').replace(/_/g, ' ');
                  const isNever = cls === '0_Never';
                  const isPredicted = result.predicted_class === cls;
                  return (
                    <div
                      key={cls}
                      className={`rounded-xl p-3 text-center border transition-all ${
                        isPredicted ? 'border-red-500/40 bg-red-500/5 scale-105' : 'border-neutral-800 bg-neutral-900/50'
                      }`}
                    >
                      <div className={`text-lg font-black tabular-nums ${isNever ? 'text-red-400' : 'text-white'}`}>
                        {prob.toFixed(1)}%
                      </div>
                      <div className="text-[9px] text-neutral-500 uppercase tracking-wider mt-1 leading-tight">{lbl}</div>
                      {isPredicted && (
                        <div className="text-[8px] text-red-400 font-bold uppercase mt-1.5 tracking-wider">Predicted</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
