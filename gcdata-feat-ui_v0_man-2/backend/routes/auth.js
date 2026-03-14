const express = require('express');
const bcrypt = require('bcryptjs');
const { signAuthToken } = require('../auth/jwt');
const { requireAuth } = require('../middleware/auth');

function createAuthRouter(pool) {
  const router = express.Router();

  router.post('/login', async (req, res) => {
    const username = String(req.body?.username || '').trim();
    const password = String(req.body?.password || '');

    if (!username || !password) {
      return res.status(400).json({ error: 'username and password are required' });
    }

    try {
      const userResult = await pool.query(
        `
          SELECT id, username, password_hash, role, client_name, user_id, is_active
          FROM app_users
          WHERE username = $1
          LIMIT 1
        `,
        [username],
      );

      if (userResult.rowCount === 0 || !userResult.rows[0].is_active) {
        return res.status(401).json({ error: 'Invalid username or password' });
      }

      const authUser = userResult.rows[0];
      const isValid = await bcrypt.compare(password, authUser.password_hash);
      if (!isValid) {
        return res.status(401).json({ error: 'Invalid username or password' });
      }

      const token = signAuthToken({
        sub: String(authUser.id),
        username: authUser.username,
        role: authUser.role,
        clientName: authUser.client_name || null,
        userId: authUser.user_id || null,
      });

      return res.json({
        token,
        user: {
          id: authUser.id,
          username: authUser.username,
          role: authUser.role,
          clientName: authUser.client_name || null,
          userId: authUser.user_id || null,
        },
      });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  router.get('/me', requireAuth, async (req, res) => {
    try {
      const meResult = await pool.query(
        `
          SELECT id, username, role, client_name, user_id, is_active
          FROM app_users
          WHERE id = $1
          LIMIT 1
        `,
        [req.auth.authUserId],
      );

      if (meResult.rowCount === 0 || !meResult.rows[0].is_active) {
        return res.status(401).json({ error: 'Invalid session' });
      }

      return res.json({
        user: {
          id: meResult.rows[0].id,
          username: meResult.rows[0].username,
          role: meResult.rows[0].role,
          clientName: meResult.rows[0].client_name || null,
          userId: meResult.rows[0].user_id || null,
        },
      });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  return router;
}

module.exports = {
  createAuthRouter,
};
