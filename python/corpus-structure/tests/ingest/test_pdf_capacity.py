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
