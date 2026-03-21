import React, {
  useEffect,
  useMemo,
  useState,
  useCallback,
  useRef,
} from "react";
import {
  Target,
  Info,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { API_BASE } from "../../lib/constants";

// ── SVG Gauge ────────────────────────────────────────────────────────────────

function ProbabilityGauge({ value }) {
  const r = 80;
  const cx = 100,
    cy = 100;
  const circumference = Math.PI * r;
  const v = Math.max(0, Math.min(100, value));
  const offset = circumference * (1 - v / 100);

  const color =
    v < 25 ? "#ef4444" : v < 50 ? "#f59e0b" : v < 75 ? "#22c55e" : "#10b981";

  const label =
    v < 15
      ? "Very Unlikely"
      : v < 35
        ? "Unlikely"
        : v < 55
          ? "Possible"
          : v < 75
            ? "Likely"
            : "Very Likely";

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" width={240} height={144}>
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#1a1a1a"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease-out, stroke 0.5s" }}
        />
        <text
          x={cx}
          y={cy - 18}
          textAnchor="middle"
          fill="white"
          fontSize="34"
          fontWeight="900"
          fontFamily="system-ui"
        >
          {v.toFixed(1)}%
        </text>
        <text
          x={cx}
          y={cy + 5}
          textAnchor="middle"
          fill="#525252"
          fontSize="9"
          fontWeight="700"
          letterSpacing="0.18em"
        >
          PUBLISH PROBABILITY
        </text>
      </svg>
      <div
        className="mt-1 text-sm font-bold uppercase tracking-wider"
        style={{ color, transition: "color 0.5s" }}
      >
        {label}
      </div>
    </div>
  );
}

const formatFeatureName = (feature) => {
  if (feature.startsWith("Input_Type_"))
    return `Input: ${feature.replace("Input_Type_", "").toUpperCase()}`;
  if (feature.startsWith("Output_Type_"))
    return `Output: ${feature.replace("Output_Type_", "")}`;
  if (feature.startsWith("Language_"))
    return `Language: ${feature.replace("Language_", "").toUpperCase()}`;
  if (feature.startsWith("Client_Name_"))
    return feature.replace("Client_Name_", "");
  if (feature.startsWith("Assigned_Channel_"))
    return `Channel: ${feature.replace("Assigned_Channel_", "")}`;
  return feature;
};

// ── Select ───────────────────────────────────────────────────────────────────

