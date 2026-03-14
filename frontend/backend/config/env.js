function normalizeEnvValue(value) {
  if (value === undefined || value === null) {
    return undefined;
  }

  const normalized = String(value).trim();
  return normalized === '' ? undefined : normalized;
}

function firstEnv(...names) {
  for (const name of names) {
    const value = normalizeEnvValue(process.env[name]);
    if (value !== undefined) {
      return value;
    }
  }

  return undefined;
}

function resolveSslConfig(host) {
  const sslMode = firstEnv('PGSSLMODE', 'POSTGRES_SSLMODE', 'DB_SSLMODE');

  if (!sslMode || sslMode === 'disable' || String(host || '').startsWith('/')) {
    return undefined;
  }

  return {
    rejectUnauthorized: false,
  };
}

function resolveDbConfig() {
  const connectionString = firstEnv('POSTGRES_URL', 'PGDATABASE_URL');
  if (connectionString) {
    return {
      connectionString,
      ssl: resolveSslConfig(),
    };
  }

  const host = firstEnv('PGHOST', 'POSTGRES_HOST');
  const user = firstEnv('PGUSER', 'POSTGRES_USER');
  const database = firstEnv('PGDATABASE', 'POSTGRES_DB');
  const password = firstEnv('PGPASSWORD', 'POSTGRES_PASSWORD');
  const port = Number(firstEnv('PGPORT', 'POSTGRES_PORT') || 5432);

  if (!host || !user || !database) {
    const databaseUrl = firstEnv('DATABASE_URL');
    if (databaseUrl && databaseUrl.startsWith('postgres')) {
      return {
        connectionString: databaseUrl,
        ssl: resolveSslConfig(),
      };
    }

    throw new Error(
      'Missing PostgreSQL configuration. Set PG* vars, POSTGRES_* vars, or a PostgreSQL DATABASE_URL.',
    );
  }

  return {
    host,
    port,
    user,
    database,
    password,
    ssl: resolveSslConfig(host),
  };
}

function getConfig() {
  return {
    port: Number(firstEnv('PORT', 'API_PORT') || 4000),
    db: resolveDbConfig(),
    agent: {
      baseUrl: firstEnv('AGENT_BASE_URL') || 'http://127.0.0.1:8000',
      timeoutMs: Number(firstEnv('AGENT_TIMEOUT_MS') || 30000),
    },
  };
}

module.exports = {
  getConfig,
  firstEnv,
  normalizeEnvValue,
};
