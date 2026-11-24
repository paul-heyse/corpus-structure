"""Independent resource, expression, multiplicity and time-zone contracts."""

from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from duckdb import col, fn, lit

from corpus_structure.analytics import connection
from corpus_structure.settings import AnalyticsSettings


def test_invocation_uses_settings_and_releases_private_spill(tmp_path):
    settings = AnalyticsSettings(threads=2, memory_limit="128MB", scratch_path=tmp_path)
    with connection(settings) as db:
        actual = db.native.execute(
            "SELECT current_setting('threads'), current_setting('memory_limit'), "
            "current_setting('temp_directory'), current_setting('TimeZone'), "
            "current_setting('async_threads'), current_setting('default_collation')"
        ).fetchall()[0]
        assert actual[0] == 2 and actual[1] == "122.0 MiB" and actual[3] == "UTC"
        assert actual[4:] == (2, "binary")
        scratch = Path(actual[2])
        assert scratch.is_absolute() and scratch.parent == tmp_path
        assert scratch.is_dir() and scratch.stat().st_mode & 0o077 == 0
        value = datetime(2026, 11, 19, 12, 34, tzinfo=UTC)
        table = pa.table({"time": pa.array([value], type=pa.timestamp("us", tz="Asia/Tokyo"))})
        result = db.from_arrow(table).to_arrow_table()
        assert result.schema.field("time").type.tz == "UTC"
        assert result.column("time")[0].as_py() == value
    assert not scratch.exists()


def test_parent_job_uses_its_captured_settings(tmp_path, monkeypatch):
    from corpus_structure import analytics
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

    ambient = AnalyticsSettings(threads=4, memory_limit="2GB")
    captured = AnalyticsSettings(
        threads=2,
        memory_limit="32MB",
        batch_size=23,
        scratch_path=tmp_path,
        job_workspace_bytes=64 * 1024**2,
        job_spill_bytes=128 * 1024**2,
    )
    monkeypatch.setattr(analytics, "_settings", ambient)
    allocation = analytics.AnalyticalAllocation.for_policy(
        CharacterizationExecutionPolicy(cpu_native_threads=1), captured
    )
    with analytics.analytical_job(allocation, check_active=lambda: None, settings=captured):
        assert analytics.configured().batch_size == 23
        with connection() as db:
            assert db.native.sql("SELECT current_setting('memory_limit')").fetchall() == [
                ("30.5 MiB",)
            ]
    assert analytics.configured() is ambient


def test_fresh_standard_pdf_child_can_acquire_analytics_before_docling(tmp_path):
    """A primitive handoff leaves the generated-helper factories visible to custody."""
    from dataclasses import replace
    from pickle import dumps
    from subprocess import run
    from sys import executable
    from textwrap import dedent

    from corpus_structure.analytics import AnalyticalAllocation
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

    settings = AnalyticsSettings(threads=2, memory_limit="32MB")
    allocation = replace(
        AnalyticalAllocation.for_policy(CharacterizationExecutionPolicy(), settings),
        scratch_root=tmp_path,
    )
    child = run(
        [
            executable,
            "-c",
            dedent("""
                import os
                import pickle
                import sys

                os.environ["PYDANTIC_DISABLE_PLUGINS"] = "__all__"
                allocation = pickle.load(sys.stdin.buffer)
                import pyarrow as pa
                from corpus_structure.analytics import analytical_job, connection
                from corpus_structure.ingest.pdf_producer_contract import (
                    standard_pdf_contract,
                    standard_pdf_execution,
                )

                contract = standard_pdf_contract()
                assert "pydantic" not in sys.modules
                with analytical_job(allocation, check_active=tuple), standard_pdf_execution(contract):
                    from docling_core.types.doc import DoclingDocument

                    assert DoclingDocument(name="generated-helper custody").name == "generated-helper custody"
                    with connection() as db:
                        assert db.from_arrow(pa.table({"x": [1, 2]})).fetchall() == [(1,), (2,)]
                """),
        ],
        input=dumps(allocation),
        capture_output=True,
        timeout=90,
    )
    assert child.returncode == 0, child.stderr.decode()
    assert not list(tmp_path.iterdir())


