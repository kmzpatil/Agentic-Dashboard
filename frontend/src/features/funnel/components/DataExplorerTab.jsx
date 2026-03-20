import React from 'react';
import { formatNumber, formatPct } from '../../../lib/formatters';
import { useApi } from '../../../hooks/useApi';
import { API_BASE } from '../../../lib/constants';
import FunnelViewContextStrip from './FunnelViewContextStrip';

const Card = ({ children, className = '' }) => (
  <div className={`bg-[#111111] rounded-xl border border-neutral-800 p-4 ${className}`}>{children}</div>
);

const CardTitle = ({ title, desc }) => (
  <div className="mb-3">
    <h3 className="text-[14px] font-semibold text-white">{title}</h3>
    {desc && <p className="mt-1 text-[12px] text-neutral-500 leading-relaxed">{desc}</p>}
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

  React.useEffect(() => {
    setSelectedVideoId(null);
  }, [breakdown, filterQuery]);

  return (
    <div className="space-y-2.5">
      <FunnelViewContextStrip breakdown={breakdown} filters={filters} />

      <Card>
        <CardTitle title={`Top-down breakdown (${breakdown})`} desc="Breakdown of volume and conversion across the current view." />
        <div className="overflow-auto max-h-[340px]">
          <table className="w-full min-w-[680px] table-fixed text-sm">
            <colgroup>
              <col className="w-auto" />
              <col className="w-28" />
              <col className="w-28" />
              <col className="w-28" />
              <col className="w-28" />
            </colgroup>
            <thead className="sticky top-0 bg-[#111111]">
              <tr className="text-neutral-500 border-b border-neutral-800">
                <th className="px-2 text-left py-2 text-[12px] font-medium">Label</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Uploaded</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Created</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Published</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Conversion</th>
              </tr>
            </thead>
            <tbody>
              {(data?.breakdown || []).map((row, index) => (
                <tr key={`${row.label || 'unknown'}-${index}`} className="border-b border-neutral-900 hover:bg-[#0d0d0d] transition-colors">
                  <td className="px-2 py-2 text-neutral-200 text-[13px] font-medium truncate" title={row.label || '(unknown)'}>{row.label || '(unknown)'}</td>
                  <td className="px-2 py-2 text-right text-neutral-400 text-[13px] whitespace-nowrap">{formatNumber(row.uploaded_count)}</td>
                  <td className="px-2 py-2 text-right text-neutral-400 text-[13px] whitespace-nowrap">{formatNumber(row.created_count)}</td>
                  <td className="px-2 py-2 text-right text-neutral-400 text-[13px] whitespace-nowrap">{formatNumber(row.published_count)}</td>
                  <td className="px-2 py-2 text-right text-neutral-300 text-[13px] font-mono whitespace-nowrap">{formatPct(row.conversion)}</td>
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
        <div className="mb-2 text-[12px] text-neutral-500">
          Showing {journeyVideos.length} video pipelines from the current filtered view.
        </div>
        <div className="overflow-auto max-h-[320px]">
          <table className="w-full min-w-[980px] table-fixed text-sm">
            <colgroup>
              <col className="w-28" />
              <col className="w-32" />
              <col className="w-28" />
              <col className="w-24" />
              <col className="w-24" />
              <col className="w-20" />
              <col className="w-auto" />
              {canInspectRawJourney && <col className="w-24" />}
            </colgroup>
            <thead className="sticky top-0 bg-[#111111]">
              <tr className="text-neutral-500 border-b border-neutral-800">
                <th className="px-2 text-left py-2 text-[12px] font-medium whitespace-nowrap">Video ID</th>
                <th className="px-2 text-left py-2 text-[12px] font-medium whitespace-nowrap">Input</th>
                <th className="px-2 text-left py-2 text-[12px] font-medium whitespace-nowrap">Language</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Created</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Published</th>
                <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Conv</th>
                <th className="px-2 text-left py-2 text-[12px] font-medium">Output mix</th>
                {canInspectRawJourney && <th className="px-2 text-right py-2 text-[12px] font-medium whitespace-nowrap">Inspect</th>}
              </tr>
            </thead>
            <tbody>
              {journeyVideos.map((row) => (
                <tr key={row.video_id} className="border-b border-neutral-900 hover:bg-[#0d0d0d] transition-colors">
                  <td className="px-2 py-2 text-neutral-200 text-[13px] font-mono whitespace-nowrap">{row.video_id}</td>
                  <td className="px-2 py-2 text-neutral-400 text-[13px] truncate" title={row.input_type || '-'}>{row.input_type || '-'}</td>
                  <td className="px-2 py-2 text-neutral-400 text-[13px] truncate" title={row.language || '-'}>{row.language || '-'}</td>
                  <td className="px-2 py-2 text-right text-neutral-400 text-[13px] whitespace-nowrap">{formatNumber(row.created_assets)}</td>
                  <td className="px-2 py-2 text-right text-neutral-400 text-[13px] whitespace-nowrap">{formatNumber(row.published_posts)}</td>
                  <td className="px-2 py-2 text-right text-neutral-300 text-[13px] font-mono whitespace-nowrap">{formatPct(row.conversion)}</td>
                  <td className="px-2 py-2 text-neutral-500 text-[12px] truncate" title={(row.output_mix || []).join(' | ') || '-'}>{(row.output_mix || []).join(' | ') || '-'}</td>
                  {canInspectRawJourney && (
                    <td className="px-2 py-2 text-right">
                      <button
                        className="px-3 py-1 rounded-full text-[12px] font-medium bg-[#1A1A1A] text-neutral-300 hover:bg-[#2A2A2A] transition-colors"
                        onClick={() => setSelectedVideoId(row.video_id)}
                      >
                        View
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
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 px-3"
          onClick={() => setSelectedVideoId(null)}
        >
          <Card
            className="w-full max-w-5xl max-h-[88vh] overflow-hidden p-4 md:p-5"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-[14px] font-semibold text-white">Video {selectedVideoId} — detailed asset journey</h3>
              <button
                className="text-[12px] px-3 py-1 rounded-full bg-[#1A1A1A] text-neutral-300 hover:bg-[#2A2A2A] transition-colors"
                onClick={() => setSelectedVideoId(null)}
              >
                Close
              </button>
            </div>

            <div className="max-h-[calc(88vh-72px)] overflow-y-auto pr-1">
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
                      <div key={item.k} className="bg-[#0A0A0A] border border-neutral-800 rounded-lg p-2.5 text-[12px]">
                        <span className="text-neutral-500">{item.k}: </span>
                        <span className="text-neutral-200">{item.v || '-'}</span>
                      </div>
                    ))}
                  </div>
                  <div className="overflow-auto max-h-[340px]">
                    <table className="w-full min-w-[760px] table-fixed text-[12px]">
                      <colgroup>
                        <col className="w-32" />
                        <col className="w-24" />
                        <col className="w-24" />
                        <col className="w-32" />
                        <col className="w-auto" />
                      </colgroup>
                      <thead className="sticky top-0 bg-[#111111]">
                        <tr className="text-neutral-500">
                          <th className="px-2 text-left py-2 whitespace-nowrap">Asset</th>
                          <th className="px-2 text-left py-2 whitespace-nowrap">Output</th>
                          <th className="px-2 text-right py-2 whitespace-nowrap">Created Dur</th>
                          <th className="px-2 text-left py-2 whitespace-nowrap">Post</th>
                          <th className="px-2 text-left py-2">Platforms</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(videoDetails.data.assets || []).map((a, idx) => (
                          <tr key={`${a.asset_id || 'asset'}-${a.post_id || 'no-post'}-${idx}`} className="border-b border-neutral-900">
                            <td className="px-2 py-2 text-neutral-200 truncate" title={a.asset_id || '-'}>{a.asset_id || '-'}</td>
                            <td className="px-2 py-2 text-neutral-400 truncate" title={a.output_type || '-'}>{a.output_type || '-'}</td>
                            <td className="px-2 py-2 text-right text-neutral-400 whitespace-nowrap">{formatNumber(a.created_duration)}</td>
                            <td className="px-2 py-2 text-neutral-400 truncate" title={a.post_id || '-'}>{a.post_id || '-'}</td>
                            <td className="px-2 py-2 text-neutral-400 truncate" title={(a.platforms || []).join(', ') || '-'}>{(a.platforms || []).join(', ') || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
