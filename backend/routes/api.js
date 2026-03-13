const express = require('express');
const { createHealthRouter } = require('./health');
const { createOverviewRouter } = require('./overview');
const { createUsageTrendsRouter } = require('./usageTrends');
const { createFunnelRouter } = require('./funnel');
const { createExplorerRouter } = require('./explorer');

function createApiRouter(pool) {
  const router = express.Router();

  router.use('/health', createHealthRouter(pool));
  router.use('/overview', createOverviewRouter(pool));
  router.use('/usage-trends', createUsageTrendsRouter(pool));
  router.use('/funnel', createFunnelRouter(pool));
  router.use('/explorer', createExplorerRouter(pool));

  return router;
}

module.exports = {
  createApiRouter,
};
