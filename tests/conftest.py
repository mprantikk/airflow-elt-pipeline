import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def warehouse():
    """A clean warehouse schema, or skip if Postgres isn't reachable."""
    import psycopg2

    from elt import db

    try:
        psycopg2.connect(db.dsn()).close()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not reachable: {exc}")
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS raw CASCADE; DROP SCHEMA IF EXISTS staging CASCADE; "
                    "DROP SCHEMA IF EXISTS marts CASCADE;")
    db.ensure_schema()
    return db
