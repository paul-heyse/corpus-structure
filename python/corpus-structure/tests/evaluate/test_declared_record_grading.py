"""Current complete-family correctness, never generic selected-case matching."""

from copy import deepcopy

import pytest
from evaluate.declared_record_grading_support import current, cut, references
from evaluate.declared_record_policy_support import address, source

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordGradeSpecification,
    DdoRecordPredictionSelection,
    grade_complete_record_values,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.record_contracts import interpretation_identity
from corpus_structure.semantic.record_policy import RecordAlgorithm


def inputs(family, source_index=1):
    prepared, model = current()
    independent, row, coordinates = references(family, source_index)
    candidate = deepcopy(row)
    candidate["standing"] = "candidate"
    candidate["interpretation_id"] = interpretation_identity(candidate)
    report = dict(
        source_pin=source(source_index).model_dump(mode="json", exclude_none=True),
        standing="private_uncalibrated_candidates",
        inspection_outcome="produced",
        members=[dict(body=dict(candidate, candidate_type="record"))],
        coordinate_texts=coordinates,
        reading_policy_digest="retained-policy",
        reading_events=source_value(
            [
                dict(
                    record_id=candidate["record_id"],
                    interpretation_id=candidate["interpretation_id"],
                    outcome="not_run",
                )
            ]
        ),
        diagnostics_json='{"producer_diagnostics":{}}',
    )
    selected = cut()
    specification = DdoRecordGradeSpecification(
        prediction_selections=(
            DdoRecordPredictionSelection(
                source=source(source_index),
                outcome="completed",
                request_id="reading-request",
                obligation_id="reading-obligation",
                derivation_id="actual-reading-episode",
                use_id="actual-reading-use",
                project_id="project:one",
                demand_id=selected.record["demand_id"],
                read_id=selected.record["read_id"],
                product_id=f"prediction:actual:{source_index}",
                expected_cut=selected.identity,
                cut_canonical_json=selected.content.decode(),
            ),
        ),
        algorithm=RecordAlgorithm(),
    )
    kwargs = dict(
        reference_prepared=prepared,
        prediction_prepared=prepared,
        reference_model=model,
        prediction_model=model,
        reference_addresses=tuple(
            address(source(source_index), "reference:" + kind) for kind in ("A", "B", "C")
        ),
        prediction_address=address(source(source_index), f"prediction:actual:{source_index}"),
        prediction_derivation="actual-reading-episode",
        prediction_recipe=independent[0].question.reading_recipe,
    )
    return independent, report, specification, kwargs


@pytest.mark.parametrize(
    "family", ["definition", "assertion", "measurement", "table", "formula_context"]
)
def test_complete_grade_preserves_original_candidate_and_every_family(family):
    independent, report, specification, kwargs = inputs(family)
    before = canonical_bytes(report)
    grade = grade_complete_record_values(independent, report, specification, **kwargs)
    assert len(grade.frame.events) == 1
    event = grade.frame.events[0]
    assert event.correct is True
    assert event.reading.product_id == "prediction:actual:1"
    assert event.record_id == report["members"][0]["body"]["record_id"]
    assert event.interpretation_id == report["members"][0]["body"]["interpretation_id"]
    assert event.features.release_id == kwargs["prediction_prepared"].release_id
    assert canonical_bytes(report) == before
    assert report["members"][0]["body"]["standing"] == "candidate"
    assert {row.author for row in grade.frame.reference_passes} == {"actual-model"}


def test_grade_empty_source_keeps_carrier_and_coverage_outside_scored_denominator():
    independent, report, specification, kwargs = inputs("table")
    report.update(members=[], inspection_outcome="empty", reading_events=source_value([]))
    grade = grade_complete_record_values(independent, report, specification, **kwargs)
    assert grade.frame.events == ()
    (coverage,) = grade.frame.coverage
    assert coverage.outcome == "no_output" and coverage.event_ids == ()
    assert coverage.outputs[0].product_id == "prediction:actual:1"


def test_whole_grade_rejects_full_reading_difference_even_with_same_required_occurrence():
    independent, report, specification, kwargs = inputs("table")
    candidate = report["members"][0]["body"]
    from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity

    # A shorter, still exactly source-supported supplemental note changes the full
    # reading while the independently expected table/cell occurrence remains equal.
    note = next(field for field in candidate["fields"] if field["role"] == "note")
    evidence = next(
        row for row in candidate["evidence_sets"] if row["set_id"] == note["evidence_sets"][0]
    )
    anchor = next(row for row in candidate["anchors"] if row["anchor_id"] == evidence["anchors"][0])
    note["value"]["text"] = note["original"] = "hypothetic"
    anchor["source_piece"] = "hypothetic"
    anchor["end"] = 10
    anchor["anchor_id"] = anchor_identity(anchor)
    evidence["anchors"] = (anchor["anchor_id"],)
    evidence["set_id"] = evidence_set_identity(evidence)
    note["evidence_sets"] = (evidence["set_id"],)
    candidate["interpretation_id"] = interpretation_identity(candidate)
    report["reading_events"] = source_value(
        [
            dict(
                record_id=candidate["record_id"],
                interpretation_id=candidate["interpretation_id"],
                outcome="not_run",
            )
        ]
    )
    grade = grade_complete_record_values(independent, report, specification, **kwargs)
    assert grade.frame.events[0].correct is False


