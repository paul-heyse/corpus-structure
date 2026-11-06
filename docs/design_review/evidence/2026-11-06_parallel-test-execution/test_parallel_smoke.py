"""New bounded scheduling controls; no pre-existing functional cases are rerun."""

import json
import os
import time
from contextlib import ExitStack
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            id=f"case@{case}",
            marks=[pytest.mark.xdist_group(f"probe_{case}"), *([pytest.mark.db] if case in (0, 2) else [])],
        )
        for case in range(32)
    ],
)
def test_sixteen_workers_and_owned_native_contexts(case: int, worker_id: str) -> None:
    assert worker_id.startswith("gw")
    observations = Path(os.environ["QUALIFICATION_RECEIPT_DIR"]) / "smoke-observations"
    observations.mkdir(exist_ok=True)
    with ExitStack() as resources:
        database = None
        acquired = None
        if case in (0, 2):
            from corpus_structure.settings import Settings
            from native_test_support import PgAdmin, server_url

            settings = Settings()
            server = PgAdmin(server_url(settings), "template0", settings=settings)
            database = f"ci_test_parallel_{os.getpid()}_{case}"
            engine = resources.enter_context(server.database(database, "template0"))
            connection = resources.enter_context(engine.connect())
            acquired = tuple(connection.exec_driver_sql("SELECT current_database(), current_user").one())
            assert acquired[0] == database
        started = time.time()
        arrival = observations / f"arrived-{worker_id}.json"
        if not arrival.exists():
            arrival.write_text(json.dumps({"worker": worker_id, "pid": os.getpid(), "time": started}))
        deadline = time.monotonic() + 90
        while len(list(observations.glob("arrived-*.json"))) != 16:
            assert time.monotonic() < deadline, "all sixteen actual worker processes must rendezvous"
            time.sleep(0.02)
        # Keep both native acquisitions open until every first-wave item has joined.
        time.sleep(0.1)
        (observations / f"case-{case}.json").write_text(
            json.dumps({"worker": worker_id, "pid": os.getpid(), "started": started,
                        "finished": time.time(), "database": database, "acquired": acquired})
        )


@pytest.mark.shared_cluster_fault
def test_serial_lane_selection() -> None:
    assert "PYTEST_XDIST_WORKER" not in os.environ


@pytest.mark.parametrize("case", range(4))
@pytest.mark.xdist_group("receipt_probe")
def test_grouped_receipt_identity(case, pytestconfig, worker_id, record_property):
    record_property("observed_worker", worker_id)
    record_property("observed_loadgroup", pytestconfig.getoption("loadgroup", False))
    record_property("observed_dist", pytestconfig.getoption("dist"))
    assert case in range(4)
    assert pytestconfig.getoption("loadgroup", False)


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=f"compatible@{case}", marks=[pytest.mark.xdist_group(f"compatible_{case}"), *([pytest.mark.db] if case in (0, 2) else [])]) for case in range(32)],
)
def test_compatible_pair_parallel(case, worker_id):
    test_sixteen_workers_and_owned_native_contexts(case, worker_id)


@pytest.mark.parametrize("case", range(8))
@pytest.mark.xdist_group("compatible_shared_preparation")
def test_compatible_pair_single_group(case, worker_id, pytestconfig):
    assert pytestconfig.getoption("loadgroup", False)
    observations = Path(os.environ["QUALIFICATION_RECEIPT_DIR"]) / "group-observations"
    observations.mkdir(exist_ok=True)
    (observations / f"case-{case}.json").write_text(
        json.dumps({"worker": worker_id, "pid": os.getpid()})
    )
