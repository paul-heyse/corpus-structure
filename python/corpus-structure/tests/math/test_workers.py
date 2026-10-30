"""Focused controls for the full-corpus oracle's process lifecycle."""

import multiprocessing
import os
import threading
import time

import pytest
from math_support import PageWorkError, _run_pages, coverage_all, coverage_rows
from math_worker_cases import probe


def test_spawn_with_parent_thread_and_empty_input():
    done = threading.Event()
    thread = threading.Thread(target=done.wait)
    thread.start()
    try:
        assert _run_pages(probe, []) == {}
        got = _run_pages(probe, ["first", "second"], workers=1, timeout=15)
        assert set(got) == {"first", "second"}
        assert all(pid != os.getpid() and method == "spawn" for _, pid, method in got.values())
    finally:
        done.set()
        thread.join()


@pytest.mark.parametrize("page", ["error", "exit"])
def test_worker_failure_identifies_page(page):
    with pytest.raises(PageWorkError, match=page) as failure:
        _run_pages(probe, [page], workers=1, timeout=15)
    assert "incomplete pages" in " ".join(failure.value.__notes__)


def test_deadline_kills_stalled_worker_and_preserves_completed_diagnostics():
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(PageWorkError, match="deadline") as failure:
        _run_pages(probe, ["complete", "hang", "unsubmitted"], workers=1, timeout=2)
    note = " ".join(failure.value.__notes__)
    assert "completed pages: ['complete']" in note
    assert "incomplete pages: ['hang', 'unsubmitted']" in note
    assert "not submitted pages: ['unsubmitted']" in note
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not {p.pid for p in multiprocessing.active_children()} - before:
            break
        time.sleep(0.02)
    assert not {p.pid for p in multiprocessing.active_children()} - before


def test_interruption_remains_interruption():
    with pytest.raises(KeyboardInterrupt, match="deliberate interruption") as failure:
        _run_pages(probe, ["interrupt"], workers=1, timeout=15)
    assert "incomplete pages" in " ".join(failure.value.__notes__)


def test_coverage_does_not_extract_values_or_scopes(monkeypatch):
    import math_support

    def unwanted(*args, **kwargs):
        raise AssertionError("coverage must not perform downstream extraction")

    monkeypatch.setattr(math_support, "formula_values", unwanted)
    monkeypatch.setattr(math_support, "extract", unwanted)
    monkeypatch.setattr(math_support, "resolve_scopes", unwanted)
    rows = coverage_rows("special/LocationScale.html")
    assert rows
    assert all(row.start < row.end for row in rows)


def test_spawned_vendored_page_returns_real_span_rows():
    got = coverage_all(["special/LocationScale.html"])
    assert set(got) == {"special/LocationScale.html"}
    rows = got["special/LocationScale.html"]
    assert isinstance(rows, list)
    assert rows and all(row.start < row.end for row in rows)
