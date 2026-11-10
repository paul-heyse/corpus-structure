"""The source runner has one effective configuration per method, not per step."""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

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
            method_settings=None,
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
