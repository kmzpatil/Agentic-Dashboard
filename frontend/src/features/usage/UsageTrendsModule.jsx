import React, {
  useState,
  useMemo,
  useEffect,
  useRef,
  useCallback,
} from "react";
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  BarChart2,
  LineChart as LineChartIcon,
  Maximize2,
  Minimize2,
  Download,
  Image as ImageIcon,
  CircleDot,
  Layers,
  ChevronDown,
  CalendarDays,
  SlidersHorizontal,
  X,
  History,
  Settings,
  Users,
  Globe,
  Filter,
  ArrowRight,
  Play,
  Calendar,
} from "lucide-react";
import { Line } from "react-chartjs-2";
import { useApi } from "../../hooks/useApi";
import { API_BASE } from "../../lib/constants";
import { formatNumber, formatPct } from "../../lib/formatters";
import {
  UsageTrendsSkeleton,
  ChartSkeleton,
  Skeleton,
} from "../../components/common/Skeleton";

const METRIC_GROUPS = [
  {
    label: "COUNTS",
    options: [
      { value: "uploaded_count", label: "Videos Uploaded" },
      { value: "created_count", label: "Assets Created" },
      { value: "published_count", label: "Posts Published" },
    ],
  },
  {
    label: "DURATIONS",
    options: [
      { value: "uploaded_duration", label: "Upload Duration" },
      { value: "created_duration", label: "Processing Time" },
      { value: "published_duration", label: "Published Duration" },
    ],
  },
  {
    label: "RATES",
    options: [
      { value: "publish_conversion_rate", label: "Publish Rate" },
      { value: "creation_rate", label: "Creation Rate" },
      { value: "processing_efficiency", label: "Processing Efficiency" },
      { value: "waste_index", label: "Waste Index" },
    ],
  },
  {
    label: "ADVANCED",
    options: [{ value: "turnaround_time", label: "Turnaround Time" }],
  },
];

