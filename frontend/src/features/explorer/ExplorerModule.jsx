import React, { useEffect, useMemo, useState } from 'react';
import { Bar, Line, Pie } from 'react-chartjs-2';
import { Database, Table } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber } from '../../lib/formatters';
import { ExplorerSkeleton, TableSkeleton } from '../../components/common/Skeleton';

export default function ExplorerModule({ authUser }) {
  const canUseRawExplorer = authUser?.role === 'website_admin';

  const { data: tableData } = useApi(canUseRawExplorer ? `${API_BASE}/explorer/tables` : null, [canUseRawExplorer]);
  const { data: dimsData }  = useApi(`${API_BASE}/explorer/dimensions`, []);

  const [tableName,    setTableName]    = useState('');
  const [chartType,    setChartType]    = useState('bar');
  const [xColumn,      setXColumn]      = useState('');
  const [aggregation,  setAggregation]  = useState('count');
  const [yColumn,      setYColumn]      = useState('');
  const [dim1,         setDim1]         = useState('channel');
  const [dim2,         setDim2]         = useState('language');
  const [measure,      setMeasure]      = useState('uploaded_videos');
  const [timeGrain,    setTimeGrain]    = useState('none');
  const [dateField,    setDateField]    = useState('upload_date');
  const [dim1Value,    setDim1Value]    = useState('');

  useEffect(() => {
    if (!tableName && tableData?.tables?.length) setTableName(tableData.tables[0]);
  }, [tableData, tableName]);

  const tableUrl = canUseRawExplorer && tableName
    ? `${API_BASE}/explorer/table/${encodeURIComponent(tableName)}?limit=120`
    : null;
  const { data: rowsData, loading: rowsLoading, error: rowsError } = useApi(tableUrl, [tableUrl]);

  useEffect(() => {
    if (rowsData?.columns?.length) {
      if (!xColumn) setXColumn(rowsData.columns[0]);
      if (!yColumn) setYColumn(rowsData.columns[0]);
    }
  }, [rowsData, xColumn, yColumn]);

  const chartQuery = canUseRawExplorer && tableName && xColumn
    ? `${API_BASE}/explorer/chart?table=${encodeURIComponent(tableName)}&x=${encodeURIComponent(xColumn)}&aggregation=${encodeURIComponent(aggregation)}${aggregation === 'sum' ? `&y=${encodeURIComponent(yColumn)}` : ''}`
    : null;
  const { data: chartRows } = useApi(chartQuery, [chartQuery]);

  const multiQuery = `${API_BASE}/explorer/multidim?dim1=${encodeURIComponent(dim1)}&dim2=${encodeURIComponent(dim2)}&measure=${encodeURIComponent(measure)}&timeGrain=${encodeURIComponent(timeGrain)}&dateField=${encodeURIComponent(dateField)}${dim1Value ? `&dim1Value=${encodeURIComponent(dim1Value)}` : ''}`;
  const multi = useApi(multiQuery, [dim1, dim2, measure, timeGrain, dateField, dim1Value]);

  const tableChartData = useMemo(() => {
    const labels = (chartRows?.rows || []).map((row) => row.label || '(null)');
    const values = (chartRows?.rows || []).map((row) => Number(row.value || 0));
    return {
      labels,
      datasets: [{
        label:           `${aggregation}(${aggregation === 'sum' ? yColumn : '*'}) by ${xColumn}`,
        data:            values,
        backgroundColor: labels.map((_l, idx) => (idx % 2 === 0 ? 'rgba(239,68,68,0.65)' : 'rgba(96,165,250,0.65)')),
        borderColor:     'rgba(239,68,68,1)',
        borderWidth:     1,
      }],
    };
  }, [chartRows, aggregation, xColumn, yColumn]);

  const ChartComponent = chartType === 'pie' ? Pie : chartType === 'line' ? Line : Bar;

  const matrixChartData = useMemo(() => {
    const rows      = multi.data?.matrixRows || [];
    const dim1Vals  = [...new Set(rows.map((r) => r.dim1))].slice(0, 12);
    const dim2Vals  = [...new Set(rows.map((r) => r.dim2))].slice(0, 8);
    const lookup    = new Map(rows.map((r) => [`${r.dim1}|||${r.dim2}`, Number(r.value || 0)]));

    return {
      labels:   dim1Vals,
      datasets: dim2Vals.map((d2, idx) => ({
        label:           d2,
        data:            dim1Vals.map((d1) => lookup.get(`${d1}|||${d2}`) || 0),
        backgroundColor: `hsla(${(idx * 47) % 360}, 70%, 55%, 0.6)`,
        borderColor:     `hsla(${(idx * 47) % 360}, 70%, 55%, 1)`,
        borderWidth:     1,
      })),
    };
  }, [multi.data]);

  const timeSeriesChartData = useMemo(() => {
    const rows    = multi.data?.timeSeriesRows || [];
    const periods = [...new Set(rows.map((r) => String(r.period).slice(0, 10)))];
    const dim2Vals = [...new Set(rows.map((r) => r.dim2))].slice(0, 10);
    const lookup   = new Map(rows.map((r) => [`${String(r.period).slice(0, 10)}|||${r.dim2}`, Number(r.value || 0)]));

    return {
      labels:   periods,
      datasets: dim2Vals.map((d2, idx) => ({
        label:           d2,
        data:            periods.map((p) => lookup.get(`${p}|||${d2}`) || 0),
        backgroundColor: `hsla(${(idx * 47) % 360}, 70%, 55%, 0.55)`,
        borderColor:     `hsla(${(idx * 47) % 360}, 70%, 55%, 1)`,
        borderWidth:     1,
        stack:           'stacked',
      })),
    };
  }, [multi.data]);

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
        <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Database size={16} /> MULTI-DIMENSION ANALYSIS</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-4">
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dim1} onChange={(e) => setDim1(e.target.value)}>
            {(dimsData?.dimensions || []).map((d) => <option key={`d1-${d.key}`} value={d.key}>Dim1: {d.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dim2} onChange={(e) => setDim2(e.target.value)}>
            {(dimsData?.dimensions || []).map((d) => <option key={`d2-${d.key}`} value={d.key}>Dim2: {d.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={measure} onChange={(e) => setMeasure(e.target.value)}>
            {(dimsData?.measures || []).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={timeGrain} onChange={(e) => setTimeGrain(e.target.value)}>
            <option value="none">No time split</option>
            <option value="day">By day</option>
            <option value="week">By week</option>
            <option value="month">By month</option>
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dateField} onChange={(e) => setDateField(e.target.value)}>
            {(dimsData?.dateFields || []).map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
          </select>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={dim1Value} onChange={(e) => setDim1Value(e.target.value)}>
            <option value="">All {dim1}</option>
            {(multi.data?.dim1Values || []).slice(0, 80).map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>

        {multi.loading && <ExplorerSkeleton />}
        {multi.error   && <div className="text-red-400">{multi.error}</div>}

        {!multi.loading && !multi.error && (
          <>
            <div className="h-[360px] mb-4">
              {timeGrain === 'none'
                ? <Bar data={matrixChartData} options={{ responsive: true, maintainAspectRatio: false }} />
                : <Bar data={timeSeriesChartData} options={{ responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } } }} />
              }
            </div>
            <div className="overflow-auto max-h-[300px]">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-[#0A0A0A]">
                  <tr>
                    <th className="text-left px-2 py-2 text-neutral-400">{dim1}</th>
                    <th className="text-left px-2 py-2 text-neutral-400">{dim2}</th>
                    <th className="text-right px-2 py-2 text-neutral-400">value</th>
                  </tr>
                </thead>
                <tbody>
                  {(multi.data?.matrixRows || []).slice(0, 200).map((r, idx) => (
                    <tr key={`${r.dim1}-${r.dim2}-${idx}`} className="border-b border-neutral-900">
                      <td className="px-2 py-2 text-neutral-200">{r.dim1}</td>
                      <td className="px-2 py-2 text-neutral-200">{r.dim2}</td>
                      <td className="px-2 py-2 text-right text-neutral-200">{formatNumber(r.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {canUseRawExplorer ? (
        <>
          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-xs text-neutral-500 mb-2">TABLE</label>
              <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={tableName} onChange={(e) => setTableName(e.target.value)}>
                {(tableData?.tables || []).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-neutral-500 mb-2">X COLUMN</label>
              <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={xColumn} onChange={(e) => setXColumn(e.target.value)}>
                {(rowsData?.columns || []).map((col) => <option key={col} value={col}>{col}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-neutral-500 mb-2">AGGREGATION</label>
              <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={aggregation} onChange={(e) => setAggregation(e.target.value)}>
                <option value="count">count</option>
                <option value="sum">sum</option>
              </select>
            </div>
            {aggregation === 'sum' && (
              <div>
                <label className="block text-xs text-neutral-500 mb-2">Y COLUMN</label>
                <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={yColumn} onChange={(e) => setYColumn(e.target.value)}>
                  {(rowsData?.columns || []).map((col) => <option key={col} value={col}>{col}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="block text-xs text-neutral-500 mb-2">CHART TYPE</label>
              <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={chartType} onChange={(e) => setChartType(e.target.value)}>
                <option value="bar">bar</option>
                <option value="line">line</option>
                <option value="pie">pie</option>
              </select>
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Database size={16} /> TABLE CHART BUILDER</h3>
            <div className="h-[340px]">
              <ChartComponent data={tableChartData} options={{ responsive: true, maintainAspectRatio: false }} />
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Table size={16} /> TABLE DATA ({tableName || '-'})</h3>
            {rowsLoading && <TableSkeleton rows={6} cols={5} />}
            {rowsError   && <div className="text-red-400">{rowsError}</div>}
            {!rowsLoading && !rowsError && (
              <div className="overflow-auto max-h-[420px]">
                <table className="min-w-full text-xs">
                  <thead className="sticky top-0 bg-[#0A0A0A]">
                    <tr>
                      {(rowsData?.columns || []).map((col) => (
                        <th key={col} className="text-left px-3 py-2 text-neutral-400 border-b border-neutral-800">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(rowsData?.rows || []).map((row, idx) => (
                      <tr key={`${tableName}-${idx}`} className="border-b border-neutral-900 hover:bg-[#0A0A0A]">
                        {(rowsData?.columns || []).map((col) => (
                          <td key={`${idx}-${col}`} className="px-3 py-2 text-neutral-200 whitespace-nowrap">{String(row[col] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 text-sm text-neutral-400">
          Raw table browsing is available only for <strong className="text-neutral-200">website_admin</strong> users.
          Multi-dimension analytics above is role-scoped to your account.
        </div>
      )}
    </div>
  );
}
