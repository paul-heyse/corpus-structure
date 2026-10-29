"""Liveness across a killed orchestrator (P0-O-1, orchestration §3.4): a process holding a run's
liveness lock is killed with SIGKILL before or after the run's seal; `orphaned` then reports the run
(also `consolidating`), and it is cancelled.

The child is a separate interpreter holding `runs.Liveness` exactly as `ci run` does; the parent
moves the run through its states, so the kill is the only thing that ends the lock.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import Engine, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import MethodFamily, RunKind, RunStatus, Stage, TaskUnitType
from corpus_structure.orchestrate import phase0, runs
from corpus_structure.orchestrate.runner import Graph, Runner, seal

CHILD = """
import sys, time
from corpus_structure.orchestrate.runs import Liveness
with Liveness(sys.argv[1], int(sys.argv[2])):
    print("ready", flush=True)
    time.sleep(120)
"""


def orphaned(engine: Engine) -> list[int]:
    with engine.connect() as conn:
        return runs.orphaned(conn)


@pytest.mark.parametrize("sealed", [False, True], ids=["before-seal", "after-seal"])
def test_a_killed_orchestrator_leaves_its_run_orphaned_and_cancellable(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path, sealed: bool
) -> None:
    stubs = [
        orch.ingest_stub(),
        orch.Stub("consolidate.claims", TaskUnitType.RUN, MethodFamily.CONSOLIDATE),
        orch.Stub("validate.rules", TaskUnitType.RUN, MethodFamily.VALIDATE),
        orch.Stub("evaluate.score", TaskUnitType.RUN, MethodFamily.EVAL),
    ]
    with committing_db.begin() as conn:
        w = orch.setup_project(conn, tmp_path, methods=stubs)
        run = runs.create_run(
            conn,
            project_id=w.project_id,
            kind=RunKind.FULL,
            versions=w.versions,
            registry=w.registry,
            documents=w.documents,
            commit="t",
        ).id
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, url, str(run)], stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout is not None and child.stdout.readline().strip() == "ready"
        with committing_db.begin() as conn:
            runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)
        if sealed:
            runner = Runner(
                committing_db,
                w.registry,
                Graph(()),
                phase0.stub_pass,
                None,
                MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            )
            with committing_db.begin() as conn:
                seal(
                    conn,
                    run,
                    lambda c: runner._run_task(conn, run, Stage.FINALIZE, c),
                    runner.graph,
                )
        assert run not in orphaned(committing_db)  # the lock is held
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
    deadline = time.monotonic() + 10
    while run not in orphaned(committing_db) and time.monotonic() < deadline:
        time.sleep(0.05)  # the server ends the backend once it sees the socket close
    assert run in orphaned(committing_db)
    with committing_db.begin() as conn:
        status = conn.execute(
            text("SELECT status FROM ops.run WHERE id = :r"), {"r": run}
        ).scalar_one()
        assert status == ("consolidating" if sealed else "running")
        runs.cancel_run(conn, run)
    assert orphaned(committing_db) == []
