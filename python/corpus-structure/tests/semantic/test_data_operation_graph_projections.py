"""Independent interpretation, completeness and selected-graph expectations."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_model import MODEL_VERSION, read_effective_data_operations
from semantic.data_operation_declaration_support import model, operation


def test_current_model_archives_exact_interpretation_and_refuses_missing_projection():
    compiled = model(operation("op:alone"))
    assert compiled.version == MODEL_VERSION
    assert [p.name for p in compiled.graph_projections] == [
        "semantic-reference",
        "potential-producers",
        "selected-dependencies",
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
