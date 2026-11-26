"""Extract: fetch the day's claims drop.

In production this would pull a file from an SFTP server or an EHR export
API. Here it generates a deterministic synthetic file per date, including
the defects real drops contain (duplicate rows, mixed-case statuses,
currency-formatted amounts, the odd row with a missing payer).
"""

from __future__ import annotations

import csv
import hashlib
import random
from datetime import date, timedelta
from pathlib import Path

LANDING = Path(__file__).resolve().parent.parent / "data" / "landing"
PAYERS = ["BlueStar Health", "United Care Plus", "Medicare", "Medicaid", "Self-Pay"]
STATUSES = ["Submitted", "SUBMITTED", "paid", "Paid", "denied", "DENIED"]
CPT = ["99213", "99214", "93000", "73721", "71046", "20610"]


def fetch_daily_drop(ds: str, landing: Path = LANDING) -> Path:
    """Return the path of the drop for logical date `ds` (YYYY-MM-DD)."""
    landing.mkdir(parents=True, exist_ok=True)
    path = landing / f"claims_{ds}.csv"
    if path.exists():
        return path
    seed = int(hashlib.sha256(ds.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    day = date.fromisoformat(ds)
    rows = []
    for i in range(rng.randint(180, 260)):
        dos = day - timedelta(days=rng.randint(0, 10))
        billed = round(rng.uniform(80, 900), 2)
        rows.append({
            "claim_id": f"{ds.replace('-', '')}-{i:04d}",
            "payer": rng.choice(PAYERS) if rng.random() > 0.01 else "",
            "cpt_code": rng.choice(CPT),
            "service_date": dos.isoformat(),
            "billed_amount": f"${billed:,.2f}" if rng.random() < 0.2 else f"{billed}",
            "status": rng.choices(STATUSES, weights=[20, 15, 28, 25, 7, 5])[0],
        })
    rows += rng.sample(rows, k=3)  # re-sent rows
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path
