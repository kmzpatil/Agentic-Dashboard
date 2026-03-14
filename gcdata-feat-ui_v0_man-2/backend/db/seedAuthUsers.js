require('dotenv').config();

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

async function getClientName(pool) {
  if (process.env.AUTH_CLIENT_ADMIN_CLIENT_NAME) {
    const requested = process.env.AUTH_CLIENT_ADMIN_CLIENT_NAME;
    const exists = await pool.query('SELECT 1 FROM clients WHERE "Client_Name" = $1 LIMIT 1', [requested]);
    if (exists.rowCount === 0) {
      throw new Error(`AUTH_CLIENT_ADMIN_CLIENT_NAME not found in clients table: ${requested}`);
    }
    return requested;
  }

  const result = await pool.query('SELECT "Client_Name" FROM clients ORDER BY "Client_Name" LIMIT 1');
  if (result.rowCount === 0) {
    throw new Error('No clients found. Seed the analytics dataset first.');
  }
  return result.rows[0].Client_Name || result.rows[0].client_name;
}

async function getScopedUser(pool, fallbackClientName) {
  if (process.env.AUTH_USER_ID) {
    const requested = Number(process.env.AUTH_USER_ID);
    if (!Number.isInteger(requested)) {
      throw new Error('AUTH_USER_ID must be an integer');
    }
    const result = await pool.query(
      'SELECT "User_ID", "User_Name", "Client_Name" FROM users WHERE "User_ID" = $1 LIMIT 1',
      [requested],
    );
    if (result.rowCount === 0) {
      throw new Error(`AUTH_USER_ID not found in users table: ${requested}`);
    }
    return result.rows[0];
  }

  const result = await pool.query(
    'SELECT "User_ID", "User_Name", "Client_Name" FROM users ORDER BY "User_ID" LIMIT 1',
  );
  if (result.rowCount === 0) {
    throw new Error('No users found. Seed the analytics dataset first.');
  }

  return {
    ...result.rows[0],
    Client_Name: result.rows[0].Client_Name || result.rows[0].client_name || fallbackClientName,
  };
}

async function upsertUser(pool, user) {
  await pool.query(
    `
      INSERT INTO app_users (username, password_hash, role, client_name, user_id, is_active)
      VALUES ($1, $2, $3, $4, $5, TRUE)
      ON CONFLICT (username)
      DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        role = EXCLUDED.role,
        client_name = EXCLUDED.client_name,
        user_id = EXCLUDED.user_id,
        is_active = TRUE,
        updated_at = NOW()
    `,
    [user.username, user.passwordHash, user.role, user.clientName, user.userId],
  );
}

async function run() {
  const { db } = getConfig();
  const pool = createPool(db);

  try {
    await ensureAuthSchema(pool);

    const clientName = await getClientName(pool);
    const scopedUser = await getScopedUser(pool, clientName);

    const websiteAdminPassword = process.env.AUTH_WEBSITE_ADMIN_PASSWORD || 'Admin@12345';
    const clientAdminPassword = process.env.AUTH_CLIENT_ADMIN_PASSWORD || 'Client@12345';
    const userPassword = process.env.AUTH_USER_PASSWORD || 'User@12345';

    const websiteAdminHash = await bcrypt.hash(websiteAdminPassword, 12);
    const clientAdminHash = await bcrypt.hash(clientAdminPassword, 12);
    const userHash = await bcrypt.hash(userPassword, 12);

    await upsertUser(pool, {
      username: process.env.AUTH_WEBSITE_ADMIN_USERNAME || 'website_admin',
      passwordHash: websiteAdminHash,
      role: 'website_admin',
      clientName: null,
      userId: null,
    });

    await upsertUser(pool, {
      username: process.env.AUTH_CLIENT_ADMIN_USERNAME || 'client_admin_client1',
      passwordHash: clientAdminHash,
      role: 'client_admin',
      clientName,
      userId: null,
    });

    await upsertUser(pool, {
      username: process.env.AUTH_USER_USERNAME || 'user_local_1',
      passwordHash: userHash,
      role: 'user',
      clientName: scopedUser.Client_Name || scopedUser.client_name || clientName,
      userId: Number(scopedUser.User_ID || scopedUser.user_id),
    });

    console.log('Auth users seeded successfully.');
    console.log(`website_admin username: ${process.env.AUTH_WEBSITE_ADMIN_USERNAME || 'website_admin'}`);
    console.log(`client_admin username: ${process.env.AUTH_CLIENT_ADMIN_USERNAME || 'client_admin_client1'} (client: ${clientName})`);
    console.log(`user username: ${process.env.AUTH_USER_USERNAME || 'user_local_1'} (User_ID: ${scopedUser.User_ID || scopedUser.user_id})`);
  } finally {
    await pool.end();
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
