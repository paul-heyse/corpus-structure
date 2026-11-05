"""Independent expectations distinguish group dimensions and missing membership."""

import pytest

from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
    StructuralReferenceCase,
    score_structural_reference,
)
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)


def frame():
    source = ExternalSourceRef(
        project_id="original",
        run_id=1,
        cut_id=2,
        release_id="release:old",
        result_revision=3,
        source_view_id=4,
        native_task_id=5,
        native_product_key="pdf",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    return StructuralEvaluationFrame(
        inputs=StructuralInput(
            question="definition in context",
            scope="statistics",
            inventory_id="inventory",
            policy_id="policy",
            sources=(source,),
            passages=(
                StructuralPassage(
                    passage_id="p1",
                    source_ref=source.identity,
                    start=0,
                    end=4,
                    text="mean",
                    scope="population",
                ),
            ),
            dependencies=("inventory",),
        ),
        operation="definition_applicability",
        direction="source_first",
        rubric_version="1",
        rubric_text="Inspect whether the source defines population mean, not an example.",
    )


def reference(frozen, **changes):
    values = dict(
        case_id="c1",
        facet="applicability",
        path=("definition", "readings", 0, "outcome"),
        expected="applicable_definition",
        source_passages=("p1",),
        judgment="supported",
        explanation="Independent source reading.",
    )
    values.update(changes)
    return StructuralAuthoredReference(
        frame_digest=frozen.identity, cases=(StructuralReferenceCase.model_validate(values),)
    )


def product(frozen, outcome="mention"):
    return dict(
        kind="definition_applicability",
        inputs=frozen.inputs.model_dump(mode="json"),
        definition=dict(
            usage_id="p1",
            candidate_list_id="list",
            eligible_targets=["p1"],
            candidate_targets=["p1"],
            readings=[
                dict(target_id="p1", outcome=outcome, evidence=["p1"], reason="Evidence retained.")
            ],
        ),
    )


def test_wrong_relationship_and_missing_member_are_not_supported():
    frozen = frame()
    result = score_structural_reference(frozen, reference(frozen), product(frozen))
    assert result["cases"][0]["outcome"] == "mismatch"
    assert result["publication_authority"] is False
    missing = score_structural_reference(
        frozen, reference(frozen, path=("members", 0)), product(frozen)
    )
    assert missing["cases"][0]["found"] is False
    assert missing["cases"][0]["outcome"] == "mismatch"


def test_null_is_distinct_from_missing_and_unassessed_stays_unassessed():
    frozen = frame()
    null = reference(frozen, path=("inputs", "passages", 0, "parent"), expected=None)
    assert (
        score_structural_reference(frozen, null, product(frozen))["cases"][0]["outcome"] == "match"
    )
    assert (
        score_structural_reference(
            frozen, reference(frozen, path=("missing",), expected=None), product(frozen)
        )["cases"][0]["outcome"]
        == "mismatch"
    )
    unassessed = reference(frozen, judgment="unassessed")
    assert (
        score_structural_reference(frozen, unassessed, product(frozen))["cases"][0]["outcome"]
        == "unassessed"
    )


def test_changed_frame_foreign_source_and_duplicate_cases_refuse():
    frozen = frame()
    with pytest.raises(ValueError, match="frozen group"):
        score_structural_reference(
            frozen, reference(frozen).model_copy(update={"frame_digest": "f" * 64}), {}
        )
    with pytest.raises(ValueError, match="outside frozen"):
        score_structural_reference(
            frozen, reference(frozen, source_passages=("foreign",)), product(frozen)
        )
    case = reference(frozen).cases[0]
    with pytest.raises(ValueError, match="repeats"):
        StructuralAuthoredReference(frame_digest=frozen.identity, cases=(case, case))


def test_source_first_frame_cannot_select_outputs():
    with pytest.raises(ValueError, match="output-first"):
        StructuralEvaluationFrame.model_validate(
            dict(frame().model_dump(), product_ids=["produced"])
        )