function FilterSelect({ label, value, onChange, options, disabled }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const selectedLabel =
    options.find((item) => item.value === value)?.label || "Select";

  return (
    <div ref={ref} className={`relative ${disabled ? "opacity-45" : ""}`}>
      <label className="mb-0.5 block text-[9px] font-semibold uppercase tracking-[0.1em] text-neutral-600 select-none">
        {label}
      </label>
      <button
        type="button"
        onClick={() => {
          if (!disabled) setOpen((prev) => !prev);
        }}
        disabled={disabled}
        className={[
          "w-full h-[34px] rounded-lg border px-2.5",
          "flex items-center justify-between gap-2",
          "text-[12px] font-medium transition-colors",
          disabled
            ? "border-neutral-800 bg-[#0b0b0b] text-neutral-600 cursor-not-allowed"
            : "border-neutral-800 bg-[#0b0b0b] text-neutral-200 hover:border-neutral-700 hover:bg-[#111111]",
        ].join(" ")}
      >
        <span className="truncate text-left">{selectedLabel}</span>
        <svg
          width="10"
          height="6"
          viewBox="0 0 10 6"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform ${open ? "rotate-180 text-red-400" : "text-neutral-500"}`}
        >
          <path
            d="M1 1L5 5L9 1"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </button>

      {open && !disabled && (
        <div className="absolute left-0 right-0 mt-2 z-50 rounded-xl border border-neutral-800 bg-[#0f0f0f] shadow-[0_18px_40px_rgba(0,0,0,0.45)] p-1 max-h-[260px] overflow-y-auto">
          {options.map((item) => {
            const active = item.value === value;
            return (
              <button
                key={item.value || "none"}
                type="button"
                onClick={() => {
                  onChange(item.value);
                  setOpen(false);
                }}
                className={[
                  "w-full rounded-lg px-2 py-1.5 text-left text-[12px] transition-colors",
                  active
                    ? "bg-red-500/12 text-red-300"
                    : "text-neutral-300 hover:bg-neutral-800 hover:text-white",
                ].join(" ")}
              >
                <span className="truncate block">{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Slider ───────────────────────────────────────────────────────────────────

function DurationSlider({ label, value, onChange, max, unit = "s" }) {
  const display =
    unit === "s"
      ? value >= 3600
        ? `${(value / 3600).toFixed(1)}h`
        : value >= 60
          ? `${Math.round(value / 60)}m`
          : `${value}s`
      : `${value} day${value !== 1 ? "s" : ""}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">
          {label}
        </label>
        <span className="text-xs font-bold text-white tabular-nums">
          {display}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
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

function formatDurationCap(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "0s+";
  if (seconds >= 3600) return `${(seconds / 3600).toFixed(1)}h+`;
  if (seconds >= 60) return `${(seconds / 60).toFixed(1)}m+`;
  return `${seconds}s+`;
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function PublishPredictorGame({ authUser }) {
  const role = authUser?.role || "user";
  const isAdmin = role === "website_admin";
  const lockedClient = !isAdmin ? authUser?.clientName || "" : "";

  const [options, setOptions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showInfo, setShowInfo] = useState(false);

  // form
  const [client, setClient] = useState("");
  const [channel, setChannel] = useState("");
  const [inputType, setInputType] = useState("");
  const [language, setLanguage] = useState("");
  const [outputType, setOutputType] = useState("");
  const [uploadedDuration, setUploadedDuration] = useState(3000);
  const [createdDuration, setCreatedDuration] = useState(1500);
  const [uploadToCreateDays, setUploadToCreateDays] = useState(1);
  const [uploadedDurationOverflow, setUploadedDurationOverflow] =
    useState(false);
  const [createdDurationOverflow, setCreatedDurationOverflow] = useState(false);
  const [uploadToCreateDaysOverflow, setUploadToCreateDaysOverflow] =
    useState(false);

  const debounceRef = useRef(null);

  const token = localStorage.getItem("frammer_auth_token");
  const authHeaders = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token],
  );

  // ── fetch options (triggers model training on first ever call) ──────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const controller = new AbortController();
        // First call may train the model — allow up to 3 minutes
        const timeout = setTimeout(() => controller.abort(), 180_000);
        const res = await fetch(`${API_BASE}/publish-predictor/options`, {
          headers: authHeaders,
          signal: controller.signal,
        });
        clearTimeout(timeout);
        const data = await res.json();
        if (!res.ok)
          throw new Error(data?.error || `Server returned ${res.status}`);
        if (cancelled) return;
        setOptions(data);
        if (isAdmin) {
          if (data.clients?.length) setClient(data.clients[0]);
        } else {
          setClient(lockedClient || data.clients?.[0] || "");
        }
        if (data.input_types?.length) setInputType(data.input_types[0]);
        if (data.languages?.length) setLanguage(data.languages[0]);
        if (data.output_types?.length) setOutputType(data.output_types[0]);
        setUploadedDuration(
          Math.round((data.max_uploaded_duration || 15000) / 3),
        );
        setCreatedDuration(
          Math.round((data.max_created_duration || 10000) / 3),
        );
      } catch (err) {
        if (!cancelled) {
          const msg =
            err.name === "AbortError"
              ? "Model training timed out — refresh to retry (model may be cached now)"
              : err.message;
          setError(msg);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authHeaders, isAdmin, lockedClient]);

  useEffect(() => {
    if (!isAdmin && lockedClient && client !== lockedClient) {
      setClient(lockedClient);
    }
  }, [isAdmin, lockedClient, client]);

  // auto-set channel when client changes
  const selectedClient = isAdmin ? client : lockedClient || client;
  const availableChannels = useMemo(() => {
    if (!options?.channel_by_client || !selectedClient) return [];
    return options.channel_by_client[selectedClient] || [];
  }, [options, selectedClient]);

  const normalizedImpacts = useMemo(() => {
    const raw = Array.isArray(result?.shap_impacts) ? result.shap_impacts : [];
    const prepared = raw.map((item) => {
      const impact = Number(item?.impact || 0);
      return {
        feature: String(item?.feature || "Unknown"),
        impact,
        absImpact: Math.abs(impact),
      };
    });

    const totalAbsImpact = prepared.reduce(
      (sum, item) => sum + item.absImpact,
      0,
    );
    return prepared
      .map((item) => ({
        ...item,
        contributionPct:
          totalAbsImpact > 0 ? (item.absImpact / totalAbsImpact) * 100 : 0,
      }))
      .sort((a, b) => b.contributionPct - a.contributionPct);
  }, [result]);

  useEffect(() => {
    if (availableChannels.length > 0 && !availableChannels.includes(channel)) {
      setChannel(availableChannels[0]);
    }
  }, [availableChannels]);

  const uploadedDurationCap = Number(options?.max_uploaded_duration || 15000);
  const createdDurationCap = Number(options?.max_created_duration || 10000);
  const daysCap = 10;

  const effectiveUploadedDuration = uploadedDurationOverflow
    ? uploadedDurationCap
    : uploadedDuration;
  const effectiveCreatedDuration = createdDurationOverflow
    ? createdDurationCap
    : createdDuration;
  const effectiveUploadToCreateDays = uploadToCreateDaysOverflow
    ? daysCap
    : uploadToCreateDays;

  useEffect(() => {
    if (!uploadedDurationOverflow) return;
    setUploadedDuration(uploadedDurationCap);
  }, [uploadedDurationOverflow, uploadedDurationCap]);

  useEffect(() => {
    if (!createdDurationOverflow) return;
    setCreatedDuration(createdDurationCap);
  }, [createdDurationOverflow, createdDurationCap]);

  useEffect(() => {
    if (!uploadToCreateDaysOverflow) return;
    setUploadToCreateDays(daysCap);
  }, [uploadToCreateDaysOverflow, daysCap]);

  // ── predict (debounced) ────────────────────────────────────────────────
  const predict = useCallback(async () => {
    if (!selectedClient || !channel || !inputType || !language || !outputType)
      return;
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/publish-predictor/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify({
          client_name: selectedClient,
          assigned_channel: channel,
          input_type: inputType,
          language,
          output_type: outputType,
          uploaded_duration: effectiveUploadedDuration,
          created_duration: effectiveCreatedDuration,
          upload_to_create_days: effectiveUploadToCreateDays,
        }),
      });
      const payload = await res.json();
      if (!res.ok)
        throw new Error(payload?.error || `Prediction failed (${res.status})`);
      setResult(payload);
    } catch (err) {
      setError(err.message || "Prediction failed");
    }
  }, [
    selectedClient,
    channel,
    inputType,
    language,
    outputType,
    effectiveUploadedDuration,
    effectiveCreatedDuration,
    effectiveUploadToCreateDays,
    authHeaders,
  ]);

  useEffect(() => {
    if (!options || loading) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(predict, 350);
    return () => clearTimeout(debounceRef.current);
  }, [
    selectedClient,
    channel,
    inputType,
    language,
    outputType,
    effectiveUploadedDuration,
    effectiveCreatedDuration,
    effectiveUploadToCreateDays,
    options,
    loading,
  ]);

  // ── loading / error ────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <style>{`
          @keyframes oracleDot { 0%,100%{transform:translateY(0);opacity:.35} 50%{transform:translateY(-8px);opacity:1} }
        `}</style>
        <div className="flex gap-2 mb-4">
          {[0, 1, 2, 3, 4].map((i) => (
            <span
              key={i}
              className="block w-2.5 h-2.5 rounded-full bg-red-500"
              style={{
                animation: `oracleDot 1.2s ease-in-out ${i * 0.15}s infinite`,
              }}
            />
          ))}
        </div>
        <p className="text-sm font-black uppercase tracking-[0.2em] text-neutral-300">
          Initialising ML Model
        </p>
        <p className="mt-2 text-xs text-neutral-600">
          Training RandomForest classifier on first load — this is a one-time
          operation…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-6 py-4 text-sm text-red-400">
          {error}
        </div>
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
            <h3 className="text-sm font-black uppercase tracking-[0.12em] text-white">
              Publish Oracle
            </h3>
            <p className="text-[11px] text-neutral-500 mt-0.5">
              Interactive what-if simulation — tweak asset attributes and watch
              publish probability change in real time
            </p>
          </div>
        </div>

        {isAdmin && (
          <div className="flex items-center gap-2">
            {options?.accuracy != null && (
              <div className="rounded-lg border border-neutral-800 bg-[#111] px-3 py-1.5 text-[10px] font-bold text-neutral-400 tracking-wider">
                ACCURACY{" "}
                <span className="text-emerald-400 ml-1">
                  {(options.accuracy * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {options?.total_samples > 0 && (
              <div className="rounded-lg border border-neutral-800 bg-[#111] px-3 py-1.5 text-[10px] font-bold text-neutral-400 tracking-wider">
                {(options.total_samples / 1000).toFixed(0)}K{" "}
                <span className="text-neutral-500">SAMPLES</span>
              </div>
            )}
            <button
              onClick={() => setShowInfo((v) => !v)}
              className={`p-2 rounded-lg border transition-colors ${showInfo ? "border-red-500/40 bg-red-500/10 text-red-400" : "border-neutral-800 text-neutral-500 hover:text-white"}`}
            >
              <Info size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Info panel */}
      {isAdmin && showInfo && (
        <div className="rounded-xl border border-neutral-800 bg-[#0d0d0d] p-5 space-y-4">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-red-400">
            How it works
          </h4>
          <p className="text-xs text-neutral-400 leading-relaxed">
            A <strong className="text-white">RandomForest classifier</strong>{" "}
            (100 decision trees, balanced class weights) is trained on
            historical pipeline data. It learns patterns across{" "}
            <strong className="text-neutral-200">
              client, channel, content type, language, and duration
            </strong>{" "}
            to predict if an asset is likely to be published.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              ["100", "Decision Trees"],
              [
                `${options?.total_samples ? (options.total_samples / 1000).toFixed(0) + "K" : "—"}`,
                "Training Rows",
              ],
              ["8", "Feature Dims"],
              [`${options?.classes?.length || "—"}`, "Output Classes"],
              [
                `${options?.accuracy ? (options.accuracy * 100).toFixed(1) + "%" : "—"}`,
                "Test Accuracy",
              ],
            ].map(([val, lbl]) => (
              <div
                key={lbl}
                className="rounded-lg bg-neutral-900 p-3 text-center"
              >
                <div className="text-lg font-black text-white">{val}</div>
                <div className="text-[9px] text-neutral-500 uppercase tracking-wider">
                  {lbl}
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-neutral-600">
            Target classes: <span className="text-neutral-400">Published</span>{" "}
            and <span className="text-neutral-400">Not Published</span>.
          </p>
        </div>
      )}

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── Left: Configure ── */}
        <div className="lg:col-span-2 rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6 space-y-5">
          <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500">
            Configure Asset
          </h4>

          {isAdmin ? (
            <FilterSelect
              label="Client"
              value={client}
              onChange={setClient}
              options={(options?.clients || []).map((v) => ({
                label: v,
                value: v,
              }))}
            />
          ) : (
            <div>
              <label className="mb-0.5 block text-[9px] font-semibold uppercase tracking-[0.1em] text-neutral-600 select-none">
                Client
              </label>
              <div className="w-full h-[34px] rounded-lg border border-neutral-800 bg-[#0b0b0b] px-2.5 text-[12px] text-neutral-300 font-medium flex items-center">
                {selectedClient || "N/A"}
              </div>
            </div>
          )}

          <FilterSelect
            label="Channel"
            value={channel}
            onChange={setChannel}
            options={availableChannels.map((v) => ({ label: v, value: v }))}
          />

          <div className="grid grid-cols-2 gap-4">
            <FilterSelect
              label="Input Type"
              value={inputType}
              onChange={setInputType}
              options={(options?.input_types || []).map((v) => ({
                label: v,
                value: v,
              }))}
            />
            <FilterSelect
              label="Language"
              value={language}
              onChange={setLanguage}
              options={(options?.languages || []).map((v) => ({
                label: v,
                value: v,
              }))}
            />
          </div>

          <FilterSelect
            label="Output Type"
            value={outputType}
            onChange={setOutputType}
            options={(options?.output_types || []).map((v) => ({
              label: v,
              value: v,
            }))}
          />

          <div className="pt-3 border-t border-neutral-800/50 space-y-4">
            <div className="flex items-end gap-2">
              <div className="flex-1 min-w-0">
                <DurationSlider
                  label="Upload Duration"
                  value={uploadedDuration}
                  onChange={(v) => {
                    setUploadedDuration(v);
                    if (v < uploadedDurationCap)
                      setUploadedDurationOverflow(false);
                  }}
                  max={uploadedDurationCap}
                />
              </div>
              <button
                type="button"
                onClick={() => setUploadedDurationOverflow((prev) => !prev)}
                className={`h-[28px] w-[92px] shrink-0 inline-flex items-center justify-center text-center text-[10.5px] font-semibold rounded-md border transition-colors ${uploadedDurationOverflow ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 text-neutral-500 hover:text-neutral-300"}`}
              >
                {formatDurationCap(uploadedDurationCap)}
              </button>
            </div>

            <div className="flex items-end gap-2">
              <div className="flex-1 min-w-0">
                <DurationSlider
                  label="Created Duration"
                  value={createdDuration}
                  onChange={(v) => {
                    setCreatedDuration(v);
                    if (v < createdDurationCap)
                      setCreatedDurationOverflow(false);
                  }}
                  max={createdDurationCap}
                />
              </div>
              <button
                type="button"
                onClick={() => setCreatedDurationOverflow((prev) => !prev)}
                className={`h-[28px] w-[92px] shrink-0 inline-flex items-center justify-center text-center text-[10.5px] font-semibold rounded-md border transition-colors ${createdDurationOverflow ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 text-neutral-500 hover:text-neutral-300"}`}
              >
                {formatDurationCap(createdDurationCap)}
              </button>
            </div>

            <div className="flex items-end gap-2">
              <div className="flex-1 min-w-0">
                <DurationSlider
                  label="Days to Create"
                  value={uploadToCreateDays}
                  onChange={(v) => {
                    setUploadToCreateDays(v);
                    if (v < daysCap) setUploadToCreateDaysOverflow(false);
                  }}
                  max={daysCap}
                  unit="d"
                />
              </div>
              <button
                type="button"
                onClick={() => setUploadToCreateDaysOverflow((prev) => !prev)}
                className={`h-[28px] w-[92px] shrink-0 inline-flex items-center justify-center text-center text-[10.5px] font-semibold rounded-md border transition-colors ${uploadToCreateDaysOverflow ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 text-neutral-500 hover:text-neutral-300"}`}
              >
                {daysCap}+ days
              </button>
            </div>

            {(uploadedDurationOverflow ||
              createdDurationOverflow ||
              uploadToCreateDaysOverflow) && (
              <p className="text-[11px] text-neutral-500">
                Open-ended buckets map to capped model values to keep
                predictions stable.
              </p>
            )}
          </div>
        </div>

        {/* ── Right: Prediction ── */}
        <div className="lg:col-span-3 space-y-5">
          {/* Gauge */}
          <div className="rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6 flex flex-col items-center">
            {result ? (
              <ProbabilityGauge
                value={Number(result.publish_probability || 0)}
              />
            ) : (
              <div className="py-12 text-xs text-neutral-500">
                Waiting for first prediction…
              </div>
            )}

            {/* Predicted class pill */}
            {result && (
              <div className="mt-4 flex items-center gap-2">
                <span className="text-[10px] text-neutral-500 font-bold uppercase tracking-wider">
                  Most likely:
                </span>
                <span
                  className={`rounded-md px-3 py-1 text-xs font-bold border flex items-center gap-1.5 ${result.predicted_class === "1" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-red-500/10 border-red-500/30 text-red-300"}`}
                >
                  {result.predicted_class === "1" ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <XCircle size={13} />
                  )}
                  {result.predicted_class === "1"
                    ? "Publication Predicted"
                    : "Publication Unlikely"}
                </span>
              </div>
            )}
          </div>

          {/* RCA stats */}
          {result && (
            <div className="rounded-2xl border border-neutral-800 bg-[#0a0a0a] p-6">
              <h4 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500 mb-4">
                RCA Stats (Normalized Contribution)
              </h4>
              {!normalizedImpacts.length ? (
                <div className="text-sm text-neutral-600 italic py-4 text-center">
                  SHAP diagnostics unavailable for this prediction.
                </div>
              ) : (
                <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                  {normalizedImpacts.map((item, idx) => {
                    const impact = Number(item.impact || 0);
                    const positive = impact >= 0;
                    return (
                      <div
                        key={`${item.feature}-${idx}`}
                        className="flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-900/40 p-3"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`h-7 w-7 rounded-md flex items-center justify-center ${positive ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}
                            >
                              {positive ? (
                                <TrendingUp size={14} />
                              ) : (
                                <TrendingDown size={14} />
                              )}
                            </div>
                            <span className="text-sm text-neutral-200 truncate">
                              {formatFeatureName(item.feature)}
                            </span>
                          </div>
                          <div className="mt-2 h-1.5 w-full rounded-full bg-neutral-800 overflow-hidden">
                            <div
                              className={`h-full ${positive ? "bg-emerald-500" : "bg-rose-500"}`}
                              style={{
                                width: `${Math.max(0, Math.min(100, item.contributionPct))}%`,
                              }}
                            />
                          </div>
                        </div>
                        <div className="ml-4 text-right">
                          <div
                            className={`text-sm font-bold tabular-nums ${positive ? "text-emerald-400" : "text-rose-400"}`}
                          >
                            {item.contributionPct.toFixed(1)}%
                          </div>
                          <div className="text-[10px] text-neutral-500 tabular-nums">
                            {positive ? "+" : ""}
                            {impact.toFixed(3)} SHAP
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
