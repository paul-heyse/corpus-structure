"""Independent controls for bounded journal custody, safe configured capture and replay."""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path

import pytest
from structlog.contextvars import get_contextvars

from corpus_structure.cli.exception_observations import ExceptionStack, ExceptionTrace
from corpus_structure.cli.managed import ResultError, ResultStore
from corpus_structure.cli.observation_logging import (
    ChildDrain,
    bound,
    capture,
    event,
    logger,
    routes,
)
from corpus_structure.cli.observations import (
    RECORD_BYTES,
    Cursor,
    Journal,
    Observation,
    ObservationError,
    ObservationReader,
    ObservationSelection,
    ObservationWriter,
    encode_row,
)


def test_managed_bindings_sealing_primary_export_and_replay(tmp_path, monkeypatch):
    store = ResultStore(tmp_path / "results")
    with store.operation("controlled", observations=True) as invocation:
        invocation.bind_observations(
            run_id=77, task_id=91, attempt=2, provider_invocation="provider-a"
        )
        invocation.stage("processing")
        primary = invocation.directory / "report.json"
        primary.write_text("{}")
        invocation.publish("report", primary)
        live = store.read_observations(invocation.id)
        assert live.standing == "running" and live.authentication_bytes == 0
        row = next(row for row in live.rows if row.kind == "stage")
        assert row.bindings.run_id == 77 and row.bindings.task_id == 91
        assert row.bindings.attempt == 2 and row.bindings.provider_invocation == "provider-a"
    assert store.deliver(invocation.id, None, None) == primary

    def forbidden(*args, **kwargs):
        raise AssertionError("replay cannot execute the producer")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    replay = store.read_observations(invocation.id)
    assert replay.standing == "sealed" and replay.coverage == "complete_prefix"
    assert replay.authentication_bytes == replay.observed_bytes > 0
    assert replay.rows[-1].kind == "settlement"
    # A held read authenticates a pinned input once, while new readers authenticate again.
    with store.open_observations(invocation.id) as reader:
        first = reader.read(ObservationSelection(limit=1))
        second = reader.read(ObservationSelection(), after=first.next_after)
        assert first.authentication_bytes == second.authentication_bytes == replay.observed_bytes
    (invocation.directory / "observations.jsonl").write_bytes(
        b"X" + (invocation.directory / "observations.jsonl").read_bytes()[1:]
    )
    with pytest.raises(ResultError, match="digest"):
        store.read_observations(invocation.id)


def test_configured_native_foreign_safe_fanout_and_thread_context(tmp_path):
    writer = ObservationWriter(tmp_path / "journal")
    terminal = io.StringIO()
    original = {"nested": {"token": "never-visible", "zero": 0, "false": False}}

    class Unsupported:
        def __repr__(self):
            raise AssertionError("unsupported values must not invoke repr")

    route = logging.getLogger("controlled.method")
    before = (route.level, route.propagate, tuple(route.handlers))
    with (
        capture(writer, stream=terminal, invocation_id="outer"),
        routes("controlled.method"),
        bound(run_id=8, method="controlled.method"),
    ):
        logging.getLogger("corpus_structure.database").info(
            "notice password=hidden",
            extra={"database_notice": original, "unapproved": "never-copy"},
        )
        logger().info("native", unsupported=Unsupported(), false=False, zero=0)
        logger().debug("rejected")

        def work(index):
            with bound(task_id=index + 1):
                route.warning("worker %s", index)

        with ThreadPoolExecutor(max_workers=4) as pool:
            contexts = [copy_context() for _ in range(8)]
            list(
                pool.map(
                    lambda item: item[0].run(work, item[1]), zip(contexts, range(8), strict=True)
                )
            )
        assert get_contextvars()["run_id"] == 8
    assert "run_id" not in get_contextvars()
    assert (route.level, route.propagate, tuple(route.handlers)) == before
    writer.close()
    data = writer.path.read_bytes()
    assert b"never-visible" not in data and b"hidden" not in data and b"never-copy" not in data
    assert "hidden" not in terminal.getvalue()
    assert original["nested"]["token"] == "never-visible"
    rows = [Observation.model_validate_json(line) for line in data.splitlines()]
    assert len(rows) == 10 and [row.sequence for row in rows] == list(range(1, 11))
    foreign = rows[0]
    notice = foreign.fields["database_notice"]
    assert isinstance(notice, dict)
    assert notice["nested"] == {"token": "**********", "zero": 0, "false": False}
    assert rows[1].fields["false"] is False and rows[1].fields["zero"] == 0
    assert {row.bindings.task_id for row in rows[2:]} == set(range(1, 9))
    assert all(
        row.bindings.run_id == 8 and row.bindings.method == "controlled.method" for row in rows
    )


