const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '.env') });

const { getConfig } = require('./backend/config/env');
const { createPool } = require('./backend/db/pool');
const { createApp } = require('./backend/app');

async function startServer() {
  const config = getConfig();
  const pool = createPool(config.db);

  pool.on('error', (error) => {
    console.error('Unexpected PostgreSQL pool error:', error);
  });

  await pool.query('SELECT 1');

  const app = createApp({
    pool,
    agent: config.agent,
  });

  const server = app.listen(config.port, () => {
    console.log(`Frammer API listening on http://localhost:${config.port}`);
  });

  const shutdown = async () => {
    server.close(async () => {
      await pool.end();
      process.exit(0);
    });
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

startServer().catch((error) => {
  console.error('Failed to start Frammer API:', error);
  process.exit(1);
});
