// Load root .env first (has AUTH_* vars), then local frontend/.env for overrides
require('dotenv').config({ path: require('path').resolve(__dirname, '../../../.env') });
require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });

const fs = require('fs/promises');
const path = require('path');
const bcrypt = require('bcryptjs');

const { getConfig } = require('../config/env');
const { createPool } = require('./pool');

async function ensureAuthSchema(pool) {
  const exists = await pool.query(`SELECT to_regclass('public.app_users') AS table_name`);
  if (exists.rows[0]?.table_name) {
    return;
  }
  const schemaPath = path.join(__dirname, 'auth_schema.sql');
  const sql = await fs.readFile(schemaPath, 'utf8');
  await pool.query(sql);
}

async function upsertUser(pool, user) {
  await pool.query(
    `
      INSERT INTO app_users (username, password_hash, role, client_name, user_id, is_active)
      VALUES ($1, $2, $3, $4, $5, TRUE)
      ON CONFLICT (username)
      DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        role          = EXCLUDED.role,
        client_name   = EXCLUDED.client_name,
        user_id       = EXCLUDED.user_id,
        is_active     = TRUE,
        updated_at    = NOW()
    `,
    [user.username, user.passwordHash, user.role, user.clientName, user.userId],
  );
}

// Collect all numbered entries for a prefix pattern, e.g. AUTH_USER{n}_USERNAME
function collectNumberedEntries(prefix) {
  const entries = [];
  for (let i = 1; i <= 20; i++) {
    const username = process.env[`${prefix}${i}_USERNAME`];
    if (!username) break;
    entries.push({
      username,
      password:   process.env[`${prefix}${i}_PASSWORD`] || '',
      clientName: process.env[`${prefix}${i}_CLIENT`]   || null,
      userId:     process.env[`${prefix}${i}_ID`]       ? Number(process.env[`${prefix}${i}_ID`]) : null,
    });
  }
  return entries;
}

async function run() {
  const { db } = getConfig();
  const pool = createPool(db);

  try {
    await ensureAuthSchema(pool);

    const seeded = [];

    // ── website_admin (single) ────────────────────────────────────────────────
    const waUsername = process.env.AUTH_WEBSITE_ADMIN_USERNAME || 'website_admin';
    const waPassword = process.env.AUTH_WEBSITE_ADMIN_PASSWORD || 'Admin@12345';
    await upsertUser(pool, {
      username:     waUsername,
      passwordHash: await bcrypt.hash(waPassword, 12),
      role:         'website_admin',
      clientName:   null,
      userId:       null,
    });
    seeded.push(`  [website_admin]  ${waUsername}  /  ${waPassword}`);

    // ── client_admins — numbered (AUTH_CLIENT_ADMIN1_*, AUTH_CLIENT_ADMIN2_*, …) ──
    const clientAdmins = collectNumberedEntries('AUTH_CLIENT_ADMIN');
    // fallback: single AUTH_CLIENT_ADMIN_* for backwards compat
    if (clientAdmins.length === 0 && process.env.AUTH_CLIENT_ADMIN_USERNAME) {
      clientAdmins.push({
        username:   process.env.AUTH_CLIENT_ADMIN_USERNAME,
        password:   process.env.AUTH_CLIENT_ADMIN_PASSWORD || 'Client@12345',
        clientName: process.env.AUTH_CLIENT_ADMIN_CLIENT   || null,
        userId:     null,
      });
    }
    for (const ca of clientAdmins) {
      await upsertUser(pool, {
        username:     ca.username,
        passwordHash: await bcrypt.hash(ca.password, 12),
        role:         'client_admin',
        clientName:   ca.clientName,
        userId:       null,
      });
      seeded.push(`  [client_admin]   ${ca.username}  /  ${ca.password}  (client: ${ca.clientName})`);
    }

    // ── users — numbered (AUTH_USER1_*, AUTH_USER2_*, …) ─────────────────────
    const users = collectNumberedEntries('AUTH_USER');
    // fallback: single AUTH_USER_* for backwards compat
    if (users.length === 0 && process.env.AUTH_USER_USERNAME) {
      users.push({
        username:   process.env.AUTH_USER_USERNAME,
        password:   process.env.AUTH_USER_PASSWORD || 'User@12345',
        clientName: process.env.AUTH_USER_CLIENT   || null,
        userId:     process.env.AUTH_USER_ID        ? Number(process.env.AUTH_USER_ID) : null,
      });
    }
    for (const u of users) {
      await upsertUser(pool, {
        username:     u.username,
        passwordHash: await bcrypt.hash(u.password, 12),
        role:         'user',
        clientName:   u.clientName,
        userId:       u.userId,
      });
      seeded.push(`  [user]           ${u.username}  /  ${u.password}  (client: ${u.clientName}, user_id: ${u.userId})`);
    }

    console.log('\nAuth users seeded successfully:\n');
    seeded.forEach((line) => console.log(line));
    console.log('');
  } finally {
    await pool.end();
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
