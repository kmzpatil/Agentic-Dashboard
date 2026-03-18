import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import FunnelFilterBar from './components/FunnelFilterBar';
import OverviewFlowTab from './components/OverviewFlowTab';
import ChannelEfficiencyTab from './components/ChannelEfficiencyTab';
import ContentAnalysisTab from './components/ContentAnalysisTab';
import DataExplorerTab from './components/DataExplorerTab';
import {
  buildBreakdownOutcomeLinks,
  buildFromTotals,
  groupSmallLinks,
  makeSankeyOptions,
  MAX_BREAKDOWN_SOURCES,
  normalizeSankeyLinks,
} from './utils/funnelFlow';

const ANALYSIS_TABS = [
  { id: 'overview', label: 'Pipeline & Flow' },
  { id: 'channel',  label: 'Channel Efficiency' },
  { id: 'content',  label: 'Content Analysis' },
  { id: 'explorer', label: 'Data Explorer' },
];
const BREAKDOWN_SOURCES_LIMITS = {
  channel: 12,
  user: 12,
  team: 10,
  client: 10,
  output_type: 10,
  input_type: 8,
  language: 8,
};

const EMPTY_FILTERS = { client: '', input_type: '', language: '', channel: '', user: '', team: '' };
const FILTER_DIMENSIONS = new Set(['client', 'input_type', 'language', 'channel', 'user', 'team']);
const FILTER_KEYS = ['client', 'input_type', 'language', 'channel', 'user', 'team'];

function buildFiltersFromRouteState(routeState = {}) {
  const next = { ...EMPTY_FILTERS };
  FILTER_KEYS.forEach((key) => {
    if (routeState[key]) next[key] = routeState[key];
  });
  return next;
}

