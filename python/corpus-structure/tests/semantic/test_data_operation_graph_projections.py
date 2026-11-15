"""Independent interpretation, completeness and selected-graph expectations."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    read_effective_data_operations,
)
from semantic.data_operation_declaration_support import model, operation


def test_current_model_archives_exact_interpretation_and_refuses_missing_projection():
    compiled = model(operation("op:alone"))
    assert compiled.version == MODEL_VERSION
    assert [p.name for p in compiled.graph_projections] == [
        "semantic-reference",
        "potential-producers",
        "selected-dependencies",
        "bound-requests",
        "selected-support",
        "source-hierarchy",
        "assessment",
        "task-assessment",
        "lexical-reference",
        "possible-call",
        "resolved-definition",
        "type-reference",
        "implementation-determinant",
    ]
    restored = read_effective_data_operations(compiled.content)
    assert restored.content == compiled.content
    assert restored.projection_graph("selected-dependencies").node_ids == ("op:alone",)
    with pytest.raises(ValueError, match="interpretation"):
        replace(compiled, graph_projections=()).projection_graph("semantic-reference")
    definitions = list(compiled.graph_projections)
    definitions[0] = replace(definitions[0], relationship_kinds=())
    with pytest.raises(ValueError, match="interpretation"):
        replace(compiled, graph_projections=tuple(definitions)).projection_graph(
            "semantic-reference"
        )


def test_potential_and_selected_projections_keep_roles_and_scope_distinct():
    compiled = model(
        operation("op:left"),
        operation("op:right"),
        operation("op:isolate"),
        operation("op:result", dependencies=["op:left"], potential_dependencies=["op:right"]),
    )
    potential = compiled.projection_graph("potential-producers")
    selected = compiled.projection_graph("selected-dependencies")
    assert potential.closure(("op:result",)) == ("op:left", "op:result", "op:right")
    assert selected.closure(("op:result",)) == ("op:left", "op:result")
    assert "op:isolate" in selected.node_ids
    chosen = compiled.projection_graph(
        "selected-dependencies", selected_dependencies=(("op:result", ("op:right",)),)
    )
    assert [(e.target, e.relation, e.position) for e in chosen.edges] == [
        ("op:left", "operation_dependency", 0),
        ("op:right", "selected_operation_dependency", 0),
    ]
    with pytest.raises(ValueError, match="outside"):
        compiled.projection_graph(
            "selected-dependencies", selected_dependencies=(("op:result", ("op:isolate",)),)
        )


def test_unknown_projection_and_unresolved_endpoints_refuse():
    compiled = model(operation("op:alone"))
    with pytest.raises(ValueError, match="unknown graph"):
        compiled.projection_graph("not-declared")
    with pytest.raises(ValueError, match="unknown selected"):
        compiled.projection_graph("selected-dependencies", selected_dependencies=(("unknown", ()),))


def test_v6_specs_are_interpretations_not_selected_runtime_facts():
    compiled = model(operation("op:alone"))
    support = compiled.projection_definition("selected-support")
    assert support.source_contract == "selected-native-records"
    assert support.snapshot == "native-read-and-trust"
    assert support.completeness == "explicit-examined-universe"
    assert support.identity == "qualified-native-reference"
    assert "scope-boundary" in support.analyses
    assert compiled.projection_definition("source-hierarchy").orientation == "parent-to-child"
    assert (
        compiled.projection_definition("task-assessment").selection
        == "protected-question-and-prediction"
    )
    with pytest.raises(ValueError, match="source acquisition"):
        compiled.projection_graph("selected-support")


def test_v5_compact_archive_read_preserves_exact_bytes_and_headers():
    import json

    from corpus_structure.semantic.data_operation_model import EffectiveIdentity
    from corpus_structure.semantic.identity import canonical_bytes

    compiled = model(operation("op:alone"))
    record = json.loads(compiled.content)
    record["version"] = "data-operation-model-v5"
    record["graph_projections"] = record["graph_projections"][:3]
    for implementation in record["implementation_slices"]:
        implementation.pop("references")
    original = canonical_bytes(record)
    restored = read_effective_data_operations(original)
    assert restored.content == original
    assert all(type(identity) is EffectiveIdentity for identity in restored.identities)
    assert len(restored.graph_projections) == 3
    with pytest.raises(ValueError, match="interpretation"):
        restored.projection_definition("selected-support")


def test_captured_reference_occurrences_are_diagnostic_not_recipe_salts():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from semantic.test_data_operation_compilation import operation_source, python_inputs

    compiled = compile_data_operations(
        python_sources=python_inputs(operation_source(body="return helper(x) + helper(x)"))
    )
    implementation = compiled.implementation_slices[0]
    assert {node.category for node in implementation.nodes} <= set(
        compiled.projection_definition("possible-call").node_kinds
    )
    assert {edge.relation for edge in implementation.edges} == set(
        compiled.projection_definition("implementation-determinant").relationship_kinds
    )
    calls = [
        fact
        for fact in implementation.references
        if fact.relation == "possible_call" and fact.target == "python:example.helper"
    ]
    assert len(calls) == 2
    assert len({fact.location for fact in calls}) == 2
    assert {fact.source for fact in calls} == {"python:example.derive"}
    assert {fact.supplying_owner for fact in calls} == {"example.derive"}
    assert {fact.provenance for fact in calls} == {"closed-source-structural"}
    assert "references" not in implementation.semantic_records()
    stripped = replace(implementation, references=())
    assert stripped.semantic_records() == implementation.semantic_records()
    reopened = read_effective_data_operations(compiled.content)
    assert reopened.implementation_slices[0].references == implementation.references
