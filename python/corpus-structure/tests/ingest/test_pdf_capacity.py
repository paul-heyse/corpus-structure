"""Dedicated service controls restore GPU ownership on success, failure and cancellation."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from corpus_structure.ingest.pdf_capacity import native_before_nemotron


@pytest.fixture
def capacity_service():
    state = {"sleeping": False, "model": "nemotron-parse", "events": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = (
                {"data": [{"id": state["model"]}]}
                if self.path == "/v1/models"
                else {"is_sleeping": state["sleeping"]}
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def do_POST(self):
            name = urlsplit(self.path).path
            state["events"].append(name)
            state["sleeping"] = name == "/sleep"
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("failure", [None, RuntimeError, KeyboardInterrupt])
def test_native_phase_restores_service_after_success_failure_or_cancellation(
    capacity_service, failure
):
    endpoint, state = capacity_service

    def run():
        with native_before_nemotron(endpoint, timeout_seconds=2):
            assert state["sleeping"]
            if failure is not None:
                raise failure("native stopped")

    if failure is None:
        run()
    else:
        with pytest.raises(failure, match="native stopped"):
            run()
    assert state["events"] == ["/sleep", "/wake_up"]
    assert not state["sleeping"]


def test_foreign_model_is_never_suspended(capacity_service):
    endpoint, state = capacity_service
    state["model"] = "other-service"
    with (
        pytest.raises(ValueError, match="dedicated Nemotron model"),
        native_before_nemotron(endpoint),
    ):
        pytest.fail("foreign service was accepted")
    assert state["events"] == []


def test_remote_endpoint_and_unbounded_timeout_are_rejected():
    with (
        pytest.raises(ValueError, match="dedicated local"),
        native_before_nemotron("https://other/v1"),
    ):
        pytest.fail("remote service was accepted")
    with (
        pytest.raises(ValueError, match="sixty seconds"),
        native_before_nemotron("http://127.0.0.1:8035/v1", timeout_seconds=90),
    ):
        pytest.fail("unbounded control timeout was accepted")


def test_standalone_handoff_can_nest_inside_the_integrated_phase(capacity_service):
    from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron

    endpoint, state = capacity_service
    with native_before_nemotron(endpoint):
        with suspend_resident_nemotron(endpoint):
            assert state["sleeping"]
        assert state["sleeping"]
    assert state["events"] == ["/sleep", "/wake_up"]
    assert not state["sleeping"]


def test_uncertain_group_retirement_keeps_gpu_descriptor_quarantined(monkeypatch):
    import os
    from types import SimpleNamespace

    from corpus_structure.core.work import PhysicalRetirementUncertain
    from corpus_structure.ingest import pdf_capacity

    closed = []
    monkeypatch.setattr(pdf_capacity, "_quarantined_gpu_fds", [])
    monkeypatch.setattr(pdf_capacity, "_gpu_quarantine", None)
    monkeypatch.setattr(pdf_capacity.os, "open", lambda *_: 41)
    monkeypatch.setattr(pdf_capacity.os, "fstat", lambda _: SimpleNamespace(st_uid=os.getuid()))
    monkeypatch.setattr(pdf_capacity.os, "close", closed.append)
    monkeypatch.setattr(pdf_capacity.fcntl, "flock", lambda *_: None)
    with pytest.raises(ExceptionGroup, match="managed child"), pdf_capacity.pdf_gpu_slot():
        raise ExceptionGroup(
            "managed child", [PhysicalRetirementUncertain("group:123 remains live")]
        )
    assert pdf_capacity._quarantined_gpu_fds == [41] and not closed
    with (
        pytest.raises(PhysicalRetirementUncertain, match="managed group cleanup"),
        pdf_capacity.pdf_gpu_slot(),
    ):
        pytest.fail("uncertain group retirement advertised free GPU capacity")


def test_gpu_slot_borrows_resident_hosts_before_locking(monkeypatch):
    from contextlib import contextmanager

    from corpus_structure.ingest import pdf_capacity
    from corpus_structure.orchestrate import execution_host

    events = []

    @contextmanager
    def borrow(active):
        events.append("borrow")
        yield
        events.append("release")

    def locked(active):
        events.append("lock")
        yield
        events.append("unlock")

    monkeypatch.setattr(execution_host, "external_execution_gpu", borrow)
    monkeypatch.setattr(pdf_capacity, "_locked_gpu_slot", locked)
    with pdf_capacity.pdf_gpu_slot():
        assert events == ["borrow", "lock"]
    assert events == ["borrow", "lock", "unlock", "release"]


@pytest.mark.parametrize("cancel", [False, True])
def test_gpu_slot_waits_on_private_lock_and_checks_cancellation(tmp_path, monkeypatch, cancel):
    import fcntl
    import os
    from concurrent.futures import CancelledError
    from contextlib import nullcontext

    from corpus_structure.ingest import pdf_capacity
    from corpus_structure.orchestrate import execution_host

    monkeypatch.setattr(pdf_capacity, "Path", lambda _: tmp_path)
    monkeypatch.setattr(pdf_capacity, "sleep", lambda _: None)
    monkeypatch.setattr(execution_host, "external_execution_gpu", lambda _: nullcontext())
    path = tmp_path / f"corpus-structure-pdf-gpu-{os.getuid()}.lock"
    holder = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    checks = []

    def active():
        checks.append(True)
        if cancel and len(checks) == 2:
            raise CancelledError("cancelled while waiting")
        if len(checks) == 3:
            fcntl.flock(holder, fcntl.LOCK_UN)
        assert len(checks) <= 3

    try:
        fcntl.flock(holder, fcntl.LOCK_EX)
        if cancel:
            with pytest.raises(CancelledError, match="while waiting"), pdf_capacity.pdf_gpu_slot(active):
                pytest.fail("cancelled waiter acquired the lock")
            assert len(checks) == 2
        else:
            with pdf_capacity.pdf_gpu_slot(active):
                assert len(checks) == 3
                with pytest.raises(BlockingIOError):
                    fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(holder)
