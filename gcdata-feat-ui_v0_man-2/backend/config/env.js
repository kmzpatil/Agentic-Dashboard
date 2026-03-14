function getConfig() {
  const port = Number(process.env.PORT || process.env.API_PORT || 4000);

  const db = {
    host: process.env.PGHOST,
    port: Number(process.env.PGPORT),
    user: process.env.PGUSER,
    database: process.env.PGDATABASE,
    password: process.env.PGPASSWORD || undefined,
  };

  if (!db.host || !db.port || !db.user || !db.database) {
    throw new Error('Missing required database environment variables: PGHOST, PGPORT, PGUSER, PGDATABASE');
  }

  return { port, db };
}

module.exports = {
  getConfig,
};
