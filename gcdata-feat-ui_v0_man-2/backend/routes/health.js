const express = require('express');

function createHealthRouter(pool) {
  const router = express.Router();

  router.get('/', async (_req, res) => {
    try {
      await pool.query('SELECT 1');
      res.json({ ok: true });
    } catch (error) {
      res.status(500).json({ ok: false, error: error.message });
    }
  });

  return router;
}

module.exports = {
  createHealthRouter,
};
