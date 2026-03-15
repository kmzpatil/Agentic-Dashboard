    CREATE TABLE IF NOT EXISTS app_users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    client_name TEXT,
    user_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users(role);
    CREATE INDEX IF NOT EXISTS idx_app_users_client_name ON app_users(client_name);
    CREATE INDEX IF NOT EXISTS idx_app_users_user_id ON app_users(user_id);