def test_concurrent_invocations_do_not_leak_destinations(tmp_path):
    store = ResultStore(tmp_path)

    def work(number):
        with store.operation("parallel", observations=True) as invocation:
            with bound(run_id=number):
                event("parallel", f"run {number}")
            return invocation.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        identities = list(pool.map(work, (17, 28)))
    for number, identity in zip((17, 28), identities, strict=True):
        rows = store.read_observations(identity).rows
        selected = [row for row in rows if row.kind == "parallel"]
        assert len(selected) == 1 and selected[0].bindings.run_id == number
        assert all(row.bindings.invocation_id == identity for row in rows)


def test_grouped_failure_keeps_original_identity_and_typed_safe_exception(tmp_path):
    store = ResultStore(tmp_path)
    try:
        raise ValueError("cause token=private")
    except ValueError as cause:
        failure = ExceptionGroup(
            "group password=private", [RuntimeError("child"), LookupError("second child")]
        )
        failure.add_note("note api_key=private")
        failure.__cause__ = cause
    with (
        pytest.raises(ExceptionGroup) as caught,
        store.operation("failure", observations=True) as invocation,
    ):
        invocation.stage("failing")
        raise failure
    assert caught.value is failure
    manifest = store.show(invocation.id)
    assert manifest.observations is not None
    assert manifest.outcome == "failed" and manifest.observations.standing == "sealed"
    page = store.read_observations(invocation.id)
    row = next(row for row in page.rows if row.kind == "unexpected_exception")
    assert row.stage == "failing" and row.bindings.invocation_id == invocation.id
    product = row.exception
    assert product is not None
    root = product.stacks[0]
    assert isinstance(root, ExceptionStack) and root.exc_type == "ExceptionGroup"
    assert root.exc_notes == ("note api_key=**********",)
    child = root.exceptions[0]
    assert isinstance(child, ExceptionTrace)
    child_stack = child.stacks[0]
    assert isinstance(child_stack, ExceptionStack) and child_stack.exc_type == "RuntimeError"
    chained = product.stacks[1]
    assert isinstance(chained, ExceptionStack) and chained.is_cause is True
    assert (
        "private" not in product.model_dump_json() and '"locals"' not in product.model_dump_json()
    )

    def wrap(error: Exception) -> Exception:
        return ExceptionGroup("nested", [error])

    deep: Exception = RuntimeError("deep root")
    for _ in range(80):
        deep = wrap(deep)
    with (
        pytest.raises(ExceptionGroup) as caught,
        store.operation("deep", observations=True) as second,
    ):
        raise deep
    assert caught.value is deep
    typed = next(
        row.exception
        for row in store.read_observations(second.id).rows
        if row.kind == "unexpected_exception"
    )
    assert typed is not None and any(
        "traversal limit" in detail.reason for detail in typed.omissions
    )


