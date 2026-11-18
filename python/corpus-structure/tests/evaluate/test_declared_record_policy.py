"""Protected DTO controls; these authored values grant no native authority."""

import json

import pytest
from evaluate.declared_record_policy_support import grade_frame, source
from evaluate.declared_record_policy_test_support import (
    fit_basis as fit_basis,
)
from jsonschema import Draft7Validator

from corpus_structure.evaluate.declared_record_policy import (
    PROTECTED_NAMESPACE,
    DdoRecordGrade,
    DdoRecordGradeEvent,
    DdoRecordGradeFrame,
    DdoRecordReferencePass,
    protected_record_policy_kind_declarations,
)


def validate_changes(frame, **changes):
    return DdoRecordGradeFrame.model_validate({**frame.model_dump(mode="python"), **changes})


def test_grade_preserves_low_scored_events_and_separate_no_output_coverage():
    frame = grade_frame(calibration=True)
    grade = DdoRecordGrade.from_frame(frame)
    assert grade.frame.events[0].final_event is not None
    assert grade.frame.events[0].final_event.final_event_score == -123.5
    assert len(grade.frame.events) == 1
    assert [row.outcome for row in grade.frame.coverage] == ["completed", "no_output"]
    assert grade.frame.prediction_release_id == "release:test"
    assert grade.frame.source_release_id == "release:original"
    assert grade.frame.events[0].features.release_id == "release:test"
    assert DdoRecordGrade.model_validate_json(grade.model_dump_json()) == grade
    assert '"correct":false' in grade.frame_canonical_json
    assert '"records"' not in grade.frame_canonical_json
    for changes in (
        {"frame_digest": "0" * 64},
        {"frame_canonical_json": grade.frame_canonical_json + " "},
    ):
        with pytest.raises(ValueError, match="canonical bytes or digest"):
            DdoRecordGrade.model_validate({**grade.model_dump(mode="python"), **changes})


@pytest.mark.parametrize(
    "field,value",
    (
        ("project_id", "other-project"),
        ("subject", "other-view"),
        ("subject_definition", "different-source-definition"),
        ("original_source", "other-original"),
        ("analyzed_scope_meaning", '["string","other-scope"]'),
    ),
)
def test_grade_event_requires_complete_source_view_context(field, value):
    event = grade_frame().events[0]
    source = event.source.model_copy(update={"subject_definition": "original-source-view"})
    reading = event.reading.model_copy(update={"subject_definition": "original-source-view"})
    values = {**event.model_dump(mode="python"), "source": source, "reading": reading}
    assert DdoRecordGradeEvent.model_validate(values).reading.context == reading.context
    with pytest.raises(ValueError, match="complete source context"):
        DdoRecordGradeEvent.model_validate(
            {**values, "reading": reading.model_copy(update={field: value})}
        )


@pytest.mark.parametrize(
    "change",
    [
        "drop-source",
        "drop-event",
        "duplicate-event",
        "wrong-recipe",
        "missing-origin",
        "unscored-calibration",
    ],
)
def test_frame_refuses_incomplete_or_relabelled_population(change):
    frame = grade_frame()
    changes = {
        "drop-source": {"coverage": frame.coverage[:1]},
        "drop-event": {"events": ()},
        "duplicate-event": {"events": frame.events * 2},
        "wrong-recipe": {"reading_recipe": "different-recipe"},
        "missing-origin": {"origin_groups": frame.origin_groups[:1]},
        "unscored-calibration": {"partition": "final_event_calibration"},
    }[change]
    with pytest.raises(ValueError):
        validate_changes(frame, **changes)


def test_reference_question_and_independence_are_explicit():
    frame = grade_frame()
    a, b, c = frame.reference_passes[:3]
    for passes in (
        (a, a, c),
        (a, b.model_copy(update={"reference": a.reference}), c),
        (a, b, c.model_copy(update={"adjudicates": ("1" * 64, "2" * 64)})),
        (a, b.model_copy(update={"question_digest": "0" * 64}), c),
    ):
        with pytest.raises(ValueError):
            validate_changes(frame, reference_passes=(*passes, *frame.reference_passes[3:]))
    with pytest.raises(ValueError, match="exposed prediction"):
        DdoRecordReferencePass.model_validate(
            {**a.model_dump(mode="python"), "exposed_outputs": (a.reference,)}
        )


