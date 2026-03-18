import React from 'react';
import { formatNumber, formatPct } from '../../../lib/formatters';
import { useApi } from '../../../hooks/useApi';
import { API_BASE } from '../../../lib/constants';

const Card = ({ children, className = '' }) => (
  <div className={`bg-[#111111] rounded-xl border border-neutral-800 p-5 ${className}`}>{children}</div>
);

const CardTitle = ({ title, desc }) => (
  <div className="mb-4">
    <h3 className="text-[13px] font-semibold text-white">{title}</h3>
    {desc && <p className="mt-1 text-[11px] text-neutral-500 leading-relaxed">{desc}</p>}
  </div>
);

export default function DataExplorerTab({ authUser, data, breakdown, filters }) {
  const role = authUser?.role || 'user';
  const canInspectRawJourney = role === 'website_admin' || role === 'client_admin';
  const [selectedVideoId, setSelectedVideoId] = React.useState(null);
  const journeyVideos = data?.journeyVideos || [];
  const filterQuery = React.useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const query = params.toString();
    return query ? `?${query}` : '';
  }, [filters]);
  const videoDetailsUrl = canInspectRawJourney && selectedVideoId
    ? `${API_BASE}/funnel/video/${selectedVideoId}${filterQuery}`
    : null;
  const videoDetails = useApi(videoDetailsUrl, [videoDetailsUrl]);
  const viewLabel = (breakdown || 'channel').replace('_', ' ');
  const activeFilters = Object.entries(filters || {}).filter(([, v]) => v);

  React.useEffect(() => {
    setSelectedVideoId(null);
  }, [breakdown, filterQuery]);

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
        <CardTitle title={`Top-down breakdown (${breakdown})`} desc="Breakdown of volume and conversion across the current view." />
        <div className="overflow-auto max-h-[340px]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[#111111]">
              <tr className="text-neutral-500 border-b border-neutral-800">
                <th className="text-left py-2 text-[11px] font-medium">Label</th>
                <th className="text-right py-2 text-[11px] font-medium">Uploaded</th>
                <th className="text-right py-2 text-[11px] font-medium">Created</th>
                <th className="text-right py-2 text-[11px] font-medium">Published</th>
                <th className="text-right py-2 text-[11px] font-medium">Conversion</th>
              </tr>
            </thead>
            <tbody>
              {(data?.breakdown || []).map((row, index) => (
                <tr key={`${row.label || 'unknown'}-${index}`} className="border-b border-neutral-900 hover:bg-[#0d0d0d] transition-colors">
                  <td className="py-2 text-neutral-200 text-[12px] font-medium">{row.label || '(unknown)'}</td>
                  <td className="py-2 text-right text-neutral-400 text-[12px]">{formatNumber(row.uploaded_count)}</td>
                  <td className="py-2 text-right text-neutral-400 text-[12px]">{formatNumber(row.created_count)}</td>
                  <td className="py-2 text-right text-neutral-400 text-[12px]">{formatNumber(row.published_count)}</td>
                  <td className="py-2 text-right text-neutral-300 text-[12px] font-mono">{formatPct(row.conversion)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardTitle title="Raw Video Journey Inspector" desc="Inspect individual raw video pipelines — see every asset and its publication status." />
        {!canInspectRawJourney && (
          <div className="rounded-lg border border-neutral-800 bg-[#0a0a0a] px-3 py-2 text-[11.5px] text-neutral-400">
            Raw journey inspection is available for client_admin and website_admin roles.
          </div>
        )}
        <div className="mb-2 text-[11px] text-neutral-500">
          Showing {journeyVideos.length} video pipelines from the current filtered view.
        </div>
        <div className="overflow-auto max-h-[320px]">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[#111111]">
              <tr className="text-neutral-500 border-b border-neutral-800">
                <th className="text-left py-2 text-[11px] font-medium">Video ID</th>
                <th className="text-left py-2 text-[11px] font-medium">Input</th>
                <th className="text-left py-2 text-[11px] font-medium">Language</th>
                <th className="text-right py-2 text-[11px] font-medium">Created</th>
                <th className="text-right py-2 text-[11px] font-medium">Published</th>
                <th className="text-right py-2 text-[11px] font-medium">Conv</th>
                <th className="text-left py-2 text-[11px] font-medium">Output mix</th>
                {canInspectRawJourney && <th className="text-right py-2 text-[11px] font-medium">Inspect</th>}
              </tr>
            </thead>
            <tbody>
              {journeyVideos.map((row) => (
                <tr key={row.video_id} className="border-b border-neutral-900 hover:bg-[#0d0d0d] transition-colors">
                  <td className="py-2 text-neutral-200 text-[12px] font-mono">{row.video_id}</td>
                  <td className="py-2 text-neutral-400 text-[12px]">{row.input_type || '-'}</td>
                  <td className="py-2 text-neutral-400 text-[12px]">{row.language || '-'}</td>
                  <td className="py-2 text-right text-neutral-400 text-[12px]">{formatNumber(row.created_assets)}</td>
                  <td className="py-2 text-right text-neutral-400 text-[12px]">{formatNumber(row.published_posts)}</td>
                  <td className="py-2 text-right text-neutral-300 text-[12px] font-mono">{formatPct(row.conversion)}</td>
                  <td className="py-2 text-neutral-500 text-[10.5px]">{(row.output_mix || []).join(' | ') || '-'}</td>
                  {canInspectRawJourney && (
                    <td className="py-2 text-right">
                      <button
                        className="px-3 py-1 rounded-full text-[10.5px] font-medium bg-[#1A1A1A] text-neutral-300 hover:bg-[#2A2A2A] transition-colors"
                        onClick={() => setSelectedVideoId(row.video_id)}
                      >
                        view
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {canInspectRawJourney && selectedVideoId && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[13px] font-semibold text-white">Video {selectedVideoId} — detailed asset journey</h3>
            <button
              className="text-[10.5px] px-3 py-1 rounded-full bg-[#1A1A1A] text-neutral-300 hover:bg-[#2A2A2A] transition-colors"
              onClick={() => setSelectedVideoId(null)}
            >
              Close
            </button>
          </div>
          {videoDetails.loading && <div className="text-neutral-400 text-sm">Loading video details...</div>}
          {videoDetails.error && <div className="text-red-400 text-sm">{videoDetails.error}</div>}
          {videoDetails.data && (
            <div className="space-y-3 text-sm">
              <div className="text-neutral-300">{videoDetails.data.video.headline || '(no headline)'}</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { k: 'Input', v: videoDetails.data.video.input_type },
                  { k: 'Language', v: videoDetails.data.video.language },
                  { k: 'Channels', v: (videoDetails.data.video.channels || []).join(', ') },
                  { k: 'Duration', v: formatNumber(videoDetails.data.video.uploaded_duration) },
                ].map((item) => (
                  <div key={item.k} className="bg-[#0A0A0A] border border-neutral-800 rounded-lg p-2.5 text-[11.5px]">
                    <span className="text-neutral-500">{item.k}: </span>
                    <span className="text-neutral-200">{item.v || '-'}</span>
                  </div>
                ))}
              </div>
              <div className="overflow-auto max-h-[280px]">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-[#111111]">
                    <tr className="text-neutral-500">
                      <th className="text-left py-2">Asset</th>
                      <th className="text-left py-2">Output</th>
                      <th className="text-right py-2">Created Dur</th>
                      <th className="text-left py-2">Post</th>
                      <th className="text-left py-2">Platforms</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(videoDetails.data.assets || []).map((a, idx) => (
                      <tr key={`${a.asset_id || 'asset'}-${a.post_id || 'no-post'}-${idx}`} className="border-b border-neutral-900">
                        <td className="py-2 text-neutral-200">{a.asset_id}</td>
                        <td className="py-2 text-neutral-400">{a.output_type || '-'}</td>
                        <td className="py-2 text-right text-neutral-400">{formatNumber(a.created_duration)}</td>
                        <td className="py-2 text-neutral-400">{a.post_id || '-'}</td>
                        <td className="py-2 text-neutral-400">{(a.platforms || []).join(', ') || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
