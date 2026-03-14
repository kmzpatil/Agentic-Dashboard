const express = require('express');
const { getAgentHealth } = require('../agent/client');

const REQUIRED_TABLES = [
  'channels',
  'clients',
  'created_assets',
  'post_distribution',
  'published_posts',
  'raw_video_channel',
  'raw_videos',
  'users',
];

function createHealthRouter(pool, agentConfig) {
  const router = express.Router();

  router.get('/', async (_req, res) => {
    const response = {
      ok: false,
      services: {},
      schema: {},
    };

    try {
      const databaseInfoResult = await pool.query(
        `
          SELECT current_database() AS database_name, current_user AS current_user
        `,
      );
      const tablesResult = await pool.query(
        `
          SELECT tablename
          FROM pg_tables
          WHERE schemaname = 'public'
          ORDER BY tablename
        `,
      );

      const availableTables = tablesResult.rows.map((row) => row.tablename);
      const missingTables = REQUIRED_TABLES.filter((table) => !availableTables.includes(table));

      response.services.database = {
        ok: missingTables.length === 0,
        database: databaseInfoResult.rows[0]?.database_name || null,
        user: databaseInfoResult.rows[0]?.current_user || null,
        tables: availableTables.length,
        missingTables,
      };
      response.schema = {
        requiredTables: REQUIRED_TABLES,
        availableTables,
      };
    } catch (error) {
      response.services.database = {
        ok: false,
        error: error.message,
      };
    }

    response.services.agent = await getAgentHealth(agentConfig);
    response.ok = Boolean(response.services.database?.ok) && Boolean(response.services.agent?.ok);

    res.json(response);
  });

  return router;
}

module.exports = {
  createHealthRouter,
};
