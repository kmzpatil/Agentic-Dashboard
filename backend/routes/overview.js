const express = require('express');
const {
  KPI_QUERY,
  CHANNEL_TOP_PERFORMER_QUERY,
  USER_TOP_PERFORMER_QUERY,
  INPUT_TOP_PERFORMER_QUERY,
  OUTPUT_TOP_PERFORMER_QUERY,
  LANGUAGE_TOP_PERFORMER_QUERY,
  ALERTS_QUERY,
} = require('../queries/overviewQueries');

function createOverviewRouter(pool) {
  const router = express.Router();

  router.get('/', async (_req, res) => {
    try {
      const [kpiResult, channelResult, userResult, inputResult, outputResult, langResult, alertResult] = await Promise.all([
        pool.query(KPI_QUERY),
        pool.query(CHANNEL_TOP_PERFORMER_QUERY),
        pool.query(USER_TOP_PERFORMER_QUERY),
        pool.query(INPUT_TOP_PERFORMER_QUERY),
        pool.query(OUTPUT_TOP_PERFORMER_QUERY),
        pool.query(LANGUAGE_TOP_PERFORMER_QUERY),
        pool.query(ALERTS_QUERY),
      ]);

      const kpis = kpiResult.rows[0];

      const topPerformers = [
        { dimension: 'Channel', ...(channelResult.rows[0] || {}) },
        { dimension: 'User', ...(userResult.rows[0] || {}) },
        { dimension: 'Input Type', ...(inputResult.rows[0] || {}) },
        { dimension: 'Output Type', ...(outputResult.rows[0] || {}) },
        { dimension: 'Language', ...(langResult.rows[0] || {}) },
      ].filter((item) => item.label);

      const alerts = alertResult.rows.map((row) => ({
        title: `${row.channel_name}: ${Number(row.conversion).toFixed(2)}% conversion`,
        subtitle: `${row.created_count} created, ${row.published_count} published`,
        severity: Number(row.conversion) < 0.5 ? 'critical' : 'warning',
      }));

      res.json({ kpis, topPerformers, alerts });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  return router;
}

module.exports = {
  createOverviewRouter,
};
