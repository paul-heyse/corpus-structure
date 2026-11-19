"""The local stop command requests cooperation from the exact managed owner."""

import json
import queue
import select
import socket
import subprocess
import sys
from threading import Event, Thread

import pytest
from typer.testing import CliRunner

from corpus_structure.cli.managed import ResultStore, app
from corpus_structure.cli.managed_stop import stop_result, stoppable_invocation
from corpus_structure.core.execution_control import ExecutionStopped, check_execution_active
from corpus_structure.core.work import PhysicalRetirementUncertain

pytestmark = pytest.mark.skipif(
    not hasattr(socket, "SO_PEERCRED"), reason="the managed control route uses Linux peer credentials"
)


@pytest.mark.parametrize("uncertain", [False, True])
def test_running_stop_uses_the_managed_owner_and_reports_custody(tmp_path, monkeypatch, uncertain):
    store = ResultStore(tmp_path)
    ready = queue.Queue()
    release = Event()
    failures = []

    def owner():
        try:
            with (
                store.operation("data.execute", account=True) as invocation,
                stoppable_invocation(invocation),
            ):
                ready.put(invocation.id)
                assert release.wait(10)
                try:
                    check_execution_active()
                except ExecutionStopped as error:
                    if uncertain:
                        raise PhysicalRetirementUncertain("fixture remains owned") from error
                    raise
        except (ExecutionStopped, PhysicalRetirementUncertain):
            return
        except BaseException as error:
            failures.append(error)

    thread = Thread(target=owner)
    thread.start()
    try:
        result = ready.get(timeout=10)
        monkeypatch.setattr("corpus_structure.cli.managed.result_store", lambda _ctx: store)
        invocation = CliRunner().invoke(app, ["stop", result, "--reason", "controlled test", "--json"])
        assert invocation.exit_code == 0, invocation.output
        assert json.loads(invocation.output)["state"] == "stop_requested"
        assert stop_result(store, result, "repeat").state == "stop_requested"
    finally:
        release.set()
        thread.join(10)
    assert not failures and not thread.is_alive()
    assert stop_result(store, result, "terminal").state == (
        "unresolved_custody" if uncertain else "confirmed_retirement"
    )


def test_missing_or_stale_control_binding_cannot_request_a_stop(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("data.execute", account=True) as invocation:
        assert stop_result(store, invocation.id, "unsupported owner").state == "unavailable"
        with stoppable_invocation(invocation):
            control = invocation.manifest.details["execution_control"]
            control["started"] += 1
            invocation.stage(invocation.manifest.stage)
            assert stop_result(store, invocation.id, "stale owner").state == "unavailable"
            check_execution_active()
    assert stop_result(store, invocation.id, "completed").state == "already_terminal"


def test_stop_reaches_a_separate_owner_process(tmp_path):
    script = """
import sys
import time
from pathlib import Path
from corpus_structure.cli.managed import ResultStore
from corpus_structure.cli.managed_stop import stoppable_invocation
from corpus_structure.core.execution_control import ExecutionStopped, check_execution_active

try:
    with (
        ResultStore(Path(sys.argv[1])).operation("data.execute", account=True) as invocation,
        stoppable_invocation(invocation),
    ):
        print(invocation.id, flush=True)
        while True:
            check_execution_active()
            time.sleep(0.01)
except ExecutionStopped:
    pass
"""
    with subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as owner:
        try:
            assert owner.stdout is not None
            readable, _, _ = select.select([owner.stdout], [], [], 20)
            assert readable, "managed owner did not become available"
            result = owner.stdout.readline().strip()
            store = ResultStore(tmp_path)
            assert stop_result(store, result, "separate caller").state == "stop_requested"
            assert owner.wait(10) == 0
            assert stop_result(store, result, "confirmed reader").state == "confirmed_retirement"
        finally:
            if owner.poll() is None:
                owner.kill()
