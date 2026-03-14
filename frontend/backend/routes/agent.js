const express = require('express');
const { getAgentHealth, requestAgentJson } = require('../agent/client');

function respondWithAgentError(res, error) {
  res.status(error.status || 503).json({
    error: error.message,
    details: error.details || null,
  });
}

function createAgentRouter(agentConfig) {
  const router = express.Router();

  router.get('/agent/health', async (_req, res) => {
    const payload = await getAgentHealth(agentConfig);
    res.json(payload);
  });

  router.post('/chat', async (req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, '/api/chat', {
        method: 'POST',
        body: req.body,
      });
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  router.post('/query', async (req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, '/api/query', {
        method: 'POST',
        body: req.body,
      });
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  router.get('/agent/tables', async (_req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, '/api/tables');
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  router.get('/agent/schema/search', async (req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, '/api/schema/search', {
        query: {
          q: req.query.q,
          limit: req.query.limit,
        },
      });
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  router.get('/conversations', async (req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, '/api/conversations', {
        query: { user_id: req.query.user_id },
      });
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  router.get('/conversations/:id', async (req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, `/api/conversations/${req.params.id}`);
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  router.delete('/conversations/:id', async (req, res) => {
    try {
      const payload = await requestAgentJson(agentConfig, `/api/conversations/${req.params.id}`, {
        method: 'DELETE',
      });
      res.json(payload);
    } catch (error) {
      respondWithAgentError(res, error);
    }
  });

  return router;
}

module.exports = {
  createAgentRouter,
};
