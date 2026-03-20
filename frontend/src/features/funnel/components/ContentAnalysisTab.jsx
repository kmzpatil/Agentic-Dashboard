import React, { useEffect, useMemo, useState } from 'react';
import { Chart } from 'react-chartjs-2';
import { useApi } from '../../../hooks/useApi';
import { API_BASE } from '../../../lib/constants';

const C = {
  red: '#ef4444',
  grid: 'rgba(255,255,255,0.04)',
};

function redGrayPalette(count, alpha = 0.9) {
  if (!count || count <= 0) return [`rgba(239, 68, 68, ${alpha})`];
  if (count === 1) return [`rgba(239, 68, 68, ${alpha})`];

  const start = { r: 239, g: 68, b: 68 };
  const end = { r: 163, g: 163, b: 163 };

  return Array.from({ length: count }, (_, idx) => {
    const t = idx / (count - 1);
    const r = Math.round(start.r + (end.r - start.r) * t);
    const g = Math.round(start.g + (end.g - start.g) * t);
    const b = Math.round(start.b + (end.b - start.b) * t);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  });
}

const Card = ({ children, className = '' }) => (
  <div className={`bg-[#111111] rounded-xl border border-neutral-800 p-5 ${className}`}>{children}</div>
);

const CardTitle = ({ title, desc }) => (
  <div className="mb-4">
    <h3 className="text-[13px] font-semibold text-white">{title}</h3>
    {desc && <p className="mt-1 text-[11px] text-neutral-500 leading-relaxed">{desc}</p>}
  </div>
);

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#a3a3a3', font: { size: 10 } }, grid: { display: false } },
    y: { ticks: { color: '#a3a3a3', font: { size: 10 } }, grid: { color: C.grid } },
  },
};

const predictorSelectClass = [
  'w-full rounded-md border border-neutral-800 bg-[#0d0d0d] px-3 py-2',
  'text-[12px] text-neutral-200 outline-none',
  'focus:border-neutral-600',
].join(' ');

const predictorNumberClass = [
  'w-full rounded-md border border-neutral-800 bg-[#0d0d0d] px-3 py-2',
  'text-[22px] leading-none text-neutral-100 outline-none',
  'focus:border-neutral-600',
].join(' ');

function PredictorField({ label, children }) {
  return (
    <div>
      <div className="mb-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-neutral-600">{label}</div>
      {children}
    </div>
  );
}

function heatCellStyle(value, minValue, maxValue) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  if (safe <= 0.0001) {
    return {
      backgroundColor: 'rgb(39, 28, 36)',
      borderColor: 'rgb(66, 45, 58)',
      color: '#f8fafc',
    };
  }

  const range = Math.max(maxValue - minValue, 1e-6);
  const t = Math.max(0, Math.min(1, (safe - minValue) / range));

  const red = { r: 166, g: 35, b: 64 };
  const green = { r: 44, g: 130, b: 88 };
  const baseR = Math.round(red.r + (green.r - red.r) * t);
  const baseG = Math.round(red.g + (green.g - red.g) * t);
  const baseB = Math.round(red.b + (green.b - red.b) * t);
  const bg = { r: 24, g: 24, b: 27 };
  const mix = 0.72;
  const r = Math.round(baseR * mix + bg.r * (1 - mix));
  const g = Math.round(baseG * mix + bg.g * (1 - mix));
  const b = Math.round(baseB * mix + bg.b * (1 - mix));
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  return {
    backgroundColor: `rgb(${r}, ${g}, ${b})`,
    borderColor: `rgb(${Math.max(r - 18, 0)}, ${Math.max(g - 18, 0)}, ${Math.max(b - 18, 0)})`,
    color: luminance > 0.6 ? '#111827' : '#f8fafc',
  };
}

function formatHeatPct(value) {
  const safe = Number.isFinite(Number(value)) ? Number(value) : 0;
  return `${safe.toFixed(2).replace(/\.00$/, '')}%`;
}

function sortUnique(values = []) {
  return Array.from(new Set(values.filter(Boolean))).sort((left, right) => left.localeCompare(right));
}

