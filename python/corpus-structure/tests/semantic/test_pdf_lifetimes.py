"""Actual child settlement and explicitly closed native reader lifetimes."""

import multiprocessing
import os

import pytest
from pdf_validation_support import (
    acknowledge_then_exit_nonzero,
    acknowledge_then_hold,
    hold_validation,
)

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.semantic import pdf_publication
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader


def test_db_free_validation_cancellation_reaps_its_actual_spawned_child(tmp_path, monkeypatch):
    context = multiprocessing.get_context("spawn")
    projection = tmp_path / "child-started"
    pids = []

    class Context:
        Pipe = staticmethod(context.Pipe)

        @staticmethod
        def Process(*, target, args):
            return context.Process(target=hold_validation, args=args)

    monkeypatch.setattr(pdf_publication.multiprocessing, "get_context", lambda mode: Context())

    def check():
        if projection.exists():
            alive = [p for p in multiprocessing.active_children() if p.is_alive()]
            assert len(alive) == 1
            assert alive[0].pid is not None
            pids.append(alive[0].pid)
            raise DatabaseOperationCancelled("operator cancelled native validation")

    with pytest.raises(DatabaseOperationCancelled, match="operator cancelled"):
        pdf_publication._run_native_validation(tmp_path / "capture", projection, check)
    assert len(pids) == 1
    with pytest.raises(ProcessLookupError):
        os.kill(pids[0], 0)
    assert all(p.pid != pids[0] for p in multiprocessing.active_children())


def test_borrowed_event_fragments_remain_owned_by_selected_source_caller():
    reader = object.__new__(PublishedPdfReader)
    closed = []

    def selected_events():
        try:
            yield {"kind": "literal", "value": "["}
            yield {"kind": "literal", "value": "]"}
        finally:
            closed.append(True)

    events = selected_events()
    fragment = reader.iter_native_json(events)
    assert next(fragment) == b"["
    fragment.close()
    assert closed == []
    assert next(events)["value"] == "]"
    events.close()
    assert closed == [True]


def test_child_cleanup_keeps_primary_and_attempts_all_independent_handles(tmp_path, monkeypatch):
    closed = []

    class Parent:
        def close(self):
            closed.append("parent")

    class Child:
        def close(self):
            closed.append("child")
            raise OSError("pipe close failed")

    class Process:
        pid = None

        def close(self):
            closed.append("process")

    class Context:
        @staticmethod
        def Pipe(*args, **kwargs):
            return Parent(), Child()

        @staticmethod
        def Process(*args, **kwargs):
            return Process()

    monkeypatch.setattr(pdf_publication.multiprocessing, "get_context", lambda mode: Context())
    primary = DatabaseOperationCancelled("cancel before launch")

    def check():
        raise primary

    with pytest.raises(DatabaseOperationCancelled) as caught:
        pdf_publication._run_native_validation(tmp_path / "capture", tmp_path / "out", check)
    assert caught.value is primary
    assert closed == ["child", "parent", "process"]
    assert any("pipe close failed" in note for note in primary.__notes__)


def test_borrowed_companion_fragment_does_not_close_selected_source_cursor():
    reader = object.__new__(PublishedPdfReader)
    closed = []

    def selected_events():
        try:
            yield {"kind": "row", "body": {"kept": "value"}}
            yield {"kind": "close"}
        finally:
            closed.append(True)

    events = selected_events()
    fragment = reader.iter_companion_json("native_metadata", events)
    assert next(fragment) == b'{"kept":"value"'
    fragment.close()
    assert closed == []
    assert next(events)["kind"] == "close"
    events.close()
    assert closed == [True]


def _select_validation_target(monkeypatch, target):
    context = multiprocessing.get_context("spawn")

    class Context:
        Pipe = staticmethod(context.Pipe)

        @staticmethod
        def Process(*, target=None, args=()):
            return context.Process(target=selected, args=args)

    selected = target
    monkeypatch.setattr(pdf_publication.multiprocessing, "get_context", lambda mode: Context())


def test_positive_validation_ack_requires_successful_terminal_exit(tmp_path, monkeypatch):
    _select_validation_target(monkeypatch, acknowledge_then_exit_nonzero)
    projection = tmp_path / "child-pid"
    with pytest.raises(RuntimeError, match="exited with status 17"):
        pdf_publication._run_native_validation(tmp_path / "capture", projection, lambda: None)
    pid = int(projection.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert all(child.pid != pid for child in multiprocessing.active_children())


def test_validation_settlement_after_ack_keeps_owner_cancellation_and_reaps(tmp_path, monkeypatch):
    _select_validation_target(monkeypatch, acknowledge_then_hold)
    projection = tmp_path / "ack-sent"
    checks_after_ack = 0
    primary = DatabaseOperationCancelled("cancel validation shutdown")

    def check():
        nonlocal checks_after_ack
        if projection.exists():
            checks_after_ack += 1
            if checks_after_ack >= 2:
                raise primary

    with pytest.raises(DatabaseOperationCancelled) as caught:
        pdf_publication._run_native_validation(tmp_path / "capture", projection, check)
    assert caught.value is primary and checks_after_ack >= 2
    pid = int(projection.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert all(child.pid != pid for child in multiprocessing.active_children())


@pytest.mark.parametrize("close_fails", [False, True])
def test_program_child_acknowledges_only_after_owned_store_cleanup(
    tmp_path, monkeypatch, close_fails
):
    from corpus_structure.semantic import pdf_payload_validation, pdf_records

    capture, projection = tmp_path / "capture.arrow", tmp_path / "projection.jsonl"
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from semantic.pdf_record_reader_support import NativeRows, native

    lowered = NativeRows(native())
    pdf_publication.write_pdf_oracle_capture(
        capture,
        context=trusted_pdf_context(),
        kind="native",
        rows=lambda family, filters: lowered.iter_rows(family, filters),
        json_fields="text",
        check_active=lambda: None,
    )
    events = []
    sent = []
    document = {
        "body": {"self_ref": "#/body", "children": []},
        "furniture": {"self_ref": "#/furniture", "children": []},
        "pages": {},
    }

    class Store:
        def __init__(self, path):
            events.append("store-open")

        def add(self, family, body):
            pass

        def stream_descriptors(self):
            return ()

        def parts(self, stream):
            return ()

        def validate(self, native, *, items, regions):
            assert native is document and len(items) == 2 and not regions
            events.append("store-validated")

        def close(self):
            events.append("store-closed")
            if close_fails:
                raise OSError("controlled store cleanup failure")

    class Result:
        def send(self, value):
            assert events[-1] == "store-closed"
            sent.append(value)
            events.append("outcome-sent")

        def close(self):
            events.append("pipe-closed")

    monkeypatch.setattr(pdf_payload_validation, "FrozenPayloadStore", Store)
    monkeypatch.setattr(
        pdf_records, "reconstruct_native_document", lambda *args, **kwargs: document
    )
    monkeypatch.setattr(
        pdf_records,
        "validate_native_callbacks",
        lambda native, *, contract: events.append("callbacks-validated"),
    )
    pdf_publication._native_validation_child(str(capture), str(projection), Result())
    assert events == [
        "store-open",
        "callbacks-validated",
        "store-validated",
        "store-closed",
        "outcome-sent",
        "pipe-closed",
    ]
    if close_fails:
        assert sent[0][0] is False and "cleanup failed" in sent[0][1]
    else:
        assert sent == [(True, None)]