export default function FunnelModule({ authUser, routeState = {}, onNavigate }) {
  const compositionChartRef = useRef(null);

  const [breakdown, setBreakdown] = useState(routeState.breakdown || 'channel');
  const [filters, setFilters] = useState(() => buildFiltersFromRouteState(routeState));
  const [compositionSourceMode, setCompositionSourceMode] = useState('top');
  const [compositionTopN, setCompositionTopN] = useState(() => BREAKDOWN_SOURCES_LIMITS[routeState.breakdown || 'channel'] || MAX_BREAKDOWN_SOURCES);
  const [analysisTab, setAnalysisTab] = useState('overview');

  useEffect(() => {
    const nextBreakdown = routeState.breakdown || 'channel';
    const next = buildFiltersFromRouteState(routeState);
    setBreakdown(nextBreakdown);
    setFilters(next);
    setCompositionTopN(BREAKDOWN_SOURCES_LIMITS[nextBreakdown] || MAX_BREAKDOWN_SOURCES);
  }, [routeState.breakdown, routeState.client, routeState.input_type, routeState.language,
      routeState.channel, routeState.user, routeState.team]);

  const effectiveFilters = useMemo(() => filters, [filters]);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    p.set('breakdown', breakdown);
    Object.entries(effectiveFilters).forEach(([k, v]) => { if (v) p.set(k, v); });
    return p.toString();
  }, [breakdown, effectiveFilters]);

  const { data, loading, error } = useApi(`${API_BASE}/funnel?${queryString}`, [queryString]);

  const navigate = (overrides = {}) => onNavigate?.({
    view: 'funnel',
    breakdown,
    ...effectiveFilters,
    dimension: '',
    value: '',
    ...overrides,
  });

  const handleBreakdownChange = (next) => {
    const nextFilters = { ...effectiveFilters };
    if (FILTER_DIMENSIONS.has(next)) {
      nextFilters[next] = '';
    }
    setBreakdown(next);
    setFilters(nextFilters);
    onNavigate?.({ view: 'funnel', breakdown: next, ...nextFilters, dimension: '', value: '' });
  };
  const handleFiltersChange   = (next) => {
    setFilters(next);
    navigate(next);
  };
  const handleZoom            = (dim, val) => {
    const next = { ...filters, [dim]: val };
    setFilters(next);
    navigate(next);
  };

  const stageLinks = useMemo(() => normalizeSankeyLinks(data?.sankeyLinks || []), [data?.sankeyLinks]);
  const showAllCompositionSources = compositionSourceMode === 'all';
  const publishedPlatformTailLinks = useMemo(() => (
    (data?.compositionLinks || [])
      .map((item) => ({
        from: String(item?.from || ''),
        to: String(item?.to || ''),
        flow: Number(item?.flow || 0),
        edgeType: String(item?.edgeType || ''),
      }))
      .filter((item) => item.edgeType === 'published_to_platform' && item.from === 'Published' && item.to && item.flow > 0)
  ), [data?.compositionLinks]);
  const compositionBaseLinks = useMemo(() => {
    if (breakdown === 'client') return data?.compositionLinks || [];
    return buildBreakdownOutcomeLinks(
      data?.breakdown || [],
      breakdown,
      showAllCompositionSources ? null : compositionTopN,
      !showAllCompositionSources,
      publishedPlatformTailLinks,
    );
  }, [data?.compositionLinks, data?.breakdown, breakdown, showAllCompositionSources, compositionTopN, publishedPlatformTailLinks]);

  const totalBreakdownSources = useMemo(() => (
    (data?.breakdown || [])
      .map((row) => String(row?.label || '').trim())
      .filter((label) => label && label !== 'Published' && label !== 'Not Published' && label !== 'Other')
      .length
  ), [data?.breakdown]);
  const hiddenBreakdownSources = Math.max(totalBreakdownSources - compositionTopN, 0);

  const compositionLinks = useMemo(() => groupSmallLinks(compositionBaseLinks), [compositionBaseLinks]);
  const stageFromTotals = useMemo(() => buildFromTotals(stageLinks), [stageLinks]);
  const compositionFromTotals = useMemo(() => buildFromTotals(compositionLinks), [compositionLinks]);
  const groupedCompositionCount = useMemo(() => compositionLinks.filter((item) => item.grouped).length, [compositionLinks]);
  const compositionColumn = useMemo(() => {
    if (!compositionLinks.length) return undefined;
    const column = {};
    compositionLinks.forEach((item) => {
      const from = String(item?.from || '');
      const to = String(item?.to || '');
      if (!from || !to) return;

      const toLower = to.toLowerCase();
      const fromLower = from.toLowerCase();
      const isOutcomeNode = toLower === 'published' || toLower === 'not published';
      const fromIsOutcomeNode = fromLower === 'published' || fromLower === 'not published';

      if (isOutcomeNode) {
        column[to] = 1;
        if (column[from] === undefined) column[from] = 0;
        return;
      }

      if (fromIsOutcomeNode) {
        column[from] = 1;
        if (column[to] === undefined) column[to] = 2;
      }
    });
    return column;
  }, [compositionLinks]);
  const compositionPriority = useMemo(() => {
    if (!compositionLinks.length) return undefined;
    const priority = {};
    compositionLinks.forEach((item) => {
      const from = String(item?.from || '');
      const to = String(item?.to || '');
      const resolvePriority = (node) => {
        if (node === 'Published') return -100;
        if (node === 'Not Published') return -50;
        if (node === 'Other') return 9999;
        return 0;
      };
      if (from && priority[from] === undefined) priority[from] = resolvePriority(from);
      if (to && priority[to] === undefined) priority[to] = resolvePriority(to);
    });
    return priority;
  }, [compositionLinks]);

  const stageSankeyData = useMemo(() => ({
    datasets: [{
      data: stageLinks,
      colorFrom: '#64748b',
      colorTo: '#22c55e',
      colorMode: 'gradient',
      borderColor: 'rgba(0, 0, 0, 0)',
      borderWidth: 0,
      nodeWidth: 20,
      nodePadding: 30,
    }],
  }), [stageLinks]);

  const compositionSankeyData = useMemo(() => ({
    datasets: [{
      data: compositionLinks,
      column: compositionColumn,
      priority: compositionPriority,
      colorFrom: '#f59e0b',
      colorTo: '#ef4444',
      colorMode: 'gradient',
      borderColor: 'rgba(0, 0, 0, 0)',
      borderWidth: 0,
      nodeWidth: 18,
      nodePadding: 24,
    }],
  }), [compositionLinks, compositionColumn, compositionPriority]);

  const handleCompositionZoom = useCallback((link) => {
    if (!link || link.grouped || link.from === 'Other') return;
    const to = String(link.to || '').trim().toLowerCase();
    if (to !== 'published' && to !== 'not published') return;
    const dim = breakdown;
    if (dim) handleZoom(dim, link.zoomValue || link.from);
  }, [breakdown, handleZoom]);

  const handleCompositionClick = useCallback((event) => {
    const chart = compositionChartRef.current;
    if (!chart || !event?.nativeEvent || !compositionLinks.length) return;

    const points = chart.getElementsAtEventForMode(event.nativeEvent, 'nearest', { intersect: false }, true);
    if (!points?.length) return;

    const link = compositionLinks[points[0].index];
    handleCompositionZoom(link);
  }, [compositionLinks, handleCompositionZoom]);

  const handleCompositionChartHover = useCallback((event) => {
    const chart = compositionChartRef.current;
    if (!chart || !event?.nativeEvent) return;
    const points = chart.getElementsAtEventForMode(event.nativeEvent, 'nearest', { intersect: false }, true);
    if (event.nativeEvent.target?.style) {
      event.nativeEvent.target.style.cursor = points?.length ? 'pointer' : 'default';
    }
  }, []);

  const stageSankeyOptions = useMemo(() => makeSankeyOptions(stageFromTotals), [stageFromTotals]);
  const compositionSankeyOptions = useMemo(() => makeSankeyOptions(compositionFromTotals), [compositionFromTotals]);

  const hasActive = Object.values(effectiveFilters).some(Boolean);

  return (
    <div className="h-full overflow-y-auto bg-[#050505]">
      {/* Ambient glow blob */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[700px] h-[340px] rounded-full bg-violet-600/5 blur-[120px]" />
      </div>

      <div className="relative mx-auto w-full max-w-[1440px] px-6 pt-6 pb-12 space-y-9">

        {/* ── Filter bar ── */}
        <FunnelFilterBar
          authUser={authUser}
          breakdown={breakdown}
          filters={effectiveFilters}
          onBreakdownChange={handleBreakdownChange}
          onFiltersChange={handleFiltersChange}
        />

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 rounded-full border-2 border-neutral-800 border-t-violet-500 animate-spin" />
          </div>
        )}
        {error && <div className="text-red-400 py-8 text-center text-sm">{error}</div>}

        {!loading && !error && (
          <>
            {/* ── Tabs ── */}
            <div>
              <div className="flex items-center gap-3 mb-5">
                <span className="text-[9.5px] font-bold uppercase tracking-[0.2em] text-neutral-600">Views</span>
                <div className="flex gap-1">
                  {ANALYSIS_TABS.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setAnalysisTab(tab.id)}
                      className={[
                        'relative px-3.5 py-1.5 rounded-full text-[11.5px] font-semibold transition-all duration-150',
                        analysisTab === tab.id
                          ? 'text-white'
                          : 'text-neutral-600 hover:text-neutral-300',
                      ].join(' ')}
                    >
                      {analysisTab === tab.id && (
                        <span className="absolute inset-0 rounded-full bg-white/8 ring-1 ring-white/10" />
                      )}
                      <span className="relative">{tab.label}</span>
                    </button>
                  ))}
                </div>
                <div className="flex-1 h-px bg-neutral-900" />
                {hasActive && (
                  <span className="text-[10px] text-violet-400 font-medium">Filtered</span>
                )}
              </div>

              {analysisTab === 'overview' && (
                <OverviewFlowTab
                  data={data}
                  breakdown={breakdown}
                  filters={effectiveFilters}
                  groupedCompositionCount={groupedCompositionCount}
                  stageSankeyData={stageSankeyData}
                  stageSankeyOptions={stageSankeyOptions}
                  compositionSankeyData={compositionSankeyData}
                  compositionSankeyOptions={compositionSankeyOptions}
                  compositionChartRef={compositionChartRef}
                  handleCompositionClick={handleCompositionClick}
                  handleCompositionChartHover={handleCompositionChartHover}
                  compositionSourceMode={compositionSourceMode}
                  onCompositionSourceModeChange={setCompositionSourceMode}
                  compositionTopN={compositionTopN}
                  onCompositionTopNChange={setCompositionTopN}
                  totalBreakdownSources={totalBreakdownSources}
                  hiddenBreakdownSources={hiddenBreakdownSources}
                />
              )}

              {analysisTab === 'channel'  && <ChannelEfficiencyTab  authUser={authUser} data={data} breakdown={breakdown} filters={effectiveFilters} />}
              {analysisTab === 'content'  && <ContentAnalysisTab   authUser={authUser} data={data} breakdown={breakdown} filters={effectiveFilters} />}
              {analysisTab === 'explorer' && <DataExplorerTab       authUser={authUser} data={data} breakdown={breakdown} filters={effectiveFilters} />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
