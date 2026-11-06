"""Independent expectations distinguish group dimensions and missing membership."""

import pytest

from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
    StructuralReferenceCase,
    StructuralSourceGroup,
    StructuralSourceOpportunity,
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
        partition="development",
        source_groups=(
            StructuralSourceGroup(source_ref=source.identity, origin_group="source-family"),
        ),
        opportunities=(
            StructuralSourceOpportunity(
                opportunity_id="term", passage_id="p1", facet="role", source_state="stated"
            ),
        ),
        inspected_scope="source-passage",
        operation="definition_components",
        direction="source_first",
        rubric_version="1",
        rubric_text="Inspect whether the source defines population mean, not an example.",
    )


def reference(frozen, **changes):
    values = dict(
        case_id="c1",
        facet="applicability",
        path=("definition_components", "stages", 0, "outcome"),
        expected="succeeded",
        source_passages=("p1",),
        judgment="supported",
        explanation="Independent source reading.",
    )
    values.update(changes)
    return StructuralAuthoredReference(
        frame_digest=frozen.identity, cases=(StructuralReferenceCase.model_validate(values),)
    )


def product(frozen, outcome="empty"):
    return dict(
        version="structural-product-3",
        kind="definition_components",
        inputs=frozen.inputs.model_dump(mode="json"),
        definition_components=dict(
            components=[],
            stages=[
                dict(
                    passage_id="p1",
                    operation="located_extraction",
                    outcome=outcome,
                    reason="Actual extraction outcome.",
                )
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


def test_current_source_population_and_legacy_refusal():
    from corpus_structure.evaluate.structural_assessment import decode_structural_frame

    original = frame()
    values = original.model_dump(mode="json")
    assert decode_structural_frame(values).protocol == "structural-evaluation-frame-3"
    for protocol in ("structural-evaluation-frame-1", "structural-evaluation-frame-2"):
        with pytest.raises(ValueError):
            decode_structural_frame(dict(values, protocol=protocol))
    with pytest.raises(ValueError, match="exposed sources"):
        decode_structural_frame(
            dict(values, partition="final_assessment", exposure_history=["feedback"])
        )
    with pytest.raises(ValueError, match="source group assignment"):
        decode_structural_frame(
            dict(values, source_groups=[dict(source_ref="foreign", origin_group="wrong")])
        )