def test_reader_partial_utf8_corruption_and_cursor_shortening(tmp_path):
    path = tmp_path / "journal"
    row = Observation(
        sequence=1, timestamp="now", kind="test", message="λ", producer="child", producer_sequence=1
    )
    encoded = encode_row(row)
    cut = encoded.index("λ".encode()) + 1
    path.write_bytes(encoded[:cut])
    journal = Journal()
    with path.open("rb") as stream:
        reader = ObservationReader("result", journal, stream.fileno())
        pending = reader.read(ObservationSelection(), running=True)
        assert pending.pending_tail and pending.end_offset == 0 and not pending.corrupt
        with path.open("ab") as target:
            target.write(encoded[cut:])
        complete = reader.read(ObservationSelection(), after=pending.next_after)
        assert [item.message for item in complete.rows] == ["λ"]
        with path.open("ab") as target:
            target.write(b"{malformed}\n")
        corrupt = reader.read(ObservationSelection(), after=complete.next_after)
        assert corrupt.corrupt and corrupt.end_offset == len(encoded) and not corrupt.continuation
        assert corrupt.coverage == "corrupt"
        path.write_bytes(b"")
        with pytest.raises(ObservationError, match="shortened"):
            reader.read(ObservationSelection(), after=complete.next_after)


def test_closed_unfinished_tail_is_corrupt_and_cursor_is_bound(tmp_path):
    from hashlib import sha256

    path = tmp_path / "journal"
    path.write_bytes(b'{"unfinished"')
    journal = Journal(
        standing="sealed", length=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest()
    )
    with path.open("rb") as stream:
        reader = ObservationReader("r", journal, stream.fileno())
        page = reader.read(ObservationSelection())
        assert page.corrupt and page.pending_tail and page.end_offset == 0
        assert page.next_after is not None
        forged = Cursor.decode(page.next_after).model_copy(update={"result": "other"})
        with pytest.raises(ObservationError, match="different"):
            reader.read(ObservationSelection(), after=forged.encode())


def test_filtered_scan_response_and_collection_bounds(tmp_path):
    writer = ObservationWriter(tmp_path / "journal")
    for index in range(100):
        writer.append({"message": "x" * 4000, "index": index})
    writer.close()
    with writer.path.open("rb") as stream:
        reader = ObservationReader("r", writer.journal, stream.fileno())
        page = reader.read(
            ObservationSelection(severity="ERROR", examined_bytes=65536, max_bytes=65536)
        )
        assert page.rows == [] and page.examined_bytes == 65536 and page.end_offset > 0
        assert page.continuation and page.coverage == "continued"
        assert page.authentication_bytes == writer.path.stat().st_size
    limited = ObservationWriter(tmp_path / "limited", limit=8192)
    for index in range(100):
        limited.append({"message": "x" * 3000, "index": index})
    limited.close()
    assert limited.journal.omitted is not None
    assert limited.path.stat().st_size <= 8192 and limited.journal.omitted > 0
    rows = [
        Observation.model_validate_json(line) for line in limited.path.read_bytes().splitlines()
    ]
    assert rows[-1].kind == "collection_summary"
    assert rows[-1].fields["omitted"] == limited.journal.omitted
    assert all(len(line) + 1 <= RECORD_BYTES for line in limited.path.read_bytes().splitlines())


def test_journal_replacement_and_failed_optional_sink(tmp_path, monkeypatch):
    store = ResultStore(tmp_path / "results")
    with store.operation("test", observations=True) as invocation:
        invocation.stage("processing")
        cursor = store.read_observations(invocation.id).next_after
    path = invocation.directory / "observations.jsonl"
    path.rename(path.with_suffix(".old"))
    path.write_bytes(b"")
    with pytest.raises(ResultError, match="owner publication"):
        store.read_observations(invocation.id, after=cursor)
    writer = ObservationWriter(tmp_path / "sink")
    with capture(writer):

        def failed_append(*args, **kwargs):
            raise OSError("diagnostics unavailable")

        monkeypatch.setattr(writer, "_append", failed_append)
        event("business", "continues")
    assert writer.journal.standing == "unavailable"
    writer.close()


