const express = require('express');
const {
  METRIC_SQL,
  getTrendInsights,
  buildAccessFilter,
  getMetricQuery,
} = require('../queries/analyticsShared');

function createUsageTrendsRouter(pool) {
  const router = express.Router();

  router.get('/', async (req, res) => {
    const granularity = ['day', 'week', 'month', 'quarter'].includes(req.query.granularity)
      ? req.query.granularity
      : 'month';

    const metric = Object.prototype.hasOwnProperty.call(METRIC_SQL, req.query.metric)
      ? req.query.metric
      : 'uploaded_count';

    try {
      const accessFilter = buildAccessFilter(req.auth, 2, 'rv');
      const sql = getMetricQuery(metric, accessFilter);
      const { rows } = await pool.query(sql, [granularity, ...accessFilter.params]);
      const points = rows.map((r) => ({
        period: r.period,
        value:  Number(r.value || 0),
      }));

      const latest   = points[points.length - 1] || null;
      const previous = points[points.length - 2] || null;
      const deltaPct = latest && previous && previous.value !== 0
        ? ((latest.value - previous.value) / previous.value) * 100
        : null;

      res.json({
        metric,
        granularity,
        series: points,
        summary: {
          latestValue:         latest ? Number(latest.value.toFixed(2)) : 0,
          latestPeriod:        latest?.period || null,
          deltaVsPreviousPct:  deltaPct === null ? null : Number(deltaPct.toFixed(2)),
        },
        anomalies: getTrendInsights(points),
      });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  return router;
}

module.exports = {
  createUsageTrendsRouter,
};
