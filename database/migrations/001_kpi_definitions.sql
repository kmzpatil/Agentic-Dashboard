-- Migration: Add kpi_definitions table for Custom KPI feature
-- This table is additive and does NOT modify any existing tables.

CREATE TABLE IF NOT EXISTS kpi_definitions (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    dsl_json    JSONB NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Idempotent: add created_by if it was missing from an earlier schema version
ALTER TABLE kpi_definitions
    ADD COLUMN IF NOT EXISTS created_by TEXT;

CREATE INDEX IF NOT EXISTS idx_kpi_definitions_created_at ON kpi_definitions (created_at DESC);
