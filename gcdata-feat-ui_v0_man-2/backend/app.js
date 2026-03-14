const express = require('express');
const cors = require('cors');
const { createApiRouter } = require('./routes/api');
const { createAuthRouter } = require('./routes/auth');
const { createHealthRouter } = require('./routes/health');
const { requireAuth } = require('./middleware/auth');

function createApp(pool) {
  const app = express();

  app.use(cors());
  app.use(express.json());
  app.use('/api/auth', createAuthRouter(pool));
  app.use('/api/health', createHealthRouter(pool));
  app.use('/api', requireAuth, createApiRouter(pool));

  return app;
}

module.exports = {
  createApp,
};
