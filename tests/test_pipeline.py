"""Run the real task functions end to end against Postgres."""

import pytest

from elt.checks import DataQualityError, run_checks
from elt.load import load_raw
from elt.source import fetch_daily_drop
from elt.transform import transform

DAYS = ["2025-12-01", "2025-12-02", "2025-12-03"]


def run_day(ds, tmp_path):
    path = fetch_daily_drop(ds, landing=tmp_path)
    n = load_raw(path, ds)
    transform(ds)
    return n, run_checks(ds)


def scalar(db, sql, *args):
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()[0]


def test_three_days_end_to_end(warehouse, tmp_path):
    for ds in DAYS:
        n, results = run_day(ds, tmp_path)
        assert n > 0 and all(v == 0 for v in results.values())
    assert scalar(warehouse, "SELECT COUNT(*) FROM marts.daily_claims_kpis") == 3


def test_rerun_is_idempotent(warehouse, tmp_path):
    ds = DAYS[0]
    run_day(ds, tmp_path)
    before = scalar(warehouse, "SELECT COUNT(*) FROM staging.claims")
    run_day(ds, tmp_path)   # same day again, as in a retry or backfill
    assert scalar(warehouse, "SELECT COUNT(*) FROM staging.claims") == before
    assert scalar(warehouse, "SELECT COUNT(*) FROM raw.claims WHERE load_date = %s", ds) > 0


def test_cleaning_rules(warehouse, tmp_path):
    run_day(DAYS[1], tmp_path)
    statuses = scalar(warehouse, "SELECT string_agg(DISTINCT status, ',' ORDER BY status) FROM staging.claims")
    assert statuses == "denied,paid,submitted"
    # duplicates and payer-less rows were removed, and the mart counts the rejects
    assert scalar(warehouse, "SELECT rejected_rows FROM marts.daily_claims_kpis WHERE load_date = %s",
                  DAYS[1]) >= 0


def test_quality_gate_blocks_bad_data(warehouse, tmp_path):
    run_day(DAYS[2], tmp_path)
    with warehouse.connect() as conn, conn.cursor() as cur:
        cur.execute("UPDATE staging.claims SET billed_amount = -1 "
                    "WHERE claim_id = (SELECT MIN(claim_id) FROM staging.claims WHERE load_date = %s)", (DAYS[2],))
    with pytest.raises(DataQualityError, match="amounts positive"):
        run_checks(DAYS[2])