def test_child_drain_io_failure_is_ancillary(tmp_path, monkeypatch):
    writer = ObservationWriter(tmp_path / "parent")
    spool = tmp_path / "child"
    spool.write_bytes(b"{}\n")
    drain = ChildDrain(spool, writer)
    monkeypatch.setattr(os, "pread", lambda *args: (_ for _ in ()).throw(OSError("read failed")))
    drain.drain(final=True)
    assert drain.stopped
    writer.close()
    rows = [Observation.model_validate_json(line) for line in writer.path.read_bytes().splitlines()]
    assert rows[0].kind == "child_transfer_unavailable"


def test_killed_owner_partial_read_and_inspect_watch_streams(tmp_path):
    script = """
import os,sys
from pathlib import Path
from corpus_structure.cli.managed import ResultStore
with ResultStore(Path(sys.argv[1])).operation('controlled', observations=True) as invocation:
 invocation.stage('working')
 print(invocation.id, flush=True)
 os._exit(0)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True, check=True
    )
    identity = completed.stdout.strip()
    page = ResultStore(tmp_path).read_observations(identity)
    assert page.standing == "running" and page.authentication_bytes == 0
    command = str(Path(sys.executable).with_name("ci"))
    environment = {**os.environ, "CORPUS_CI_RESULTS": str(tmp_path)}
    for args in (
        ["inspect", identity, "--view", "timeline"],
        ["watch", identity, "--seconds", "0"],
    ):
        result = subprocess.run(
            [command, "results", *args, "--json"],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        body = json.loads(result.stdout)
        assert body["outcome"] == "running" and body["custody"] == "unsettled"
        report = body.get("inspection", body)
        assert report["observations"]["standing"] == "running"
        assert report["native"]["availability"] == "unavailable"


def test_nonobservational_method_routes_preserve_prior_logging_even_concurrently(tmp_path):
    route = logging.getLogger("controlled.native")
    output = io.StringIO()
    old_handlers, old_level, old_propagate = route.handlers[:], route.level, route.propagate
    previous = logging.StreamHandler(output)
    route.handlers = [previous]
    route.setLevel(logging.WARNING)
    route.propagate = False
    try:
        with routes("controlled.native"):
            route.warning("ordinary warning")
        writer = ObservationWriter(tmp_path / "journal")
        with capture(writer), routes("controlled.native"):
            route.warning("owned warning")
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(route.warning, "unbound concurrent warning").result()
        writer.close()
        assert output.getvalue() == "ordinary warning\nunbound concurrent warning\n"
        retained = [
            Observation.model_validate_json(line).message
            for line in writer.path.read_bytes().splitlines()
        ]
        assert retained == ["owned warning"]
    finally:
        route.handlers = old_handlers
        route.setLevel(old_level)
        route.propagate = old_propagate


def test_inspection_bounds_joined_zero_rows_and_withholds_sole_row_cursor(tmp_path, monkeypatch):
    import shlex

    import typer

    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState
    from corpus_structure.cli.result_inspection import NativeInspection, inspect_result

    store = ResultStore(tmp_path)
    with store.operation("bounded", observations=True) as invocation:
        invocation.bind_observations(run_id=42, project="nondefault project's space")
        invocation.stage("selected")
    monkeypatch.setattr(
        "corpus_structure.cli.result_inspection.native_inspection",
        lambda *args: NativeInspection(
            availability="available",
            run={
                "run_id": 42,
                "status": "source_ready",
                "readiness": "source_ready",
                "extra": "x" * 100000,
            },
            counts={"done": 1},
            denominator=1,
        ),
    )
    ctx = typer.Context(typer.main.get_command(app), obj=CliState())
    report = inspect_result(
        ctx, store, invocation.id, ObservationSelection(severity="CRITICAL", max_bytes=65536)
    )
    assert report.observations.rows == [] and len(report.model_dump_json().encode()) <= 65536
    assert report.native.run == {
        "run_id": 42,
        "status": "source_ready",
        "readiness": "source_ready",
    }
    action = next(item for item in report.next_actions if item.kind == "resume_run")
    assert shlex.split(action.command) == [
        "ci",
        "run",
        "resume",
        "42",
        "--project",
        "nondefault project's space",
    ]
    monkeypatch.setattr(
        "corpus_structure.cli.result_inspection.native_inspection",
        lambda *args: NativeInspection(reason="No native reader selected"),
    )
    with store.operation("large-row", observations=True) as large:
        large.bind_observations(project="p" * 16000)
        assert large.observation_writer is not None
        large.observation_writer.append(
            {},
            imported=Observation(
                sequence=1,
                timestamp="now",
                kind="large",
                stage="large",
                message="large",
                fields={"data": "x" * 54000},
                producer="controlled",
                producer_sequence=1,
            ),
        )
    selection = ObservationSelection(stage="large", max_bytes=65536)
    bounded = inspect_result(ctx, store, large.id, selection)
    assert bounded.observations.rows == [] and bounded.observations.continuation
    assert bounded.observations.next_after is not None
    cursor = Cursor.decode(bounded.observations.next_after)
    assert cursor.sequence == 1  # The invocation row preceded the withheld large record.
    continued = inspect_result(
        ctx,
        store,
        large.id,
        selection.model_copy(update={"max_bytes": 1048576}),
        after=bounded.observations.next_after,
    )
    assert [row.kind for row in continued.observations.rows] == ["large"]
    assert len(bounded.model_dump_json().encode()) <= 65536


def test_watch_latest_window_declares_scan_progress_after_multiple_pages_and_quiet_poll(
    cli, tmp_path
):
    store = ResultStore(tmp_path)
    with store.operation("window", observations=True) as result:
        writer = result.observation_writer
        assert writer is not None
        for index in range(125):
            writer.append({"kind": "window", "message": f"event {index}"})
        expected = store.read_observations(result.id, ObservationSelection(limit=1000)).rows
        output = cli(
            "results",
            "watch",
            result.id,
            "--seconds",
            "0.3",
            "--json",
            env={"CORPUS_CI_RESULTS": str(tmp_path)},
        )
        assert output.exit_code == 0, output.output
        page = json.loads(output.stdout)["inspection"]["observations"]
        assert [row["sequence"] for row in page["rows"]] == [row.sequence for row in expected[-10:]]
        assert page["coverage"] == page["selection_kind"] == "latest_window"
        assert page["position_semantics"] == "watch_scan_progress"
        assert page["window_limit"] == 10
        assert page["returned_sequence_range"] == [expected[-10].sequence, expected[-1].sequence]
        assert page["window_evicted"] == len(expected) - 10
        assert page["window_budget_evicted"] == 0
        assert page["start_offset"] == page["end_offset"]
        assert page["next_after"] is not None


def test_watch_latest_window_counts_budget_evictions_without_rewinding_scan(cli, tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("large-window", observations=True) as result:
        writer = result.observation_writer
        assert writer is not None
        for index in range(12):
            writer.append(
                {},
                imported=Observation(
                    sequence=index + 1,
                    timestamp="now",
                    kind="large",
                    message=f"event {index}",
                    fields={"data": "x" * 54000},
                    producer="controlled",
                    producer_sequence=index + 1,
                ),
            )
    output = cli(
        "results",
        "watch",
        result.id,
        "--seconds",
        "0",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert output.exit_code == 0, output.output
    page = json.loads(output.stdout)["inspection"]["observations"]
    assert page["selection_kind"] == "latest_window"
    assert 0 < page["window_budget_evicted"] == page["response_omitted"]
    assert page["selected_count"] + page["window_budget_evicted"] == 10
    assert page["returned_sequence_range"] == [
        page["rows"][0]["sequence"],
        page["rows"][-1]["sequence"],
    ]
    cursor = Cursor.decode(page["next_after"])
    assert cursor.offset == page["end_offset"] == page["observed_bytes"]
    assert len(json.loads(output.stdout)["inspection"]["observations"]["rows"]) < 10
