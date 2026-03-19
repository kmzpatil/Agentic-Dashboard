import { formatNumber } from '../../../lib/formatters';

export const SMALL_FLOW_SHARE = 0.018;
export const MAX_BREAKDOWN_SOURCES = 10;

function sankeyLinkSort(a, b) {
  const aFromOther = a.from === 'Other' ? 1 : 0;
  const bFromOther = b.from === 'Other' ? 1 : 0;
  if (aFromOther !== bFromOther) return aFromOther - bFromOther;
  return b.flow - a.flow || a.from.localeCompare(b.from) || a.to.localeCompare(b.to);
}

export function normalizeSankeyLinks(links = []) {
  return links
    .map((item) => ({
      from: String(item?.from || ''),
      to: String(item?.to || ''),
      flow: Number(item?.flow || 0),
      edgeType: item?.edgeType,
    }))
    .filter((item) => item.from && item.to && item.flow > 0)
    .sort(sankeyLinkSort);
}

const STAGE_NODE_ALIASES = {
  upload: 'Uploaded',
  uploaded: 'Uploaded',
  processed: 'Processed',
  'not processed': 'Not Processed',
  created: 'Created',
  published: 'Published',
  'not published': 'Not Published',
  platform: 'Platform posts',
  'platform posts': 'Platform posts',
};

function canonicalizeStageNode(label) {
  const key = String(label || '').trim().toLowerCase();
  return STAGE_NODE_ALIASES[key] || String(label || '').trim();
}

export function normalizeStageSankeyLinks(links = []) {
  const normalized = normalizeSankeyLinks(links)
    .map((item) => ({
      ...item,
      from: canonicalizeStageNode(item.from),
      to: canonicalizeStageNode(item.to),
    }))
    .filter((item) => item.from && item.to && item.flow > 0);

  const merged = new Map();
  normalized.forEach((item) => {
    const key = `${item.from}::${item.to}`;
    const prev = merged.get(key);
    if (!prev) {
      merged.set(key, { ...item });
      return;
    }
    merged.set(key, {
      ...prev,
      flow: Number(prev.flow || 0) + Number(item.flow || 0),
    });
  });

  const edgeMap = new Map(Array.from(merged.values()).map((item) => [`${item.from}::${item.to}`, item]));
  const getFlow = (from, to) => Number(edgeMap.get(`${from}::${to}`)?.flow || 0);

  const uploadedToProcessed = getFlow('Uploaded', 'Processed');
  const uploadedToNotProcessed = getFlow('Uploaded', 'Not Processed');
  const processedToCreatedRaw = getFlow('Processed', 'Created');
  const createdToPublished = getFlow('Created', 'Published');
  const createdToNotPublished = getFlow('Created', 'Not Published');
  const publishedToPlatformRaw = getFlow('Published', 'Platform posts');

  const processedToCreated = uploadedToProcessed > 0
    ? Math.min(processedToCreatedRaw, uploadedToProcessed)
    : processedToCreatedRaw;
  const createdExpansion = Math.max(processedToCreatedRaw - processedToCreated, 0);

  const publishedToPlatform = createdToPublished > 0
    ? Math.min(publishedToPlatformRaw, createdToPublished)
    : publishedToPlatformRaw;
  const platformExpansion = Math.max(publishedToPlatformRaw - publishedToPlatform, 0);

  const repaired = [];
  if (uploadedToProcessed > 0) repaired.push({ from: 'Uploaded', to: 'Processed', flow: uploadedToProcessed, edgeType: 'uploaded_to_processed' });
  if (uploadedToNotProcessed > 0) repaired.push({ from: 'Uploaded', to: 'Not Processed', flow: uploadedToNotProcessed, edgeType: 'uploaded_to_not_processed' });
  if (processedToCreated > 0) repaired.push({ from: 'Processed', to: 'Created', flow: processedToCreated, edgeType: 'processed_to_created' });
  if (createdExpansion > 0) repaired.push({ from: 'Asset Expansion', to: 'Created', flow: createdExpansion, edgeType: 'asset_expansion_to_created' });
  if (createdToPublished > 0) repaired.push({ from: 'Created', to: 'Published', flow: createdToPublished, edgeType: 'created_to_published' });
  if (createdToNotPublished > 0) repaired.push({ from: 'Created', to: 'Not Published', flow: createdToNotPublished, edgeType: 'created_to_not_published' });
  if (publishedToPlatform > 0) repaired.push({ from: 'Published', to: 'Platform posts', flow: publishedToPlatform, edgeType: 'published_to_platform' });
  if (platformExpansion > 0) repaired.push({ from: 'Cross-post Expansion', to: 'Platform posts', flow: platformExpansion, edgeType: 'cross_post_expansion_to_platform' });

  const handledEdges = new Set([
    'Uploaded::Processed',
    'Uploaded::Not Processed',
    'Processed::Created',
    'Created::Published',
    'Created::Not Published',
    'Published::Platform posts',
  ]);

  edgeMap.forEach((item, key) => {
    if (handledEdges.has(key)) return;
    repaired.push(item);
  });

  return repaired.sort(sankeyLinkSort);
}

