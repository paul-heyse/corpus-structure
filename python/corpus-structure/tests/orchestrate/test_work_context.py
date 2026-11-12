"""Interleaved native plans keep anonymous logs and work callbacks in their own scope."""

import logging
from concurrent.futures import Future

import pytest
from structlog.contextvars import get_contextvars

from corpus_structure.cli.observation_logging import bound, capture
from corpus_structure.cli.observations import Observation, ObservationWriter
from corpus_structure.core.work import PreparedWork, ReadyGroup, drive_prepared_work


@pytest.mark.parametrize("failed", [False, True])
def test_interleaved_plan_context_covers_submission_collection_retirement_and_cleanup(
    tmp_path, failed
):
    writer = ObservationWriter(tmp_path / "contexts.jsonl")
    log = logging.getLogger("corpus_structure.context_test")
    initial = get_contextvars()
    handles = []
    closed = []
    failure = RuntimeError("controlled plan failure")

    class Handle:
        def __init__(self, run):
            self.run = run
            self.future = Future()
            self.retire_calls = 0

        def check_active(self):
            log.warning("%s:active", self.run)

        def flush(self):
            log.warning("%s:flush", self.run)
            if not self.future.done():
                self.future.set_result(self.run)

        def collect(self):
            log.warning("%s:collect", self.run)
            return self.future.result()

        def retire(self):
            log.warning("%s:retire", self.run)
            self.retire_calls += 1
            return self.retire_calls >= 2

        def cancel(self):
            log.warning("%s:cancel", self.run)
            self.future.cancel()

    def leaf(run):
        handle = Handle(run)
        handles.append(handle)
        try:

            def submit():
                log.warning("%s:submit", run)
                return handle

            (reply,) = yield (PreparedWork(submit, lambda: log.warning("%s:abandon", run)),)
            log.warning("%s:reduced", run)
            if failed and run == 101:
                raise failure
            return reply
        finally:
            log.warning("%s:leaf_close", run)

    def source(run):
        with bound(run_id=run, project=f"p{run}", release_id=f"r{run}"):
            try:
                log.warning("%s:created", run)
                return (yield ReadyGroup((leaf(run),)))
            finally:
                log.warning("%s:source_close", run)
                closed.append(run)

    def operation():
        result = yield ReadyGroup((source(101), source(202)))
        log.warning("999:parent_reduced")
        return result

    with capture(writer, invocation_id="context-operation"), bound(run_id=999):
        if failed:
            with pytest.raises(RuntimeError) as raised:
                drive_prepared_work(operation(), lambda: None)
            assert raised.value is failure
        else:
            assert drive_prepared_work(operation(), lambda: None) == ((101,), (202,))
        assert get_contextvars()["run_id"] == 999
    assert get_contextvars() == initial
    assert sorted(closed) == [101, 202]
    writer.close()
    rows = [Observation.model_validate_json(line) for line in writer.path.read_bytes().splitlines()]
    assert rows
    for row in rows:
        expected = int(row.message.partition(":")[0])
        assert row.bindings.run_id == expected, (row.message, row.bindings)
        if expected != 999:
            assert row.bindings.project == f"p{expected}"
            assert row.bindings.release_id == f"r{expected}"
    for run in (101, 202):
        phases = {row.message.partition(":")[2] for row in rows if row.bindings.run_id == run}
        assert {"submit", "flush", "collect", "retire", "leaf_close", "source_close"} <= phases
    assert all(handle.retire_calls >= 2 for handle in handles)
