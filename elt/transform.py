"""Transform: raw -> staging -> marts, for one load date."""

from .db import run_sql_file


def transform(ds: str) -> None:
    run_sql_file("transform.sql", {"ds": ds})