export function normalizeLinksByIncomingCapacity(links = [], nodeOrder = []) {
  const normalized = normalizeSankeyLinks(links);
  if (!normalized.length || !nodeOrder.length) return normalized;

  const outgoingByNode = new Map();
  normalized.forEach((item) => {
    if (!outgoingByNode.has(item.from)) outgoingByNode.set(item.from, []);
    outgoingByNode.get(item.from).push(item);
  });

  const incomingByNode = new Map();
  const adjusted = [];
  const visited = new Set();

  const processNode = (node) => {
    const outgoing = outgoingByNode.get(node) || [];
    if (!outgoing.length) {
      visited.add(node);
      return;
    }

    const totalOutgoing = outgoing.reduce((sum, item) => sum + Number(item.flow || 0), 0);
    const incoming = Number(incomingByNode.get(node) || 0);

    // Source nodes (no incoming) keep original magnitudes. Other nodes are capped by incoming flow.
    let factor = 1;
    if (incoming > 0 && totalOutgoing > incoming) {
      factor = incoming / totalOutgoing;
    }

    outgoing.forEach((item) => {
      const adjustedFlow = Number(item.flow || 0) * factor;
      adjusted.push({
        ...item,
        flow: adjustedFlow,
        rawFlow: Number(item.flow || 0),
      });
      incomingByNode.set(item.to, Number(incomingByNode.get(item.to) || 0) + adjustedFlow);
    });

    visited.add(node);
  };

  nodeOrder.forEach(processNode);

  // Process any nodes not explicitly ordered.
  outgoingByNode.forEach((_value, node) => {
    if (!visited.has(node)) processNode(node);
  });

  return adjusted.sort(sankeyLinkSort);
}

export function groupSmallLinks(links = [], minShare = SMALL_FLOW_SHARE) {
  const normalized = normalizeSankeyLinks(links);
  if (!normalized.length) return [];

  const total = normalized.reduce((sum, item) => sum + item.flow, 0);
  const threshold = total * minShare;
  if (!threshold) return normalized;

  const grouped = [];
  const buckets = new Map();

  normalized.forEach((item) => {
    const edgeType = String(item.edgeType || '');
    const preserveOutcomeEdge =
      edgeType.startsWith('client_to_') ||
      edgeType.endsWith('_to_published') ||
      edgeType.endsWith('_to_not_published') ||
      edgeType === 'published_to_platform';
    if (preserveOutcomeEdge || item.flow >= threshold || item.to === 'Other') {
      grouped.push(item);
      return;
    }

    const key = `${item.from}::Other`;
    const prev = buckets.get(key);
    buckets.set(key, {
      from: item.from,
      to: 'Other',
      flow: (prev?.flow || 0) + item.flow,
      edgeType: item.edgeType,
      grouped: true,
    });
  });

  return [...grouped, ...Array.from(buckets.values())]
    .sort(sankeyLinkSort);
}

