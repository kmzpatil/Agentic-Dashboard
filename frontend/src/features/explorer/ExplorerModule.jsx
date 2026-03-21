import React, { useEffect, useMemo, useState } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import { Database, Table, Activity, ChevronDown, Check, Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber } from '../../lib/formatters';

function DualDateSlider({ startDate, endDate, onStartChange, onEndChange }) {
  const now = new Date();
  const SLIDER_MAX_DATE = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const SLIDER_MIN_DATE = new Date('2025-01-01').getTime();
  const MS_PER_DAY = 24 * 60 * 60 * 1000;

  const minVal = startDate ? new Date(startDate).getTime() : SLIDER_MIN_DATE;
  const maxVal = endDate ? new Date(endDate).getTime() : SLIDER_MAX_DATE;

  const getPercent = (val) => Math.max(0, Math.min(100, ((val - SLIDER_MIN_DATE) / (SLIDER_MAX_DATE - SLIDER_MIN_DATE)) * 100));

  const handleMinChange = (e) => {
    const val = Math.min(Number(e.target.value), maxVal - MS_PER_DAY);
    const dateObj = new Date(val);
    const yyyy = dateObj.getFullYear();
    const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
    const dd = String(dateObj.getDate()).padStart(2, '0');
    onStartChange(`${yyyy}-${mm}-${dd}`);
  };

  const handleMaxChange = (e) => {
    const val = Math.max(Number(e.target.value), minVal + MS_PER_DAY);
    const dateObj = new Date(val);
    const yyyy = dateObj.getFullYear();
    const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
    const dd = String(dateObj.getDate()).padStart(2, '0');
    onEndChange(`${yyyy}-${mm}-${dd}`);
  };

  return (
    <div className="relative w-full h-[38px] flex items-center">
      <div className="absolute w-full h-1.5 bg-neutral-800 rounded-full"></div>
      <div
        className="absolute h-1.5 bg-[#ef4444] rounded-full"
        style={{ left: `${getPercent(minVal)}%`, width: `${getPercent(maxVal) - getPercent(minVal)}%` }}
      ></div>
      <input
        type="range"
        min={SLIDER_MIN_DATE}
        max={SLIDER_MAX_DATE}
        step={MS_PER_DAY}
        value={minVal}
        onChange={handleMinChange}
        className="absolute w-full appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-[#ef4444] [&::-webkit-slider-thumb]:appearance-none z-20 cursor-pointer"
      />
      <input
        type="range"
        min={SLIDER_MIN_DATE}
        max={SLIDER_MAX_DATE}
        step={MS_PER_DAY}
        value={maxVal}
        onChange={handleMaxChange}
        className="absolute w-full appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-[#ef4444] [&::-webkit-slider-thumb]:appearance-none z-20 cursor-pointer"
      />
    </div>
  );
}

