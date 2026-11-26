"""Data quality gate. Any failed check raises, which fails the Airflow task
and stops bad data reaching the marts' consumers."""

from __future__ import annotations

from .db import connect

CHECKS = {
    "staging rows loaded for the day": (
        "SELECT CASE WHEN COUNT(*) > 0 THEN 0 ELSE 1 END FROM staging.claims WHERE load_date = %(ds)s"
    ),
    "no duplicate claim_id in staging": (
        "SELECT COUNT(*) FROM (SELECT claim_id FROM staging.claims GROUP BY claim_id HAVING COUNT(*) > 1) d"
    ),
    "statuses standardised": (
        "SELECT COUNT(*) FROM staging.claims WHERE load_date = %(ds)s AND status NOT IN ('submitted','paid','denied')"
    ),
    "amounts positive": (
        "SELECT COUNT(*) FROM staging.claims WHERE load_date = %(ds)s AND billed_amount <= 0"
    ),
    "no service date after load date": (
        "SELECT COUNT(*) FROM staging.claims WHERE load_date = %(ds)s AND service_date > load_date"
    ),
    "staging reconciles to raw (distinct, valid rows)": """
        SELECT ABS(
            (SELECT COUNT(DISTINCT claim_id) FROM raw.claims WHERE load_date = %(ds)s AND NULLIF(payer, '') IS NOT NULL)
          - (SELECT COUNT(*) FROM staging.claims WHERE load_date = %(ds)s))
    """,
    "daily KPI row present": (
        "SELECT CASE WHEN COUNT(*) = 1 THEN 0 ELSE 1 END FROM marts.daily_claims_kpis WHERE load_date = %(ds)s"
    ),
}


class DataQualityError(Exception):
    pass


def run_checks(ds: str) -> dict[str, int]:
    results = {}
    with connect() as conn, conn.cursor() as cur:
        for name, sql in CHECKS.items():
            cur.execute(sql, {"ds": ds})
            results[name] = int(cur.fetchone()[0])
    failed = {k: v for k, v in results.items() if v}
    if failed:
        raise DataQualityError(f"{len(failed)} check(s) failed for {ds}: {failed}")
    return results
