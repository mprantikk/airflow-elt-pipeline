"""Load: copy the raw drop into raw.claims, idempotently per load date."""

from __future__ import annotations

import csv
from pathlib import Path

from .db import connect

COLUMNS = ["claim_id", "payer", "cpt_code", "service_date", "billed_amount", "status"]


def load_raw(path: str | Path, ds: str) -> int:
    with open(path, newline="") as f:
        rows = [tuple(r[c] for c in COLUMNS) + (ds,) for r in csv.DictReader(f)]
    with connect() as conn, conn.cursor() as cur:
        # delete-then-insert makes reruns and backfills safe
        cur.execute("DELETE FROM raw.claims WHERE load_date = %s", (ds,))
        cur.executemany(
            f"INSERT INTO raw.claims ({', '.join(COLUMNS)}, load_date) VALUES ({', '.join(['%s'] * 7)})",
            rows,
        )
    return len(rows)
