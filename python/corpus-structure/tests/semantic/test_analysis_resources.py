"""Invocation resources and delayed native row ownership, without PostgreSQL fixtures."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import duckdb
import pytest
from sqlalchemy import Engine
from typer.testing import CliRunner

from corpus_structure.semantic._operation_ids import CutId, RunId
from corpus_structure.semantic.analytics import AnalysisScope, BorrowedRows
from corpus_structure.settings import AnalyticsSettings

from .test_analytics import empty_packet, prepared_inputs


@pytest.fixture(scope="module")
def prepared():
    return prepared_inputs()[2]


@pytest.mark.parametrize("started", [False, True])
def test_rows_refuse_first_and_resumed_consumption_after_scope_close(prepared, started):
    scope = AnalysisScope(empty_packet(prepared))
    rows = scope.connection.sql("SELECT range FROM range(3) ORDER BY range").iter_rows(2)
    assert isinstance(rows, BorrowedRows)
    if started:
        assert next(rows) == (0,)
    scope.close()
    with pytest.raises(RuntimeError, match="analysis scope is closed"):
        next(rows)
    assert not scope._row_iterators
    rows.close()
    scope.close()


def test_delayed_rows_cannot_submit_after_scope_close(prepared):
    scope = AnalysisScope(empty_packet(prepared))
    rows = scope.connection.sql("SELECT error('native query must not execute')").iter_rows()
    scope.close()
    with pytest.raises(RuntimeError, match="analysis scope is closed"):
        next(rows)


def test_row_exhaustion_explicit_close_and_detached_outputs(prepared):
    with AnalysisScope(empty_packet(prepared)) as scope:
        relation = scope.connection.sql("SELECT range FROM range(3) ORDER BY range")
        rows = relation.iter_rows(2)
        detached = list(rows)
        assert detached == [(0,), (1,), (2,)]
        assert not scope._row_iterators
        partial = relation.iter_rows(2)
        assert next(partial) == (0,)
        partial.close()
        partial.close()
        with pytest.raises(StopIteration):
            next(partial)
        assert not scope._row_iterators
        table = relation.to_arrow_table()
        reader = relation.to_arrow_reader()
    assert detached == [(0,), (1,), (2,)]
    assert table.to_pylist() == [{"range": 0}, {"range": 1}, {"range": 2}]
    with pytest.raises(RuntimeError, match="analysis scope is closed"):
        next(reader)


def test_only_supported_closeable_row_generator_is_adopted(prepared):
    with AnalysisScope(empty_packet(prepared)) as scope:
        with pytest.raises(TypeError, match="supported closeable row generator"):
            scope._borrow_rows(iter([(1,)]))
        assert scope._borrow([1, 2]) == [1, 2]


def test_unsupported_delayed_outputs_refuse_before_native_execution(prepared):
    with AnalysisScope(empty_packet(prepared)) as scope:
        relation = scope.connection.sql("SELECT error('native query must not execute')")
        with pytest.raises(TypeError, match="lazy Polars results are unsupported"):
            relation.pl(lazy=True)
        with pytest.raises(TypeError, match="unowned Arrow capsules are unsupported"):
            relation.__arrow_c_stream__()


def test_row_close_cancellation_settles_other_iterators_readers_and_connection(
    prepared, monkeypatch
):
    scope = AnalysisScope(empty_packet(prepared))
    events = []

    def cancelled_rows():
        try:
            yield (1,)
        finally:
            events.append("cancelled rows")
            raise asyncio.CancelledError("row cancellation")

    def other_rows():
        try:
            yield (2,)
        finally:
            events.append("other rows")

    class Reader:
        def close(self):
            events.append("reader")
            raise OSError("reader cleanup failure")

    first = scope._borrow_rows(cancelled_rows())
    second = scope._borrow_rows(other_rows())
    assert next(first) == (1,) and next(second) == (2,)
    monkeypatch.setattr(scope, "_readers", [Reader()])
    scratch = Path(scope._scratch.name)
    with pytest.raises(asyncio.CancelledError, match="row cancellation") as failure:
        scope.close()
    assert events == ["cancelled rows", "other rows", "reader"]
    assert len(scope.cleanup_failures) == 2
    assert any("reader cleanup failure" in note for note in failure.value.__notes__)
    assert not scratch.exists() and not scope._row_iterators
    with pytest.raises(duckdb.ConnectionException, match="closed"):
        scope._connection.sql("SELECT 1")
    scope.close()


def test_iteration_cancellation_releases_generator_before_scope_cleanup(prepared):
    scope = AnalysisScope(empty_packet(prepared))
    events = []

    def cancelled_rows():
        try:
            yield (1,)
            raise asyncio.CancelledError("iteration cancelled")
        finally:
            events.append("generator settled")

    with pytest.raises(asyncio.CancelledError, match="iteration cancelled"), scope:
        rows = scope._borrow_rows(cancelled_rows())
        assert next(rows) == (1,)
        next(rows)
    assert events == ["generator settled"] and not scope._row_iterators
    assert not Path(scope._scratch.name).exists()


def test_consolidation_applies_invocation_resources_to_actual_scope(tmp_path, monkeypatch):
    from corpus_structure.semantic import PreparationProfile, analytics, prepare_release
    from corpus_structure.semantic import domain_operations as operations
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.publication import PublicationBatch
    from corpus_structure.semantic.query import SnapshotBinding

    bundle, deps, _ = prepared_inputs()
    prepared = prepare_release(
        bundle, composed_dependencies(deps), PreparationProfile(version="semantic-2")
    )
    resources = AnalyticsSettings(
        threads=2, memory_limit="64MiB", scratch_path=tmp_path / "scratch"
    )
    inputs = operations.CutInput(
        CutId(1),
        RunId(17),
        "control",
        prepared,
        "output",
        (),
        (),
        PublicationBatch(prepared.release_id, "output", "control"),
        {},
        {},
        SnapshotBinding(prepared.release_id, "source", 0, "cut:1"),
    )
    configs = []
    connect = analytics.duckdb.connect

    def actual_connection(*args, **kwargs):
        configs.append(dict(kwargs["config"]))
        return connect(*args, **kwargs)

    class Observed(Exception):
        pass

    class Policy:
        version = "control-policy"
        release_id = prepared.release_id

        def evaluate(self, received, scope, fused):
            assert received is inputs
            assert scope.connection.sql("SELECT current_setting('threads')").fetchall() == [(2,)]
            assert scope.packet.binding.release_id == prepared.release_id
            assert fused.num_rows == 0
            raise Observed

    monkeypatch.setattr(operations, "_completed_result", lambda *args: None)
    monkeypatch.setattr(operations, "_cut_input", lambda *args: inputs)
    monkeypatch.setattr(operations, "ReleasedRulesPolicy", lambda *args: Policy())
    monkeypatch.setattr(analytics.duckdb, "connect", actual_connection)
    with pytest.raises(Observed):
        operations.consolidate_cut(cast(Engine, object()), CutId(1), "output", analytics=resources)
    assert len(configs) == 1
    assert configs[0]["threads"] == "2" and configs[0]["memory_limit"] == "64MiB"
    scratch = Path(configs[0]["temp_directory"])
    assert scratch.parent == resources.scratch_path and not scratch.exists()


class FinalizationResult:
    def __init__(self):
        self._mapping = False

    def mappings(self):
        self._mapping = True
        return self

    def one_or_none(self):
        return {"status": "finished", "result_realization_id": "output"}

    def one(self):
        if self._mapping:
            return {
                "project_id": "control",
                "release_id": "release-control",
                "input_realization_id": "source-control",
            }
        # Native ops.run order: exercise the generated materializer before the
        # independently asserted resource snapshot reaches consolidation.
        return (
            17,
            "control",
            "release-control",
            "source-control",
            0,
            "fixture-digest",
            b"[]",
            "source",
            0,
            "{}",
            "",
            "finished",
            "fixture",
            "output",
            True,
        )

    def first(self):
        return None

    def scalar_one_or_none(self):
        return 1

    def scalar_one(self):
        return "output"


class FinalizationConnection:
    def execute(self, *args, **kwargs):
        return FinalizationResult()


class FinalizationEngine:
    @contextmanager
    def connect(self):
        yield FinalizationConnection()

    begin = connect


def test_finalization_preserves_selected_resource_snapshot(tmp_path, monkeypatch):
    from corpus_structure.orchestrate.commands import finalize_bound_run
    from corpus_structure.semantic import domain_operations

    resources = AnalyticsSettings(threads=3, memory_limit="72MiB", scratch_path=tmp_path)
    engine = cast(Engine, FinalizationEngine())
    observed = []

    def consolidated(actual_engine, cut, output, *, analytics):
        observed.append((actual_engine, cut, output, analytics))
        return "controlled result"

    monkeypatch.setattr(domain_operations, "consolidate_cut", consolidated)
    assert finalize_bound_run(engine, 17, "output", analytics=resources) == "controlled result"
    assert observed == [(engine, 1, "output", resources)]
    assert observed[0][3] is resources


@pytest.mark.parametrize("command", ["finalize", "regenerate"])
def test_cli_passes_resolved_analytics_without_reacquiring_defaults(command, tmp_path, monkeypatch):
    from corpus_structure.cli import orchestrate as cli
    from corpus_structure.cli.app import app
    from corpus_structure.orchestrate import commands
    from corpus_structure.semantic import releases, runtime
    from corpus_structure.semantic.domain_operations import DomainResult
    from corpus_structure.semantic.publication import PublicationReceipt
    from corpus_structure.semantic.types import PreparedRelease

    resources = {"threads": "3", "memory_limit": "72MiB", "scratch_path": str(tmp_path)}
    for key, value in resources.items():
        monkeypatch.setenv("CORPUS_ANALYTICS__" + key.upper(), value)
    observed = []

    @contextmanager
    def engine(*args, **kwargs):
        yield FinalizationEngine()

    def finalized(engine, run, output, *, analytics):
        observed.append(analytics)
        return DomainResult(
            run, CutId(1), output, PublicationReceipt("control", 1, "0" * 64), 0, 0, 1
        )

    monkeypatch.setattr(cli, "ENGINE", engine)
    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(commands, "finalize_bound_run", finalized)
    from types import SimpleNamespace

    prepared = cast(PreparedRelease, SimpleNamespace(release_id="release-control"))
    monkeypatch.setattr(releases, "load_release", lambda *args: prepared)
    args = (
        ["run", "finalize", "17", "--output-realization", "output", "--json"]
        if command == "finalize"
        else [
            "regenerate",
            "--domain",
            "statistics",
            "--corpus",
            str(tmp_path),
            "--project",
            "control",
            "--resume-run",
            "17",
            "--leave-unselected",
            "--json",
        ]
    )
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, (result.output, result.exception)
    assert len(observed) == 1
    assert observed[0].threads == 3 and observed[0].memory_limit == "72MiB"
    assert observed[0].scratch_path == tmp_path