def _analytical_worker(mode: str, ready_path: str, proceed_path: str, *, check_active) -> str:
    import json
    from pathlib import Path
    from time import sleep

    import numpy as np
    import pyarrow as pa
    from duckdb import col, fn

    from corpus_structure.analytics import connection, current_allocation

    allocation = current_allocation()
    assert allocation is not None
    ready = Path(ready_path)
    proceed = Path(proceed_path)
    reader = None
    with connection() as db:
        actual = db.native.sql(
            "SELECT current_setting('threads'), current_setting('memory_limit'), "
            "current_setting('max_temp_directory_size'), current_setting('temp_directory')"
        ).fetchall()[0]
        if mode == "interrupt":
            ready.touch()
            db.native.sql("SELECT sum(hash(i)) FROM range(100000000000) t(i)").fetchall()
        elif mode == "spill":
            relation = db.from_arrow(pa.table({"id": np.arange(1_000_000)})).sort(
                fn("hash", col("id")).asc().nulls_last()
            )
            reader = relation.to_arrow_reader(batch_size=50)
            assert reader.read_next_batch().num_rows == 50
            spill = sum(path.stat().st_size for path in Path(actual[3]).iterdir())
            assert 1024**2 <= spill <= allocation.spill_bytes
            ready.touch()
            for _ in range(2000):
                if proceed.exists():
                    break
                check_active()
                sleep(0.01)
            else:
                raise TimeoutError("second analytical worker never settled")
        else:
            from decimal import Decimal

            ticks = 1680000000000000001
            table = pa.table(
                {
                    "instant": pa.array([ticks, None, ticks], type=pa.timestamp("ns", "UTC")),
                    "small": pa.array(
                        [Decimal("1.20"), None, Decimal("1.20")], type=pa.decimal128(7, 2)
                    ),
                    "large": pa.array(
                        [Decimal("123456789012345678.900123"), Decimal("-0.000001"), None],
                        type=pa.decimal128(30, 6),
                    ),
                }
            )
            with db.from_arrow(table).to_arrow_reader(batch_size=2) as result:
                restored = result.read_all()
            assert restored.column("instant").cast(pa.int64()).to_pylist() == [ticks, None, ticks]
            assert restored.column("small").to_pylist() == [Decimal("1.20"), None, Decimal("1.20")]
            assert restored.column("large").to_pylist() == [
                Decimal("123456789012345678.900123"),
                Decimal("-0.000001"),
                None,
            ]
    if reader is not None:
        try:
            reader.read_next_batch()
        except pa.ArrowInvalid as error:
            assert "already been closed" in str(error)
        else:
            raise AssertionError("analytical job kept a reader open after retirement")
    return json.dumps(actual)


