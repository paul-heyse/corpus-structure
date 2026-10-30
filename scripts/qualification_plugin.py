"""Public pytest hooks supplement reportlog; reports remain the outcome authority."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, TextIO

import pytest
from hypothesis import settings

_stream: TextIO | None = None
_identity: dict[str, object] = {}


def _emit(event: str, **values: object) -> None:
    if _stream is not None:
        _stream.write(
            json.dumps({"event": event, "time": time.time(), **_identity, **values}) + "\n"
        )
        _stream.flush()


def record_native_context(context: dict[str, object]) -> None:
    """Native fixture calls this with masked context only after actual acquisition."""
    _emit("native_context", context=context)


def pytest_configure(config: pytest.Config) -> None:
    global _stream, _identity
    directory = os.environ.get("QUALIFICATION_RECEIPT_DIR")
    if directory is None:
        return
    worker = os.environ.get("PYTEST_XDIST_WORKER", "controller")
    _identity = {"pid": os.getpid(), "worker": worker}
    _stream = (Path(directory) / f"events-{worker}-{os.getpid()}.jsonl").open("x")
    config.add_cleanup(_close)
    _emit("process_start")


def _close() -> None:
    global _stream
    if _stream is not None:
        _stream.close()
        _stream = None


def pytest_sessionstart(session: pytest.Session) -> None:
    _emit(
        "session_start",
        hypothesis_profile=settings.get_current_profile_name(),
        hypothesis_settings=str(settings.default),
        faulthandler_timeout=session.config.getini("faulthandler_timeout"),
        faulthandler_exit_on_timeout=session.config.getini("faulthandler_exit_on_timeout"),
    )


def pytest_collection_finish(session: pytest.Session) -> None:
    _emit("collection_finish", selected=[item.nodeid for item in session.items])


def pytest_deselected(items: list[pytest.Item]) -> None:
    _emit("deselected", nodes=[item.nodeid for item in items])


def pytest_runtest_logstart(nodeid: str, location: object) -> None:
    _emit("logstart", nodeid=nodeid, location=location)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> Generator[None, Any, Any]:
    _emit("phase_start", nodeid=item.nodeid, phase="setup")
    return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, Any, Any]:
    _emit("phase_start", nodeid=item.nodeid, phase="call")
    return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> Generator[None, Any, Any]:
    _emit("phase_start", nodeid=item.nodeid, phase="teardown")
    return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    if call.excinfo is not None:
        # Import lazily: pure test collection never acquires application/native settings.
        from test_prerequisites import PrerequisiteUnavailable

        error = call.excinfo.value
        if isinstance(error, PrerequisiteUnavailable):
            report.user_properties.extend(
                [
                    ("qualification_prerequisite", error.category),
                    ("qualification_reason", error.reason),
                ]
            )
    return report


def pytest_runtest_logfinish(nodeid: str, location: object) -> None:
    _emit("logfinish", nodeid=nodeid, location=location)


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: Any, error: object) -> None:
    _emit("worker_down", lost_worker=node.gateway.id, error=str(error) if error else None)
