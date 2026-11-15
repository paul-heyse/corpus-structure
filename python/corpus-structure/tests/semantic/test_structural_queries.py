"""Structural public selection refuses retired run registration and ambiguous cursors."""

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve import structural_products as reader
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry


def test_structural_questions_require_actual_selected_contracts():
    registry = build_registry(GENERIC)
    assert (
        not {
            "structural_definitions",
            "structural_applicability",
            "structural_comparisons",
            "structural_dossiers",
            "source_decision_journey",
            "dossier_representation",
        }
        & registry.keys()
    )
    root = dict(
        product_id="native:actual",
        member_id=None,
        use_id="use:actual",
        derivation_id="episode:actual",
    )
    request = reader.SelectedStructuralRequest.model_validate(
        dict(demand_id="d", project_id="p", roots=[root])
    )
    assert request.roots[0].model_dump() == root
    assert "SelectedStructuralRoot" in request.model_json_schema()["$defs"]
    for old in (dict(run_id=1), dict(task_id=1), dict(cut_id=1)):
        with pytest.raises(ValidationError):
            reader.SelectedStructuralRequest.model_validate(
                dict(demand_id="d", project_id="p", roots=[root], **old)
            )


@pytest.mark.parametrize("position", [True, -1, "", "-1", "1.0", "\u0661"])
def test_structural_cursor_cannot_alias_a_different_position(monkeypatch, position):
    def refuse(*args, **kwargs):
        raise AssertionError("invalid continuation reached native acquisition")

    monkeypatch.setattr(reader, "structural_scope", refuse)
    with pytest.raises((ValidationError, InvalidContinuation, ValueError)):
        request = reader.SelectedDossierRequest.model_validate(
            dict(
                demand_id="d",
                project_id="p",
                root=dict(
                    product_id="native:actual",
                    member_id=None,
                    use_id="use:actual",
                    derivation_id="episode:actual",
                ),
                cursor=position,
            )
        )
        reader.inspect_selected_dossier(None, request)
