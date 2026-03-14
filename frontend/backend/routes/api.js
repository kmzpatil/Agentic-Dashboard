const express = require('express');
const { createOverviewRouter }    = require('./overview');
const { createUsageTrendsRouter } = require('./usageTrends');
const { createFunnelRouter }      = require('./funnel');
const { createExplorerRouter }    = require('./explorer');
const { createAgentRouter }       = require('./agent');

function createApiRouter({ pool, agent }) {
  const router = express.Router();

  router.use('/overview',     createOverviewRouter(pool));
  router.use('/usage-trends', createUsageTrendsRouter(pool));
  router.use('/funnel',       createFunnelRouter(pool));
  router.use('/explorer',     createExplorerRouter(pool));
  // Agent proxy: POST /chat, POST /query, GET /agent/health, GET /agent/tables
  router.use('/',             createAgentRouter(agent));

  return router;
}

module.exports = {
  createApiRouter,
};
