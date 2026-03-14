const express = require('express');
const {
  getKpiQuery,
  getChannelTopPerformerQuery,
  getUserTopPerformerQuery,
  getInputTopPerformerQuery,
  getOutputTopPerformerQuery,
  getLanguageTopPerformerQuery,
  getAlertsQuery,
} = require('../queries/overviewQueries');
const { buildAccessFilter } = require('../queries/analyticsShared');

function createOverviewRouter(pool) {
  const router = express.Router();

  router.get('/', async (req, res) => {
    try {
      const accessFilter = buildAccessFilter(req.auth, 1, 'rv');
      const [kpiResult, channelResult, userResult, inputResult, outputResult, langResult, alertResult] = await Promise.all([
        pool.query(getKpiQuery(accessFilter), accessFilter.params),
        pool.query(getChannelTopPerformerQuery(accessFilter), accessFilter.params),
        pool.query(getUserTopPerformerQuery(accessFilter), accessFilter.params),
        pool.query(getInputTopPerformerQuery(accessFilter), accessFilter.params),
        pool.query(getOutputTopPerformerQuery(accessFilter), accessFilter.params),
        pool.query(getLanguageTopPerformerQuery(accessFilter), accessFilter.params),
        pool.query(getAlertsQuery(accessFilter), accessFilter.params),
      ]);

      const kpis = kpiResult.rows[0];

      const topPerformers = [
        { dimension: 'Channel',     ...(channelResult.rows[0] || {}) },
        { dimension: 'User',        ...(userResult.rows[0]    || {}) },
        { dimension: 'Input Type',  ...(inputResult.rows[0]   || {}) },
        { dimension: 'Output Type', ...(outputResult.rows[0]  || {}) },
        { dimension: 'Language',    ...(langResult.rows[0]    || {}) },
      ].filter((item) => item.label);

      const alerts = alertResult.rows.map((row) => ({
        title:    `${row.channel_name}: ${Number(row.conversion).toFixed(2)}% conversion`,
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