def test_two_admitted_analytical_workers_drain_readers_and_interrupted_engine(
    tmp_path, monkeypatch
):
    import importlib
    import inspect
    import json
    from dataclasses import replace
    from time import monotonic, sleep
    from types import SimpleNamespace
    from typing import cast

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.semantic import cpu_execution
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope, CPURequestCancelled
    from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor
    from corpus_structure.semantic.types import PreparedRelease

    name = "analytical_worker_fixture"
    source = inspect.getsource(_analytical_worker).encode()
    source_path = tmp_path / (name + ".py")
    source_path.write_bytes(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    signature = inspect.signature(importlib.import_module(name)._analytical_worker)
    cpu_path = Path(cpu_execution.__file__).resolve()
    descriptor = PythonCPUDescriptor(
        (
            (name, str(source_path), source),
            (cpu_execution.__name__, str(cpu_path), cpu_path.read_bytes()),
        ),
        name + "._analytical_worker",
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
    )
    workspace = 32 * 1024**2
    settings = AnalyticsSettings(
        scratch_path=tmp_path / "spill",
        threads=2,
        job_workspace_bytes=workspace,
        job_spill_bytes=64 * 1024**2,
    )
    policy = replace(
        CharacterizationExecutionPolicy(),
        max_packet_bytes=2048,
        max_reply_bytes=1024,
        max_owned_bytes=2 * (workspace + 3072),
    )
    scope = CPUExecutionScope(
        cast(PreparedRelease, SimpleNamespace(release_id="unused")),
        policy,
        retain_schema=False,
        analytics_settings=settings,
    )
    proceed = tmp_path / "proceed"

    def submit(mode, ready):
        packet = descriptor.packet(
            {"mode": mode, "ready_path": str(ready), "proceed_path": str(proceed)}, signature
        )
        permit = scope.try_admit(packet_bytes=len(packet), analytical=True)
        assert permit is not None
        return scope.submit_closed_python(permit, packet)

    try:
        first_ready, second_ready = tmp_path / "reader-open", tmp_path / "engine-active"
        serial = submit("fidelity", first_ready)
        serial.future.result(timeout=30)
        serial.collect()
        assert serial.retire() and scope.budget.used_bytes == 0

        held = submit("spill", first_ready)
        active = submit("interrupt", second_ready)
        assert scope.budget.used_bytes > 2 * workspace
        assert scope.try_admit(packet_bytes=0, analytical=True) is None

        deadline = monotonic() + 20
        while not (first_ready.exists() and second_ready.exists()):
            assert monotonic() < deadline
            for handle in (held, active):
                if handle.future.done():
                    handle.collect()
            sleep(0.01)
        assert len(list(settings.scratch_path.iterdir())) == 2
        active.cancel()
        assert active.future.result(timeout=10).error_type == "CPURequestCancelled"
        with pytest.raises(CPURequestCancelled):
            active.collect()
        assert active.retire() and scope.budget.used_bytes > workspace
        assert not held.future.done()
        proceed.touch()
        held.future.result(timeout=10)
        threads, memory, spill, scratch = json.loads(json.loads(held.collect().content))
        assert (threads, memory, spill) == (1, "24.0 MiB", "64.0 MiB")
        assert not Path(scratch).exists()
        assert held.retire() and scope.budget.used_bytes == 0
        assert list(settings.scratch_path.iterdir()) == []
    finally:
        proceed.touch()
        scope.close()


@pytest.mark.parametrize("operation", ("filter", "select", "sort", "aggregate", "join"))
def test_expression_entries_refuse_sql_text(tmp_path, operation):
    with connection(AnalyticsSettings(scratch_path=tmp_path)) as db:
        relation = db.from_arrow(pa.table({"id": [1]}))
        with pytest.raises(TypeError, match="expression"):
            if operation == "join":
                relation.join(relation, "id=id")
            else:
                getattr(relation, operation)("id")


def test_bag_and_set_operations_preserve_their_declared_multiplicity(tmp_path):
    with connection(AnalyticsSettings(scratch_path=tmp_path)) as db:
        left = db.from_arrow(pa.table({"id": [1, 1, 2]}))
        right = db.from_arrow(pa.table({"id": [1]}))
        assert left.union_all(right).sort(col("id")).fetchall() == [(1,), (1,), (1,), (2,)]
        assert left.union(right).sort(col("id")).fetchall() == [(1,), (2,)]
        assert left.except_all(right).sort(col("id")).fetchall() == [(1,), (2,)]
        assert left.except_(right).sort(col("id")).fetchall() == [(2,)]
        assert left.intersect_all(left).sort(col("id")).fetchall() == [(1,), (1,), (2,)]
        assert left.intersect(left).sort(col("id")).fetchall() == [(1,), (2,)]
        with pytest.raises(TypeError, match="columns or types"):
            left.union_all(db.from_arrow(pa.table({"id": ["1"]})))


def test_named_window_comparison_keeps_occurrences_and_explicit_null_order(tmp_path):
    table = pa.table(
        {
            "scope": ["p", "q", "p", "p"],
            "ordinal": [None, 0, 0, 0],
            "occurrence": ["last", "sibling", "β", "a"],
        }
    )
    ordinal = col("ordinal").asc().nulls_last()
    occurrence = col("occurrence").asc()
    with connection(AnalyticsSettings(scratch_path=tmp_path)) as db:
        typed = (
            db.from_arrow(table)
            .filter(col("scope") == lit("p"))
            .select(
                col("occurrence"),
                fn("row_number")
                .over(
                    partition_by=[col("scope")],
                    order_by=[ordinal, occurrence],
                )
                .alias("position"),
            )
            .sort(col("position").asc())
            .fetchall()
        )
        db.native.register("occurrences", table)
        comparison = db.native.sql(
            "SELECT occurrence, row_number() OVER (PARTITION BY scope "
            "ORDER BY ordinal ASC NULLS LAST, occurrence ASC) AS position "
            "FROM occurrences WHERE scope = ? ORDER BY position",
            params=["p"],
        ).fetchall()
    assert typed == comparison == [("a", 1), ("β", 2), ("last", 3)]


def test_bad_scratch_refuses_before_connection(tmp_path):
    unavailable = tmp_path / "file"
    unavailable.write_bytes(b"occupied")
    with (
        pytest.raises(OSError, match=str(unavailable)),
        connection(AnalyticsSettings(scratch_path=unavailable)),
    ):
        pytest.fail("unavailable scratch was admitted")


def test_export_capture_honors_batch_size_and_resident_bound():
    from corpus_structure.semantic.refusal_types import SemanticRefusal
    from corpus_structure.serve.companion_export import _capture_batches

    table = pa.table({"id": [1, 2, 3]})
    for mode in ("resident", "spooled"):
        settings = AnalyticsSettings(capture_mode=mode, batch_size=2)
        batches = list(_capture_batches(iter(table.to_batches()), settings))
        assert [batch.num_rows for batch in batches] == [2, 1]
        assert pa.Table.from_batches(batches).to_pylist() == [{"id": 1}, {"id": 2}, {"id": 3}]
    with pytest.raises(SemanticRefusal, match="resident capture exceeds"):
        list(
            _capture_batches(
                iter(table.to_batches()),
                AnalyticsSettings(capture_mode="resident", resident_limit_bytes=1),
            )
        )


def _worker_analytics_consumers(directory):
    import os
    from contextlib import ExitStack, contextmanager
    from types import SimpleNamespace
    from unittest.mock import patch

    from corpus_structure.ingest import pdf_candidate_geometry, pdf_stream_reconciliation
    from corpus_structure.ingest.pdf_candidate_source import InMemoryCandidatePageSource
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
    from corpus_structure.semantic import rich_relations
    from corpus_structure.semantic.analytical_kernels import ViewClaim

    observed = []

    @contextmanager
    def inspect_connection():
        with connection() as db:
            observed.append(
                db.native.execute(
                    "SELECT current_setting('threads'), current_setting('memory_limit'), "
                    "current_setting('temp_directory'), current_setting('TimeZone'), "
                    "current_setting('async_threads'), current_setting('default_collation')"
                ).fetchall()[0]
            )
            yield db

    with ExitStack() as stack:
        for module in (pdf_candidate_geometry, pdf_stream_reconciliation):
            stack.enter_context(patch.object(module, "analytical_connection", inspect_connection))
        candidates = InMemoryCandidatePageSource(
            (
                CandidatePage(
                    7,
                    True,
                    False,
                    (InlineCandidate(7, "x", 1, 2, 3, 4, "TOPLEFT", None, "fixture"),),
                    True,
                ),
            )
        )
        document = SimpleNamespace(pages={7: SimpleNamespace(size=SimpleNamespace(height=100))})
        with pdf_candidate_geometry.CandidateGeometry(document, candidates, {7}) as geometry:
            geometry_rows = geometry.connection.table("candidate_geometry").fetchall()
        replay = Path(directory) / "observations.arrow"
        pdf_stream_reconciliation.write_recognition_replay(
            replay,
            [({"page": 2}, {"value": "second"}, b"two"), ({"page": 1}, {"value": "first"}, b"one")],
        )
        replay_rows = list(pdf_stream_reconciliation.iter_recognition_replay(replay))
        kernel = rich_relations.RichRelationKernel(
            property_ids=frozenset({"p:value"}), check_active=lambda: None
        )
        views = kernel.views(
            claims=tuple(
                ViewClaim(name, "p:value", "subject:one", None, None)
                for name in ("first", "second")
            ),
            entities=(),
            identity=(),
            alternatives=(),
            specs=(),
        )
    return (
        os.getpid(),
        observed,
        geometry_rows,
        replay_rows,
        views,
        pa.cpu_count(),
        pa.io_thread_count(),
    )


def test_spawned_cpu_uses_captured_settings_for_real_analytical_consumers(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace
    from typing import cast

    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.types import PreparedRelease

    monkeypatch.setenv("CORPUS_ANALYTICS__THREADS", "7")
    monkeypatch.setenv("CORPUS_ANALYTICS__MEMORY_LIMIT", "512MB")
    selected = AnalyticsSettings(threads=2, memory_limit="128MB", scratch_path=tmp_path / "spill")
    scope = CPUExecutionScope(
        cast(PreparedRelease, SimpleNamespace(release_id="unused")),
        retain_schema=False,
        analytics_settings=selected,
    )
    try:
        pid, observed, geometry, replay, views, arrow_cpu, arrow_io = (
            scope._executor().submit(_worker_analytics_consumers, tmp_path).result(timeout=60)
        )
    finally:
        scope.close()
    assert pid != os.getpid()
    assert (arrow_cpu, arrow_io) == (scope.policy.cpu_native_threads,) * 2
    assert len(observed) == 2
    for threads, memory, directory, zone, io_threads, collation in observed:
        assert (threads, memory, zone) == (2, "122.0 MiB", "UTC")
        assert (io_threads, collation) == (2, "binary")
        assert Path(directory).parent == selected.scratch_path
        assert not Path(directory).exists()
    assert len(geometry) == 1 and geometry[0][:2] == (7, 0)
    assert replay == [
        ({"page": 1}, {"value": "first"}, b"one"),
        ({"page": 2}, {"value": "second"}, b"two"),
    ]
    same_slot = {row.claim: row.facts for row in views if row.view == "same_slot"}
    assert same_slot == {"first": ("second",), "second": ("first",)}
    assert list(selected.scratch_path.iterdir()) == []


def test_direct_demand_captures_analytics_once_and_preserves_explicit_override(
    monkeypatch, tmp_path
):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from corpus_structure import analytics
    from corpus_structure.orchestrate import data_operations, execution_host
    from corpus_structure.semantic import data_operation_service

    @contextmanager
    def opened(value):
        yield value

    ambient = AnalyticsSettings(threads=2, scratch_path=tmp_path / "ambient")
    override = AnalyticsSettings(threads=4, scratch_path=tmp_path / "override")
    monkeypatch.setattr(analytics, "_settings", ambient)
    prepared = SimpleNamespace()
    basis = SimpleNamespace(
        prepared=prepared,
        runtime=None,
        sources=None,
        runtime_locations=None,
        schema=None,
        declarations=None,
        captured_contracts=(),
    )
    host = SimpleNamespace(
        run=lambda _: opened("run-token"), acquire_basis=lambda *args, **kwargs: basis
    )
    monkeypatch.setattr(execution_host, "execution_host_scope", lambda: opened(host))
    monkeypatch.setattr(
        data_operation_service,
        "read_data_demand",
        lambda *args, **kwargs: {
            "project_id": "project",
            "release_id": "release",
            "runtime_id": "runtime",
        },
    )
    captured = []

    def executor(*args, **kwargs):
        captured.append(kwargs["analytics_settings"])
        return SimpleNamespace(run=lambda *args, **kwargs: "completed")

    monkeypatch.setattr(data_operations, "NativeDemandExecutor", executor)
    engine = SimpleNamespace(begin=lambda: opened(None))
    assert data_operation_service.execute_data_demand(engine, "demand") == "completed"
    assert (
        data_operation_service.execute_data_demand(engine, "demand", analytics_settings=override)
        == "completed"
    )
    assert captured[0] is ambient and captured[1] is override