export default function ContentAnalysisTab({ authUser, data, breakdown = 'channel', filters, filterOptions, filterOptionsLoading }) {
  const isAdmin = authUser?.role === 'website_admin';
  const breakdownRows = data?.breakdown || [];
  const showClientHeatmap = isAdmin && breakdown === 'client';
  const viewLabel = breakdown.replace('_', ' ');
  const heatmapRows = data?.inputTypeClientHeatmap || [];
  const activeFilters = Object.entries(filters || {}).filter(([, value]) => value);

  const [predictorCollapsed, setPredictorCollapsed] = useState(false);
  const [predictorClient, setPredictorClient] = useState('');
  const [predictorChannel, setPredictorChannel] = useState('');
  const [predictorInputType, setPredictorInputType] = useState('');
  const [predictorLanguage, setPredictorLanguage] = useState('');
  const [predictorOutputType, setPredictorOutputType] = useState('');
  const [uploadedDuration, setUploadedDuration] = useState('357');
  const [createdDuration, setCreatedDuration] = useState('1312');
  const [uploadToCreateDays, setUploadToCreateDays] = useState('2');
  const [predictResult, setPredictResult] = useState(null);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictError, setPredictError] = useState('');

  const optionsQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (predictorClient) params.set('client', predictorClient);
    if (predictorChannel) params.set('channel', predictorChannel);
    if (predictorInputType) params.set('input_type', predictorInputType);
    if (predictorLanguage) params.set('language', predictorLanguage);
    return params.toString();
  }, [predictorClient, predictorChannel, predictorInputType, predictorLanguage]);

  const optionsUrl = useMemo(
    () => `${API_BASE}/funnel/filter-options${optionsQuery ? `?${optionsQuery}` : ''}`,
    [optionsQuery],
  );
  const { data: scopedOptionsData } = useApi(optionsUrl, [optionsUrl]);
  
  // Use filter options passed from parent FunnelModule instead of making redundant base call
  const baseOptionsData = filterOptions || {};

  const predictorClients = useMemo(() => sortUnique(baseOptionsData?.clients || []), [baseOptionsData?.clients]);
  const predictorChannels = useMemo(() => {
    const src = predictorClient ? scopedOptionsData : baseOptionsData;
    return sortUnique(src?.channels || []);
  }, [predictorClient, scopedOptionsData, baseOptionsData]);
  const predictorInputTypes = useMemo(() => {
    const src = predictorChannel ? scopedOptionsData : baseOptionsData;
    return sortUnique(src?.input_types || []);
  }, [predictorChannel, scopedOptionsData, baseOptionsData]);
  const predictorLanguages = useMemo(() => {
    const src = predictorInputType ? scopedOptionsData : baseOptionsData;
    return sortUnique(src?.languages || []);
  }, [predictorInputType, scopedOptionsData, baseOptionsData]);
  const predictorOutputTypes = useMemo(() => {
    const src = predictorLanguage ? scopedOptionsData : baseOptionsData;
    const backendTypes = src?.output_types || [];
    if (backendTypes.length > 0) return sortUnique(backendTypes);
    const fallbackTypes = (data?.outputTypeSurvival || []).map((row) => row.output_type);
    return sortUnique(fallbackTypes);
  }, [predictorLanguage, scopedOptionsData, baseOptionsData, data?.outputTypeSurvival]);

  const canChooseChannel = Boolean(predictorClient);
  const canChooseInputType = Boolean(predictorChannel);
  const canChooseLanguage = Boolean(predictorInputType);
  const canChooseOutputType = Boolean(predictorLanguage);

  const canPredict = Boolean(
    predictorClient
      && predictorChannel
      && predictorInputType
      && predictorLanguage
      && predictorOutputType
      && Number(uploadedDuration) > 0
        && Number(createdDuration) > 0
      && Number(uploadToCreateDays) >= 0,
  );

  useEffect(() => {
    let ignore = false;

    const runPrediction = async () => {
      if (!canPredict) {
        setPredictResult(null);
        setPredictError('');
        return;
      }

      setPredictLoading(true);
      setPredictError('');
      try {
        const token = localStorage.getItem('frammer_auth_token');
        const response = await fetch(`${API_BASE}/funnel/predictor/predict`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            client: predictorClient,
            channel: predictorChannel,
            input_type: predictorInputType,
            language: predictorLanguage,
            output_type: predictorOutputType,
            uploaded_duration: Number(uploadedDuration),
            created_duration: Number(createdDuration),
            upload_to_create_days: Number(uploadToCreateDays),
          }),
        });

        if (!response.ok) throw new Error(`Predict failed: ${response.status}`);
        const payload = await response.json();
        if (!ignore) setPredictResult(payload);
      } catch (error) {
        if (!ignore) {
          setPredictResult(null);
          setPredictError(error?.message || 'Prediction unavailable');
        }
      } finally {
        if (!ignore) setPredictLoading(false);
      }
    };

    runPrediction();
    return () => { ignore = true; };
  }, [
    canPredict,
    predictorClient,
    predictorChannel,
    predictorInputType,
    predictorLanguage,
    predictorOutputType,
    uploadedDuration,
    createdDuration,
    uploadToCreateDays,
  ]);

  const heatRange = useMemo(() => {
    const allValues = heatmapRows.flatMap((row) => (
      (row.clients || [])
        .map((cell) => Number(cell.conversion_pct))
        .filter((num) => Number.isFinite(num))
    ));
    const values = allValues.filter((num) => num > 0);
    if (!values.length) return { min: 0, max: 1 };
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [heatmapRows]);

  const outputTypeSurvivalData = useMemo(() => {
    return {
      labels: breakdownRows.map((row) => row.label),
      datasets: [{
        label: 'Conversion %',
        data: breakdownRows.map((row) => Number(row.conversion || 0)),
        backgroundColor: redGrayPalette(breakdownRows.length, 0.9),
        borderRadius: 4,
      }],
    };
  }, [breakdownRows]);

  const publishByClientData = useMemo(() => {
    const rows = data?.publishByClient || [];
    return {
      labels: rows.map((row) => row.client_name),
      datasets: [{
        label: 'Conversion %',
        data: rows.map((row) => Number(row.conversion_pct || 0)),
        backgroundColor: redGrayPalette(rows.length, 0.72),
        borderRadius: 5,
        barPercentage: 0.58,
      }],
    };
  }, [data?.publishByClient]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center rounded-full border border-neutral-700/80 bg-neutral-900/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          View by: {viewLabel}
        </span>
        {activeFilters.length > 0 && (
          <span className="inline-flex items-center rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-[10px] font-semibold text-violet-300">
            {activeFilters.length} filter{activeFilters.length > 1 ? 's' : ''} active
          </span>
        )}
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-neutral-300">Publish Predictor</h3>
          <button
            type="button"
            onClick={() => setPredictorCollapsed((prev) => !prev)}
            className="rounded-md border border-neutral-800 px-2.5 py-1 text-[11px] text-neutral-500 hover:text-neutral-300"
          >
            {predictorCollapsed ? 'expand +' : 'collapse −'}
          </button>
        </div>

        {!predictorCollapsed && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
              <PredictorField label="Client">
                <select
                  className={predictorSelectClass}
                  value={predictorClient}
                  onChange={(event) => {
                    setPredictorClient(event.target.value);
                    setPredictorChannel('');
                    setPredictorInputType('');
                    setPredictorLanguage('');
                    setPredictorOutputType('');
                  }}
                >
                  <option value="">— client —</option>
                  {predictorClients.map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </PredictorField>

              <PredictorField label="Channel">
                <select
                  className={predictorSelectClass}
                  value={predictorChannel}
                  onChange={(event) => {
                    setPredictorChannel(event.target.value);
                    setPredictorInputType('');
                    setPredictorLanguage('');
                    setPredictorOutputType('');
                  }}
                  disabled={!canChooseChannel}
                >
                  <option value="">— channel —</option>
                  {predictorChannels.map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </PredictorField>

              <PredictorField label="Input type">
                <select
                  className={predictorSelectClass}
                  value={predictorInputType}
                  onChange={(event) => {
                    setPredictorInputType(event.target.value);
                    setPredictorLanguage('');
                    setPredictorOutputType('');
                  }}
                  disabled={!canChooseInputType}
                >
                  <option value="">— input —</option>
                  {predictorInputTypes.map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </PredictorField>

              <PredictorField label="Language">
                <select
                  className={predictorSelectClass}
                  value={predictorLanguage}
                  onChange={(event) => {
                    setPredictorLanguage(event.target.value);
                    setPredictorOutputType('');
                  }}
                  disabled={!canChooseLanguage}
                >
                  <option value="">— lang —</option>
                  {predictorLanguages.map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </PredictorField>

              <PredictorField label="Output type">
                <select
                  className={predictorSelectClass}
                  value={predictorOutputType}
                  onChange={(event) => setPredictorOutputType(event.target.value)}
                  disabled={!canChooseOutputType}
                >
                  <option value="">— output —</option>
                  {predictorOutputTypes.map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </PredictorField>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_0.55fr]">
              <PredictorField label="Upload dur (s)">
                <input
                  type="number"
                  className={predictorNumberClass}
                  value={uploadedDuration}
                  onChange={(event) => setUploadedDuration(event.target.value)}
                />
              </PredictorField>
              <PredictorField label="Created dur (s)">
                <input
                  type="number"
                  className={predictorNumberClass}
                  value={createdDuration}
                  onChange={(event) => setCreatedDuration(event.target.value)}
                />
              </PredictorField>
              <PredictorField label="Upload - Create days">
                <input
                  type="number"
                  className={predictorNumberClass}
                  value={uploadToCreateDays}
                  onChange={(event) => setUploadToCreateDays(event.target.value)}
                />
              </PredictorField>
            </div>

            <div className="rounded-lg border border-neutral-800 bg-[#0c0c0c] px-4 py-3 text-[12px]">
              {!canPredict && <span className="text-neutral-500">Select client → channel → input type → language → output type to run prediction.</span>}
              {predictLoading && <span className="text-neutral-400">Predicting…</span>}
              {!predictLoading && predictError && <span className="text-red-400">{predictError}</span>}
              {!predictLoading && !predictError && predictResult && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-3">
                    <span className="text-[15px] font-bold text-white">{predictResult.prediction}</span>
                    <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">
                      {predictResult.confidence_pct}% confidence
                    </span>
                  </div>
                  {predictResult.confidence_by_n && (
                    <div className="flex flex-wrap gap-2">
                      {[
                        { key: '0', label: 'Never' },
                        { key: '1', label: '≤1 day' },
                        { key: '2', label: '≤2 days' },
                        { key: '3', label: '≤3 days' },
                        { key: '4+', label: '>3 days' },
                      ].map(({ key, label }) => (
                        <div key={key} className="flex items-center gap-1.5 rounded-md border border-neutral-800 bg-[#111] px-2 py-1">
                          <span className="text-[10px] text-neutral-500">{label}</span>
                          <span className="text-[11px] font-semibold text-neutral-300">{predictResult.confidence_by_n[key]}%</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      {showClientHeatmap ? (
        <Card>
          <CardTitle
            title="Input type × client — publish conversion heatmap"
            desc="Extra detail for client view. Metric is published ÷ created."
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] border-separate border-spacing-y-1 text-sm">
              <thead>
                <tr className="text-neutral-500">
                  <th className="sticky left-0 z-20 bg-[#111111] py-2 text-left pr-4 text-[10.5px] font-medium">Input type</th>
                  {(data?.heatmapClients || []).map((client) => (
                    <th key={client} className="py-2 text-center text-[10.5px] font-medium">{client}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapRows.map((row) => (
                  <tr key={row.input_type}>
                    <td className="sticky left-0 z-10 bg-[#111111] py-2 pr-4 text-neutral-200 text-[12px] font-medium max-w-[230px] truncate" title={row.input_type}>
                      {row.input_type}
                    </td>
                    {(row.clients || []).map((cell, index) => {
                      const conversion = Number(cell.conversion_pct);
                      const safeConversion = Number.isFinite(conversion) ? conversion : 0;
                      const cellStyle = heatCellStyle(safeConversion, heatRange.min, heatRange.max);
                      return (
                        <td
                          key={index}
                          className="rounded-md border px-4 py-2 text-center font-semibold text-[11.5px] font-mono min-w-[120px]"
                          style={cellStyle}
                          title={`Created: ${cell.assets_created || 0}, Published: ${cell.posts_published || 0}`}
                        >
                          {formatHeatPct(safeConversion)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center gap-3 text-[10.5px] text-neutral-500">
            <span>Lower conversion</span>
            <div className="h-2 w-28 rounded-full bg-gradient-to-r from-[#7a233f] to-[#2d6f55] border border-neutral-700/70" />
            <span>Higher conversion</span>
          </div>
        </Card>
      ) : (
        <Card>
          <CardTitle
            title={`${breakdown.replace('_', ' ')} — publish conversion`}
            desc="Conversion rate (%) by the current View by categories."
          />
          <div className="h-[220px]">
            <Chart type="bar" data={outputTypeSurvivalData} options={barOptions} />
          </div>
        </Card>
      )}

      {isAdmin && publishByClientData.labels.length > 0 && (
        <Card>
          <CardTitle
            title="Publish conversion by client"
            desc="Published ÷ created by client for the current filter context."
          />
          <div className="h-[220px]">
            <Chart
              type="bar"
              data={publishByClientData}
              options={{
                ...barOptions,
                scales: {
                  ...barOptions.scales,
                  y: {
                    ...barOptions.scales.y,
                    ticks: {
                      ...barOptions.scales.y.ticks,
                      callback: (value) => `${value}%`,
                    },
                    title: {
                      display: true,
                      text: 'Conversion rate (%)',
                      color: '#a3a3a3',
                      font: { size: 10 },
                    },
                  },
                },
              }}
            />
          </div>
        </Card>
      )}
    </div>
  );
}
