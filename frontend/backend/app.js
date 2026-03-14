const express = require('express');
const cors = require('cors');
const { createApiRouter } = require('./routes/api');
const { createAuthRouter } = require('./routes/auth');
const { createHealthRouter } = require('./routes/health');
const { requireAuth } = require('./middleware/auth');

function createApp({ pool, agent }) {
  const app = express();

  app.use(cors());
  app.use(express.json());

  // Public routes — no auth required
  app.use('/api/auth',   createAuthRouter(pool));
  app.use('/api/health', createHealthRouter(pool, agent));

  // All other /api routes require a valid JWT
  app.use('/api', requireAuth, createApiRouter({ pool, agent }));

  return app;
}

module.exports = {
  createApp,
};
