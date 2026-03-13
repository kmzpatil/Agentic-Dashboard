const express = require('express');
const cors = require('cors');
const { createApiRouter } = require('./routes/api');

function createApp(pool) {
  const app = express();

  app.use(cors());
  app.use(express.json());
  app.use('/api', createApiRouter(pool));

  return app;
}

module.exports = {
  createApp,
};
