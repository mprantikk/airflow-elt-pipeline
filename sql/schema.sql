CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Raw: exactly what arrived, as text, plus the load date
CREATE TABLE IF NOT EXISTS raw.claims (
    claim_id       TEXT,
    payer          TEXT,
    cpt_code       TEXT,
    service_date   TEXT,
    billed_amount  TEXT,
    status         TEXT,
    load_date      DATE NOT NULL,
    loaded_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_raw_claims_load_date ON raw.claims (load_date);

-- Staging: typed, cleaned, one row per claim
CREATE TABLE IF NOT EXISTS staging.claims (
    claim_id       TEXT PRIMARY KEY,
    payer          TEXT NOT NULL,
    cpt_code       CHAR(5) NOT NULL,
    service_date   DATE NOT NULL,
    billed_amount  NUMERIC(12, 2) NOT NULL,
    status         TEXT NOT NULL,
    load_date      DATE NOT NULL
);

-- Mart: one row per day for the ops dashboard
CREATE TABLE IF NOT EXISTS marts.daily_claims_kpis (
    load_date          DATE PRIMARY KEY,
    claims             INT NOT NULL,
    billed_amount      NUMERIC(14, 2) NOT NULL,
    denial_rate_pct    NUMERIC(5, 1),
    avg_charge_lag     NUMERIC(5, 1),
    rejected_rows      INT NOT NULL,
    refreshed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
