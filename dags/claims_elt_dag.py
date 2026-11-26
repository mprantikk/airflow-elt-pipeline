"""
Daily claims ELT
================

extract  ->  load_raw  ->  transform  ->  quality_checks  ->  publish_summary

* **extract** pulls the day's claims drop (synthetic here; SFTP/API in production)
* **load_raw** lands it untouched in `raw.claims`, idempotently per load date
* **transform** cleans and types it into `staging.claims` and refreshes
  `marts.daily_claims_kpis`
* **quality_checks** fails the run if any data-quality rule breaks
* **publish_summary** logs the day's KPIs (swap for Slack/email in production)

Every task is safe to re-run, so backfills are just `airflow dags backfill`.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `elt` importable

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "data-ops",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=20),
}


@dag(
    dag_id="claims_daily_elt",
    description="Extract, load, transform and QA the daily claims drop",
    schedule="0 6 * * *",
    start_date=datetime(2025, 12, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["elt", "claims", "data-quality"],
    doc_md=__doc__,
)
def claims_daily_elt():
    @task
    def extract(ds: str | None = None) -> str:
        from elt.db import ensure_schema
        from elt.source import fetch_daily_drop

        ensure_schema()
        path = fetch_daily_drop(ds)
        log.info("Fetched drop %s", path)
        return str(path)

    @task
    def load_raw(path: str, ds: str | None = None) -> int:
        from elt.load import load_raw as _load

        n = _load(path, ds)
        log.info("Loaded %s raw rows for %s", n, ds)
        return n

    @task
    def transform(raw_rows: int, ds: str | None = None) -> None:
        from elt.transform import transform as _transform

        _transform(ds)

    @task
    def quality_checks(ds: str | None = None) -> dict:
        from elt.checks import run_checks

        return run_checks(ds)

    @task
    def publish_summary(results: dict, ds: str | None = None) -> None:
        from elt.db import connect

        with connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT claims, billed_amount, denial_rate_pct, rejected_rows "
                        "FROM marts.daily_claims_kpis WHERE load_date = %s", (ds,))
            claims, billed, denial, rejected = cur.fetchone()
        log.info("%s: %s claims, $%s billed, denial rate %s%%, %s rows rejected, %s checks passed",
                 ds, claims, billed, denial, rejected, len(results))

    path = extract()
    rows = load_raw(path)
    done = transform(rows)
    results = quality_checks()
    done >> results
    publish_summary(results)


claims_daily_elt()