def test_population_keeps_exact_ordered_all_of_sources_and_default_origin_support():
    from corpus_structure.evaluate.declared_record_policy import (
        DdoRecordReferencePopulation,
        _fit_feature_value,
        grade_complete_record_population_values,
    )

    cases = [inputs("table", index) for index in range(1, 5)]
    populations = tuple(
        DdoRecordReferencePopulation(
            pass_kind=kind,
            references=tuple(case[0][position] for case in cases),
        )
        for position, kind in enumerate(("A", "B", "C"))
    )
    predictions = tuple(case[1] for case in cases)
    # Two genuinely empty sources remain in the full source census. They are not
    # negative correctness labels and cannot manufacture the missing class support.
    predictions[0].update(members=[], inspection_outcome="empty", reading_events=source_value([]))
    predictions[1].update(members=[], inspection_outcome="empty", reading_events=source_value([]))
    prepared, model = current()
    specification = DdoRecordGradeSpecification(
        prediction_selections=tuple(case[2].prediction_selections[0] for case in cases),
        algorithm=RecordAlgorithm(),
    )
    kwargs = dict(
        reference_prepared=prepared,
        reference_model=model,
        prediction_prepared=(prepared,) * 4,
        prediction_models=(model,) * 4,
        reference_addresses=cases[0][3]["reference_addresses"],
        prediction_addresses=tuple(case[3]["prediction_address"] for case in cases),
        prediction_recipes=(cases[0][3]["prediction_recipe"],) * 4,
        cut_release_id=prepared.release_id,
    )
    grade = grade_complete_record_population_values(
        populations, predictions, specification, **kwargs
    )
    assert [row.original_source for row in grade.frame.sources] == [
        "original:1",
        "original:2",
        "original:3",
        "original:4",
    ]
    assert [row.outcome for row in grade.frame.coverage] == [
        "no_output",
        "no_output",
        "completed",
        "completed",
    ]
    assert len(grade.frame.reference_passes) == 12
    assert len(grade.frame.events) == 2
    assert all(row.correct for row in grade.frame.events)
    provisional = _fit_feature_value(
        grade, algorithm=RecordAlgorithm(), assumptions="complete actual source census"
    )
    assert provisional.instance is None
    assert provisional.diagnostics.positive_count == 2
    assert provisional.diagnostics.negative_count == 0
    assert provisional.diagnostics.declared_origin_group_count == 2
    with pytest.raises(ValueError, match="all-of"):
        grade_complete_record_population_values(
            populations, predictions[:-1], specification, **kwargs
        )
    with pytest.raises(ValueError, match="ordered source"):
        grade_complete_record_population_values(
            populations,
            predictions,
            specification.model_copy(
                update={
                    "prediction_selections": tuple(reversed(specification.prediction_selections)),
                }
            ),
            **kwargs,
        )
    with pytest.raises(ValueError, match="actual prediction carrier"):
        grade_complete_record_population_values(
            populations, (None, *predictions[1:]), specification, **kwargs
        )


def test_actual_grade_and_fit_factories_compile_as_closed_project_derivations():
    from pathlib import Path

    from corpus_structure.evaluate.declared_record_policy import (
        protected_record_policy_kind_declarations,
        record_policy_inputs,
        record_policy_operation_sources,
    )
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.reading_resolution_products import (
        reading_resolution_declarations,
        reading_resolution_operation_sources,
    )
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = record_policy_inputs(
        SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
    )
    model = compile_data_operations(
        bundle,
        declarations=(
            protected_record_policy_kind_declarations(),
            reading_resolution_declarations(),
        ),
        python_sources=combine_primary_sources(
            record_policy_operation_sources(), reading_resolution_operation_sources()
        ),
    )
    grade, fit = model.operation("record_policy.grade"), model.operation("record_policy.fit")
    assert grade.subject == fit.subject
    assert all(
        operation.effects == () and operation.profile == "derivation" for operation in (grade, fit)
    )
    assert grade.capabilities.prepared_factory is not None
    assert fit.capabilities.prepared_factory is not None
    assert (
        grade.capabilities.prepared_factory.entrypoint
        == "corpus_structure.methods.declared_record_policy.RecordPolicyGrade.acquire_port"
    )
    assert (
        fit.capabilities.prepared_factory.entrypoint
        == "corpus_structure.methods.declared_record_policy.RecordPolicyFit.acquire_port"
    )
    assert [role.name for role in grade.roles if role.direction == "output"] == ["grade"]
    assert [role.name for role in fit.roles if role.direction == "output"] == ["fitted"]
    assert next(role for role in grade.roles if role.name == "prediction").collection == "set"
    assert fit.outcomes == ("success", "empty")
    prediction = next(role for role in grade.roles if role.name == "prediction")
    assert prediction.support is not None
    assert prediction.support.source_set == "record-policy-predictions"
    grade_sources = {}
    for role in fit.roles:
        if role.name in {"feature_grade", "calibration_grade"}:
            assert role.support is not None
            grade_sources[role.name] = role.support.source_set
    assert grade_sources == {
        "feature_grade": "record-policy-feature-grades",
        "calibration_grade": "record-policy-calibration-grades",
    }
    assert [
        role.kind.rsplit("/", 1)[-1]
        for role in grade.roles
        if role.name in {"reference_a", "reference_b", "adjudication"}
    ] == [
        "DdoRecordReferencePopulationA",
        "DdoRecordReferencePopulationB",
        "DdoRecordReferencePopulationC",
    ]
    assert all(item.complete for item in model.implementation_slices)
