"""Protected DTO controls; these authored values grant no native authority."""

import json

import pytest
from jsonschema import Draft7Validator

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordCoverage, DdoRecordFinalEvent, DdoRecordGrade, DdoRecordGradeEvent,
    DdoRecordGradeFrame, DdoRecordOrigin, DdoRecordReferencePass,
    PROTECTED_NAMESPACE, protected_record_policy_kind_declarations,
)
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef, DeclaredStructuralSource
from semantic.record_policy_support import vector


def source(index):
    return DeclaredStructuralSource(
        source=f'["source:{index}",null]', source_product=f"source:{index}",
        subject=f"subject:{index}", subject_definition="subject-definition:original-section",
        document=f"original:{index}", original_source=f"original:{index}",
        projection_digest="a" * 64, section_pointer="#/groups/0", membership="descendants",
        project_id="project:one", analyzed_scope_meaning='["null"]', kind_contract="kind:source",
    )


def address(selected, product):
    return DeclaredProductRef(
        product_id=product, member_id=None, kind_contract="kind:reading",
        project_id=selected.project_id, subject=selected.subject,
        subject_definition=selected.subject_definition, original_source=selected.original_source,
        analyzed_scope_meaning=selected.analyzed_scope_meaning,
    )


def grade_frame(*, calibration=False):
    first, empty = source(1), source(2)
    reading = address(first, "product:reading")
    passes = tuple(DdoRecordReferencePass(
        reference=address(first, "reference:" + kind), pass_kind=kind, author="author:" + kind,
        content_digest=content * 64, question_digest="e" * 64, rubric_digest="f" * 64,
        source_cut_id="cut:source", adjudicates=("b" * 64, "c" * 64) if kind == "C" else (),
    ) for kind, content in (("A", "b"), ("B", "c"), ("C", "d")))
    event = DdoRecordGradeEvent(
        record_id="record:0", interpretation_id="reading:0", reading=reading,
        source=first, source_release_id="release:test", derivation_id="derivation:reading",
        reading_recipe="resolve.m1_readings/declared", features=vector(0, -3), correct=False,
        origin_group="origin:one", final_event=DdoRecordFinalEvent(
            feature_instance_digest="1" * 64, feature_input_digest="a" * 64,
            event_procedure="procedure:whole-reading", final_event_score=-123.5,
        ) if calibration else None,
    )
    return DdoRecordGradeFrame(
        partition="final_event_calibration" if calibration else "feature_fit",
        project_id="project:one", family="table", family_contract="kind:table-reading",
        reading_recipe="resolve.m1_readings/declared", subset="source-sections",
        question_digest="e" * 64, rubric_digest="f" * 64, reference_digest="d" * 64,
        source_cut_id="cut:source", prediction_cut_id="cut:prediction",
        source_release_id="release:original", prediction_release_id="release:test",
        sources=(first, empty), reference_passes=passes, events=(event,),
        coverage=(DdoRecordCoverage(source=first, outputs=(reading,), outcome="completed", event_ids=("reading:0",)),
                  DdoRecordCoverage(source=empty, outputs=(), outcome="no_output", event_ids=())),
        origin_groups=(DdoRecordOrigin(source=first, origin_group="origin:one"),
                       DdoRecordOrigin(source=empty, origin_group="origin:two")),
    )


def validate_changes(frame, **changes):
    return DdoRecordGradeFrame.model_validate({**frame.model_dump(mode="python"), **changes})


def test_grade_preserves_low_scored_events_and_separate_no_output_coverage():
    frame = grade_frame(calibration=True)
    grade = DdoRecordGrade.from_frame(frame)
    assert grade.frame.events[0].final_event.final_event_score == -123.5
    assert len(grade.frame.events) == 1
    assert [row.outcome for row in grade.frame.coverage] == ["completed", "no_output"]
    assert grade.frame.prediction_release_id == "release:test"
    assert grade.frame.source_release_id == "release:original"
    assert grade.frame.events[0].features.release_id == "release:test"
    assert DdoRecordGrade.model_validate_json(grade.model_dump_json()) == grade
    assert '"correct":false' in grade.frame_canonical_json
    assert '"records"' not in grade.frame_canonical_json
    for changes in ({"frame_digest": "0" * 64}, {"frame_canonical_json": grade.frame_canonical_json + " "}):
        with pytest.raises(ValueError, match="canonical bytes or digest"):
            DdoRecordGrade.model_validate({**grade.model_dump(mode="python"), **changes})


@pytest.mark.parametrize("change", ["drop-source", "drop-event", "duplicate-event", "wrong-recipe", "wrong-release", "missing-origin", "unscored-calibration"])
def test_frame_refuses_incomplete_or_relabelled_population(change):
    frame = grade_frame()
    changes = {
        "drop-source": {"coverage": frame.coverage[:1]},
        "drop-event": {"events": ()},
        "duplicate-event": {"events": frame.events * 2},
        "wrong-recipe": {"reading_recipe": "different-recipe"},
        "wrong-release": {"prediction_release_id": "release:unrelated"},
        "missing-origin": {"origin_groups": frame.origin_groups[:1]},
        "unscored-calibration": {"partition": "final_event_calibration"},
    }[change]
    with pytest.raises(ValueError):
        validate_changes(frame, **changes)


def test_reference_question_and_independence_are_explicit():
    frame = grade_frame()
    a, b, c = frame.reference_passes
    for passes in (
        (a, a, c), (a, b.model_copy(update={"author": a.author}), c),
        (a, b, c.model_copy(update={"adjudicates": ("1" * 64, "2" * 64)})),
        (a, b.model_copy(update={"question_digest": "0" * 64}), c),
    ):
        with pytest.raises(ValueError):
            validate_changes(frame, reference_passes=passes)
    with pytest.raises(ValueError, match="exposed prediction"):
        DdoRecordReferencePass.model_validate({**a.model_dump(mode="python"), "exposed_outputs": (a.reference,)})


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
    Draft7Validator(schema).validate(DdoRecordGrade.from_frame(grade_frame()).model_dump(mode="json"))
    assert schema["additionalProperties"] is False
    assert schema["definitions"]["DdoRecordGradeFrame"]["properties"]["reference_passes"]["minItems"] == 3