export function buildBreakdownOutcomeLinks(
  rows = [],
  breakdown,
  maxSources = MAX_BREAKDOWN_SOURCES,
  aggregateRemainderAsOther = false,
  publishedPlatformTailLinks = [],
) {
  const prepared = rows
    .map((row) => {
      const from = String(row?.label || '').trim();
      const created = Number(row?.created_count || 0);
      const published = Number(row?.published_count || 0);
      const notPublished = Math.max(created - published, 0);
      return { from, created, published, notPublished };
    })
    .filter((row) => row.from && row.from !== 'Published' && row.from !== 'Not Published' && row.from !== 'Other')
    .sort((a, b) => b.created - a.created);

  const edgePrefix = breakdown || 'dimension';
  const sourceLimit = Number.isFinite(maxSources) && maxSources > 0 ? Number(maxSources) : prepared.length;
  const kept = prepared.slice(0, sourceLimit);
  const remainder = prepared.slice(sourceLimit);
  const links = [];

  kept.forEach((row) => {
    if (row.published > 0) {
      links.push({ from: row.from, to: 'Published', flow: row.published, edgeType: `${edgePrefix}_to_published`, zoomValue: row.from });
    }
    if (row.notPublished > 0) {
      links.push({ from: row.from, to: 'Not Published', flow: row.notPublished, edgeType: `${edgePrefix}_to_not_published`, zoomValue: row.from });
    }
  });

  if (aggregateRemainderAsOther && remainder.length > 0) {
    const otherPublished = remainder.reduce((sum, row) => sum + row.published, 0);
    const otherNotPublished = remainder.reduce((sum, row) => sum + row.notPublished, 0);
    if (otherPublished > 0) {
      links.push({ from: 'Other', to: 'Published', flow: otherPublished, edgeType: `${edgePrefix}_to_published`, grouped: true });
    }
    if (otherNotPublished > 0) {
      links.push({ from: 'Other', to: 'Not Published', flow: otherNotPublished, edgeType: `${edgePrefix}_to_not_published`, grouped: true });
    }
  }

  const platformTail = (publishedPlatformTailLinks || [])
    .map((item) => ({
      from: String(item?.from || ''),
      to: String(item?.to || ''),
      flow: Number(item?.flow || 0),
      edgeType: String(item?.edgeType || ''),
    }))
    .filter((item) => item.from === 'Published' && item.to && item.to !== 'Published' && item.flow > 0);

  if (!platformTail.length) return links;

  const publishedInflow = links
    .filter((item) => item.to === 'Published' && item.from !== 'Published')
    .reduce((sum, item) => sum + Number(item.flow || 0), 0);
  const platformTotal = platformTail.reduce((sum, item) => sum + Number(item.flow || 0), 0);

  if (publishedInflow > 0 && platformTotal > 0) {
    const scale = publishedInflow / platformTotal;
    return [
      ...links,
      ...platformTail.map((item) => ({
        ...item,
        flow: item.flow * scale,
      })),
    ];
  }

  return [...links, ...platformTail];
}

export function buildFromTotals(links = []) {
  return links.reduce((acc, item) => {
    acc[item.from] = (acc[item.from] || 0) + item.flow;
    return acc;
  }, {});
}

export function makeSankeyOptions(fromTotals = {}, extras = {}, { interactive = false, hiddenSources = 0 } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    color: '#e5e7eb',
    font: { size: 12, weight: '600', family: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif' },
    layout: { padding: { top: 10, right: 24, bottom: 14, left: 24 } },
    interaction: { mode: 'nearest', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        displayColors: false,
        backgroundColor: 'rgba(9, 9, 11, 0.96)',
        borderColor: 'rgba(63, 63, 70, 0.9)',
        borderWidth: 1,
        titleColor: '#fafafa',
        bodyColor: '#d4d4d8',
        padding: 12,
        titleFont: { size: 13, weight: 'bold' },
        bodyFont: { size: 12 },
        callbacks: {
          title: (items) => {
            const raw = items?.[0]?.raw || {};
            const fromLabel = raw.from === 'Other' && hiddenSources > 0
              ? `Other (${hiddenSources} sources)`
              : (raw.from || 'Source');
            return `${fromLabel} → ${raw.to || 'Target'}`;
          },
          label: (ctx) => {
            const raw = ctx?.raw || {};
            const flow = Number(raw.flow || 0);
            const fromTotal = Number(fromTotals[raw.from] || 0);
            const share = fromTotal > 0 ? (flow / fromTotal) * 100 : 0;
            const lines = [`${formatNumber(Math.round(flow))} flow (${share.toFixed(1)}% of ${raw.from || 'source'})`];
            if (interactive && !raw.grouped) {
              const toLower = (raw.to || '').toLowerCase();
              if (toLower === 'published' || toLower === 'not published') {
                lines.push('Click to filter by this source');
              }
            }
            return lines;
          },
        },
      },
    },
    ...extras,
  };
}