export default function ExplorerModule({ authUser }) {
  const canUseRawExplorer = authUser?.role === 'website_admin';

  // API Calls - Structural Data
  const { data: tableData } = useApi(canUseRawExplorer ? `${API_BASE}/explorer/tables` : null, [canUseRawExplorer]);
  const { data: dimsDataRaw } = useApi(`${API_BASE}/explorer/dimensions`, []);

  // Inject Team_Name dynamically
  const dimsData = useMemo(() => {
    if (!dimsDataRaw) return dimsDataRaw;
    const dims = [...(dimsDataRaw.dimensions || [])];
    if (!dims.find(d => d.key === 'Team_Name')) {
      dims.push({ key: 'Team_Name', label: 'Team Name' });
    }
    return { ...dimsDataRaw, dimensions: dims };
  }, [dimsDataRaw]);

  // Fetch available channels for the dropdown
  const { data: channelsListData, loading: channelsLoading, error: channelsError } = useApi(`${API_BASE}/explorer/channels`, []);

  // State Management
  const [tableName, setTableName] = useState('');
  const [dim1, setDim1] = useState('output_type');
  const [dim2, setDim2] = useState('input_type');
  const [measure, setMeasure] = useState('uploaded_videos');
  const [timeGrain, setTimeGrain] = useState('none');
  const [dateField, setDateField] = useState('upload_date');
  const [dim1Value, setDim1Value] = useState('');
  const [viewTab, setViewTab] = useState('multi'); // 'multi' or 'raw'

  // Multi-select state for Custom Dropdown
  const [selectedChannels, setSelectedChannels] = useState(['all']);
  const [isChannelDropdownOpen, setIsChannelDropdownOpen] = useState(false);
  const [channelSearchTerm, setChannelSearchTerm] = useState('');

  // States for Dim2 Custom Dropdown
  const [selectedDim2Values, setSelectedDim2Values] = useState(['all']);
  const [isDim2DropdownOpen, setIsDim2DropdownOpen] = useState(false);
  const [dim2SearchTerm, setDim2SearchTerm] = useState('');
  const [hasPreselectedDim2, setHasPreselectedDim2] = useState(false);

  // States for Date Filtering
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // NEW STATES
  const [isTimeAnalysisOn, setIsTimeAnalysisOn] = useState(false);

  // Raw Table Upgrades
  const [rowLimit, setRowLimit] = useState(120);
  const [columnFilters, setColumnFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'default' }); // 'asc', 'desc', 'default'

  // Dimension Analysis Table Upgrades
  const [dimTableSort, setDimTableSort] = useState({ key: null, direction: 'default' });

  // Default table selection - filter out app_users
  const safeTables = useMemo(() => {
    return (tableData?.tables || []).filter(t => t !== 'app_users');
  }, [tableData]);

  useEffect(() => {
    if (!tableName && safeTables.length) setTableName(safeTables[0]);
  }, [safeTables, tableName]);

  // Dimension Collision Handlers
  const handleDim1Change = (e) => {
    const val = e.target.value;
    setDim1(val);
    if (val === dim2) {
      const availableDim2 = (dimsData?.dimensions || []).find(d => d.key !== val && d.key !== 'channel');
      setDim2(availableDim2 ? availableDim2.key : '');
      setSelectedDim2Values(['all']);
    }
  };

  const handleDim2Change = (e) => {
    setDim2(e.target.value);
    setSelectedDim2Values(['all']); // Reset the dim2 filter when the dimension changes
    setHasPreselectedDim2(false); // Enable pre-selection for the new dimension
  };

  // Custom Dropdown Toggles
  const toggleChannel = (channel) => {
    if (channel === 'all') {
      setSelectedChannels(['all']);
    } else {
      let newSelection = selectedChannels.filter(c => c !== 'all');
      if (newSelection.includes(channel)) {
        newSelection = newSelection.filter(c => c !== channel);
      } else {
        newSelection.push(channel);
      }
      if (newSelection.length === 0) newSelection = ['all'];
      setSelectedChannels(newSelection);
    }
  };

  const toggleDim2Value = (val) => {
    const strVal = String(val);
    if (strVal === 'all') {
      setSelectedDim2Values(['all']);
    } else {
      let newSelection = selectedDim2Values.filter(v => v !== 'all');
      if (newSelection.includes(strVal)) {
        newSelection = newSelection.filter(v => v !== strVal);
      } else {
        newSelection.push(strVal);
      }
      if (newSelection.length === 0) newSelection = ['all'];
      setSelectedDim2Values(newSelection);
    }
  };

  const handleColumnFilterChange = (col, type, value) => {
    setColumnFilters(prev => {
      const existing = prev[col] || {};
      return {
        ...prev,
        [col]: { ...existing, [type]: value }
      };
    });
  };

  const handleSortToggle = (colKey) => {
    setSortConfig(prev => {
      if (prev.key === colKey) {
        if (prev.direction === 'asc') return { key: colKey, direction: 'desc' };
        if (prev.direction === 'desc') return { key: null, direction: 'default' };
      }
      return { key: colKey, direction: 'asc' };
    });
  };

  // Effective Time Grain parsing
  const effectiveTimeGrain = isTimeAnalysisOn ? (timeGrain === 'none' ? 'day' : timeGrain) : 'none';

  // Toggle Handler
  const handleTimeAnalysisToggle = () => {
    const newState = !isTimeAnalysisOn;
    setIsTimeAnalysisOn(newState);
    if (newState && timeGrain === 'none') {
      setTimeGrain('day');
    }
  };

  // Button Labels
  const getChannelButtonLabel = () => {
    if (channelsLoading) return 'Loading...';
    if (channelsError) return 'Error loading';
    if (selectedChannels.includes('all')) return 'All Channels';
    if (selectedChannels.length === 1) return selectedChannels[0];
    return `${selectedChannels.length} Selected`;
  };

  const activeDim2Label = (dimsData?.dimensions || []).find(d => d.key === dim2)?.label || 'Dim 2';
  const getDim2ButtonLabel = () => {
    if (selectedDim2Values.includes('all')) return `All ${activeDim2Label}s`;
    if (selectedDim2Values.length === 1) return selectedDim2Values[0];
    return `${selectedDim2Values.length} Selected`;
  };

  const channelsParam = selectedChannels.includes('all') ? 'all' : selectedChannels.join(',');

  // API Calls - Table & Chart Data
  const tableUrl = canUseRawExplorer && tableName
    ? `${API_BASE}/explorer/table/${encodeURIComponent(tableName)}?limit=${rowLimit}`
    : null;
  const { data: rowsData, loading: rowsLoading, error: rowsError } = useApi(tableUrl, [tableUrl]);

  // Dynamically build multiQuery URL
  let multiQuery = `${API_BASE}/explorer/multidim?dim1=${encodeURIComponent(dim1)}&dim2=${encodeURIComponent(dim2)}&measure=${encodeURIComponent(measure)}&timeGrain=${encodeURIComponent(effectiveTimeGrain)}&dateField=${encodeURIComponent(dateField)}&channels=${encodeURIComponent(channelsParam)}`;
  if (dim1Value) multiQuery += `&dim1Value=${encodeURIComponent(dim1Value)}`;

  // Date Filters apply globally now if set
  if (startDate) multiQuery += `&startDate=${encodeURIComponent(startDate)}`;
  if (endDate) multiQuery += `&endDate=${encodeURIComponent(endDate)}`;

  const multi = useApi(multiQuery, [dim1, dim2, measure, effectiveTimeGrain, dateField, dim1Value, channelsParam, startDate, endDate]);

  // Pre-select first 4 values for Dim2 when data loads
  useEffect(() => {
    if (!hasPreselectedDim2 && multi.dataUrl === multiQuery && multi.data?.dim2Values?.length > 0) {
      const firstFour = multi.data.dim2Values.slice(0, 4).map(String);
      setSelectedDim2Values(firstFour);
      setHasPreselectedDim2(true);
    }
  }, [multi.data?.dim2Values, multi.dataUrl, multiQuery, hasPreselectedDim2]);

  // Same gradient as "Channel publish conversion" in Funnel → red (#ef4444) to dark slate (#48485a)
  const getIndexColor = (idx, total = 1) => {
    const t = total <= 1 ? 0 : idx / (total - 1);
    const r = Math.round(239 + (72  - 239) * t);
    const g = Math.round(68  + (72  - 68)  * t);
    const b = Math.round(68  + (90  - 68)  * t);
    return {
      bg:     `rgba(${r},${g},${b},0.85)`,
      border: `rgb(${r},${g},${b})`,
    };
  };

  // Data Formatting
  const matrixChartData = useMemo(() => {
    let rows = multi.data?.matrixRows || [];

    // Apply Frontend Dim2 Filter
    if (!selectedDim2Values.includes('all')) {
      rows = rows.filter(r => selectedDim2Values.includes(String(r.dim2)));
    }

    const dim1Vals = [...new Set(rows.map((r) => r.dim1))];

    if (dim2 === 'none') {
      const lookup = new Map();
      rows.forEach(r => {
        lookup.set(r.dim1, (lookup.get(r.dim1) || 0) + Number(r.value || 0));
      });
      return {
        labels: dim1Vals,
        datasets: [{
          label: 'Total',
          data: dim1Vals.map((d1) => lookup.get(d1) || 0),
          backgroundColor: 'rgba(239,68,68,0.75)',
          borderColor: '#ef4444',
          borderWidth: 1,
        }]
      };
    }

    const dim2Vals = [...new Set(rows.map((r) => r.dim2))];
    const lookup = new Map(rows.map((r) => [`${r.dim1}|||${r.dim2}`, Number(r.value || 0)]));

    return {
      labels: dim1Vals,
      datasets: dim2Vals.map((d2, idx) => {
        const colors = getIndexColor(idx, dim2Vals.length);
        return {
          label: d2,
          data: dim1Vals.map((d1) => lookup.get(`${d1}|||${d2}`) || 0),
          backgroundColor: colors.bg,
          borderColor: colors.border,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        }
      }),
    };
  }, [multi.data, selectedDim2Values, dim2]);

  const timeSeriesChartData = useMemo(() => {
    let rows = multi.data?.timeSeriesRows || [];

    // Apply Frontend Dim2 Filter
    if (!selectedDim2Values.includes('all')) {
      rows = rows.filter(r => selectedDim2Values.includes(String(r.dim2)));
    }

    const periods = [...new Set(rows.map((r) => String(r.period).slice(0, 10)))];

    if (dim2 === 'none') {
      const lookup = new Map();
      rows.forEach(r => {
        const p = String(r.period).slice(0, 10);
        lookup.set(p, (lookup.get(p) || 0) + Number(r.value || 0));
      });
      return {
        labels: periods,
        datasets: [{
          label: 'Total',
          data: periods.map((p) => lookup.get(p) || 0),
          backgroundColor: 'rgba(239,68,68,0.75)',
          borderColor: '#ef4444',
          borderWidth: 1,
          stack: 'stacked',
        }]
      };
    }

    const dim2Vals = [...new Set(rows.map((r) => r.dim2))];
    const lookup = new Map(rows.map((r) => [`${String(r.period).slice(0, 10)}|||${r.dim2}`, Number(r.value || 0)]));

    return {
      labels: periods,
      datasets: dim2Vals.map((d2, idx) => {
        const colors = getIndexColor(idx, dim2Vals.length);
        return {
          label: d2,
          data: periods.map((p) => lookup.get(`${p}|||${d2}`) || 0),
          backgroundColor: colors.bg,
          borderColor: colors.border,
          borderWidth: 2,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5,
          stack: 'stacked',
        }
      }),
    };
  }, [multi.data, selectedDim2Values, dim2]);

  const filteredTotalRecords = useMemo(() => {
    if (effectiveTimeGrain === 'none') {
      const rows = multi.data?.matrixRows || [];
      if (selectedDim2Values.includes('all')) return rows.length;
      return rows.filter(r => selectedDim2Values.includes(String(r.dim2))).length;
    } else {
      const rows = multi.data?.timeSeriesRows || [];
      if (selectedDim2Values.includes('all')) return rows.length;
      return rows.filter(r => selectedDim2Values.includes(String(r.dim2))).length;
    }
  }, [multi.data, selectedDim2Values, effectiveTimeGrain]);

  const filteredMeasureTotal = useMemo(() => {
    const rows = effectiveTimeGrain === 'none'
      ? (multi.data?.matrixRows || [])
      : (multi.data?.timeSeriesRows || []);

    const scopedRows = selectedDim2Values.includes('all')
      ? rows
      : rows.filter(r => selectedDim2Values.includes(String(r.dim2)));

    return scopedRows.reduce((sum, row) => sum + Number(row.value || 0), 0);
  }, [multi.data, selectedDim2Values, effectiveTimeGrain]);

  // Sorted Dimension Data Analysis Table Data
  const sortedDimensionRows = useMemo(() => {
    let baseRows = [];
    if (effectiveTimeGrain === 'none') {
      baseRows = multi.data?.matrixRows || [];
    } else {
      baseRows = multi.data?.timeSeriesRows || [];
    }

    // 1. Apply frontend dim2 filter
    if (!selectedDim2Values.includes('all')) {
      baseRows = baseRows.filter(r => selectedDim2Values.includes(String(r.dim2)));
    }

    // 2. Apply Sorting
    if (!dimTableSort.key || dimTableSort.direction === 'default') return baseRows;

    return [...baseRows].sort((a, b) => {
      let valA = a[dimTableSort.key];
      let valB = b[dimTableSort.key];

      // Special formatting/parsing for period dates if sorting by period
      if (dimTableSort.key === 'period') {
        valA = valA ? String(valA).slice(0, 10) : '';
        valB = valB ? String(valB).slice(0, 10) : '';
      }

      if (valA == null) return 1;
      if (valB == null) return -1;

      const numA = Number(valA);
      const numB = Number(valB);

      const isNumericSort = !isNaN(numA) && !isNaN(numB) && valA !== '' && valB !== '';
      const isDateSort = !isNumericSort && !isNaN(Date.parse(valA)) && !isNaN(Date.parse(valB));

      let comp = 0;
      if (isNumericSort) comp = numA - numB;
      else if (isDateSort) comp = new Date(valA) - new Date(valB);
      else comp = String(valA).localeCompare(String(valB));

      return dimTableSort.direction === 'asc' ? comp : -comp;
    });
  }, [multi.data, selectedDim2Values, effectiveTimeGrain, dimTableSort]);

  // Filtered Raw Data
  const filteredRowsData = useMemo(() => {
    if (!rowsData?.rows) return [];
    return rowsData.rows.filter(row => {
      for (const [col, filterObj] of Object.entries(columnFilters)) {
        if (!filterObj) continue;
        const cellVal = row[col];

        // Text Search
        if (filterObj.text && filterObj.text.trim()) {
          const searchStr = filterObj.text.toLowerCase().trim();
          if (!String(cellVal ?? '').toLowerCase().includes(searchStr)) return false;
        }

        // Multi-Select Array Check
        if (filterObj.selectedValues && Array.isArray(filterObj.selectedValues) && filterObj.selectedValues.length > 0) {
          if (!filterObj.selectedValues.includes('all')) {
            if (!filterObj.selectedValues.includes(String(cellVal ?? ''))) return false;
          }
        }

        // Min / Max Value
        if (filterObj.min !== undefined && filterObj.min !== '') {
          if (Number(cellVal) < Number(filterObj.min)) return false;
        }
        if (filterObj.max !== undefined && filterObj.max !== '') {
          if (Number(cellVal) > Number(filterObj.max)) return false;
        }

        // Date Range
        if (filterObj.start || filterObj.end) {
          if (!cellVal) return false;
          const cellDate = new Date(cellVal);
          if (filterObj.start && cellDate < new Date(filterObj.start)) return false;
          if (filterObj.end && cellDate > new Date(filterObj.end)) return false;
        }
      }
      return true;
    });
  }, [rowsData, columnFilters]);

  // Sorted Raw Data (Applies strictly to already filtered rows)
  const sortedAndFilteredRowsData = useMemo(() => {
    if (!sortConfig.key || sortConfig.direction === 'default') return filteredRowsData;

    return [...filteredRowsData].sort((a, b) => {
      let valA = a[sortConfig.key];
      let valB = b[sortConfig.key];

      // Handle nulls/undefined safely (push to bottom)
      if (valA == null) return 1;
      if (valB == null) return -1;

      // Attempt numeric parsing for sorting
      const numA = Number(valA);
      const numB = Number(valB);

      const isNumericSort = !isNaN(numA) && !isNaN(numB) && valA !== '' && valB !== '';

      // If date parsing is required (detect timestamp formats)
      const isDateSort = !isNumericSort && !isNaN(Date.parse(valA)) && !isNaN(Date.parse(valB));

      let comparison = 0;
      if (isNumericSort) {
        comparison = numA - numB;
      } else if (isDateSort) {
        comparison = new Date(valA) - new Date(valB);
      } else {
        comparison = String(valA).localeCompare(String(valB));
      }

      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });
  }, [filteredRowsData, sortConfig]);

  // Table distinct options cache for datalists
  const distinctColumnValues = useMemo(() => {
    const cache = {};
    if (rowsData?.rows && rowsData?.columns) {
      rowsData.columns.forEach(col => {
        cache[col] = [...new Set(rowsData.rows.map(r => String(r[col] ?? '')))].filter(Boolean);
      });
    }
    return cache;
  }, [rowsData]);

  return (
    <div className="flex h-full w-full flex-col bg-[#050505] text-white overflow-hidden font-sans">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-900 bg-[#080808] px-6 py-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-red-500/20 bg-red-500/10">
            <Database className="h-4 w-4 text-red-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Explorer</h2>
            <p className="text-[11px] text-neutral-500">Slice and visualize data across any dimension combination.</p>
          </div>
        </div>

        {/* View Switcher (Admin Only) */}
        {canUseRawExplorer && (
          <div className="flex gap-1 rounded-full border border-neutral-800 bg-[#0D0D0D] p-1">
            <button onClick={() => setViewTab('multi')} className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all duration-200 ${viewTab === 'multi' ? 'bg-[#1a1a1a] text-white shadow-sm' : 'text-neutral-500 hover:text-neutral-200'}`}>Multi-Dim Analysis</button>
            <button onClick={() => setViewTab('raw')} className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all duration-200 ${viewTab === 'raw' ? 'bg-[#1a1a1a] text-white shadow-sm' : 'text-neutral-500 hover:text-neutral-200'}`}>Raw Table Explorer</button>
          </div>
        )}
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 overflow-y-auto min-w-0 min-h-0 p-6 bg-[#050505]">

        {/* Dynamic Control Bar (Filters) */}
        <div className={`bg-[#0d0d0d] border border-neutral-800/60 rounded-2xl p-5 flex flex-col gap-4 ${viewTab === 'raw' ? 'mb-0 rounded-b-none border-b-0' : 'mb-6'}`}>

          {/* Multi-Dim Controls */}
          {viewTab === 'multi' && (
            <>
              {/* Row 1: Main Dropdowns */}
              <div className="flex flex-row gap-4 items-end flex-wrap relative w-full">

                {/* Time Analysis Toggle */}
                <div className="flex flex-col gap-2 flex-1 min-w-[100px] max-w-[120px] justify-center">
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold mb-1 cursor-pointer select-none" onClick={handleTimeAnalysisToggle}>Time Analysis</label>
                  <button
                    onClick={handleTimeAnalysisToggle}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isTimeAnalysisOn ? 'bg-[#ef4444]' : 'bg-neutral-700'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isTimeAnalysisOn ? 'translate-x-[22px]' : 'translate-x-[4px]'}`} />
                  </button>
                </div>

                {/* Channel Filter */}
                <div className="flex flex-col gap-1 relative flex-1 min-w-[140px]">
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Filter Channels</label>

                  <div
                    onClick={() => setIsChannelDropdownOpen(!isChannelDropdownOpen)}
                    className={`w-full bg-[#0a0a0a] border rounded-xl px-3 py-2 text-xs text-white max-w-none flex items-center justify-between cursor-pointer select-none transition-colors ${isChannelDropdownOpen ? 'border-neutral-600' : 'border-neutral-800 hover:border-neutral-700'}`}
                  >
                    <span className="truncate pr-2">{getChannelButtonLabel()}</span>
                    <ChevronDown size={14} className={`text-neutral-500 transition-transform ${isChannelDropdownOpen ? 'rotate-180' : ''}`} />
                  </div>

                  {isChannelDropdownOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setIsChannelDropdownOpen(false)} />
                      <div className={`absolute top-[100%] left-0 mt-1 w-[220px] bg-[#111111] border border-neutral-700 rounded-lg shadow-2xl z-50 max-h-[280px] overflow-y-auto overflow-x-hidden pb-1 flex flex-col`}>
                        <div className="sticky top-0 bg-[#111111] z-10 px-2 py-2 border-b border-neutral-800">
                          <div className="relative">
                            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-500" />
                            <input
                              type="text"
                              placeholder="Search channels..."
                              className="w-full bg-[#0A0A0A] border border-neutral-700 rounded pl-7 pr-2 py-1.5 text-xs text-white outline-none focus:border-neutral-500 transition-colors"
                              value={channelSearchTerm}
                              onChange={(e) => setChannelSearchTerm(e.target.value)}
                              onClick={(e) => e.stopPropagation()}
                            />
                          </div>
                        </div>

                        <div onClick={() => toggleChannel('all')} className="flex items-center px-3 py-2 text-xs cursor-pointer hover:bg-neutral-800 transition-colors shrink-0">
                          <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center ${selectedChannels.includes('all') ? 'bg-[#ef4444] border-[#ef4444]' : 'border-neutral-600 bg-[#0A0A0A]'}`}>
                            {selectedChannels.includes('all') && <Check size={12} className="text-white" />}
                          </div>
                          <span className={selectedChannels.includes('all') ? 'text-white font-medium' : 'text-neutral-300'}>All Channels</span>
                        </div>
                        <div className="h-px w-full bg-neutral-800 my-1 shrink-0" />

                        {(channelsListData?.channels || [])
                          .filter(c => c.toLowerCase().includes(channelSearchTerm.toLowerCase()))
                          .map((c) => {
                            const isSelected = selectedChannels.includes(c);
                            return (
                              <div key={`filter-${c}`} onClick={() => toggleChannel(c)} className="flex items-center px-3 py-2 text-xs cursor-pointer hover:bg-neutral-800 transition-colors shrink-0">
                                <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center shrink-0 ${isSelected ? 'bg-[#ef4444] border-[#ef4444]' : 'border-neutral-600 bg-[#0A0A0A]'}`}>
                                  {isSelected && <Check size={12} className="text-white" />}
                                </div>
                                <span className={`truncate ${isSelected ? 'text-white font-medium' : 'text-neutral-300'}`} title={c}>{c}</span>
                              </div>
                            );
                          })}
                      </div>
                    </>
                  )}
                </div>

                <div className="flex flex-col gap-1 flex-1 min-w-[120px]">
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Analyze By (X-Axis)</label>
                  <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white w-full outline-none focus:border-neutral-600 transition-colors" value={dim1} onChange={handleDim1Change}>
                    {(dimsData?.dimensions || []).map((d) => <option key={`d1-${d.key}`} value={d.key}>{d.label}</option>)}
                  </select>
                </div>

                <div className="flex flex-col gap-1 flex-1 min-w-[120px]">
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">{isTimeAnalysisOn ? 'Split By (legend)' : 'Segment By (legend)'}</label>
                  <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white w-full outline-none focus:border-neutral-600 transition-colors" value={dim2} onChange={handleDim2Change}>
                    <option value="none">None (Overall Data)</option>
                    {(dimsData?.dimensions || []).filter(d => d.key !== dim1 && d.key !== 'channel').map((d) => <option key={`d2-${d.key}`} value={d.key}>{d.label}</option>)}
                  </select>
                </div>

                {/* Dim 2 Dynamic Filter automatically placed strictly next to Dimension 2 selection */}
                {dim2 !== 'none' && (
                  <div className="flex flex-col gap-1 relative flex-1 min-w-[140px]">
                    <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">{isTimeAnalysisOn ? 'Breakdown' : activeDim2Label}</label>

                    <div
                      onClick={() => setIsDim2DropdownOpen(!isDim2DropdownOpen)}
                      className={`w-full bg-[#0a0a0a] border rounded-xl px-3 py-2 text-xs text-white max-w-none flex items-center justify-between cursor-pointer select-none transition-colors ${isDim2DropdownOpen ? 'border-neutral-600' : 'border-neutral-800 hover:border-neutral-700'}`}
                    >
                      <span className="truncate pr-2">{getDim2ButtonLabel()}</span>
                      <ChevronDown size={14} className={`text-neutral-500 transition-transform ${isDim2DropdownOpen ? 'rotate-180' : ''}`} />
                    </div>

                    {isDim2DropdownOpen && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setIsDim2DropdownOpen(false)} />
                        <div className={`absolute top-[100%] left-0 mt-1 w-[220px] bg-[#111111] border border-neutral-700 rounded-lg shadow-2xl z-50 max-h-[280px] overflow-y-auto overflow-x-hidden pb-1 flex flex-col`}>
                          <div className="sticky top-0 bg-[#111111] z-10 px-2 py-2 border-b border-neutral-800">
                            <div className="relative">
                              <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-500" />
                              <input
                                type="text"
                                placeholder={`Search ${isTimeAnalysisOn ? 'breakdown' : activeDim2Label}s...`}
                                className="w-full bg-[#0A0A0A] border border-neutral-700 rounded pl-7 pr-2 py-1.5 text-xs text-white outline-none focus:border-neutral-500 transition-colors"
                                value={dim2SearchTerm}
                                onChange={(e) => setDim2SearchTerm(e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                              />
                            </div>
                          </div>

                          <div onClick={() => toggleDim2Value('all')} className="flex items-center px-3 py-2 text-xs cursor-pointer hover:bg-neutral-800 transition-colors shrink-0">
                            <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center ${selectedDim2Values.includes('all') ? 'bg-[#ef4444] border-[#ef4444]' : 'border-neutral-600 bg-[#0A0A0A]'}`}>
                              {selectedDim2Values.includes('all') && <Check size={12} className="text-white" />}
                            </div>
                            <span className={selectedDim2Values.includes('all') ? 'text-white font-medium' : 'text-neutral-300'}>All {isTimeAnalysisOn ? 'Breakdown' : activeDim2Label}s</span>
                          </div>
                          <div className="h-px w-full bg-neutral-800 my-1 shrink-0" />

                          {(multi.data?.dim2Values || [])
                            .filter(val => String(val).toLowerCase().includes(dim2SearchTerm.toLowerCase()))
                            .map((val) => {
                              const isSelected = selectedDim2Values.includes(String(val));
                              return (
                                <div key={`filter-dim2-${val}`} onClick={() => toggleDim2Value(val)} className="flex items-center px-3 py-2 text-xs cursor-pointer hover:bg-neutral-800 transition-colors shrink-0">
                                  <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center shrink-0 ${isSelected ? 'bg-[#ef4444] border-[#ef4444]' : 'border-neutral-600 bg-[#0A0A0A]'}`}>
                                    {isSelected && <Check size={12} className="text-white" />}
                                  </div>
                                  <span className={`truncate ${isSelected ? 'text-white font-medium' : 'text-neutral-300'}`} title={val}>{val}</span>
                                </div>
                              );
                            })}
                          {!multi.loading && (multi.data?.dim2Values?.length || 0) === 0 && (
                            <div className="px-3 py-2 text-xs text-neutral-500 italic">No values found</div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                )}


                {!isTimeAnalysisOn && (
                  <div className="flex flex-col gap-1 flex-1 min-w-[140px]">
                    <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Measure (Y-Axis)</label>
                    <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white w-full outline-none focus:border-neutral-600 transition-colors" value={measure} onChange={(e) => setMeasure(e.target.value)}>
                      {(dimsData?.measures || []).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
                    </select>
                  </div>
                )}

                {/* Time Grain: Hidden when Time Analysis is OFF */}
                {isTimeAnalysisOn && (
                  <div className="flex flex-col gap-1 flex-1 min-w-[100px]">
                    <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Time Grain</label>
                    <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white w-full outline-none focus:border-neutral-600 transition-colors" value={timeGrain} onChange={(e) => setTimeGrain(e.target.value)}>
                      <option value="day">By day</option>
                      <option value="week">By week</option>
                      <option value="month">By month</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Row 2: Date Pickers Now Always Visible */}
              <div className="flex flex-row gap-4 items-end pt-4 border-t border-neutral-800/50 mt-2 w-full flex-wrap">
                {isTimeAnalysisOn && (
                  <div className="flex flex-col gap-1 flex-1 min-w-[140px]">
                    <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Date Field</label>
                    <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-1.5 text-xs text-white w-full outline-none focus:border-neutral-600 transition-colors" value={dateField} onChange={(e) => setDateField(e.target.value)}>
                      <option value="upload_date">Upload Date</option>
                      <option value="create_date">Create Date</option>
                      <option value="publish_date">Publish Date</option>
                    </select>
                  </div>
                )}
                <div
                  className="flex flex-col gap-1 flex-1 min-w-[120px] cursor-pointer"
                  onClick={(e) => {
                    const input = e.currentTarget.querySelector('input');
                    if (input && e.target.tagName !== 'INPUT') {
                      try { input.showPicker(); } catch (err) { }
                    }
                  }}
                >
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold cursor-pointer">Date Range from</label>
                  <input
                    type="date"
                    className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-1.5 text-xs text-neutral-300 w-full outline-none focus:border-neutral-600 transition-colors [&::-webkit-calendar-picker-indicator]:invert-[0.8] cursor-pointer"
                    style={{ colorScheme: 'dark' }}
                    min="2025-01-01"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>

                {/* Visual Range Slider */}
                <div className="flex flex-col gap-1 flex-[2] min-w-[200px] justify-center px-2">
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold invisible">Timeline</label>
                  <DualDateSlider startDate={startDate} endDate={endDate} onStartChange={setStartDate} onEndChange={setEndDate} />
                </div>

                <div
                  className="flex flex-col gap-1 flex-1 min-w-[120px] cursor-pointer"
                  onClick={(e) => {
                    const input = e.currentTarget.querySelector('input');
                    if (input && e.target.tagName !== 'INPUT') {
                      try { input.showPicker(); } catch (err) { }
                    }
                  }}
                >
                  <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold cursor-pointer">to</label>
                  <input
                    type="date"
                    className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-1.5 text-xs text-neutral-300 w-full outline-none focus:border-neutral-600 transition-colors [&::-webkit-calendar-picker-indicator]:invert-[0.8] cursor-pointer"
                    style={{ colorScheme: 'dark' }}
                    min="2025-01-01"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}

          {/* Raw Table Controls */}
          {viewTab === 'raw' && canUseRawExplorer && (
            <div className="flex flex-row gap-4 items-end flex-wrap">
              <div className="flex flex-col gap-1 shrink-0 min-w-[140px]">
                <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Select Table</label>
                <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white w-full max-w-sm outline-none focus:border-neutral-600 transition-colors" value={tableName} onChange={(e) => {
                  setTableName(e.target.value);
                  setColumnFilters({}); // Optionally clear filters on table switch
                  setSortConfig({ key: null, direction: 'default' }); // Optionally empty sort
                }}>
                  {safeTables.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1 shrink-0 min-w-[80px]">
                <label className="text-[10px] uppercase tracking-wider text-neutral-500 font-semibold">Rows</label>
                <select className="bg-[#0a0a0a] border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white w-full outline-none focus:border-neutral-600 transition-colors" value={rowLimit} onChange={(e) => setRowLimit(Number(e.target.value))}>
                  <option value={10}>10</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={120}>120</option>
                  <option value={500}>500</option>
                </select>
              </div>

              {/* Clear Filters Button */}
              {(Object.values(columnFilters).some(filterObj => Object.values(filterObj).some(val => val !== '' && val !== undefined)) || sortConfig.key) && (
                <div className="flex shrink-0">
                  <button
                    onClick={() => {
                      setColumnFilters({});
                      setSortConfig({ key: null, direction: 'default' });
                    }}
                    className="h-[34px] px-4 bg-[#ef4444]/10 hover:bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/20 rounded text-xs font-semibold transition-colors flex items-center justify-center"
                  >
                    Clear Filters
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dynamic Views */}
        {viewTab === 'multi' && (
          <div className="space-y-6 pb-8">
            {/* Top Row: Visual Analysis & Metrics */}
            <div className="flex flex-col lg:flex-row gap-6">
              {/* Chart Area */}
              <div className="flex-1 bg-[#0d0d0d] border border-neutral-800/60 rounded-2xl p-5 min-w-0">
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-400 mb-4 flex items-center gap-2">
                  <Activity size={14} className="text-red-400" /> Visual Analysis
                </h3>
                {multi.loading ? (
                  <div className="flex flex-col items-center justify-center h-[360px] w-full bg-[#0a0a0a] border border-dashed border-neutral-800/60 rounded-2xl animate-pulse">
                    <div className="w-8 h-8 border-4 border-neutral-700 border-t-[#ef4444] rounded-full animate-spin mb-4"></div>
                    <span className="text-xs text-neutral-500">Loading new data...</span>
                  </div>
                ) : multi.error ? (
                  <div className="text-red-400 text-sm py-10 text-center">{multi.error}</div>
                ) : (
                  <div className="flex flex-col w-full h-full relative">
                    {/* Pinned custom legend */}
                    {dim2 !== 'none' && (
                      <div className="flex flex-wrap items-center justify-center gap-4 mb-4 z-10 sticky left-0 w-full px-4">
                        {(effectiveTimeGrain === 'none' ? matrixChartData.datasets : timeSeriesChartData.datasets).map((ds, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-xs text-neutral-300">
                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: ds.borderColor }}></span>
                            <span>{ds.label}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Scrollable Chart Area or Empty State */}
                    {(effectiveTimeGrain === 'none' ? matrixChartData.labels.length === 0 : timeSeriesChartData.labels.length === 0) ? (
                      <div className="flex flex-col items-center justify-center h-[360px] w-full text-neutral-500 bg-[#0a0a0a] border border-dashed border-neutral-800/60 rounded-2xl">
                        <Table size={24} className="mb-2 text-neutral-400" />
                        <span className="text-xs">No data available for the selected filters</span>
                      </div>
                    ) : (
                      <div className={`w-full overflow-x-auto overflow-y-hidden`}>
                        <div
                          style={{
                            minWidth: Math.max(100, (effectiveTimeGrain === 'none' ? matrixChartData.labels.length : timeSeriesChartData.labels.length) * 40) + 'px',
                            height: '360px',
                            position: 'relative'
                          }}
                        >
                          {effectiveTimeGrain === 'none'
                            ? <Bar data={matrixChartData} options={{
                                responsive: true,
                                maintainAspectRatio: false,
                                interaction: { mode: 'index', intersect: false },
                                plugins: {
                                  legend: { display: false },
                                  tooltip: {
                                    backgroundColor: 'rgba(10,10,10,0.92)',
                                    borderColor: 'rgba(255,255,255,0.08)',
                                    borderWidth: 1,
                                    titleColor: '#e5e5e5',
                                    bodyColor: '#a3a3a3',
                                    padding: 10,
                                    callbacks: {
                                      labelColor: (ctx) => ({ backgroundColor: ctx.dataset.backgroundColor, borderColor: ctx.dataset.borderColor }),
                                    },
                                  },
                                },
                                scales: {
                                  x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#a3a3a3' } },
                                  y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#a3a3a3' } },
                                },
                                borderRadius: 6,
                                borderSkipped: false,
                              }} />
                            : <Line data={timeSeriesChartData} options={{
                                responsive: true,
                                maintainAspectRatio: false,
                                interaction: { mode: 'index', intersect: false },
                                plugins: {
                                  legend: { display: false },
                                  tooltip: {
                                    backgroundColor: 'rgba(10,10,10,0.92)',
                                    borderColor: 'rgba(255,255,255,0.08)',
                                    borderWidth: 1,
                                    titleColor: '#e5e5e5',
                                    bodyColor: '#a3a3a3',
                                    padding: 10,
                                    callbacks: {
                                      labelColor: (ctx) => ({ backgroundColor: ctx.dataset.borderColor, borderColor: ctx.dataset.borderColor }),
                                    },
                                  },
                                },
                                scales: {
                                  x: { stacked: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#a3a3a3' } },
                                  y: { stacked: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#a3a3a3' } },
                                },
                              }} />
                          }
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Relocated Metrics Sidebar */}
              <div className="w-full lg:w-[260px] shrink-0">
                <div className="bg-[#0d0d0d] border border-neutral-800/60 rounded-2xl p-5 flex flex-col gap-3 h-full">
                  <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-500 mb-1">Summary</div>
                  {multi.loading ? (
                    <div className="flex flex-col gap-3 animate-pulse">
                      {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="bg-[#0a0a0a] border border-neutral-800 rounded-xl p-4 h-[72px]">
                          <div className="w-20 h-2 bg-neutral-800 rounded mb-3"></div>
                          <div className="w-16 h-5 bg-neutral-800 rounded"></div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 lg:grid-cols-1 gap-3">
                      <div className="relative bg-[#0a0a0a] border border-neutral-800 rounded-xl p-4 overflow-hidden">
                        <div className="absolute left-0 top-0 h-0.5 w-full bg-red-500 opacity-40" />
                        <div className="text-[9px] uppercase tracking-[0.15em] text-neutral-500 font-bold mb-1">Total Records</div>
                        <div className="text-2xl font-black text-red-400">{filteredTotalRecords}</div>
                      </div>
                      <div className="relative bg-[#0a0a0a] border border-neutral-800 rounded-xl p-4 overflow-hidden">
                        <div className="absolute left-0 top-0 h-0.5 w-full bg-emerald-500 opacity-40" />
                        <div className="text-[9px] uppercase tracking-[0.15em] text-neutral-500 font-bold mb-1">Measure Total</div>
                        <div className="text-2xl font-black text-emerald-400">{formatNumber(filteredMeasureTotal)}</div>
                      </div>
                      <div className="relative bg-[#0a0a0a] border border-neutral-800 rounded-xl p-4 overflow-hidden">
                        <div className="absolute left-0 top-0 h-0.5 w-full bg-neutral-500 opacity-40" />
                        <div className="text-[9px] uppercase tracking-[0.15em] text-neutral-500 font-bold mb-1">Measure</div>
                        <div className="text-sm font-bold text-neutral-200 capitalize">{measure.replace(/_/g, ' ')}</div>
                      </div>
                      <div className="relative bg-[#0a0a0a] border border-neutral-800 rounded-xl p-4 overflow-hidden">
                        <div className="absolute left-0 top-0 h-0.5 w-full bg-neutral-500 opacity-40" />
                        <div className="text-[9px] uppercase tracking-[0.15em] text-neutral-500 font-bold mb-1">Primary Dim</div>
                        <div className="text-sm font-bold text-neutral-200 capitalize">{dim1.replace(/_/g, ' ')}</div>
                      </div>
                      <div className="relative bg-[#0a0a0a] border border-neutral-800 rounded-xl p-4 overflow-hidden">
                        <div className="absolute left-0 top-0 h-0.5 w-full bg-neutral-500 opacity-40" />
                        <div className="text-[9px] uppercase tracking-[0.15em] text-neutral-500 font-bold mb-1">{isTimeAnalysisOn ? 'Split By' : 'Secondary Dim'}</div>
                        <div className="text-sm font-bold text-neutral-200 capitalize">{dim2.replace(/_/g, ' ')}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Dimension Analysis Data Table */}
            <div className="bg-[#0d0d0d] border border-neutral-800/60 rounded-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-neutral-800/60">
                <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-400 flex items-center gap-2">
                  <Table size={13} className="text-red-400" /> Dimension Analysis Data
                </h3>
              </div>
              {multi.loading ? (
                <div className="p-4 flex flex-col gap-3 animate-pulse">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-8 bg-neutral-800/50 rounded w-full"></div>
                  ))}
                </div>
              ) : multi.error ? (
                <div className="text-red-400 text-sm py-10 text-center">{multi.error}</div>
              ) : (
                <div className={`overflow-x-auto max-h-[420px]`}>
                  <table className="min-w-full text-xs text-left border-collapse whitespace-nowrap">
                    <thead className="bg-[#0A0A0A] sticky top-0 z-10">
                      <tr>
                        {effectiveTimeGrain === 'none' ? (
                          <>
                            <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a]">
                              <div
                                className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
                                onClick={() => setDimTableSort(p => ({
                                  key: 'dim1',
                                  direction: p.key === 'dim1' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                }))}
                              >
                                {dim1}
                                {dimTableSort.key === 'dim1' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                              </div>
                            </th>
                            {dim2 !== 'none' && (
                              <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a]">
                                <div
                                  className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
                                  onClick={() => setDimTableSort(p => ({
                                    key: 'dim2',
                                    direction: p.key === 'dim2' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                  }))}
                                >
                                  {dim2}
                                  {dimTableSort.key === 'dim2' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                                </div>
                              </th>
                            )}
                            <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a] text-right">
                              <div
                                className="flex items-center justify-end gap-2 cursor-pointer hover:text-white transition-colors"
                                onClick={() => setDimTableSort(p => ({
                                  key: 'value',
                                  direction: p.key === 'value' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                }))}
                              >
                                Value
                                {dimTableSort.key === 'value' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                              </div>
                            </th>
                          </>
                        ) : (
                          <>
                            <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a]">
                              <div
                                className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
                                onClick={() => setDimTableSort(p => ({
                                  key: 'period',
                                  direction: p.key === 'period' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                }))}
                              >
                                Period
                                {dimTableSort.key === 'period' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                              </div>
                            </th>
                            <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a]">
                              <div
                                className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
                                onClick={() => setDimTableSort(p => ({
                                  key: 'dim1',
                                  direction: p.key === 'dim1' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                }))}
                              >
                                {dim1}
                                {dimTableSort.key === 'dim1' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                              </div>
                            </th>
                            {dim2 !== 'none' && (
                              <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a]">
                                <div
                                  className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
                                  onClick={() => setDimTableSort(p => ({
                                    key: 'dim2',
                                    direction: p.key === 'dim2' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                  }))}
                                >
                                  {isTimeAnalysisOn ? 'Breakdown' : dim2}
                                  {dimTableSort.key === 'dim2' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                                </div>
                              </th>
                            )}
                            <th className="px-4 py-3 font-bold text-neutral-500 uppercase text-[10px] tracking-[0.12em] border-b border-neutral-800/60 bg-[#0a0a0a] text-right">
                              <div
                                className="flex items-center justify-end gap-2 cursor-pointer hover:text-white transition-colors"
                                onClick={() => setDimTableSort(p => ({
                                  key: 'value',
                                  direction: p.key === 'value' ? (p.direction === 'asc' ? 'desc' : (p.direction === 'desc' ? 'default' : 'asc')) : 'asc'
                                }))}
                              >
                                Value
                                {dimTableSort.key === 'value' ? (dimTableSort.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />) : <ArrowUpDown size={12} />}
                              </div>
                            </th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {effectiveTimeGrain === 'none' ? (
                        sortedDimensionRows.map((r, idx) => {
                          return (
                            <tr key={`matrix-${idx}`} className="border-b border-neutral-900 hover:bg-neutral-800/50 transition-colors">
                              <td className="px-4 py-2 text-neutral-200">{r.dim1}</td>
                              {dim2 !== 'none' && <td className="px-4 py-2 text-neutral-200">{r.dim2}</td>}
                              <td className="px-4 py-2 text-neutral-200 text-right">{formatNumber(r.value)}</td>
                            </tr>
                          );
                        })
                      ) : (
                        sortedDimensionRows.map((r, idx) => {
                          return (
                            <tr key={`ts-${idx}`} className="border-b border-neutral-900 hover:bg-neutral-800/50 transition-colors">
                              <td className="px-4 py-2 text-neutral-200">{String(r.period).slice(0, 10)}</td>
                              <td className="px-4 py-2 text-neutral-200">{r.dim1}</td>
                              {dim2 !== 'none' && <td className="px-4 py-2 text-neutral-200">{r.dim2}</td>}
                              <td className="px-4 py-2 text-neutral-200 text-right">{formatNumber(r.value)}</td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {viewTab === 'raw' && canUseRawExplorer && (
          <div className="space-y-6 pb-8">
            <div className="bg-[#0d0d0d] border border-neutral-800/60 rounded-b-2xl overflow-hidden">
              {rowsLoading && <div className="text-neutral-500 text-sm py-10 text-center">Loading table...</div>}
              {rowsError && <div className="text-red-400 text-sm py-10 text-center">{rowsError}</div>}
              {!rowsLoading && !rowsError && (
                <div className={`overflow-x-auto overflow-y-auto max-h-[600px]`}>
                  <table className="min-w-full text-xs text-left border-collapse whitespace-nowrap relative">
                    <thead className="sticky top-0 z-20 shadow-sm after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-full after:h-[1px] after:bg-neutral-800">
                      <tr>
                        {(rowsData?.columns || []).map((col) => {
                          const colLower = String(col).toLowerCase();
                          const isDateCol = ['create_date', 'publish_date', 'upload_date'].includes(colLower);
                          const isDurationCol = ['created_duration', 'published_duration', 'uploaded_duration'].includes(colLower);
                          const isIdCol = colLower.includes('_id') || colLower === 'id';
                          const distincts = distinctColumnValues[col] || [];
                          const isNumericCol = isDurationCol || isIdCol || (distincts.length > 0 && distincts.every(val => val !== '' && !isNaN(Number(val))));

                          const isSortable = isNumericCol || isDateCol;

                          return (
                            <th key={`th-${col}`} className="px-4 py-3 font-semibold text-neutral-500 uppercase bg-[#0a0a0a] text-[10px] tracking-[0.12em]">
                              <div className="mb-2 whitespace-nowrap flex items-center justify-between gap-2">
                                <span>{col}</span>
                                {isSortable && (
                                  <div
                                    onClick={() => handleSortToggle(col)}
                                    className="cursor-pointer hover:bg-neutral-800 p-1 rounded transition-colors text-neutral-500 hover:text-white"
                                  >
                                    {sortConfig.key === col ? (
                                      sortConfig.direction === 'asc' ? <ArrowUp size={12} className="text-[#ef4444]" /> : <ArrowDown size={12} className="text-[#ef4444]" />
                                    ) : (
                                      <ArrowUpDown size={12} />
                                    )}
                                  </div>
                                )}
                              </div>
                            </th>
                          );
                        })}
                      </tr>
                      <tr>
                        {(rowsData?.columns || []).map((col) => {
                          const colLower = String(col).toLowerCase();
                          const isDateCol = ['create_date', 'publish_date', 'upload_date'].includes(colLower);
                          const isDurationCol = ['created_duration', 'published_duration', 'uploaded_duration'].includes(colLower);

                          return (
                            <th key={`filter-${col}`} className="px-2 pb-3 bg-[#0a0a0a] align-top border-b border-neutral-800/60">
                              {isDateCol ? (
                                <div className="flex flex-col gap-1 min-w-[120px]">
                                  <input
                                    type="date"
                                    title="Start Date"
                                    className="w-full bg-[#0a0a0a] border border-neutral-800 rounded-lg px-2 py-1.5 text-xs text-neutral-300 outline-none focus:border-neutral-600 transition-colors [&::-webkit-calendar-picker-indicator]:invert-[0.8]"
                                    value={columnFilters[col]?.start || ''}
                                    onChange={(e) => handleColumnFilterChange(col, 'start', e.target.value)}
                                  />
                                  <input
                                    type="date"
                                    title="End Date"
                                    className="w-full bg-[#0a0a0a] border border-neutral-800 rounded-lg px-2 py-1.5 text-xs text-neutral-300 outline-none focus:border-neutral-600 transition-colors [&::-webkit-calendar-picker-indicator]:invert-[0.8]"
                                    value={columnFilters[col]?.end || ''}
                                    onChange={(e) => handleColumnFilterChange(col, 'end', e.target.value)}
                                  />
                                </div>
                              ) : isDurationCol ? (
                                <div className="flex flex-col gap-1 min-w-[80px]">
                                  <input
                                    type="number"
                                    placeholder=">= Min"
                                    className="w-full bg-[#0a0a0a] border border-neutral-800 rounded-lg px-2 py-1.5 text-xs text-neutral-300 outline-none focus:border-neutral-600 transition-colors"
                                    value={columnFilters[col]?.min || ''}
                                    onChange={(e) => handleColumnFilterChange(col, 'min', e.target.value)}
                                  />
                                  <input
                                    type="number"
                                    placeholder="<= Max"
                                    className="w-full bg-[#0a0a0a] border border-neutral-800 rounded-lg px-2 py-1.5 text-xs text-neutral-300 outline-none focus:border-neutral-600 transition-colors"
                                    value={columnFilters[col]?.max || ''}
                                    onChange={(e) => handleColumnFilterChange(col, 'max', e.target.value)}
                                  />
                                </div>
                              ) : (
                                (() => {
                                  const distincts = distinctColumnValues[col] || [];
                                  const isNumericCol = distincts.length > 0 && distincts.every(val => val !== '' && !isNaN(Number(val)));
                                  const renderMultiSelect = !isNumericCol && distincts.length > 10;

                                  if (renderMultiSelect) {
                                    const selectedArr = columnFilters[col]?.selectedValues || ['all'];
                                    const isOpen = columnFilters[col]?.dropdownOpen || false;
                                    const searchTerm = columnFilters[col]?.search || '';

                                    const toggleValue = (val) => {
                                      let newSelection = [...selectedArr].filter(v => v !== 'all');
                                      if (val === 'all') {
                                        newSelection = ['all'];
                                      } else {
                                        if (newSelection.includes(val)) {
                                          newSelection = newSelection.filter(v => v !== val);
                                        } else {
                                          newSelection.push(val);
                                        }
                                        if (newSelection.length === 0) newSelection = ['all'];
                                      }
                                      handleColumnFilterChange(col, 'selectedValues', newSelection);
                                    };

                                    const getLabel = () => {
                                      if (selectedArr.includes('all')) return 'All Values';
                                      if (selectedArr.length === 1) return selectedArr[0];
                                      return `${selectedArr.length} Selected`;
                                    };

                                    return (
                                      <div className="flex flex-col gap-1 relative min-w-[140px] max-w-[180px]">
                                        <div
                                          onClick={() => handleColumnFilterChange(col, 'dropdownOpen', !isOpen)}
                                          className={`bg-[#0A0A0A] border rounded px-3 py-1.5 text-xs text-neutral-300 w-full flex items-center justify-between cursor-pointer select-none transition-colors ${isOpen ? 'border-[#ef4444]' : 'border-neutral-700 hover:border-neutral-600'}`}
                                        >
                                          <span className="truncate pr-2">{getLabel()}</span>
                                          <ChevronDown size={14} className={`text-neutral-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                                        </div>

                                        {isOpen && (
                                          <>
                                            <div className="fixed inset-0 z-40" onClick={() => handleColumnFilterChange(col, 'dropdownOpen', false)} />
                                            <div className={`absolute top-[100%] left-0 mt-1 w-[220px] bg-[#111111] border border-neutral-700 rounded-lg shadow-2xl z-50 max-h-[240px] overflow-y-auto overflow-x-hidden py-1 flex flex-col font-normal`}>
                                              <div className="sticky top-0 bg-[#111111] z-10 px-2 py-2 border-b border-neutral-800">
                                                <div className="relative">
                                                  <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-500" />
                                                  <input
                                                    type="text"
                                                    placeholder="Search..."
                                                    className="w-full bg-[#0A0A0A] border border-neutral-700 rounded pl-7 pr-2 py-1.5 text-xs text-white outline-none focus:border-neutral-500 transition-colors"
                                                    value={searchTerm}
                                                    onChange={(e) => handleColumnFilterChange(col, 'search', e.target.value)}
                                                    onClick={(e) => e.stopPropagation()}
                                                  />
                                                </div>
                                              </div>

                                              <div onClick={() => toggleValue('all')} className="flex items-center px-3 py-2 text-xs cursor-pointer hover:bg-neutral-800 transition-colors shrink-0">
                                                <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center ${selectedArr.includes('all') ? 'bg-[#ef4444] border-[#ef4444]' : 'border-neutral-600 bg-[#0A0A0A]'}`}>
                                                  {selectedArr.includes('all') && <Check size={12} className="text-white" />}
                                                </div>
                                                <span className={selectedArr.includes('all') ? 'text-white font-medium' : 'text-neutral-300'}>All Values</span>
                                              </div>
                                              <div className="h-px w-full bg-neutral-800 my-1 shrink-0" />

                                              {distincts
                                                .filter(c => String(c).toLowerCase().includes(searchTerm.toLowerCase()))
                                                .map((c) => {
                                                  const isSelected = selectedArr.includes(String(c));
                                                  return (
                                                    <div key={`ms-${c}`} onClick={() => toggleValue(String(c))} className="flex items-center px-3 py-2 text-xs cursor-pointer hover:bg-neutral-800 transition-colors shrink-0">
                                                      <div className={`w-4 h-4 rounded border mr-2 flex items-center justify-center shrink-0 ${isSelected ? 'bg-[#ef4444] border-[#ef4444]' : 'border-neutral-600 bg-[#0A0A0A]'}`}>
                                                        {isSelected && <Check size={12} className="text-white" />}
                                                      </div>
                                                      <span className={`truncate ${isSelected ? 'text-white font-medium' : 'text-neutral-300'}`} title={c}>{c}</span>
                                                    </div>
                                                  );
                                                })}
                                            </div>
                                          </>
                                        )}
                                      </div>
                                    );
                                  }

                                  return (
                                    <div className="min-w-[100px] max-w-[160px]">
                                      <input
                                        type={isNumericCol ? "number" : "text"}
                                        list={isNumericCol ? undefined : `list-${col}`}
                                        placeholder={`Filter${isNumericCol ? ' number' : ''}...`}
                                        className="w-full bg-[#0a0a0a] border border-neutral-800 rounded-lg px-2 py-1.5 text-xs text-neutral-300 outline-none focus:border-neutral-600 transition-colors"
                                        value={columnFilters[col]?.text || ''}
                                        onChange={(e) => handleColumnFilterChange(col, 'text', e.target.value)}
                                      />
                                      {!isNumericCol && (
                                        <datalist id={`list-${col}`}>
                                          {distincts.map(val => (
                                            <option key={val} value={val} />
                                          ))}
                                        </datalist>
                                      )}
                                    </div>
                                  );
                                })()
                              )}
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {sortedAndFilteredRowsData.length === 0 ? (
                        <tr>
                          <td colSpan={rowsData?.columns?.length || 1} className="px-4 py-8 text-center text-neutral-500 italic">No matching rows</td>
                        </tr>
                      ) : (
                        sortedAndFilteredRowsData.map((row, idx) => (
                          <tr key={`${tableName}-${idx}`} className="border-b border-neutral-900 hover:bg-neutral-800/50 transition-colors">
                            {(rowsData?.columns || []).map((col) => (
                              <td key={`${idx}-${col}`} className="px-4 py-2 text-neutral-200">{String(row[col] ?? '')}</td>
                            ))}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
