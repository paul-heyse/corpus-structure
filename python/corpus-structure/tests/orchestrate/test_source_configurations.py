"""The source runner has one effective configuration per method, not per step."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import _source_configurations, run_source_methods
from corpus_structure.semantic.operations import OperationBinding, OperationConflict


class Configuration(BaseModel):
    value: int = 1


def registry():
    method = SimpleNamespace(name="source.example", version="1", Config=Configuration)
    return MethodRegistry(
        (method,),
        MethodsFile(
            configs={
                "source.example": {
                    "default": {"value": 1},
                    "alias": {"value": 1},
                    "other": {"value": 2},
                }
            }
        ),
    )


def graph(*names):
    return Graph(((Stage.LINK, tuple(Step(name) for name in names)),))


def test_conflicting_step_defaults_refuse_before_database_work(monkeypatch):
    from corpus_structure.semantic import contracts

    monkeypatch.setattr(contracts, "require_bound_operation", lambda *args: None)
    monkeypatch.setattr(contracts, "execution_payload", lambda prepared: None)

    # This engine cannot perform database work. A late refusal would fail here.
    class NoDatabase:
        def connect(self):
            raise AssertionError("configuration conflict reached the database")

        def begin(self):
            raise AssertionError("configuration conflict created a run")

    created = []
    with pytest.raises(OperationConflict, match=r"one effective configuration.*source\.example"):
        run_source_methods(
            NoDatabase(),
            project_id="control",
            prepared=SimpleNamespace(release_id="release:control"),
            binding=OperationBinding("release:control", "input:control", 0, b"{}"),
            registry=registry(),
            graph=graph("source.example/default", "source.example/other"),
            method_settings=MethodSettings(data_dir=Path("."), model_cache=Path(".")),
            on_created=created.append,
        )
    assert created == []


def test_equivalent_named_aliases_share_effective_configuration():
    selected = _source_configurations(
        registry(), graph("source.example", "source.example/alias"), {}
    )
    assert tuple(selected) == ("source.example",)
    assert selected["source.example"].params == {"value": 1}
    assert selected["source.example"].name == "default"


def test_override_makes_different_step_defaults_equivalent():
    selected = _source_configurations(
        registry(),
        graph("source.example/default", "source.example/other"),
        {"source.example": "alias"},
    )
    assert selected["source.example"].name == "alias"
    assert selected["source.example"].params == {"value": 1}


@pytest.mark.parametrize("eligible,selected", [(True, True), (False, True), (True, False)])
def test_source_unit_uses_metadata_without_hydrating_the_source(eligible, selected):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.orchestrate.semantic import _unit

    source = SimpleNamespace(id=11, document_id=7, analysis_eligible=eligible)
    lookups = []

    def reference(identity):
        lookups.append(identity)
        return source

    def hydrate(*args):
        pytest.fail("unit identity hydrated source payload")

    reader = SimpleNamespace(
        source_view_ref=reference,
        source_views=lambda: (source,) if selected else (),
        source_view=hydrate,
    )
    unit = _unit(None, SimpleNamespace(reader=reader), UnitRef(TaskUnitType.SOURCE_VIEW, 11))
    assert unit.document_id == 7 and unit.source_view_id == 11
    assert unit.context_only == (not eligible or not selected)
    assert lookups == [11]


def test_claim_source_prewarm_waits_inside_fence_and_closes_snapshot_before_retry(monkeypatch):
    from contextlib import contextmanager

    from corpus_structure.orchestrate.semantic import _claim_source_work
    from corpus_structure.semantic.execution_preparation import (
        RegionalPreparation,
        _ReadCapacityUnavailable,
    )

    events = []
    opened = False
    available = False
    source = SimpleNamespace(id=11)
    region = RegionalPreparation(SimpleNamespace())
    prepared = SimpleNamespace(release_id="release")

    @contextmanager
    def snapshot(engine):
        nonlocal opened
        assert engine == "engine"
        opened = True
        events.append("snapshot-open")
        try:
            yield "connection"
        finally:
            opened = False
            events.append("snapshot-closed")

    def selected(conn, run_id, *, source_view_id):
        assert opened and (conn, run_id, source_view_id) == ("connection", 7, 11)
        return (source,)

    def hydrate(conn, reference, *, analysis, prepared):
        assert opened and conn == "connection" and reference is source and analysis is False
        events.append("hydrate-admission")
        if not available:
            raise _ReadCapacityUnavailable("shared bytes busy")

    def active():
        assert not opened
        events.append("claim-fence")

    monkeypatch.setattr("corpus_structure.semantic.query.read_snapshot", snapshot)
    monkeypatch.setattr("corpus_structure.semantic.source_views.selected_source_views", selected)
    monkeypatch.setattr(region, "source_view", hydrate)
    task = SimpleNamespace(unit_type="source_view", unit_id=11)
    work = _claim_source_work("engine", 7, prepared, (task,), region, active)
    assert work.try_submit() is None
    assert not opened
    available = True
    handle = work.try_submit()
    assert handle is not None and handle.collect() is None and handle.retire()
    assert not opened
    assert events == ["claim-fence", "snapshot-open", "hydrate-admission", "snapshot-closed"] * 2


def test_claim_source_prewarm_rejects_stale_claim_before_source_read(monkeypatch):
    from corpus_structure.orchestrate.semantic import _claim_source_work
    from corpus_structure.semantic.execution_preparation import RegionalPreparation

    region = RegionalPreparation(SimpleNamespace())
    monkeypatch.setattr(
        "corpus_structure.semantic.query.read_snapshot",
        lambda engine: pytest.fail("stale claim opened a source snapshot"),
    )

    def stale():
        raise OperationConflict("native claim was lost")

    work = _claim_source_work(
        "engine", 7, None, (SimpleNamespace(unit_type="source_view", unit_id=11),), region, stale
    )
    with pytest.raises(OperationConflict, match="native claim was lost"):
        work.try_submit()
