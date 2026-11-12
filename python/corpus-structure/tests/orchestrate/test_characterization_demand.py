"""Explicit document selection freezes analytic inputs independently of provenance."""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from corpus_structure.core.vocab import Stage
from corpus_structure.methods.annotation_rules import AnnotationRule
from corpus_structure.orchestrate.characterization import (
    EnrichedDocumentDemand,
    bind_characterization_views,
)
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.product_reference import ProductReference


class ConsumerConfig(BaseModel):
    characterization_layers: tuple[dict, ...] = ()


def test_binding_uses_active_analysis_and_preserves_complete_view_closure():
    old = ProductReference(1, "old", "a" * 64)
    new = ProductReference(2, "new", "b" * 64)
    method = SimpleNamespace(name="test.consumer", version="1", Config=ConsumerConfig)
    registry = MethodRegistry((method,), MethodsFile(configs={method.name: {"default": {}}}))
    view = SimpleNamespace(
        payload=dict(
            profile="selected_layers",
            layers=[old.values(), new.values()],
            active_layers=[new.values()],
        )
    )
    bound = bind_characterization_views(registry, [view], {old: object(), new: object()})
    selected = bound.overlay(method.name, "default")
    assert isinstance(selected, ConsumerConfig)
    assert selected.characterization_layers == (new.values(),)
    with pytest.raises(ValueError, match="closures"):
        bind_characterization_views(registry, [view], {new: object()})


def test_source_capture_cannot_claim_selected_analysis():
    base = ProductReference(1, "source", "a" * 64)
    with pytest.raises(ValueError, match="source-only"):
        EnrichedDocumentDemand(base, {}, (base,), source_only=True)


def test_analytical_preparation_preserves_only_selected_exact_named_declarations():
    from corpus_structure.orchestrate.source_operation import _consumer_characterization_options

    class Config(BaseModel):
        annotation_rules: tuple[AnnotationRule, ...] = ()

    rule = dict(
        rule="term",
        variant="one",
        mechanism="token",
        pattern=[{"TEXT": "X"}],
        bindings={"name": {"node": "match"}},
    )
    conflict = {**rule, "pattern": [{"TEXT": "Y"}]}
    methods = tuple(
        SimpleNamespace(name=name, version="1", Config=Config) for name in ("test.one", "test.two")
    )
    registry = MethodRegistry(
        methods,
        MethodsFile(
            configs={
                "test.one": {
                    "default": {"annotation_rules": [rule]},
                    "unselected": {"annotation_rules": [conflict]},
                },
                "test.two": {"default": {"annotation_rules": [rule]}},
            }
        ),
    )
    graph = Graph(((Stage.EXTRACT, (Step("test.one"), Step("test.two"))),))
    selected = _consumer_characterization_options(registry, graph, {})
    assert selected["text.constructions"]["annotation_rules"] == [
        AnnotationRule.model_validate(rule).model_dump(mode="json")
    ]
    with pytest.raises(ValueError, match="conflicting named rule term/one"):
        _consumer_characterization_options(registry, graph, {"test.one": "unselected"})
