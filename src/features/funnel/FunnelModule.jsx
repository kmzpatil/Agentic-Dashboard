import React, { useMemo, useState } from 'react';
import { Chart } from 'react-chartjs-2';
import { Layers } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { API_BASE } from '../../lib/constants';
import { formatNumber, formatPct } from '../../lib/formatters';
import KpiCard from '../../components/common/KpiCard';

export default function FunnelModule() {
  const [breakdown, setBreakdown] = useState('channel');
  const [zoomFilter, setZoomFilter] = useState({ dimension: '', value: '' });
  const [selectedVideoId, setSelectedVideoId] = useState(null);

  const funnelQuery = `${API_BASE}/funnel?breakdown=${encodeURIComponent(breakdown)}${zoomFilter.dimension ? `&dimension=${encodeURIComponent(zoomFilter.dimension)}&value=${encodeURIComponent(zoomFilter.value)}` : ''}`;
  const { data, loading, error } = useApi(funnelQuery, [breakdown, zoomFilter.dimension, zoomFilter.value]);
  const videoDetails = useApi(selectedVideoId ? `${API_BASE}/funnel/video/${selectedVideoId}` : null, [selectedVideoId]);

  const stageSankeyData = useMemo(() => ({
    datasets: [{
      data: data?.sankeyLinks || [],
      colorFrom: '#6b7280',
      colorTo: '#ef4444',
      colorMode: 'gradient',
      borderWidth: 1,
    }],
  }), [data]);

  const compositionSankeyData = useMemo(() => ({
    datasets: [{
      data: data?.compositionLinks || [],
      colorFrom: '#60a5fa',
      colorTo: '#ef4444',
      colorMode: 'gradient',
      borderWidth: 0.5,
    }],
  }), [data]);

  const handleCompositionClick = (_event, elements) => {
    if (!elements?.length || !data?.compositionLinks?.length) return;
    const link = data.compositionLinks[elements[0].index];
    if (!link) return;

    if (link.to.startsWith('Input: ')) {
      setZoomFilter({ dimension: 'input_type', value: link.to.replace('Input: ', '') });
    } else if (link.to.startsWith('Output: ')) {
      setZoomFilter({ dimension: 'output_type', value: link.to.replace('Output: ', '') });
    }
  };

  const sankeyOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
  };

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-[#050505]">
      <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-neutral-500 mb-2">BREAKDOWN</label>
          <select className="bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white" value={breakdown} onChange={(e) => setBreakdown(e.target.value)}>
            <option value="channel">channel</option>
            <option value="input_type">input_type</option>
            <option value="language">language</option>
            <option value="output_type">output_type</option>
          </select>
        </div>
        <button onClick={() => setZoomFilter({ dimension: '', value: '' })} className="px-4 py-2 rounded-full bg-[#1A1A1A] text-neutral-200 text-sm hover:bg-[#2A2A2A]">Reset zoom</button>
        {zoomFilter.dimension && <div className="text-sm text-neutral-400">Zoomed: {zoomFilter.dimension} = <span className="text-white font-semibold">{zoomFilter.value}</span></div>}
      </div>

      {loading && <div className="text-neutral-400">Loading funnel...</div>}
      {error && <div className="text-red-400">{error}</div>}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <KpiCard title="UPLOADED" value={formatNumber(data?.stageCounts?.uploaded_count)} subtitle="Raw videos" />
            <KpiCard title="PROCESSED" value={formatNumber(data?.stageCounts?.processed_count)} subtitle="Reached creation" />
            <KpiCard title="CREATED" value={formatNumber(data?.stageCounts?.created_count)} subtitle="Assets generated" />
            <KpiCard title="PUBLISHED" value={formatNumber(data?.stageCounts?.published_count)} subtitle="Published posts" />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
              <h3 className="font-bold text-white mb-4 flex items-center gap-2"><Layers size={16} /> STAGE FLOW</h3>
              <div className="h-[300px]">
                <Chart type="sankey" data={stageSankeyData} options={sankeyOptions} />
              </div>
            </div>
            <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
              <h3 className="font-bold text-white mb-1 flex items-center gap-2"><Layers size={16} /> INPUT TO OUTPUT TO PUBLISH FLOW</h3>
              <p className="text-xs text-neutral-500 mb-3">Click a flow link to zoom into an input type or output type journey.</p>
              <div className="h-[300px]">
                <Chart type="sankey" data={compositionSankeyData} options={{ ...sankeyOptions, onClick: handleCompositionClick }} />
              </div>
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4">Top-down breakdown ({breakdown})</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-neutral-500 border-b border-neutral-800">
                    <th className="text-left py-2">Label</th>
                    <th className="text-right py-2">Uploaded</th>
                    <th className="text-right py-2">Created</th>
                    <th className="text-right py-2">Published</th>
                    <th className="text-right py-2">Conversion</th>
                    <th className="text-right py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.breakdown || []).map((row) => (
                    <tr key={row.label} className="border-b border-neutral-900">
                      <td className="py-2 text-white">{row.label || '(unknown)'}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.uploaded_count)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.created_count)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.published_count)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatPct(row.conversion)}</td>
                      <td className="py-2 text-right">
                        <button className="px-3 py-1 rounded-full text-xs bg-[#1A1A1A] text-neutral-200 hover:bg-[#2A2A2A]" onClick={() => setZoomFilter({ dimension: breakdown, value: row.label })}>zoom</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
            <h3 className="font-bold text-white mb-4">Raw Video Journey Inspector</h3>
            <div className="overflow-auto max-h-[320px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-[#0A0A0A]">
                  <tr className="text-neutral-500 border-b border-neutral-800">
                    <th className="text-left py-2">Video ID</th>
                    <th className="text-left py-2">Input</th>
                    <th className="text-left py-2">Language</th>
                    <th className="text-right py-2">Created</th>
                    <th className="text-right py-2">Published</th>
                    <th className="text-right py-2">Conv</th>
                    <th className="text-left py-2">Output mix</th>
                    <th className="text-right py-2">Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.journeyVideos || []).slice(0, 40).map((row) => (
                    <tr key={row.video_id} className="border-b border-neutral-900">
                      <td className="py-2 text-white">{row.video_id}</td>
                      <td className="py-2 text-neutral-300">{row.input_type || '-'}</td>
                      <td className="py-2 text-neutral-300">{row.language || '-'}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.created_assets)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatNumber(row.published_posts)}</td>
                      <td className="py-2 text-right text-neutral-300">{formatPct(row.conversion)}</td>
                      <td className="py-2 text-neutral-400 text-xs">{(row.output_mix || []).join(' | ') || '-'}</td>
                      <td className="py-2 text-right">
                        <button className="px-3 py-1 rounded-full text-xs bg-[#1A1A1A] text-neutral-200 hover:bg-[#2A2A2A]" onClick={() => setSelectedVideoId(row.video_id)}>view</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {selectedVideoId && (
            <div className="bg-[#111111] rounded-xl border border-neutral-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-white">Video {selectedVideoId} detailed asset journey</h3>
                <button className="text-xs px-3 py-1 rounded-full bg-[#1A1A1A] hover:bg-[#2A2A2A]" onClick={() => setSelectedVideoId(null)}>Close</button>
              </div>
              {videoDetails.loading && <div className="text-neutral-400">Loading video details...</div>}
              {videoDetails.error && <div className="text-red-400">{videoDetails.error}</div>}
              {videoDetails.data && (
                <div className="space-y-3 text-sm">
                  <div className="text-neutral-300">{videoDetails.data.video.headline || '(no headline)'}</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Input: {videoDetails.data.video.input_type || '-'}</div>
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Language: {videoDetails.data.video.language || '-'}</div>
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Channels: {(videoDetails.data.video.channels || []).join(', ') || '-'}</div>
                    <div className="bg-[#0A0A0A] border border-neutral-800 rounded p-2">Uploaded duration: {formatNumber(videoDetails.data.video.uploaded_duration)}</div>
                  </div>
                  <div className="overflow-auto max-h-[280px]">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-[#0A0A0A]">
                        <tr>
                          <th className="text-left py-2">Asset</th>
                          <th className="text-left py-2">Output</th>
                          <th className="text-right py-2">Created Dur</th>
                          <th className="text-left py-2">Post</th>
                          <th className="text-left py-2">Platforms</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(videoDetails.data.assets || []).map((a) => (
                          <tr key={a.asset_id} className="border-b border-neutral-900">
                            <td className="py-2">{a.asset_id}</td>
                            <td className="py-2">{a.output_type || '-'}</td>
                            <td className="py-2 text-right">{formatNumber(a.created_duration)}</td>
                            <td className="py-2">{a.post_id || '-'}</td>
                            <td className="py-2">{(a.platforms || []).join(', ') || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
