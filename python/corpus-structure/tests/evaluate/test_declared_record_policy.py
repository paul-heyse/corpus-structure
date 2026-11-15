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
        (a, a, c), (a, b.model_copy(update={"reference": a.reference}), c),
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


def training_grade(*, calibration=False, feature=None, held_out_from=()):
    from corpus_structure.semantic.record_policy import reading_potential
    base = grade_frame()
    sources = tuple(source(index + (100 if calibration else 0)) for index in range(6))
    events, coverage, origins = [], [], []
    for index, (selected, value) in enumerate(zip(sources, (-3., -2., -1., 1., 2., 3.), strict=True)):
        reading = address(selected, f"product:{selected.original_source}")
        features = vector(index + (100 if calibration else 0), value)
        if calibration:
            features = features.model_copy(update={"release_id": "release:compatible"})
        event = DdoRecordGradeEvent(
            record_id=features.record_id, interpretation_id=features.interpretation_id,
            reading=reading, source=selected, source_release_id=features.release_id,
            derivation_id=f"derivation:{index}", reading_recipe=base.reading_recipe,
            features=features, correct=index >= 3, origin_group=f"origin:{selected.original_source}",
            final_event=DdoRecordFinalEvent(
                feature_instance_digest=feature.digest, feature_input_digest=features.input_digest,
                event_procedure="procedure:whole-reading",
                final_event_score=reading_potential(feature.parameters, features.values),
            ) if calibration else None,
        )
        events.append(event)
        coverage.append(DdoRecordCoverage(source=selected, outputs=(reading,), outcome="completed", event_ids=(features.interpretation_id,)))
        origins.append(DdoRecordOrigin(source=selected, origin_group=event.origin_group))
    if calibration:
        a, b, c = base.reference_passes
        passes = (a.model_copy(update={"content_digest": "1" * 64}),
                  b.model_copy(update={"content_digest": "2" * 64}),
                  c.model_copy(update={"content_digest": "3" * 64, "adjudicates": ("1" * 64, "2" * 64)}))
    else:
        passes = base.reference_passes
    return DdoRecordGrade.from_frame(validate_changes(
        base, sources=sources, events=tuple(events), coverage=tuple(coverage), origin_groups=tuple(origins),
        partition="final_event_calibration" if calibration else "feature_fit",
        prediction_release_id="release:compatible" if calibration else "release:test",
        reference_passes=passes, reference_digest=("3" if calibration else "d") * 64,
        held_out_from=held_out_from,
    ))


@pytest.fixture(scope="module")
def fit_basis():
    from corpus_structure.evaluate.declared_record_policy import (
        DdoRecordFitSpecification, DdoRecordGradeSelection, _fit_feature_value,
    )
    from corpus_structure.semantic.record_policy_authority import DdoRecordPolicyApplicability
    from semantic.record_policy_support import algorithm
    first = training_grade()
    preliminary = _fit_feature_value(first, algorithm=algorithm(), assumptions="independent complete frozen source frames")
    feature = preliminary.instance
    assert feature is not None
    second = training_grade(calibration=True, feature=feature, held_out_from=(first.frame_digest,))
    specification = DdoRecordFitSpecification(
        feature_selection=DdoRecordGradeSelection(
            project_id="project:one", demand_id="demand:grade", read_id="read:grade",
            use_id="use:grade", derivation_id="derivation:grade", product_id="product:grade",
            expected_cut="cut:grade", frame_digest=first.frame_digest,
        ),
        frozen_feature=feature, applicability=DdoRecordPolicyApplicability(
            project_id="project:one", sources=(source(900),),
        ), family_contract=first.frame.family_contract, reading_recipe=first.frame.reading_recipe,
        event_procedure="procedure:whole-reading", assumptions="independent complete frozen source frames",
        threshold=0.99, threshold_procedure="predeclared-threshold-1",
    )
    return first, second, specification


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
    assert instance.calibration.feature_instance_digest == instance.feature.digest
    assert instance.calibration.fit.frame_digest == second.frame_digest
    assert instance.feature.fit.frame_digest == first.frame_digest
    assert instance.feature.parameters.coefficients[0] > 0
    assert result.fitted.applicability.sources == (source(900),)
    assert result.fitted.reading_recipe == "resolve.m1_readings/declared"
    assert instance.threshold == 0.99


@pytest.mark.parametrize("change", ["partition", "origin", "copied-source", "heldout", "recipe", "predictor", "score"])
def test_fitting_refuses_reused_frames_origins_or_unrelated_predictor(fit_basis, change):
    from corpus_structure.evaluate.declared_record_policy import fit_declared_record_policy
    first, second, specification = fit_basis
    frame = second.frame
    if change == "partition":
        frame = frame.model_copy(update={"partition": "final_assessment"})
    elif change == "origin":
        frame = frame.model_copy(update={"origin_groups": (
            frame.origin_groups[0].model_copy(update={"origin_group": first.frame.origin_groups[0].origin_group}),
            *frame.origin_groups[1:],
        )})
    elif change == "copied-source":
        frame = frame.model_copy(update={"origin_groups": (
            frame.origin_groups[0].model_copy(update={"copied_from": (first.frame.sources[0],)}),
            *frame.origin_groups[1:],
        )})
    elif change == "heldout":
        frame = frame.model_copy(update={"held_out_from": ()})
    elif change == "recipe":
        specification = specification.model_copy(update={"reading_recipe": "different-recipe"})
    elif change == "predictor":
        feature = specification.frozen_feature
        parameters = feature.parameters.model_copy(update={"intercept": feature.parameters.intercept + 1})
        specification = specification.model_copy(update={"frozen_feature": feature.model_copy(update={"parameters": parameters})})
    elif change == "score":
        event = frame.events[0]
        frame = frame.model_copy(update={"events": (
            event.model_copy(update={"final_event": event.final_event.model_copy(update={"final_event_score": -999.})}),
            *frame.events[1:],
        )})
    # Inject at the pure numerical boundary to independently assess its refusals;
    # acquired/native DTO validation is a separate boundary.
    second = DdoRecordGrade.model_construct(
        frame=frame, frame_canonical_json=frame.model_dump_json(), frame_digest=second.frame_digest,
    )
    with pytest.raises(ValueError):
        fit_declared_record_policy(first, second, specification)


def test_same_actual_author_can_supply_distinct_source_only_passes():
    frame = grade_frame()
    passes = tuple(row.model_copy(update={"author": "actual-model-and-operator"}) for row in frame.reference_passes)
    checked = validate_changes(frame, reference_passes=passes)
    assert {row.author for row in checked.reference_passes} == {"actual-model-and-operator"}
    assert len({row.reference.product_id for row in checked.reference_passes}) == 3