def test_protected_declarations_have_one_closed_owner_for_grade_and_fitted():
    declaration = protected_record_policy_kind_declarations()
    kinds = json.loads(declaration.content)["kinds"]
    assert declaration.name == "record-policy/protected-kinds.json"
    assert len({row["id"] for row in kinds}) == len(kinds)
    assert {row["nominal_namespace"] for row in kinds} == {PROTECTED_NAMESPACE}
    assert {row["universe"] for row in kinds} == {"evaluator"}
    by_name = {row["name"]: row["json_schema"] for row in kinds}
    assert {"DdoRecordGrade", "DdoFittedRecordPolicy", "DdoRecordReferencePass"} <= by_name.keys()
    for schema in by_name.values():
        Draft7Validator.check_schema(schema)
    schema = by_name["DdoRecordGrade"]
    Draft7Validator(schema).validate(
        DdoRecordGrade.from_frame(grade_frame()).model_dump(mode="json")
    )
    assert schema["additionalProperties"] is False
    assert (
        schema["definitions"]["DdoRecordGradeFrame"]["properties"]["reference_passes"]["minItems"]
        == 3
    )


def test_separate_actual_predictor_calibration_preserves_compatible_release_lineage(fit_basis):
    from corpus_structure.evaluate.declared_record_policy import fit_declared_record_policy

    first, second, specification = fit_basis
    result = fit_declared_record_policy(first, second, specification)
    assert result.fitted is not None
    assert [row.negative_count for row in result.diagnostics] == [3, 3]
    assert [row.positive_count for row in result.diagnostics] == [3, 3]
    instance = result.fitted.instance
    assert instance.feature.applicability.release_id == "release:test"
    assert second.frame.events[0].features.release_id == "release:compatible"
    assert instance.calibration is not None
    assert instance.calibration.feature_instance_digest == instance.feature.digest
    assert instance.calibration.fit.frame_digest == second.frame_digest
    assert instance.feature.fit.frame_digest == first.frame_digest
    assert instance.feature.parameters.coefficients[0] > 0
    assert result.fitted.applicability.sources == (source(900),)
    assert result.fitted.reading_recipe == "resolve.m1_readings/declared"
    assert instance.threshold == 0.99


@pytest.mark.parametrize(
    "change", ["partition", "origin", "copied-source", "heldout", "recipe", "predictor", "score"]
)
def test_fitting_refuses_reused_frames_origins_or_unrelated_predictor(fit_basis, change):
    from corpus_structure.evaluate.declared_record_policy import fit_declared_record_policy

    first, second, specification = fit_basis
    frame = second.frame
    if change == "partition":
        frame = frame.model_copy(update={"partition": "final_assessment"})
    elif change == "origin":
        frame = frame.model_copy(
            update={
                "origin_groups": (
                    frame.origin_groups[0].model_copy(
                        update={"origin_group": first.frame.origin_groups[0].origin_group}
                    ),
                    *frame.origin_groups[1:],
                )
            }
        )
    elif change == "copied-source":
        frame = frame.model_copy(
            update={
                "origin_groups": (
                    frame.origin_groups[0].model_copy(
                        update={"copied_from": (first.frame.sources[0],)}
                    ),
                    *frame.origin_groups[1:],
                )
            }
        )
    elif change == "heldout":
        frame = frame.model_copy(update={"held_out_from": ()})
    elif change == "recipe":
        specification = specification.model_copy(update={"reading_recipe": "different-recipe"})
    elif change == "predictor":
        feature = specification.frozen_feature
        parameters = feature.parameters.model_copy(
            update={"intercept": feature.parameters.intercept + 1}
        )
        specification = specification.model_copy(
            update={"frozen_feature": feature.model_copy(update={"parameters": parameters})}
        )
    elif change == "score":
        event = frame.events[0]
        frame = frame.model_copy(
            update={
                "events": (
                    event.model_copy(
                        update={
                            "final_event": event.final_event.model_copy(
                                update={"final_event_score": -999.0}
                            )
                        }
                    ),
                    *frame.events[1:],
                )
            }
        )
    # Inject at the pure numerical boundary to independently assess its refusals;
    # acquired/native DTO validation is a separate boundary.
    second = DdoRecordGrade.model_construct(
        frame=frame,
        frame_canonical_json=frame.model_dump_json(),
        frame_digest=second.frame_digest,
    )
    with pytest.raises(ValueError):
        fit_declared_record_policy(first, second, specification)


def test_same_actual_author_can_supply_distinct_source_only_passes():
    frame = grade_frame()
    passes = tuple(
        row.model_copy(update={"author": "actual-model-and-operator"})
        for row in frame.reference_passes
    )
    checked = validate_changes(frame, reference_passes=passes)
    assert {row.author for row in checked.reference_passes} == {"actual-model-and-operator"}
    assert len({row.reference.product_id for row in checked.reference_passes}) == 3
