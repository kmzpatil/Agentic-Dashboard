require('dotenv').config();

const { getConfig } = require('./backend/config/env');
const { createPool } = require('./backend/db/pool');
const { createApp } = require('./backend/app');

const { port, db } = getConfig();
const pool = createPool(db);
const app = createApp(pool);

app.listen(port, () => {
  console.log(`API server listening on http://localhost:${port}`);
});
