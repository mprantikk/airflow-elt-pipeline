from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/warehouse"


def dsn() -> str:
    return os.environ.get("WAREHOUSE_DSN", DEFAULT_DSN)


@contextmanager
def connect():
    conn = psycopg2.connect(dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_sql_file(name: str, params: dict | None = None) -> None:
    sql = (SQL_DIR / name).read_text()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})


def ensure_schema() -> None:
    run_sql_file("schema.sql")
