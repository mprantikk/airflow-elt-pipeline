-- Rebuild staging and the KPI mart for one load date (%(ds)s). Idempotent.

DELETE FROM staging.claims WHERE load_date = %(ds)s;

INSERT INTO staging.claims (claim_id, payer, cpt_code, service_date, billed_amount, status, load_date)
SELECT DISTINCT ON (claim_id)
    claim_id,
    TRIM(payer),
    cpt_code,
    service_date::date,
    REPLACE(REPLACE(billed_amount, '$', ''), ',', '')::numeric(12, 2),
    LOWER(TRIM(status)),
    load_date
FROM raw.claims
WHERE load_date = %(ds)s
  AND NULLIF(TRIM(payer), '') IS NOT NULL      -- rows without a payer are rejected
ORDER BY claim_id, loaded_at DESC
ON CONFLICT (claim_id) DO UPDATE
    SET payer = EXCLUDED.payer, cpt_code = EXCLUDED.cpt_code, service_date = EXCLUDED.service_date,
        billed_amount = EXCLUDED.billed_amount, status = EXCLUDED.status, load_date = EXCLUDED.load_date;

INSERT INTO marts.daily_claims_kpis (load_date, claims, billed_amount, denial_rate_pct, avg_charge_lag, rejected_rows)
SELECT
    %(ds)s::date,
    COUNT(*),
    COALESCE(SUM(billed_amount), 0),
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'denied')
          / NULLIF(COUNT(*) FILTER (WHERE status IN ('paid', 'denied')), 0), 1),
    ROUND(AVG(load_date - service_date), 1),
    (SELECT COUNT(*) FROM raw.claims WHERE load_date = %(ds)s AND NULLIF(TRIM(payer), '') IS NULL)
FROM staging.claims
WHERE load_date = %(ds)s
ON CONFLICT (load_date) DO UPDATE
    SET claims = EXCLUDED.claims, billed_amount = EXCLUDED.billed_amount,
        denial_rate_pct = EXCLUDED.denial_rate_pct, avg_charge_lag = EXCLUDED.avg_charge_lag,
        rejected_rows = EXCLUDED.rejected_rows, refreshed_at = now();