// ─── FloatingDropdown ─────────────────────────────────────────────────────────
function FloatingDropdown({
  value,
  onChange,
  options,
  isGroups = false,
  minWidth = "240px",
  className = "",
  themeColor = "red",
  disabled = false,
  multiSelect = false,
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const getLabel = (val) => {
    if (multiSelect && Array.isArray(val)) {
      if (val.length === 0 || val.includes("All")) return "All";
      if (val.length === 1) return val[0];
      return `${val.length} selected`;
    }
    if (isGroups) {
      for (const group of options) {
        const opt = group.options.find((o) => o.value === val);
        if (opt) return opt.label;
      }
    } else {
      const opt = options.find(
        (o) => o.value === (Array.isArray(val) ? val[0] : val),
      );
      if (opt) return opt.label;
    }
    return Array.isArray(val) ? val[0] : val;
  };

  const handleSelect = (itemValue) => {
    if (!multiSelect) {
      onChange(itemValue);
      setOpen(false);
      return;
    }

    const current = Array.isArray(value) ? value : [value];
    let next;

    if (itemValue === "All") {
      next = ["All"];
    } else {
      const withoutAll = current.filter((v) => v !== "All");
      if (withoutAll.includes(itemValue)) {
        next = withoutAll.filter((v) => v !== itemValue);
        if (next.length === 0) next = ["All"];
      } else {
        next = [...withoutAll, itemValue];
      }
    }
    onChange(next);
  };

  const isOptionActive = (optValue) => {
    if (Array.isArray(value)) return value.includes(optValue);
    return value === optValue;
  };

  const themeClasses =
    themeColor === "red"
      ? "border-neutral-800 bg-[#0a0a0a]/80 text-neutral-200 hover:border-neutral-700 hover:bg-[#121212] focus:ring-red-500/30"
      : "border-red-500/30 bg-red-500/5 text-red-100 hover:bg-red-500/10 focus:ring-red-500/50";
  const dotColor = themeColor === "red" ? "bg-red-500" : "bg-red-400";

  return (
    <div
      ref={ref}
      className={`relative ${className}`}
      style={minWidth ? { minWidth } : {}}
    >
      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          if (!disabled) setOpen((o) => !o);
        }}
        className={`group w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border backdrop-blur-md text-sm font-bold transition-all outline-none shadow-lg ${themeClasses} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <span className="truncate">{getLabel(value)}</span>
        <ChevronDown
          size={16}
          className={`text-neutral-500 transition-transform duration-300 ${open ? "rotate-180 text-red-500" : "rotate-0"}`}
        />
      </button>
      {open && (
        <div
          className="absolute left-0 mt-2 w-full max-h-[400px] overflow-y-auto rounded-xl border border-neutral-800 bg-[#0d0d0d] backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[100] animate-in fade-in slide-in-from-top-2 duration-200"
          style={{ scrollbarWidth: "thin", scrollbarColor: "#333 #0d0d0d" }}
        >
          {isGroups ? (
            options.map((group, gi) => (
              <div
                key={group.label}
                className={gi > 0 ? "border-t border-neutral-900" : ""}
              >
                <div className="px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] text-neutral-600 bg-neutral-900/50">
                  {group.label}
                </div>
                <div className="p-1">
                  {group.options.map((opt) => {
                    const active = isOptionActive(opt.value);
                    return (
                      <button
                        key={opt.value}
                        onClick={() => handleSelect(opt.value)}
                        className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all flex items-center justify-between group/item ${
                          active
                            ? "bg-red-500/10 text-red-500 font-bold"
                            : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          {multiSelect && (
                            <div
                              className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${
                                active
                                  ? "bg-red-500 border-red-500"
                                  : "border-neutral-700 bg-neutral-900"
                              }`}
                            >
                              {active && (
                                <div className="w-1.5 h-1.5 rounded-full bg-white" />
                              )}
                            </div>
                          )}
                          {opt.label}
                        </span>
                        {active && !multiSelect && (
                          <div
                            className={`w-1.5 h-1.5 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.6)] ${dotColor}`}
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          ) : (
            <div className="p-1">
              {options.map((opt) => {
                const active = isOptionActive(opt.value);
                return (
                  <button
                    key={opt.value}
                    onClick={() => handleSelect(opt.value)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all flex items-center justify-between group/item ${
                      active
                        ? "bg-red-500/10 text-red-500 font-bold"
                        : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      {multiSelect && (
                        <div
                          className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${
                            active
                              ? "bg-red-500 border-red-500"
                              : "border-neutral-700 bg-neutral-900"
                          }`}
                        >
                          {active && (
                            <div className="w-1.5 h-1.5 rounded-full bg-white" />
                          )}
                        </div>
                      )}
                      {opt.label}
                    </span>
                    {active && !multiSelect && (
                      <div
                        className={`w-1.5 h-1.5 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.6)] ${dotColor}`}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── GranularityPills ─────────────────────────────────────────────────────────
const GRAN_OPTIONS = [
  { value: "day", label: "D" },
  { value: "week", label: "W" },
  { value: "month", label: "M" },
  { value: "quarter", label: "Q" },
];

function GranularityPills({ value, onChange }) {
  return (
    <div className="flex gap-1">
      {GRAN_OPTIONS.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`w-9 h-10 rounded-lg text-sm font-semibold transition-all cursor-pointer border flex items-center justify-center ${
              active
                ? "bg-neutral-800 border-neutral-600 text-white shadow-md"
                : "bg-transparent border-neutral-800 text-neutral-500 hover:border-neutral-700 hover:text-neutral-300"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ─── CutoffDatePicker ─────────────────────────────────────────────────────────
/**
 * A styled date input that lets the user pin the forecast horizon.
 * Clearing the input resets to "auto" (last complete period).
 */
function CutoffDatePicker({ value, onChange, maxDate }) {
  return (
    <div className="relative flex items-center">
      <CalendarDays
        size={14}
        className="absolute left-3 text-sky-400 pointer-events-none z-10"
      />
      <input
        type="date"
        value={value}
        max={maxDate}
        onChange={(e) => onChange(e.target.value)}
        className="pl-8 pr-8 py-3 rounded-xl border border-sky-500/30 bg-sky-500/5 text-sky-100 text-sm font-bold
                    focus:outline-none focus:ring-2 focus:ring-sky-500/40 transition-all
                    [color-scheme:dark] w-[180px]"
        title="Forecast start date (cutoff)"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2.5 text-sky-500/60 hover:text-sky-300 transition-colors"
          title="Reset to latest"
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}

function formatLongPeriod(period) {
  if (!period) return "";
  const date = new Date(period);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function parseIsoDate(value) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
}

function enumerateDates(startIso, endIso) {
  const start = parseIsoDate(startIso);
  const end = parseIsoDate(endIso);
  if (!start || !end || start > end) return [];

  const dates = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    dates.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
    if (dates.length > 5000) break;
  }
  return dates;
}

function DateRangeSlider({ dates, startIndex, endIndex, onChange }) {
  if (!dates.length) {
    return (
      <div className="rounded-[18px] border border-neutral-800 bg-[#111111] p-4 text-sm text-neutral-500">
        Date range unavailable.
      </div>
    );
  }

  const maxIndex = dates.length - 1;
  const safeStart = Math.min(Math.max(startIndex, 0), maxIndex);
  const safeEnd = Math.min(Math.max(endIndex, safeStart), maxIndex);
  const startPct = maxIndex === 0 ? 0 : (safeStart / maxIndex) * 100;
  const endPct = maxIndex === 0 ? 100 : (safeEnd / maxIndex) * 100;

  return (
    <div className="flex flex-col justify-center h-[46px] px-4 rounded-xl border border-neutral-800 bg-[#0a0a0a]/50">
      <div className="relative h-4 mt-2">
        <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-neutral-800" />
        <div
          className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-gradient-to-r from-red-500 to-red-400"
          style={{ left: `${startPct}%`, right: `${100 - endPct}%` }}
        />
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={safeStart}
          onChange={(event) => onChange(Number(event.target.value), safeEnd)}
          className="frammer-range absolute top-1/2 -translate-y-1/2 left-0 w-full h-4 z-20 cursor-pointer"
        />
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={safeEnd}
          onChange={(event) => onChange(safeStart, Number(event.target.value))}
          className="frammer-range absolute top-1/2 -translate-y-1/2 left-0 w-full h-4 z-30 cursor-pointer"
        />
      </div>

      <div className="mt-1.5 flex items-center justify-between text-[9px] font-black uppercase tracking-[0.12em] text-neutral-500 tabular-nums">
        <span>{dates[safeStart]}</span>
        <span>{dates[safeEnd]}</span>
      </div>
    </div>
  );
}

const MULTI_DIM_OPTIONS = [
  { value: "output_type", label: "Output Type" },
  { value: "input_type_proportion", label: "Input Type Proportion" },
  { value: "volume_dynamics", label: "Volume Dynamics" },
  { value: "duration_dynamics", label: "Duration Dynamics" },
  { value: "success_scores", label: "Success Scores" },
];

const MULTIDIM_COLORS = [
  "#38BDF8",
  "#F472B6",
  "#34D399",
  "#FBBF24",
  "#A78BFA",
  "#FB923C",
  "#60A5FA",
  "#F87171",
  "#4ADE80",
  "#E879F9",
];

const CLIENT_OPTIONAL_DIMS = new Set([
  "output_type",
  "input_type_proportion",
  "volume_dynamics",
  "duration_dynamics",
  "success_scores",
]);
const USER_OPTIONAL_DIMS = new Set([
  "output_type",
  "input_type_proportion",
  "volume_dynamics",
  "duration_dynamics",
  "success_scores",
]);
const MULTI_DIM_APPLY_DEBOUNCE_MS = 650;

function areStringArraysEqual(left = [], right = []) {
  if (left.length !== right.length) return false;
  for (let i = 0; i < left.length; i += 1) {
    if (left[i] !== right[i]) return false;
  }
  return true;
}

function formatMetricValue(metric, value) {
  if (metric.includes("rate") || metric.includes("efficiency"))
    return formatPct(value);
  return formatNumber(value);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Returns today's date as YYYY-MM-DD (used as the max value for the cutoff
 * date picker so users can't accidentally pick a future cutoff).
 */
function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Strips any trailing points where ALL non-date values are 0 or null.
 * Applied as a final safety net on the already-trimmed backend data so
 * that chart.js never renders a phantom zero drop at the right edge.
 */
function dropTrailingZeros(series) {
  let end = series.length - 1;
  while (end > 0 && !series[end].value) end--;
  return series.slice(0, end + 1);
}

function computeAnomaliesFromSeries(series) {
  if (!Array.isArray(series) || series.length < 3) return [];
  const values = series.map((point) => Number(point.value || 0));
  const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
  const variance = values.reduce((sum, val) => sum + (val - mean) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);

  const ranked = series.map((point) => {
    const value = Number(point.value || 0);
    const z = std === 0 ? 0 : (value - mean) / std;
    return { period: point.period, value, z };
  });

  return ranked
    .filter((point) => Math.abs(point.z) >= 1.5)
    .sort((a, b) => Math.abs(b.z) - Math.abs(a.z))
    .slice(0, 8)
    .map((point) => ({
      period: point.period,
      value: Number(point.value.toFixed(2)),
      zScore: Number(point.z.toFixed(2)),
      severity: Math.abs(point.z) >= 2.5 ? "high" : "medium",
      direction: point.z > 0 ? "spike" : "drop",
    }));
}

function toOptionList(values = []) {
  return values.map((value) => ({ value, label: value }));
}

function buildFilterParams(filters) {
  const params = new URLSearchParams();

  const appendMulti = (key, value) => {
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (v !== "All") params.append(key, v);
      });
    } else if (value && value !== "All") {
      params.append(key, value);
    }
  };

  appendMulti("company", filters.company);
  appendMulti("channel", filters.channel);
  appendMulti("user", filters.user);
  appendMulti("language", filters.language);
  appendMulti("input_type", filters.inputType);
  appendMulti("output_type", filters.outputType);

  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  return params.toString();
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function UsageTrendsModule({
  authUser,
  routeState,
  onNavigate,
}) {
  const defaultMetric =
    routeState.metric && routeState.metric !== "future_forecast"
      ? routeState.metric
      : "uploaded_count";

  const [metric, setMetric] = useState(defaultMetric);
  const [granularity, setGranularity] = useState(
    routeState?.granularity || "week",
  );
  const [isPredicting, setIsPredicting] = useState(
    Boolean(routeState?.isPredicting) ||
      routeState?.metric === "future_forecast",
  );
  const [predictionLength, setPredictionLength] = useState(7);
  /**
   * cutoffDate — ISO date string (YYYY-MM-DD) or empty string.
   * When non-empty it is forwarded to the backend as `cutoff_date` so that
   * Chronos starts forecasting from that specific date rather than from the
   * latest available data point.
   */
  const [cutoffDate, setCutoffDate] = useState("");
  const [multiDim, setMultiDim] = useState("output_type");
  const [clientFilter, setClientFilter] = useState(["All"]);
  const [userFilter, setUserFilter] = useState(["All"]);
  const [appliedMultiDimFilters, setAppliedMultiDimFilters] = useState({
    company: ["All"],
    user: ["All"],
    dateFrom: "",
    dateTo: "",
  });
  const [filters, setFilters] = useState({
    company:
      authUser?.role === "client_admin" ? [authUser.clientName] : ["All"],
    channel: ["All"],
    user: ["All"],
    language: ["All"],
    inputType: ["All"],
    outputType: ["All"],
    dateFrom: "",
    dateTo: "",
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);

  const [isMaximized, setIsMaximized] = useState(false);
  const [isFiltersOpen, setIsFiltersOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    return !window.matchMedia("(max-width: 1023px)").matches;
  });
  const [showPoints, setShowPoints] = useState(false);
  const [showStl, setShowStl] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const [comparisonOffset, setComparisonOffset] = useState(1);
  const chartRef = useRef(null);

  // ── Side effects ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (isMaximized) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
    document.body.style.overflow = "";
    return undefined;
  }, [isMaximized]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (chartRef.current?.resize) chartRef.current.resize();
      window.dispatchEvent(new Event("resize"));
    }, 80);
    return () => window.clearTimeout(timer);
  }, [isMaximized]);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const mediaQuery = window.matchMedia("(max-width: 1023px)");
    const handleChange = (event) => {
      if (event.matches) setIsFiltersOpen(false);
    };
    if (mediaQuery.matches) setIsFiltersOpen(false);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // Prediction mode only supports uploaded_count today
  useEffect(() => {
    if (isPredicting && metric !== "uploaded_count")
      setMetric("uploaded_count");
  }, [isPredicting, metric]);

  // Reset cutoff when prediction is toggled off
  useEffect(() => {
    if (!isPredicting) setCutoffDate("");
  }, [isPredicting]);

  const rateMetrics = useMemo(
    () =>
      new Set([
        "publish_conversion_rate",
        "creation_rate",
        "processing_efficiency",
        "waste_index",
      ]),
    [],
  );

  const resolvedMetric =
    metric === "turnaround_time" ? "turnaround_time" : metric;

  // workingFiltersQuery used for real-time validation and dynamic options
  const workingFiltersQuery = useMemo(
    () => buildFilterParams(filters),
    [filters],
  );
  const workingFiltersQuerySuffix = workingFiltersQuery
    ? `&${workingFiltersQuery}`
    : "";

  // appliedFiltersQuery used for charts, metrics, and trends
  const appliedFiltersQuery = useMemo(() => buildFilterParams(appliedFilters), [appliedFilters]);
  const appliedFiltersQuerySuffix = appliedFiltersQuery ? `&${appliedFiltersQuery}` : "";

  const effectiveCompany = filters.company && filters.company.length > 0 && filters.company[0] !== "All"
    ? filters.company[0]
    : "";
  const effectiveChannel = filters.channel && filters.channel.length > 0 && filters.channel[0] !== "All"
    ? filters.channel[0]
    : "";

  const filterOptionsUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (effectiveCompany) params.set("company", effectiveCompany);
    if (effectiveChannel) params.set("channel", effectiveChannel);
    const query = params.toString();
    return `${API_BASE}/usage-trends/v1/filters/options${query ? `?${query}` : ""}`;
  }, [effectiveCompany, effectiveChannel]);
  const { data: filterOptionsData, loading: filterOptionsLoading, error: filterOptionsError } = useApi(
    filterOptionsUrl,
    [filterOptionsUrl],
  );


  // [FIX] Scoped Filter Options for Multi-Dim section
  const multiDimCompany = useMemo(() => {
    if (authUser?.role === "client_admin") return authUser.clientName;
    if (authUser?.role === "website_admin") return clientFilter;
    return "";
  }, [authUser, clientFilter]);

  const multiDimFilterOptionsUrl = useMemo(() => {
    const p = new URLSearchParams();
    if (multiDimCompany) {
      if (Array.isArray(multiDimCompany)) {
        multiDimCompany.forEach((c) => p.append("company", c));
      } else {
        p.append("company", multiDimCompany);
      }
    }
    const q = p.toString();
    return `${API_BASE}/usage-trends/v1/filters/options${q ? `?${q}` : ""}`;
  }, [multiDimCompany]);

  const { data: multiDimFilterOptionsData } = useApi(multiDimFilterOptionsUrl, [
    multiDimFilterOptionsUrl,
  ]);

  const dateRangeUrl = `${API_BASE}/usage-trends/v1/filters/date-range`;
  const { data: dateRangeData } = useApi(dateRangeUrl, [dateRangeUrl]);

  const validateUrl = workingFiltersQuery
    ? `${API_BASE}/usage-trends/v1/filters/validate?${workingFiltersQuery}`
    : null;
  const { data: validateData } = useApi(validateUrl, [validateUrl]);

  const minDate =
    dateRangeData?.min_date || filterOptionsData?.date_range?.min_date || "";
  const maxDate =
    dateRangeData?.max_date || filterOptionsData?.date_range?.max_date || "";
  const sliderDates = useMemo(
    () => enumerateDates(minDate, maxDate),
    [minDate, maxDate],
  );

  const [multiDimStartIndex, setMultiDimStartIndex] = useState(0);
  const [multiDimEndIndex, setMultiDimEndIndex] = useState(0);
  const hasInitializedMultiDimDates = useRef(false);

  useEffect(() => {
    if (sliderDates.length > 0 && !hasInitializedMultiDimDates.current) {
      setMultiDimStartIndex(0);
      setMultiDimEndIndex(sliderDates.length - 1);
      hasInitializedMultiDimDates.current = true;
    }
  }, [sliderDates]);

  const applyMultiDimFilters = useCallback((nextFilters) => {
    setAppliedMultiDimFilters((prev) => {
      const sameCompany = areStringArraysEqual(
        prev.company || [],
        nextFilters.company || [],
      );
      const sameUser = areStringArraysEqual(
        prev.user || [],
        nextFilters.user || [],
      );
      const sameFrom = prev.dateFrom === nextFilters.dateFrom;
      const sameTo = prev.dateTo === nextFilters.dateTo;
      return sameCompany && sameUser && sameFrom && sameTo ? prev : nextFilters;
    });
  }, []);

  const handleApplyMultiDimFilters = () => {
    applyMultiDimFilters({
      company: clientFilter,
      user: userFilter,
      dateFrom: sliderDates[multiDimStartIndex] || "",
      dateTo: sliderDates[multiDimEndIndex] || "",
    });
  };

  useEffect(() => {
    if (!sliderDates.length) return;

    // Debounce multi-dim filter syncing so drag/select interactions don't spam API calls.
    const timer = window.setTimeout(() => {
      applyMultiDimFilters({
        company: clientFilter,
        user: userFilter,
        dateFrom: sliderDates[multiDimStartIndex] || "",
        dateTo: sliderDates[multiDimEndIndex] || "",
      });
    }, MULTI_DIM_APPLY_DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [
    clientFilter,
    userFilter,
    multiDimStartIndex,
    multiDimEndIndex,
    sliderDates,
    applyMultiDimFilters,
  ]);

  // ── API URLs ──────────────────────────────────────────────────────────────
  const metricsUrl = `${API_BASE}/usage-trends/v1/pipeline-metrics?granularity=${encodeURIComponent(granularity)}${appliedFiltersQuerySuffix}`;
  const {
    data: metricsData,
    loading: metricsLoading,
    error: metricsError,
  } = useApi(metricsUrl, [metricsUrl]);

  const forecastMetric =
    resolvedMetric === "turnaround_time" ? "uploaded_count" : resolvedMetric;
  const predictionUrl = useMemo(() => {
    if (!isPredicting) return null;
    let url =
      `${API_BASE}/usage-trends/v1/forecast/all-clients` +
      `?metric=${encodeURIComponent(forecastMetric)}` +
      `&granularity=${encodeURIComponent(granularity)}` +
      `&prediction_length=${predictionLength}${appliedFiltersQuerySuffix}`;
    if (cutoffDate) url += `&cutoff_date=${encodeURIComponent(cutoffDate)}`;
    return url;
  }, [
    isPredicting,
    forecastMetric,
    granularity,
    predictionLength,
    cutoffDate,
    appliedFiltersQuerySuffix,
  ]);

  const prediction = useApi(predictionUrl, [predictionUrl]);

  const multiDimUrl = useMemo(() => {
    if (multiDim === "none") return null;
    const params = new URLSearchParams();
    params.append("analysis", multiDim);
    params.append("granularity", granularity);

    if (
      appliedMultiDimFilters.company &&
      appliedMultiDimFilters.company[0] !== "All"
    ) {
      appliedMultiDimFilters.company.forEach((c) =>
        params.append("company", c),
      );
    }
    if (
      appliedMultiDimFilters.user &&
      appliedMultiDimFilters.user[0] !== "All"
    ) {
      appliedMultiDimFilters.user.forEach((u) => params.append("user", u));
    }
    if (appliedMultiDimFilters.dateFrom)
      params.append("date_from", appliedMultiDimFilters.dateFrom);
    if (appliedMultiDimFilters.dateTo)
      params.append("date_to", appliedMultiDimFilters.dateTo);

    // Mix in the global applied filters too
    if (appliedFiltersQuery) {
      const globalParams = new URLSearchParams(appliedFiltersQuery);
      for (const [key, value] of globalParams.entries()) {
        if (!params.has(key)) params.append(key, value);
      }
    }

    return `${API_BASE}/usage-trends/v1/multi-dim?${params.toString()}`;
  }, [multiDim, granularity, appliedMultiDimFilters, appliedFiltersQuery]);

  const {
    data: multiDimData,
    loading: multiDimLoading,
    error: multiDimError,
  } = useApi(multiDimUrl, [multiDimUrl]);

  const trendsUrl = `${API_BASE}/trends?metric=${encodeURIComponent(resolvedMetric)}&granularity=${encodeURIComponent(granularity)}${appliedFiltersQuerySuffix}`;
  const trends = useApi(trendsUrl, [trendsUrl]);

  const stlUrl = showStl
    ? `${API_BASE}/usage-trends/v1/stl?metric=${encodeURIComponent(resolvedMetric)}&granularity=${encodeURIComponent(granularity)}${appliedFiltersQuerySuffix}`
    : null;
  const stl = useApi(stlUrl, [stlUrl]);

  const insightsUrl = `${API_BASE}/insights?surface=trends${appliedFiltersQuerySuffix}`;
  const insights = useApi(insightsUrl, [insightsUrl]);

  const filterOptions = useMemo(() => {
    const base = {
      company: ["All"],
      channel: ["All"],
      user: ["All"],
      language: ["All"],
      input_type: ["All"],
      output_type: ["All"],
    };
    const apiFilters = filterOptionsData?.filters || {};
    return {
      company: apiFilters.company || base.company,
      channel: apiFilters.channel || base.channel,
      user: apiFilters.user || base.user,
      language: apiFilters.language || base.language,
      input_type: apiFilters.input_type || base.input_type,
      output_type: apiFilters.output_type || base.output_type,
    };
  }, [filterOptionsData]);

  const dateStartIndex = useMemo(() => {
    if (!sliderDates.length) return 0;
    const index = filters.dateFrom ? sliderDates.indexOf(filters.dateFrom) : 0;
    return index >= 0 ? index : 0;
  }, [sliderDates, filters.dateFrom]);
  const dateEndIndex = useMemo(() => {
    if (!sliderDates.length) return 0;
    const fallbackIndex = sliderDates.length - 1;
    const index = filters.dateTo
      ? sliderDates.indexOf(filters.dateTo)
      : fallbackIndex;
    return index >= 0 ? index : fallbackIndex;
  }, [sliderDates, filters.dateTo]);
  const activeFilterCount = useMemo(
    () =>
      Object.entries(filters).reduce((count, [key, value]) => {
        if (key === "dateFrom" || key === "dateTo")
          return value ? count + 1 : count;
        if (Array.isArray(value)) {
          const actualFilters = value.filter((v) => v !== "All");
          return count + actualFilters.length;
        }
        return value && value !== "All" ? count + 1 : count;
      }, 0),
    [filters],
  );

  useEffect(() => {
    if (!sliderDates.length) return;
    const nextStart =
      filters.dateFrom && sliderDates.includes(filters.dateFrom)
        ? filters.dateFrom
        : "";
    const nextEnd =
      filters.dateTo && sliderDates.includes(filters.dateTo)
        ? filters.dateTo
        : "";
    if (nextStart === filters.dateFrom && nextEnd === filters.dateTo) return;
    setFilters((prev) => ({
      ...prev,
      dateFrom: nextStart,
      dateTo: nextEnd,
    }));
  }, [sliderDates, filters.dateFrom, filters.dateTo]);

  // ── Data memos ────────────────────────────────────────────────────────────
  const historySeries = useMemo(() => {
    const rows = Array.isArray(metricsData?.data) ? metricsData.data : [];
    const grouped = new Map();
    rows.forEach((row) => {
      const dateKey = String(row.Date || "").slice(0, 10);
      if (!dateKey) return;
      const value = Number(row?.[resolvedMetric] || 0);
      if (!grouped.has(dateKey)) grouped.set(dateKey, { sum: 0, count: 0 });
      const bucket = grouped.get(dateKey);
      bucket.sum += value;
      bucket.count += 1;
    });
    const series = Array.from(grouped.entries())
      .sort(([a], [b]) => new Date(a) - new Date(b))
      .map(([period, bucket]) => ({
        period,
        value: rateMetrics.has(resolvedMetric)
          ? bucket.count
            ? bucket.sum / bucket.count
            : 0
          : bucket.sum,
      }));

    // Trim any trailing zero/null periods that slipped through (frontend safety net)
    return dropTrailingZeros(series);
  }, [metricsData, resolvedMetric, rateMetrics]);

  /**
   * Resolved cutoff used in chart annotations.
   * Prefer the user-chosen date; fall back to the `history_cutoff` returned
   * by the first client in the forecast payload.
   */
  const resolvedCutoff = useMemo(() => {
    if (cutoffDate) return cutoffDate;
    // [FIX] Auto cutoff must be last data point showing in plot
    if (historySeries.length > 0)
      return historySeries.at(-1).period.slice(0, 10);
    if (!prediction.data?.clients) return null;
    const first = Object.values(prediction.data.clients)[0];
    return first?.history_cutoff
      ? String(first.history_cutoff).slice(0, 10)
      : null;
  }, [cutoffDate, historySeries, prediction.data]);

  const predictionSeries = useMemo(() => {
    if (!isPredicting || prediction.loading || !prediction.data?.clients)
      return [];

    // Guard against stale renders while a new request is in flight
    if (
      prediction.data.metric !== forecastMetric ||
      prediction.data.prediction_length !== predictionLength
    )
      return [];

    const grouped = new Map();
    const forecastKey = `Forecast_${forecastMetric}`;

    Object.values(prediction.data.clients).forEach((clientPayload) => {
      // Skip clients that had no data before the cutoff (backend sends a warning)
      if (clientPayload?.warning) return;
      const rows = Array.isArray(clientPayload?.forecast)
        ? clientPayload.forecast
        : [];
      rows.forEach((row) => {
        const dateKey = String(row.Date || "").slice(0, 10);
        if (!dateKey) return;
        const value = Number(row?.[forecastKey] || 0);
        if (!grouped.has(dateKey)) grouped.set(dateKey, { sum: 0, count: 0 });
        const bucket = grouped.get(dateKey);
        bucket.sum += value;
        bucket.count += 1;
      });
    });

    return Array.from(grouped.entries())
      .sort(([a], [b]) => new Date(a) - new Date(b))
      .map(([period, bucket]) => ({
        period,
        value: rateMetrics.has(resolvedMetric)
          ? bucket.count
            ? bucket.sum / bucket.count
            : 0
          : bucket.sum,
      }));
  }, [
    prediction.data,
    prediction.loading,
    resolvedMetric,
    forecastMetric,
    rateMetrics,
    isPredicting,
    predictionLength,
  ]);

  /** Count of clients skipped because they had no data before the cutoff */
  const skippedClientsCount = useMemo(() => {
    if (!prediction.data?.clients) return 0;
    return Object.values(prediction.data.clients).filter((c) => c?.warning)
      .length;
  }, [prediction.data]);

  const summary = useMemo(() => {
    const latest = historySeries[historySeries.length - 1] || null;
    const previous = historySeries[historySeries.length - 2] || null;
    const deltaPct =
      latest && previous && previous.value !== 0
        ? ((latest.value - previous.value) / previous.value) * 100
        : null;
    return {
      latestValue: latest ? latest.value : 0,
      latestPeriod: latest ? latest.period : null,
      deltaVsPreviousPct: deltaPct,
    };
  }, [historySeries]);

  const computedAnomalies = useMemo(
    () => computeAnomaliesFromSeries(historySeries),
    [historySeries],
  );

  // Merge client-side + backend anomalies, dedup by period, keep higher |zScore|
  const mergedAnomalies = useMemo(() => {
    const byPeriod = new Map();
    (computedAnomalies || []).forEach(a => {
      const key = String(a.period || '').slice(0, 10);
      if (key) byPeriod.set(key, { ...a, period: key });
    });
    (trends.data?.anomalies || []).forEach(a => {
      const key = String(a.period || '').slice(0, 10);
      if (!key) return;
      const existing = byPeriod.get(key);
      if (!existing || Math.abs(a.zScore || 0) > Math.abs(existing.zScore || 0)) {
        byPeriod.set(key, { ...a, period: key });
      }
    });
    return Array.from(byPeriod.values())
      .sort((a, b) => Math.abs(b.zScore || 0) - Math.abs(a.zScore || 0));
  }, [computedAnomalies, trends.data]);

  const chartData = useMemo(() => {
    const historyByDate = new Map(
      historySeries.map((p) => [p.period, Number(p.value || 0)]),
    );
    const predictionByDate = new Map(
      predictionSeries.map((p) => [p.period, Number(p.value || 0)]),
    );

    const labels = Array.from(
      new Set([...historyByDate.keys(), ...predictionByDate.keys()]),
    ).sort((a, b) => new Date(a) - new Date(b));

    // Map of anomaly date → method metadata for O(1) lookup in point callbacks
    const anomalyPriority = {
      zscore: 1,
      seasonal_deviation: 2,
      trend_reversal: 3,
    };
    const anomalyDates = new Map();
    (computedAnomalies || []).forEach((a) => {
      const key = String(a.period || "").slice(0, 10);
      if (!key) return;
      anomalyDates.set(key, {
        direction: a.direction,
        method: "zscore",
        severity: a.severity || "medium",
      });
    });
    (trends.data?.anomalies || []).forEach((a) => {
      const key = String(a.period || "").slice(0, 10);
      const next = {
        direction: a.direction,
        method: a.method || "zscore",
        severity: a.severity || "medium",
      };
      const current = anomalyDates.get(key);
      if (
        !current ||
        anomalyPriority[next.method] >= anomalyPriority[current.method]
      ) {
        anomalyDates.set(key, next);
      }
    });

    const datasets = [
      {
        label: resolvedMetric.replace(/_/g, " "),
        data: labels.map((l) =>
          historyByDate.has(l) ? historyByDate.get(l) : null,
        ),
        borderColor: "#EF4444",
        backgroundColor: "rgba(239, 68, 68, 0.15)",
        tension: 0.25,
        borderWidth: 2,
        fill: true,
        // Anomaly points always shown (larger + colored) regardless of showPoints toggle
        pointRadius: (ctx) => {
          const date = labels[ctx.dataIndex];
          const anomaly = anomalyDates.get(date);
          if (anomaly) return anomaly.severity === "high" ? 7 : 5;
          return showPoints ? 3 : 0;
        },
        pointHoverRadius: (ctx) => {
          const date = labels[ctx.dataIndex];
          const anomaly = anomalyDates.get(date);
          if (anomaly) return anomaly.severity === "high" ? 10 : 8;
          return 5;
        },
        pointBackgroundColor: (ctx) => {
          const date = labels[ctx.dataIndex];
          const anomaly = anomalyDates.get(date);
          if (!anomaly) return "#EF4444";
          return anomaly.direction === "drop" ? "#F59E0B" : "#34D399";
        },
        pointBorderColor: (ctx) => {
          const date = labels[ctx.dataIndex];
          const anomaly = anomalyDates.get(date);
          if (!anomaly) return "#EF4444";
          if (anomaly.method === "seasonal_deviation") return "#E5E7EB";
          return "transparent";
        },
        pointBorderWidth: (ctx) => {
          const date = labels[ctx.dataIndex];
          const anomaly = anomalyDates.get(date);
          if (!anomaly) return 0;
          return anomaly.method === "seasonal_deviation" ? 1.5 : 0;
        },
        pointStyle: "circle",
        anomalyMethodMeta: Object.fromEntries(anomalyDates),
      },
    ];

    if (isPredicting && predictionSeries.length > 0) {
      datasets.push({
        label: cutoffDate
          ? `Forecast (from ${cutoffDate})`
          : resolvedCutoff
            ? `Forecast (from ${resolvedCutoff})`
            : "Forecast",
        data: labels.map((l) => predictionByDate.has(l) ? predictionByDate.get(l) : null),
        borderColor: "#38BDF8",
        backgroundColor: "rgba(56, 189, 248, 0.08)",
        borderWidth: 2,
        tension: 0.25,
        borderDash: [5, 5],
        fill: false,
        pointRadius: showPoints ? 2 : 0,
        pointHoverRadius: 4,
      });
    }

    if (showComparison && historySeries.length > 0) {
      // Create lagged series
      const laggedData = labels.map((label, idx) => {
        const sourceIdx = idx - comparisonOffset;
        if (sourceIdx >= 0) {
          const sourceDate = labels[sourceIdx];
          return historyByDate.get(sourceDate);
        }
        return null;
      });

      datasets.push({
        label: `${resolvedMetric.replace(/_/g, " ")} (${comparisonOffset}p Lag)`,
        data: laggedData,
        borderColor: "#A855F7", // Purple-500
        backgroundColor: "transparent",
        borderWidth: 2,
        tension: 0.25,
        borderDash: [3, 3],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 4,
      });
    }

    return { labels, datasets };
  }, [
    historySeries, resolvedMetric, predictionSeries,
    isPredicting, showPoints, cutoffDate, resolvedCutoff,
    computedAnomalies, trends.data, showComparison, comparisonOffset,
  ]);

  const multiDimChartData = useMemo(() => {
    if (!multiDimData?.data || !multiDimData?.series_keys) return null;
    const labels = multiDimData.data
      .map((row) => String(row.Date || "").slice(0, 10))
      .sort();
    const dataByDate = {};
    multiDimData.data.forEach((row) => {
      dataByDate[String(row.Date || "").slice(0, 10)] = row;
    });
    const datasets = multiDimData.series_keys.map((key, idx) => ({
      label: multiDimData.labels?.[key] || key.replace(/_/g, " "),
      data: labels.map((d) => Number(dataByDate[d]?.[key] || 0)),
      borderColor: MULTIDIM_COLORS[idx % MULTIDIM_COLORS.length],
      backgroundColor: `${MULTIDIM_COLORS[idx % MULTIDIM_COLORS.length]}22`,
      borderWidth: 2,
      tension: 0.25,
      fill: false,
      pointRadius: showPoints ? 2 : 0,
      pointHoverRadius: 4,
    }));
    return { labels, datasets };
  }, [multiDimData, showPoints]);

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#d1d5db" } },
        // Draw a subtle cross marker inside trend reversal anomaly dots.
        anomalyReversalMarker: {
          id: "anomalyReversalMarker",
          afterDatasetsDraw(chart) {
            const labels = chart.data.labels || [];
            const dataset = chart.data.datasets?.[0];
            const methodMeta = dataset?.anomalyMethodMeta;
            if (!dataset || !methodMeta) return;

            const meta = chart.getDatasetMeta(0);
            const points = meta?.data || [];
            const ctx = chart.ctx;
            ctx.save();
            ctx.strokeStyle = "#E5E7EB";
            ctx.lineWidth = 1;

            points.forEach((point, index) => {
              const date = String(labels[index] || "").slice(0, 10);
              const anomaly = methodMeta[date];
              if (!anomaly || anomaly.method !== "trend_reversal") return;

              const { x, y } = point.getProps(["x", "y"], true);
              const crossSize = 2;
              ctx.beginPath();
              ctx.moveTo(x - crossSize, y);
              ctx.lineTo(x + crossSize, y);
              ctx.moveTo(x, y - crossSize);
              ctx.lineTo(x, y + crossSize);
              ctx.stroke();
            });

            ctx.restore();
          },
        },
      },
      scales: {
        x: {
          ticks: { color: "#9ca3af" },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
        y: {
          ticks: { color: "#9ca3af" },
          grid: { color: "rgba(255,255,255,0.05)" },
        },
      },
    }),
    [],
  );

  // ── Export handlers ───────────────────────────────────────────────────────
  const handleExportCsv = () => {
    if (!chartData) return;
    let csv = `Date,${resolvedMetric}${isPredicting ? ",AI_Forecast" : ""}\n`;
    chartData.labels.forEach((label, i) => {
      const historyVal =
        chartData.datasets[0].data[i] !== null
          ? chartData.datasets[0].data[i]
          : "";
      const forecastVal =
        isPredicting && chartData.datasets[1]
          ? chartData.datasets[1].data[i] !== null
            ? chartData.datasets[1].data[i]
            : ""
          : "";
      csv += `${label},${historyVal}${isPredicting ? `,${forecastVal}` : ""}\n`;
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `usage_trends_${resolvedMetric}_${granularity}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExportImage = () => {
    if (chartRef.current?.canvas) {
      const url = chartRef.current.canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `usage_trends_chart.png`;
      a.click();
    }
  };

  // ── Early returns ─────────────────────────────────────────────────────────
  if (metricsLoading)
    return (
      <div className="p-6">
        <UsageTrendsSkeleton />
      </div>
    );
  if (metricsError)
    return (
      <div className="p-6 text-red-500 font-medium">
        Failed to load data: {metricsError}
      </div>
    );

  const anomalies = mergedAnomalies;
  const needsClientFilter = CLIENT_OPTIONAL_DIMS.has(multiDim);
  const needsUserFilter = USER_OPTIONAL_DIMS.has(multiDim);
  const hasDataForFilters = validateData?.has_data;

  const handleDateRangeChange = (nextStartIndex, nextEndIndex) => {
    if (!sliderDates.length) return;
    const maxIndex = sliderDates.length - 1;
    const safeStart = Math.min(
      Math.max(Math.min(nextStartIndex, nextEndIndex), 0),
      maxIndex,
    );
    const safeEnd = Math.min(
      Math.max(Math.max(nextStartIndex, nextEndIndex), 0),
      maxIndex,
    );
    setFilters((prev) => ({
      ...prev,
      dateFrom: safeStart === 0 ? "" : sliderDates[safeStart],
      dateTo: safeEnd === maxIndex ? "" : sliderDates[safeEnd],
    }));
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className={`h-full overflow-y-auto bg-[#050505] px-4 md:px-8 text-neutral-200 frammer-scrollbar ${isMaximized ? "fixed inset-0 z-50 overflow-hidden !p-8 bg-[#0a0a0a]" : "space-y-8"
        }`}
    >
      {/* ── Custom scrollbar styles ── */}
      <style>{`
          .frammer-scrollbar::-webkit-scrollbar,
          .frammer-anomaly-scroll::-webkit-scrollbar { width: 4px; }
          .frammer-scrollbar::-webkit-scrollbar-track,
          .frammer-anomaly-scroll::-webkit-scrollbar-track { background: transparent; }
          .frammer-scrollbar::-webkit-scrollbar-thumb,
          .frammer-anomaly-scroll::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 9999px; }
          .frammer-scrollbar::-webkit-scrollbar-thumb:hover,
          .frammer-anomaly-scroll::-webkit-scrollbar-thumb:hover { background: #ef4444; }
          .frammer-scrollbar, .frammer-anomaly-scroll { scrollbar-width: thin; scrollbar-color: #2a2a2a transparent; }
          .frammer-scrollbar:hover, .frammer-anomaly-scroll:hover { scrollbar-color: #ef4444 transparent; }
          .frammer-range {
            -webkit-appearance: none;
            appearance: none;
            pointer-events: none;
            background: transparent;
          }
          .frammer-range:focus { outline: none; }
          .frammer-range::-webkit-slider-runnable-track {
            height: 6px;
            background: rgba(255,255,255,0.08);
            border-radius: 3px;
          }
          .frammer-range::-moz-range-track {
            height: 6px;
            background: rgba(255,255,255,0.08);
            border-radius: 3px;
          }
          .frammer-range::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            pointer-events: auto;
            width: 18px;
            height: 18px;
            border-radius: 9999px;
            background: #fafafa;
            border: 2px solid #ef4444;
            box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.15);
            cursor: pointer;
            margin-top: -6px; /* (6px track - 18px thumb) / 2 */
          }
          .comparison-slider::-webkit-slider-thumb {
            background: #A855F7 !important;
            border: 2px solid #000 !important;
            box-shadow: 0 0 10px rgba(168, 85, 247, 0.4) !important;
          }
          .comparison-slider::-webkit-slider-runnable-track {
            background: rgba(168, 85, 247, 0.1) !important;
          }
          .frammer-range::-moz-range-thumb {
            pointer-events: auto;
            width: 18px;
            height: 18px;
            border-radius: 9999px;
            background: #fafafa;
            border: 2px solid #ef4444;
            box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.15);
            cursor: pointer;
          }
          .comparison-slider::-moz-range-thumb {
            background: #fafafa !important;
            border: 2px solid #A855F7 !important;
            box-shadow: 0 0 0 4px rgba(168, 85, 247, 0.15) !important;
          }
          .comparison-slider {
            pointer-events: auto !important;
          }
        `}</style>
      {!isMaximized && (
        <>
          {/* ── Controls bar ──────────────────────────────────────────────── */}
          <section className="relative z-[60] rounded-[24px] border border-neutral-800/80 bg-[#101010]/80 backdrop-blur-md p-6 shadow-xl transition-all duration-300 hover:border-neutral-700/80">
            <div className="flex flex-wrap lg:flex-nowrap items-start gap-5">
              {/* Metric */}
              <div className="group shrink-0">
                <div className="h-5 mb-2 flex items-end">
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] leading-none text-neutral-500 group-hover:text-neutral-300 transition-colors">
                    Metric Selection
                  </label>
                </div>
                <FloatingDropdown
                  value={metric}
                  onChange={setMetric}
                  options={METRIC_GROUPS}
                  isGroups={true}
                  disabled={isPredicting}
                  minWidth=""
                  className="w-full lg:min-w-[240px]"
                />
              </div>

              {/* Granularity */}
              <div className="group shrink-0">
                <div className="h-5 mb-2 flex items-end">
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] leading-none text-neutral-500 group-hover:text-neutral-300 transition-colors">
                    Granularity
                  </label>
                </div>
                <GranularityPills
                  value={granularity}
                  onChange={setGranularity}
                />
              </div>

              {/* Forecast toggle + controls */}
              <div className="group shrink-0">
                <div className="h-5 mb-2 flex items-center gap-3">
                  <label className="text-[10px] font-bold uppercase tracking-[0.2em] leading-none text-neutral-500 group-hover:text-neutral-300 transition-colors">
                    Forecast
                  </label>
                  <button
                    type="button"
                    aria-pressed={isPredicting}
                    onClick={() => {
                      setIsPredicting((v) => {
                        const next = !v;
                        if (next) setMetric("uploaded_count");
                        return next;
                      });
                    }}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full border transition-all ${
                      isPredicting
                        ? "border-red-500/60 bg-red-500/20"
                        : "border-neutral-700 bg-[#0a0a0a]/90"
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                        isPredicting ? "translate-x-[18px]" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>

                {/* Forecast sub-controls — only visible when predicting */}
                <div className="min-h-[46px]">
                  {isPredicting && (
                    <div className="flex items-center gap-3">
                      <FloatingDropdown
                        value={predictionLength}
                        onChange={setPredictionLength}
                        themeColor="forecast"
                        minWidth="130px"
                        options={[
                          { value: 7, label: "7 Periods" },
                          { value: 30, label: "30 Periods" },
                          { value: 60, label: "60 Periods" },
                          { value: 90, label: "90 Periods" },
                        ]}
                      />
                      <CutoffDatePicker
                        value={cutoffDate}
                        onChange={setCutoffDate}
                        maxDate={todayIso()}
                      />
                    </div>
                  )}
                </div>

                {/* Cutoff hint */}
                {isPredicting && (
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <CalendarDays size={11} className="text-sky-500/60" />
                    <span className="text-[10px] text-sky-500/60">
                      {cutoffDate
                        ? `Forecast starts after ${cutoffDate}`
                        : resolvedCutoff
                          ? `Auto cutoff: ${resolvedCutoff}`
                          : "Set a cutoff date to pin the forecast start"}
                    </span>
                  </div>
                )}

                {/* Skipped-clients warning */}
                {isPredicting && skippedClientsCount > 0 && (
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <AlertTriangle size={11} className="text-amber-500/70" />
                    <span className="text-[10px] text-amber-500/70">
                      {skippedClientsCount} client
                      {skippedClientsCount > 1 ? "s" : ""} skipped — no data
                      before cutoff date
                    </span>
                  </div>
                )}
              </div>

              <div className="hidden lg:block self-stretch w-px bg-neutral-800/70" />

              {/* KPI strip */}
              <section className="w-full xl:w-auto xl:flex-1 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 xl:gap-0 items-end">
                {/* KPI 1: This Period */}
                <div className="rounded-xl border border-neutral-800/50 bg-neutral-900/20 px-4 py-3 xl:px-3 xl:py-2 xl:bg-transparent xl:border-neutral-900/70">
                  <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
                    This Period
                  </div>
                  <div className="mt-1 text-xl xl:text-lg font-bold leading-tight text-white">
                    {formatMetricValue(resolvedMetric, summary.latestValue)}
                  </div>
                  <div className="mt-0.5 text-[11px] text-neutral-500">
                    {summary.latestPeriod
                      ? formatLongPeriod(summary.latestPeriod)
                      : "No data"}
                  </div>
                </div>

                {/* KPI 2: vs Last Period */}
                <div className="rounded-xl border border-neutral-800/50 bg-neutral-900/20 px-4 py-3 xl:px-3 xl:py-2 xl:ml-4 xl:pl-4 xl:bg-transparent xl:border-neutral-900/70 xl:border-l xl:border-l-neutral-800/70">
                  {(() => {
                    const deltaNum = summary.deltaVsPreviousPct;
                    const deltaUp = deltaNum !== null && deltaNum > 0;
                    return (
                      <>
                        <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
                          VS Last Period
                        </div>
                        <div className="mt-1 text-lg font-bold leading-tight text-white">
                          {deltaNum === null ? (
                            "—"
                          ) : (
                            <span
                              className={`inline-flex items-center gap-1 ${deltaUp ? "text-emerald-400" : "text-red-400"}`}
                            >
                              {deltaUp ? (
                                <TrendingUp size={14} />
                              ) : (
                                <TrendingDown size={14} />
                              )}
                              {Math.abs(deltaNum).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <div className="mt-0.5 text-[11px] text-neutral-500">
                          {deltaNum === null
                            ? "—"
                            : deltaUp
                              ? "Increase"
                              : Math.abs(deltaNum) > 50
                                ? "Significant drop"
                                : "Decrease"}
                        </div>
                      </>
                    );
                  })()}
                </div>

                {/* KPI 3: Date Range */}
                <div className="rounded-lg border border-neutral-900/70 bg-transparent px-3 py-2 md:ml-4 md:pl-4 md:border-l md:border-l-neutral-800/70">
                  <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
                    Date Range
                  </div>
                  <div className="mt-1 text-lg font-bold leading-tight text-white">
                    {`${historySeries.length} ${granularity}s`}
                  </div>
                  <div className="mt-0.5 text-[11px] text-neutral-500">
                    {historySeries.length > 0
                      ? `${historySeries[0].period.slice(0, 10)} – ${historySeries.at(-1).period.slice(0, 10)}`
                      : "—"}
                  </div>
                </div>
              </section>
            </div>
          </section>
        </>
      )}

      <section
        className={`${
          isMaximized
            ? "h-full"
            : "grid grid-cols-1 lg:grid-cols-[auto_1fr] xl:grid-cols-[auto_minmax(0,1fr)_300px] gap-6 items-stretch"
        }`}
      >
        {!isMaximized && (
          <aside
            className={`rounded-[24px] border border-neutral-800 bg-[#0e0e0e] shadow-xl transition-all duration-300 hover:border-neutral-700 flex flex-col h-auto lg:h-[560px] w-full ${
              isFiltersOpen ? "lg:w-[240px]" : "lg:w-[56px]"
            }`}
          >
            <div className="flex-shrink-0 border-b border-neutral-800/60 bg-[#121212] px-3 py-3 rounded-t-[24px]">
              <div className="hidden lg:flex items-center justify-between gap-2">
                {isFiltersOpen && (
                  <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                    <SlidersHorizontal size={14} className={`flex-shrink-0 ${activeFilterCount > 0 ? "text-red-400" : "text-neutral-500"}`} />
                    <div className="min-w-0 overflow-hidden">
                      <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-neutral-300 leading-none truncate">Filters</div>
                      <div className={`mt-0.5 text-[10px] font-semibold leading-none ${activeFilterCount > 0 ? "text-red-400" : "text-neutral-600"}`}>
                        {activeFilterCount > 0 ? `${activeFilterCount} applied` : "None applied"}
                      </div>
                    </div>
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setIsFiltersOpen((prev) => !prev)}
                  className="flex-shrink-0 inline-flex h-7 w-7 items-center justify-center rounded-full border border-neutral-800 bg-[#0f0f0f] text-neutral-400 transition-colors hover:border-neutral-700 hover:text-white"
                  title={isFiltersOpen ? "Collapse" : "Expand filters"}
                >
                  <ChevronDown
                    size={13}
                    className={`transition-transform duration-200 ${isFiltersOpen ? "rotate-90" : "-rotate-90"}`}
                  />
                </button>
              </div>
              <button
                type="button"
                onClick={() => setIsFiltersOpen((prev) => !prev)}
                className="flex w-full items-center justify-between text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-400 lg:hidden"
                title={isFiltersOpen ? "Collapse" : "Expand filters"}
              >
                <span>Filters</span>
                <ChevronDown size={14} className={`transition-transform ${isFiltersOpen ? "rotate-180" : "rotate-0"}`} />
              </button>
            </div>

            {/* Collapsed state — icon badge only */}
            {!isFiltersOpen && (
              <div className="flex flex-col items-center gap-3 pt-4 pb-3 lg:flex">
                <div className="relative hidden lg:block">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full border transition-colors ${activeFilterCount > 0 ? "border-red-500/30 bg-red-500/10" : "border-neutral-800 bg-transparent"
                    }`}>
                    <SlidersHorizontal size={14} className={activeFilterCount > 0 ? "text-red-400" : "text-neutral-600"} />
                  </div>
                  {activeFilterCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-black text-white leading-none">
                      {activeFilterCount}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Expanded state — scrollable list + sticky footer */}
            {isFiltersOpen && (
              <>
                {/* Scrollable filter list — fills space between header and footer */}
                <div className="flex-1 overflow-y-auto frammer-scrollbar min-h-0">
                  <div className="space-y-3 p-3">
                    {/* HIDE Client filter for client_admin and user roles */}
                    {authUser?.role !== "client_admin" &&
                      authUser?.role !== "user" && (
                        <div className="group">
                          <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                            Client
                          </label>
                          <FloatingDropdown
                            value={filters.company}
                            onChange={(value) =>
                              setFilters((prev) => ({
                                ...prev,
                                company: value,
                                channel: ["All"],
                                user: ["All"],
                                language: ["All"],
                                inputType: ["All"],
                                outputType: ["All"],
                              }))
                            }
                            options={toOptionList(filterOptions.company)}
                            minWidth="100%"
                            multiSelect={true}
                          />
                        </div>
                      )}
                    <div className="group">
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                        Channel
                      </label>
                      <FloatingDropdown
                        value={filters.channel}
                        onChange={(v) =>
                          setFilters((p) => ({ ...p, channel: v }))
                        }
                        options={toOptionList(filterOptions.channel)}
                        minWidth="100%"
                        multiSelect={true}
                      />
                    </div>
                    {/* HIDE User filter for user role */}
                    {authUser?.role !== "user" && (
                      <div className="group">
                        <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                          User
                        </label>
                        <FloatingDropdown
                          value={filters.user}
                          onChange={(v) =>
                            setFilters((p) => ({ ...p, user: v }))
                          }
                          options={toOptionList(filterOptions.user)}
                          minWidth="100%"
                          multiSelect={true}
                        />
                      </div>
                    )}
                    <div className="group">
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                        Language
                      </label>
                      <FloatingDropdown
                        value={filters.language}
                        onChange={(v) =>
                          setFilters((p) => ({ ...p, language: v }))
                        }
                        options={toOptionList(filterOptions.language)}
                        minWidth="100%"
                        multiSelect={true}
                      />
                    </div>
                    <div className="group">
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                        Input Type
                      </label>
                      <FloatingDropdown
                        value={filters.inputType}
                        onChange={(v) =>
                          setFilters((p) => ({ ...p, inputType: v }))
                        }
                        options={toOptionList(filterOptions.input_type)}
                        minWidth="100%"
                        multiSelect={true}
                      />
                    </div>
                    <div className="group">
                      <label className="mb-1 block text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-600">
                        Output Type
                      </label>
                      <FloatingDropdown
                        value={filters.outputType}
                        onChange={(v) =>
                          setFilters((p) => ({ ...p, outputType: v }))
                        }
                        options={toOptionList(filterOptions.output_type)}
                        minWidth="100%"
                        multiSelect={true}
                      />
                    </div>

                    <DateRangeSlider
                      dates={sliderDates}
                      startIndex={dateStartIndex}
                      endIndex={dateEndIndex}
                      onChange={handleDateRangeChange}
                    />

                    {/* Validation status */}
                    <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] px-3 py-2 text-[10px]">
                      {filterOptionsLoading && (
                        <span className="text-neutral-600">
                          Loading options…
                        </span>
                      )}
                      {filterOptionsError && (
                        <span className="text-amber-400">
                          Failed to load options.
                        </span>
                      )}
                      {!filterOptionsLoading &&
                        workingFiltersQuery &&
                        hasDataForFilters === false && (
                          <span className="text-red-400">
                            No data for this combination.
                          </span>
                        )}
                      {!filterOptionsLoading &&
                        workingFiltersQuery &&
                        hasDataForFilters === true && (
                          <span className="text-emerald-400">
                            Filters validated.
                          </span>
                        )}
                      {!filterOptionsLoading && !workingFiltersQuery && (
                        <span className="text-neutral-600">
                          Using full dataset.
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Sticky footer — Apply + Reset always visible at bottom */}
                <div className="flex-shrink-0 border-t border-neutral-800/60 p-3 space-y-2">
                  <button
                    type="button"
                    onClick={() => setAppliedFilters(filters)}
                    className="w-full rounded-xl bg-red-500 px-3 py-2.5 text-[11px] font-bold uppercase tracking-[0.15em] text-white transition-all hover:bg-red-400 shadow-lg shadow-red-500/20"
                  >
                    Apply Filters
                    {activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const resetVal = {
                        company:
                          authUser?.role === "client_admin"
                            ? [authUser.clientName]
                            : ["All"],
                        channel: ["All"],
                        user: ["All"],
                        language: ["All"],
                        inputType: ["All"],
                        outputType: ["All"],
                        dateFrom: "",
                        dateTo: "",
                      };
                      setFilters(resetVal);
                      setAppliedFilters(resetVal);
                    }}
                    className="w-full rounded-xl border border-neutral-800 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.15em] text-neutral-500 transition-all hover:border-red-500/30 hover:text-red-400"
                  >
                    Reset
                  </button>
                </div>
              </>
            )}
          </aside>
        )}

        <div
          className={`rounded-[24px] border border-neutral-800 bg-[#0e0e0e] flex flex-col overflow-hidden shadow-xl transition-all duration-300 hover:border-neutral-700 ${
            isMaximized ? "flex-1 h-full" : "h-[400px] lg:h-[560px]"
          }`}
        >
          {/* Chart header */}
          <div className="flex-shrink-0 flex items-center justify-between border-b border-neutral-800/60 bg-[#121212] px-6 py-4">
            <div className="flex items-center gap-2">
              <LineChartIcon size={16} className="text-red-400" />
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-300">
                Trend Analysis & Forecasts
              </h3>
            </div>
            <div className="flex items-center gap-3">
              {/* Comparison Toggle & Slider */}
              <div className="flex items-center gap-2 mr-2">
                <button
                  onClick={() => setShowComparison(!showComparison)}
                  className={`p-1.5 rounded-lg transition-all duration-300 ${
                    showComparison
                      ? "bg-purple-500/20 text-purple-400 border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)]"
                      : "text-neutral-500 hover:text-neutral-300 border border-transparent"
                  }`}
                  title="Compare with Past Period"
                >
                  <History size={18} />
                </button>

                {showComparison && (
                  <div className="flex items-center gap-3 animate-in fade-in slide-in-from-right-2 duration-300">
                    <div className="flex flex-col">
                      <input
                        type="range"
                        min="1"
                        max="12"
                        value={comparisonOffset}
                        onChange={(e) =>
                          setComparisonOffset(parseInt(e.target.value))
                        }
                        className="w-24 accent-purple-500 comparison-slider frammer-range cursor-pointer"
                      />
                    </div>
                    <span className="text-[10px] font-black text-purple-400/80 w-8 tabular-nums">
                      {comparisonOffset}P LAG
                    </span>
                  </div>
                )}
              </div>

              <div className="h-4 w-px bg-neutral-800 mx-1" />

              <button
                onClick={() => setShowPoints(!showPoints)}
                className={`text-neutral-400 hover:text-white transition-colors ${showPoints ? "text-white" : ""}`}
                title="Toggle Data Points"
              >
                <CircleDot size={18} />
              </button>
              <button
                onClick={handleExportCsv}
                className="text-neutral-400 hover:text-white transition-colors"
                title="Export CSV"
              >
                <Download size={18} />
              </button>
              <button
                onClick={handleExportImage}
                className="text-neutral-400 hover:text-white transition-colors"
                title="Export Graph Image"
              >
                <ImageIcon size={18} />
              </button>
              <button
                onClick={() => setShowStl(!showStl)}
                className={`transition-colors ${
                  showStl
                    ? "text-amber-400 hover:text-amber-300"
                    : "text-neutral-400 hover:text-white"
                }`}
                title="Toggle STL Decomposition"
              >
                <Layers size={18} />
              </button>
              <div className="mx-1 h-5 w-px bg-neutral-800" />
              <button
                onClick={() => setIsMaximized(!isMaximized)}
                className="text-neutral-400 hover:text-white transition-colors"
                title={isMaximized ? "Minimize" : "Maximize"}
              >
                {isMaximized ? (
                  <Minimize2 size={18} />
                ) : (
                  <Maximize2 size={18} />
                )}
              </button>
            </div>
          </div>

          {/* Chart body — flex-1 fills all remaining height */}
          <div className="flex-1 min-h-0 p-6 flex flex-col">
            <div className="flex-1 min-h-0 w-full">
              <Line
                key={`trend-chart-${isMaximized ? "max" : "normal"}`}
                ref={chartRef}
                data={chartData}
                options={chartOptions}
              />
            </div>
            {isPredicting && prediction.loading && (
              <div className="flex-shrink-0 mt-3 flex items-center gap-2 text-xs text-sky-400/70">
                <span className="inline-block h-3 w-3 rounded-full border border-sky-400 border-t-transparent animate-spin" />
                Loading forecast…
              </div>
            )}
          </div>
        </div>

        {/* ── Col 3: Anomaly panel — same fixed height, scrolls internally ── */}
        {!isMaximized && (
          <div className="rounded-[24px] border border-neutral-800 bg-[#0e0e0e] flex flex-col overflow-hidden shadow-xl transition-all duration-300 hover:border-neutral-700 h-[400px] lg:h-[560px] lg:col-span-2 xl:col-span-1">
            {/* Panel header — fixed, never scrolls */}
            <div className="flex-shrink-0 flex items-center gap-2 border-b border-neutral-800/60 bg-[#121212] px-6 py-4">
              <AlertTriangle size={16} className="text-amber-500" />
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-300">
                Unusual Movement & Anomalies
              </h3>
            </div>
            {/* Scrollable list — fills remaining height */}
            <div className="flex-1 min-h-0 overflow-y-auto frammer-anomaly-scroll p-5 space-y-4">
              {trends.loading && (
                <Skeleton className="h-20 w-full rounded-xl" />
              )}
              {!trends.loading &&
                anomalies.map((anomaly, idx) => (
                  <div
                    key={`${anomaly.period}-${anomaly.direction}-${anomaly.method || "zscore"}-${idx}`}
                    className="group relative overflow-hidden rounded-xl border border-neutral-800 bg-[#121212] p-5 transition-all hover:border-neutral-600 hover:bg-[#161616]"
                  >
                    <div
                      className={`absolute top-0 left-0 w-1 h-full ${anomaly.direction === "drop" ? "bg-amber-500" : "bg-emerald-500"}`}
                    />
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-sm font-bold text-white capitalize tracking-wide whitespace-nowrap">
                          {anomaly.direction === "drop"
                            ? "Significant Drop"
                            : "Abnormal Spike"}
                        </div>
                        <div className="mt-1 text-xs text-neutral-400 font-medium tracking-wider">
                          Occurred around {anomaly.period}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-black text-white">
                          {formatMetricValue(resolvedMetric, anomaly.value)}
                        </div>
                        <div className="mt-1 flex items-center justify-end gap-2">
                          <div className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">
                            {Number(anomaly.zScore).toFixed(1)}
                          </div>
                          <span
                            className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
                              anomaly.method === "seasonal_deviation"
                                ? "bg-violet-500/20 text-violet-200 ring-1 ring-violet-500/35"
                                : anomaly.method === "trend_reversal"
                                  ? "bg-orange-500/20 text-orange-200 ring-1 ring-orange-500/35"
                                  : "bg-neutral-500/20 text-neutral-200 ring-1 ring-neutral-500/35"
                            }`}
                          >
                            {anomaly.method === "seasonal_deviation"
                              ? "SEASONAL"
                              : anomaly.method === "trend_reversal"
                                ? "REVERSAL"
                                : "Z-SCORE"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              {!trends.loading && !anomalies.length && (
                <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-neutral-800 rounded-xl">
                  <div className="text-emerald-500/20 mb-3">
                    <AlertTriangle size={32} />
                  </div>
                  <div className="text-sm font-semibold text-neutral-300 mb-1">
                    System Normal
                  </div>
                  <div className="text-xs text-neutral-500">
                    No significant statistical anomalies detected.
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {showStl && !isMaximized && (
        <section className="rounded-[24px] border border-neutral-800/80 bg-[#101010]/80 backdrop-blur-md p-6 shadow-xl transition-all duration-300 hover:border-neutral-700/80">
          <div className="mb-4 flex items-center gap-2">
            <Layers size={16} className="text-amber-400" />
            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-300">
              STL Decomposition
            </h3>
          </div>

          {stl.loading && (
            <div className="space-y-4">
              <ChartSkeleton height={180} />
              <ChartSkeleton height={180} />
              <ChartSkeleton height={180} />
            </div>
          )}

          {!stl.loading && stl.error && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
              Failed to load STL decomposition: {stl.error}
            </div>
          )}

          {!stl.loading &&
            !stl.error &&
            (() => {
              const rows = Array.isArray(stl.data?.data) ? stl.data.data : [];
              const labels = rows.map((row) =>
                String(row.Date || "").slice(0, 10),
              );

              const trendData = {
                labels,
                datasets: [
                  {
                    label: "Trend",
                    data: rows.map((row) => Number(row.trend || 0)),
                    borderColor: "#38BDF8",
                    backgroundColor: "rgba(56,189,248,0.1)",
                    borderWidth: 2,
                    tension: 0.25,
                    fill: false,
                    pointRadius: 0,
                  },
                ],
              };

              const seasonalData = {
                labels,
                datasets: [
                  {
                    label: "Seasonal",
                    data: rows.map((row) => Number(row.seasonal || 0)),
                    borderColor: "#A78BFA",
                    backgroundColor: "rgba(167,139,250,0.1)",
                    borderWidth: 2,
                    tension: 0.25,
                    fill: false,
                    pointRadius: 0,
                  },
                ],
              };

              const residualData = {
                labels,
                datasets: [
                  {
                    label: "Residual",
                    data: rows.map((row) => Number(row.residual || 0)),
                    borderColor: "#F59E0B",
                    backgroundColor: "rgba(245,158,11,0.1)",
                    borderWidth: 2,
                    tension: 0.25,
                    fill: false,
                    pointRadius: 0,
                  },
                ],
              };

              const topChartOptions = {
                ...chartOptions,
                scales: {
                  ...chartOptions.scales,
                  x: {
                    ...chartOptions.scales.x,
                    display: false,
                  },
                },
              };

              const bottomChartOptions = {
                ...chartOptions,
                scales: {
                  ...chartOptions.scales,
                  x: {
                    ...chartOptions.scales.x,
                    display: true,
                  },
                },
              };

              return (
                <div className="space-y-4">
                  <div className="rounded-xl border border-neutral-800 bg-[#0e0e0e] p-3">
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
                      Trend
                    </div>
                    <div className="h-[180px]">
                      <Line data={trendData} options={topChartOptions} />
                    </div>
                  </div>

                  <div className="rounded-xl border border-neutral-800 bg-[#0e0e0e] p-3">
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
                      Seasonal
                    </div>
                    <div className="h-[180px]">
                      <Line data={seasonalData} options={topChartOptions} />
                    </div>
                  </div>

                  <div className="rounded-xl border border-neutral-800 bg-[#0e0e0e] p-3">
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-500">
                      Residual
                    </div>
                    <div className="h-[180px]">
                      <Line data={residualData} options={bottomChartOptions} />
                    </div>
                  </div>
                </div>
              );
            })()}
        </section>
      )}

      {/* ── Multi-dim section ────────────────────────────────────────────── */}
      {/* ── Multi-dim section ────────────────────────────────────────────── */}
      {!isMaximized && (
        <section className="relative z-50 rounded-[24px] border border-neutral-800/80 bg-[#101010]/80 backdrop-blur-md p-4 sm:p-6 shadow-xl transition-all duration-300 hover:border-neutral-700/80">
          <div className="flex flex-col">
            <div className="flex flex-col lg:flex-row lg:flex-wrap items-stretch lg:items-end gap-4 lg:gap-6">
            
            {/* Comparison Type */}
            <div className="w-full lg:flex-1 lg:min-w-[200px] group">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500 mb-2 block group-hover:text-neutral-300 transition-colors">
                Comparison Type
              </label>
              <FloatingDropdown
                value={multiDim}
                onChange={setMultiDim}
                options={MULTI_DIM_OPTIONS}
                minWidth=""
                className="w-full"
              />
            </div>

            {/* Scope Boundaries */}
            {needsClientFilter && authUser?.role === "website_admin" && (
              <div className="flex-1 min-w-[180px] group">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500 mb-2 block group-hover:text-neutral-300 transition-colors">
                  Client Scope
                </label>
                <FloatingDropdown
                  value={clientFilter}
                  onChange={(val) => {
                    setClientFilter(val);
                    setUserFilter(["All"]);
                  }}
                  options={toOptionList(filterOptions.company)}
                  multiSelect={true}
                  minWidth=""
                  className="w-full"
                />
              </div>
            )}

            {needsUserFilter && authUser?.role !== "user" && (
              <div className="flex-1 min-w-[180px] group">
                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500 mb-2 block group-hover:text-neutral-300 transition-colors">
                  User Scope
                </label>
                <FloatingDropdown
                  value={userFilter}
                  onChange={setUserFilter}
                  options={toOptionList(
                    multiDimFilterOptionsData?.filters?.user || ["All"],
                  )}
                  multiSelect={true}
                  minWidth=""
                  className="w-full"
                />
              </div>
            )}

            {/* Time Horizon Slider */}
            <div className="w-full lg:flex-[2] lg:min-w-[240px]">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500 mb-2 block group-hover:text-neutral-300 transition-colors">
                Date window
              </label>
              <div className="h-full flex flex-col justify-end">
                <DateRangeSlider
                  dates={sliderDates}
                  startIndex={multiDimStartIndex}
                  endIndex={multiDimEndIndex}
                  onChange={(start, end) => {
                    setMultiDimStartIndex(start);
                    setMultiDimEndIndex(end);
                  }}
                />
              </div>
            </div>

            {/* Sync Action */}
            <div className="flex flex-col items-center w-full lg:w-auto">
              <button
                onClick={handleApplyMultiDimFilters}
                className="group/btn relative h-[46px] w-full lg:w-auto flex items-center justify-center gap-3 rounded-xl bg-red-500 px-6 lg:px-8 py-0 text-[11px] font-black uppercase tracking-[0.15em] text-white shadow-lg shadow-red-500/10 transition-all hover:bg-red-400 hover:shadow-red-500/20 hover:-translate-y-0.5 active:translate-y-0 active:scale-95"
              >
                <span>Add Filter</span>
                <ArrowRight size={16} className="transition-transform group-hover/btn:translate-x-1" />
              </button>
            </div>
          </div>

            {/* Results Display Area */}
            <div className="mt-6 sm:mt-8 pt-6 sm:pt-8 border-t border-neutral-800/40">

              <div className="relative min-h-[360px] sm:min-h-[420px] rounded-[28px] sm:rounded-[36px] bg-neutral-900/20 border border-neutral-800/30 p-4 sm:p-8 shadow-inner overflow-hidden">
                
                {multiDimLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-[#101010]/60 backdrop-blur-md z-10">
                    <div className="w-full px-4 sm:px-10">
                      <ChartSkeleton height={280} />
                    </div>
                  </div>
                )}

                {multiDimError && (
                  <div className="flex flex-col items-center justify-center p-12 text-center h-[320px] relative z-10">
                    <div className="text-xl font-black text-red-400 mb-2 tracking-tight">
                      Data Error
                    </div>
                    <div className="text-sm text-neutral-500 max-w-xs leading-relaxed">
                      {multiDimError}
                    </div>
                  </div>
                )}

                {!multiDimLoading &&
                  !multiDimError &&
                  !multiDimChartData &&
                  !needsClientFilter && (
                    <div className="flex flex-col items-center justify-center p-12 text-center h-[320px] relative z-10">
                      <div className="text-xl font-black text-neutral-300 mb-2 tracking-tight">
                        No Temporal Data
                      </div>
                      <div className="text-sm text-neutral-500 max-w-xs leading-relaxed">
                        Your current synchronization parameters yielded zero
                        results. Try broadening your filter horizons.
                      </div>
                    </div>
                  )}

                {!multiDimLoading && !multiDimError && multiDimChartData && (
                  <div className="h-[280px] sm:h-[320px] w-full relative z-10">
                    <Line data={multiDimChartData} options={chartOptions} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
