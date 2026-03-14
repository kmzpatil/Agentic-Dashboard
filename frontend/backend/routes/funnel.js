const express = require('express');
const { buildFunnelFilter, buildAccessFilter } = require('../queries/analyticsShared');
const {
  getStageCountsQuery,
  getBreakdownQuery,
  getCompositionQuery,
  getJourneyQuery,
  getMixQuery,
  getVideoHeaderQuery,
  getVideoAssetsQuery,
} = require('../queries/funnelQueries');

function createFunnelRouter(pool) {
  const router = express.Router();

  router.get('/', async (req, res) => {
    const dimension = req.query.dimension;
    const value     = req.query.value;
    const breakdownDimension = ['channel', 'input_type', 'language', 'output_type'].includes(req.query.breakdown)
      ? req.query.breakdown
      : 'channel';

    const filter = buildFunnelFilter(dimension, value, 1, req.auth);

    try {
      const stageCounts = (await pool.query(getStageCountsQuery(filter), filter.params)).rows[0];

      const breakdown = (await pool.query(getBreakdownQuery(filter, breakdownDimension), filter.params)).rows.map((row) => ({
        ...row,
        conversion: Number(Number(row.conversion || 0).toFixed(2)),
      }));

      const compositionEdgesRaw = (await pool.query(getCompositionQuery(filter), filter.params)).rows;
      const compositionLinks = compositionEdgesRaw
        .filter((row) => Number(row.flow) > 0)
        .sort((a, b) => Number(b.flow) - Number(a.flow))
        .slice(0, 120)
        .map((row) => ({
          from:     row.edge_from,
          to:       row.edge_to,
          flow:     Number(row.flow),
          edgeType: row.edge_type,
        }));

      const journeyRows = (await pool.query(getJourneyQuery(filter), filter.params)).rows;
      const mixRows     = (await pool.query(getMixQuery(filter),     filter.params)).rows;

      const mixByVideo = new Map();
      mixRows.forEach((row) => {
        const key = Number(row.video_id);
        if (!mixByVideo.has(key)) mixByVideo.set(key, []);
        mixByVideo.get(key).push(`${row.output_type}: ${row.published_count}/${row.created_count}`);
      });

      const journeyVideos = journeyRows.map((row) => ({
        ...row,
        conversion: Number(Number(row.conversion || 0).toFixed(2)),
        output_mix: (mixByVideo.get(Number(row.video_id)) || []).slice(0, 4),
      }));

      res.json({
        filter:           { dimension: dimension || null, value: value || null },
        stageCounts,
        sankeyLinks: [
          { from: 'Uploaded',  to: 'Processed', flow: Number(stageCounts.processed_count) },
          { from: 'Processed', to: 'Created',   flow: Number(stageCounts.created_count)   },
          { from: 'Created',   to: 'Published', flow: Number(stageCounts.published_count) },
        ],
        compositionLinks,
        breakdownDimension,
        breakdown,
        journeyVideos,
      });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  router.get('/video/:videoId', async (req, res) => {
    const videoId = Number(req.params.videoId);
    if (Number.isNaN(videoId)) {
      return res.status(400).json({ error: 'Invalid video id' });
    }

    try {
      const accessFilter = buildAccessFilter(req.auth, 2, 'rv');
      const accessParams = [videoId, ...accessFilter.params];

      const headerResult = await pool.query(getVideoHeaderQuery(accessFilter), accessParams);

      if (headerResult.rowCount === 0) {
        return res.status(404).json({ error: 'Video not found' });
      }

      const assetsResult = await pool.query(getVideoAssetsQuery(accessFilter), accessParams);

      return res.json({
        video:  headerResult.rows[0],
        assets: assetsResult.rows,
      });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  return router;
}

module.exports = {
  createFunnelRouter,
};
