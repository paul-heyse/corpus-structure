"""Owned preparation lifetimes preserve fresh admission and mutable-value isolation."""

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.cpu_execution import CPUExecutionScope
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
    with prepare_execution("connection", "release") as execution:
        assert execution.require_release("release") is prepared
        with pytest.raises(ValueError, match="another release"):
            execution.require_release("other")
    with pytest.raises(ValueError, match="closed"):
        execution.require_release("release")
    assert calls == [("connection", "release")]


def test_public_boundary_forwards_only_request_arguments_and_closes_owned_scope(monkeypatch):
    import corpus_structure.orchestrate.characterization as owner

    @contextmanager
    def snapshot(engine):
        yield "connection"

    captured = []
    prepared = SimpleNamespace(release_id="release")
    monkeypatch.setattr("corpus_structure.semantic.query.read_snapshot", snapshot)
    monkeypatch.setattr("corpus_structure.semantic.releases.load_release", lambda *args: prepared)
    monkeypatch.setattr(
        owner,
        "_execute_characterization_demand",
        lambda execution, **kwargs: captured.append((execution, kwargs)) or "result",
    )
    request: Any = SimpleNamespace(release_id="release")
    assert owner.execute_characterization_demand("engine", request, "settings") == "result"
    execution, arguments = captured[0]
    assert set(arguments) == {
        "engine",
        "request",
        "method_settings",
        "preparation_cache",
        "registry",
        "on_created",
    }
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

    def admit(conn, ref, *, run_id):
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
