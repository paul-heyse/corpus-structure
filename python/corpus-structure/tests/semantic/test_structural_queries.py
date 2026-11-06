"""Named structural queries retain their own authority and use bounded shared inspection."""

import pytest

from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve.queries import (
    GENERIC,
    StructuralAnswer,
    StructuralParams,
    StructuralProducts,
)
from corpus_structure.serve.registry import build_registry


def test_structural_questions_are_registered_with_typed_results():
    registry = build_registry(GENERIC)
    names = {
        "structural_definitions",
        "structural_applicability",
        "structural_comparisons",
        "structural_dossiers",
    }
    assert names <= registry.keys()
    kinds = set()
    for name in names:
        query = registry[name]
        assert isinstance(query, StructuralProducts)
        kinds.add(query.kind)
        assert query.result is StructuralAnswer and query.params is StructuralParams
        assert query.scope(None, StructuralParams()).kind == "run"
        assert "StructuralProductReport" in query.result.model_json_schema()["$defs"]
    assert kinds == {
        "definition_components",
        "definition_applicability",
        "qualified_comparison",
        "dossier",
    }
    definitions = registry["structural_definitions"]
    applicability = registry["structural_applicability"]
    assert isinstance(definitions, StructuralProducts)
    assert isinstance(applicability, StructuralProducts)
    assert definitions.kind == "definition_components"
    assert applicability.kind == "definition_applicability"


@pytest.mark.parametrize("position", [True, -1, "", "-1", "1.0", "\u0661"])
def test_structural_cursor_cannot_alias_a_different_position(position):
    query = build_registry(GENERIC)["structural_definitions"]
    assert isinstance(query, StructuralProducts)
    with pytest.raises(InvalidContinuation):
        query.validate_position(position)
