"""Catch broken DAGs before they reach the scheduler."""

from pathlib import Path

import pytest

airflow = pytest.importorskip("airflow")
from airflow.models import DagBag  # noqa: E402

DAGS = Path(__file__).resolve().parent.parent / "dags"


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder=str(DAGS), include_examples=False)


def test_no_import_errors(dagbag):
    assert dagbag.import_errors == {}


def test_dag_shape(dagbag):
    dag = dagbag.get_dag("claims_daily_elt")
    assert dag is not None
    order = [t.task_id for t in dag.topological_sort()]
    assert order == ["extract", "load_raw", "transform", "quality_checks", "publish_summary"]
    assert not dag.catchup and dag.max_active_runs == 1


def test_every_task_retries_and_times_out(dagbag):
    for t in dagbag.get_dag("claims_daily_elt").tasks:
        assert t.retries >= 1, t.task_id
        assert t.execution_timeout is not None, t.task_id
