"""Owned preparation lifetimes preserve fresh admission and mutable-value isolation."""

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    CPUExecutionScope,
    OwnedByteBudget,
)
from corpus_structure.semantic.execution_preparation import (
    RegionalPreparation,
    VerifiedExecutionPreparation,
    prepare_execution,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


def test_only_full_loader_creates_execution_preparation_and_scope_cannot_escape(monkeypatch):
    prepared = SimpleNamespace(release_id="release")
    calls = []
    monkeypatch.setattr(
        "corpus_structure.semantic.releases.load_release",
        lambda conn, release: calls.append((conn, release)) or prepared,
    )
    with pytest.raises(ValueError, match="full release verification"):
        VerifiedExecutionPreparation(prepared, _authority=None)
    policy = CharacterizationExecutionPolicy(workers=1, cpu_native_threads=2)
    with prepare_execution("connection", "release", policy=policy) as execution:
        assert execution.policy is policy
        assert execution.cpu.policy is execution.providers.policy is policy
        assert execution.require_release("release") is prepared
        with pytest.raises(ValueError, match="another release"):
            execution.require_release("other")
    with pytest.raises(ValueError, match="closed"):
        execution.require_release("release")
    assert calls == [("connection", "release")]


def test_standalone_scopes_use_the_same_explicit_policy():
    from corpus_structure.methods.characterization_resources import provider_scope
    from corpus_structure.orchestrate.ready import owned_source_execution, source_admission

    prepared = SimpleNamespace(release_id="release")
    policy = CharacterizationExecutionPolicy(max_claims=1, max_active_stage_runs=1)
    with owned_source_execution(prepared, policy=policy) as execution:
        assert execution.policy is execution.cpu.policy is execution.providers.policy is policy
        owner = source_admission(execution)
        claim = owner.try_take("claim")
        assert claim is not None and owner.try_take("claim") is None
        assert execution.cpu.budget.used_bytes == policy.max_reply_bytes
        claim.release()
        assert execution.cpu.budget.used_bytes == 0
    reader = SimpleNamespace(prepared=prepared)
    unit = SimpleNamespace(run=SimpleNamespace(reader=reader))
    with provider_scope((unit,), policy=policy) as (cpu, providers):
        assert cpu is not None and providers is not None
        assert cpu.policy is providers.policy is policy


def test_standalone_source_view_unit_uses_bounded_inputs_and_release_affinity(monkeypatch):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.orchestrate.ready import owned_source_execution
    from corpus_structure.orchestrate.semantic import _unit
    from corpus_structure.semantic.operations import BoundReader

    prepared = SimpleNamespace(release_id="release")
    reference = SourceViewRef(
        11,
        "source",
        1,
        ProductReference(7, "native", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.source_views.load_source_view",
        lambda *args, **kwargs: pytest.fail("metadata-only unit construction hydrated source"),
    )
    with owned_source_execution(prepared) as execution:
        assert execution.require_release("release") is prepared
        with pytest.raises(ValueError, match="another release"):
            execution.require_release("other")
        with RegionalPreparation(execution) as regional:
            reader = BoundReader(
                cast(Any, None),
                1,
                cast(Any, prepared),
                analysis=False,
                regional_preparation=regional,
            )
            monkeypatch.setattr(reader, "source_view_ref", lambda identity: reference)
            monkeypatch.setattr(reader, "source_views", lambda: (reference,))
            unit = _unit(
                None, SimpleNamespace(reader=reader), UnitRef(TaskUnitType.SOURCE_VIEW, 11)
            )
            assert unit.source_view_id == 11 and unit.document_id == 1
            assert execution.cpu.budget.used_bytes == 0
        assert execution.cpu.budget.used_bytes == 0
    with pytest.raises(ValueError, match="closed"):
        execution.require_release("release")


def test_regional_source_hydrates_once_but_each_reader_owns_mutable_working_values(monkeypatch):
    prepared: Any = SimpleNamespace(release_id="release")
    cpu = CPUExecutionScope(prepared)
    execution = SimpleNamespace(cpu=cpu, require_release=lambda identity: prepared)
    reference = SourceViewRef(
        11,
        "source",
        1,
        ProductReference(7, "native", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    source = PreparedSourceView(
        reference, "X", ({"start": 0, "end": 1},), ({"self_ref": "#/texts/0"},), (), {"ok": True}
    )
    calls = []
    monkeypatch.setattr(
        "corpus_structure.semantic.analysis_contracts.prepare_text_policy", lambda prepared: None
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.source_views.load_source_view",
        lambda conn, *args, **kwargs: calls.append(conn) or source,
    )
    with RegionalPreparation(execution) as regional:
        first = regional.source_view("one", reference, analysis=True, prepared=prepared)
        first.items[0]["self_ref"] = "mutated"
        second = regional.source_view("two", reference, analysis=True, prepared=prepared)
        assert second.items[0]["self_ref"] == "#/texts/0"
        assert first is not second
        assert cpu.budget.used_bytes > 0
    assert cpu.budget.used_bytes == 0
    with RegionalPreparation(execution) as regional:
        regional.source_view("three", reference, analysis=True, prepared=prepared)
    assert calls == ["one", "three"]
    cpu.close()


def test_protected_layer_reuse_still_admits_each_current_run(monkeypatch):
    from corpus_structure.semantic.characterization import LayerReport

    prepared: Any = SimpleNamespace(release_id="release")
    cpu = CPUExecutionScope(prepared)
    report = LayerReport(b'{"value":[]}')
    pin = report.reference(4)
    calls = []
    monkeypatch.setattr(
        "corpus_structure.semantic.characterization_store.read_layer",
        lambda conn, ref, **kwargs: calls.append(("body", kwargs["run_id"])) or report,
    )

    def admit(conn, ref, *, run_id, max_bytes):
        calls.append(("admission", run_id))
        if run_id == 3:
            raise ValueError("current run refused")

    monkeypatch.setattr(
        "corpus_structure.semantic.characterization_store.read_layer_manifest", admit
    )
    with RegionalPreparation(SimpleNamespace(cpu=cpu)) as regional:
        assert regional.layer(None, pin, run_id=1) is report
        report.payload["value"].append("mutation")
        assert regional.layer(None, pin, run_id=2).payload == {"value": []}
        with pytest.raises(ValueError, match="current run refused"):
            regional.layer(None, pin, run_id=3)
    assert calls == [("body", 1), ("admission", 2), ("admission", 3)]
    assert cpu.budget.used_bytes == 0
    cpu.close()


def _primary_execution(*, page_bytes=1024, owned_bytes=4096):
    policy = CharacterizationExecutionPolicy(
        max_packet_bytes=page_bytes,
        max_reply_bytes=1,
        max_native_request_bytes=1,
        max_native_reply_bytes=1,
        max_owned_bytes=owned_bytes,
    )
    return SimpleNamespace(cpu=SimpleNamespace(policy=policy, budget=OwnedByteBudget(owned_bytes)))


def test_bound_primary_reads_charge_once_and_authorize_each_current_run(monkeypatch):
    from corpus_structure.semantic import _operation_calls
    from corpus_structure.semantic.characterization import LayerReport
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operations import BoundReader

    report = LayerReport(
        canonical_bytes(
            dict(
                source_scope={"source_view_ids": [9]},
                coverage=[
                    dict(
                        family="formal.syntax",
                        outcome="complete",
                        availability="available",
                        examined=[dict(projection="projection", start=0, end=1)],
                    )
                ],
            )
        )
    )
    pin = report.reference(7)
    execution = _primary_execution()
    budget = execution.cpu.budget
    connection = SimpleNamespace(begin_nested=nullcontext)
    admissions = []

    def read(conn, **kwargs):
        assert conn is connection
        assert kwargs["references"] == [pin.values()]
        assert kwargs["source_view_id"] == 9
        assert kwargs["max_bytes"] == 1024
        # Page credit exists before the native operation materializes its response.
        assert budget.used_bytes == 1024 + (len(report.content) if admissions else 0)
        admissions.append(int(kwargs["run_id"]))
        if kwargs["run_id"] == 3:
            raise ValueError("current primary run refused")
        return {"layers": [{"reference": pin.values(), "payload": report.payload}]}

    monkeypatch.setattr(_operation_calls, "read_primary_characterization", read)
    with RegionalPreparation(execution) as regional:
        reader = BoundReader(
            cast(Any, connection), 1, cast(Any, SimpleNamespace()), regional_preparation=regional
        )
        reader.characterization_selection = (pin, pin)
        source = SimpleNamespace(
            ref=SimpleNamespace(id=9, projection_digest="projection"),
            text="x",
            pieces=({"kind": "native_text", "item_ref": "#/texts/0", "start": 0, "end": 1},),
        )
        monkeypatch.setattr(reader, "source_view", lambda identity: source)
        first = reader.primary_characterization(9, families=("formal.syntax",))
        assert set(first) == {pin}
        assert budget.used_bytes == len(report.content)
        first[pin].payload["coverage"].clear()
        reader.run_id = 2
        second = reader.primary_characterization(9, families=("formal.syntax",))
        assert second[pin] is first[pin]
        assert second[pin].payload["coverage"][0]["family"] == "formal.syntax"
        assert budget.used_bytes == len(report.content)
        reader.run_id = 3
        with pytest.raises(ValueError, match="current primary run refused"):
            reader.primary_characterization(9, families=("formal.syntax",))
        assert budget.used_bytes == len(report.content)
    assert admissions == [1, 2, 3]
    assert budget.used_bytes == 0
    with pytest.raises(ValueError, match="closed"):
        regional.primary_layers(connection, 1, 9, (pin,))


def test_primary_page_admission_refuses_before_native_read(monkeypatch):
    from corpus_structure.semantic import _operation_calls

    def unexpected(*args, **kwargs):
        pytest.fail("native layer hydration ran before page admission")

    monkeypatch.setattr(_operation_calls, "read_primary_characterization", unexpected)
    execution = _primary_execution(owned_bytes=1025)
    execution.cpu.budget.reserve(2)
    with RegionalPreparation(execution) as regional, pytest.raises(CapacityExceeded):
        regional.primary_layers(None, 1, 9, ())
    assert execution.cpu.budget.used_bytes == 2
    execution.cpu.budget.release(2)
    assert execution.cpu.budget.used_bytes == 0


def test_primary_pages_charge_cumulative_bodies_and_release_on_failure(monkeypatch):
    import psycopg
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic import _operation_calls
    from corpus_structure.semantic.characterization import LayerReport
    from corpus_structure.semantic.identity import canonical_bytes

    reports = [
        LayerReport(canonical_bytes({"value": "x" * 80, "index": index})) for index in range(3)
    ]
    rows = {report.reference(index + 1): report for index, report in enumerate(reports)}
    owned = 512 + sum(len(report.content) for report in reports[:2])
    execution = _primary_execution(page_bytes=512, owned_bytes=owned)
    connection = SimpleNamespace(begin_nested=nullcontext)
    admitted = []

    def read(conn, **kwargs):
        assert kwargs["max_bytes"] == 512
        assert execution.cpu.budget.used_bytes >= 512
        pins = [ProductReference(**value) for value in kwargs["references"]]
        body = {
            "layers": [{"reference": pin.values(), "payload": rows[pin].payload} for pin in pins]
        }
        if len(canonical_bytes(body)) > kwargs["max_bytes"]:
            raise DBAPIError(None, None, psycopg.errors.ProgramLimitExceeded("page too large"))
        admitted.extend(pins)
        return body

    monkeypatch.setattr(_operation_calls, "read_primary_characterization", read)
    with RegionalPreparation(execution) as regional:
        with pytest.raises(CapacityExceeded):
            regional.primary_layers(connection, 1, 9, tuple(rows))
        # Complete selection was attempted, never replaced with a successful prefix.
        assert admitted == list(rows)
        assert list(regional._layers) == list(rows)[:2]
        assert execution.cpu.budget.used_bytes == owned - 512
    assert execution.cpu.budget.used_bytes == 0


def test_regional_layer_cache_rejects_mismatched_pin_and_reuses_exact_bytes():
    from corpus_structure.semantic.characterization import LayerReport

    execution = _primary_execution()
    report, wrong = LayerReport(b'{"value":1}'), LayerReport(b'{"value":2}')
    pin = report.reference(7)
    with RegionalPreparation(execution) as regional:
        assert regional.retain_native_layer(pin, report) is report
        assert regional.retain_native_layer(pin, LayerReport(report.content)) is report
        assert execution.cpu.budget.used_bytes == len(report.content)
        with pytest.raises(ValueError, match="exact published pin"):
            regional.retain_native_layer(pin, wrong)
        assert execution.cpu.budget.used_bytes == len(report.content)
    assert execution.cpu.budget.used_bytes == 0


def test_source_payload_is_not_loaded_until_shared_read_window_is_admitted(monkeypatch):
    from corpus_structure.semantic.identity import canonical_bytes

    prepared = SimpleNamespace(release_id="release")
    execution = _primary_execution(page_bytes=1024, owned_bytes=2048)
    execution.require_release = lambda identity: prepared
    reference = SourceViewRef(
        11,
        "source",
        1,
        ProductReference(7, "native", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    source = PreparedSourceView(reference, "X", (), (), (), {"ok": True})
    budget = execution.cpu.budget
    loads = []

    def load(*args, **kwargs):
        loads.append((budget.used_bytes, kwargs["read_budget"].max_bytes))
        return source

    monkeypatch.setattr("corpus_structure.semantic.source_views.load_source_view", load)
    with RegionalPreparation(execution) as regional:
        budget.reserve(1500)  # Another live CPU/provider/region owns this credit.
        work = regional.read_work(
            lambda: regional.source_view(None, reference, analysis=False, prepared=prepared)
        )
        assert work.try_submit() is None
        assert loads == []
        assert budget.used_bytes == 1500
        budget.release(1500)
        handle = work.try_submit()
        assert handle is not None
        assert handle.collect().text == "X"
        assert loads == [(1024, 1024)]
        expected = canonical_bytes(
            dict(
                text="X",
                pieces=(),
                items=(),
                ancestors=(),
                health={"ok": True},
                integrated_context=source.integrated_context,
            )
        )
        assert budget.used_bytes == len(expected)
        assert handle.retire()
    assert budget.used_bytes == 0


def test_layer_read_transfers_admitted_bytes_and_preserves_cache_authorization(monkeypatch):
    from corpus_structure.semantic.characterization import LayerReport

    execution = _primary_execution(page_bytes=1024, owned_bytes=2048)
    budget = execution.cpu.budget
    report = LayerReport(b'{"value":[]}')
    pin = report.reference(4)
    reads = []

    def body(conn, ref, *, run_id, max_bytes):
        reads.append(("body", budget.used_bytes, max_bytes, run_id))
        assert max_bytes == 2048
        return report

    def manifest(conn, ref, *, run_id, max_bytes):
        reads.append(("manifest", budget.used_bytes, max_bytes, run_id))
        raise ValueError("current run refused")

    monkeypatch.setattr("corpus_structure.semantic.characterization_store.read_layer", body)
    monkeypatch.setattr(
        "corpus_structure.semantic.characterization_store.read_layer_manifest", manifest
    )
    with RegionalPreparation(execution) as regional:
        budget.reserve(1)
        work = regional.read_work(lambda: regional.layer(None, pin, run_id=1))
        assert work.try_submit() is None
        assert reads == []
        budget.release(1)
        handle = work.try_submit()
        assert handle is not None
        assert handle.collect() is report
        assert budget.used_bytes == len(report.content)
        with pytest.raises(ValueError, match="current run refused"):
            regional.layer(None, pin, run_id=2)
        assert reads[0] == ("body", 2048, 2048, 1)
        assert reads[1] == ("manifest", 2048, 2048 - len(report.content), 2)
        assert budget.used_bytes == len(report.content)
    assert budget.used_bytes == 0
