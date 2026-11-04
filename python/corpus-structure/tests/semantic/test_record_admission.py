"""Independent whole-record selection cap expectations; native custody is separate."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.record_admission import cap_record_selections
from corpus_structure.semantic.record_projection import RecordAdmissionRow, RecordAssertionRow


def batch(*, incomplete=False):
    return SimpleNamespace(
        source_record=(SimpleNamespace(record_id="record", interpretation_id="reading"),),
        record_field=tuple(
            SimpleNamespace(record_id="record", interpretation_id="reading", role=role)
            for role in ("term", "scope")
        ),
        record_assertion=tuple(
            RecordAssertionRow("record", "reading", role, "entity", "fact:" + role, "occ:" + role)
            for role in (("term",) if incomplete else ("term", "scope"))
        ),
        record_admission=(
            RecordAdmissionRow(
                "record", "reading", "candidate", "candidate", "1", "not_calibrated", "unfitted"
            ),
        ),
    )


def admitted():
    return RecordAdmissionRow(
        "record",
        "reading",
        "accepted",
        "algorithm",
        "1",
        "calibrated_whole_record_event",
        "evaluated",
        "instance",
        1,
        "evaluation",
        "0.99",
        "{}",
    )


def test_ordinary_domain_rule_selection_cannot_upgrade_candidate_fields():
    selected, overlay = cap_record_selections(batch(), frozenset({"fact:term", "unrelated"}), ())
    assert selected == {"unrelated"}
    assert overlay[0].decision == "candidate"


def test_complete_evaluated_record_selects_every_field_as_one_unit():
    selected, overlay = cap_record_selections(batch(), frozenset({"unrelated"}), (admitted(),))
    assert selected == {"unrelated", "fact:term", "fact:scope"}
    assert overlay == (admitted(),)


@pytest.mark.parametrize(
    "row",
    [
        replace(admitted(), instance_digest=None),
        replace(admitted(), evaluation_id=None),
        replace(admitted(), probability_lexical=None),
        replace(admitted(), binding_json=None),
        replace(admitted(), calibration="not_calibrated"),
    ],
)
def test_acceptance_requires_complete_evaluated_calibrated_binding(row):
    with pytest.raises(ValueError, match="evaluated calibrated"):
        cap_record_selections(batch(), frozenset(), (row,))


def test_accepted_partial_graph_refuses_without_field_salvage():
    with pytest.raises(ValueError, match="complete field assertion"):
        cap_record_selections(batch(incomplete=True), frozenset(), (admitted(),))


def test_duplicate_and_foreign_decisions_refuse():
    for overlay in ((admitted(), admitted()), (replace(admitted(), record_id="foreign"),)):
        with pytest.raises(ValueError, match="duplicate or foreign"):
            cap_record_selections(batch(), frozenset(), overlay)


@pytest.fixture(scope="module")
def evaluated_reading():
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.record_contracts import interpretation_identity, record_identity
    from corpus_structure.semantic.record_policy import (
        FEATURES,
        FeatureInstance,
        FinalEventCalibration,
        FitDiagnostics,
        LinearParameters,
        PolicyApplicability,
        RecordAcceptanceInstance,
        RecordAlgorithm,
        derive_record_features,
        score_record,
    )
    from corpus_structure.semantic.record_policy_products import record_policy_inputs
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    from .test_record_assertions import inputs, record, report

    prepared = prepare_release(
        record_policy_inputs(inputs()[1]),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    algorithm = RecordAlgorithm(features=(FEATURES[0],))
    raw = record(
        "DefinitionRecordFields",
        {
            "term": dict(
                state="present",
                value=dict(kind="text", text="term"),
                original="term",
                pieces="term",
            ),
            "defining_text": dict(
                state="present",
                value=dict(kind="text", text="definition"),
                original="definition",
                pieces="definition",
            ),
            "scope": dict(
                state="present", value=dict(kind="native_location", pointer="#/inspected/scope")
            ),
        },
    )
    raw["policy_version"] = algorithm.version
    raw["record_id"] = record_identity(prepared.release_id, raw)
    raw["interpretation_id"] = interpretation_identity(raw)
    fit = FitDiagnostics(
        partition="feature_fit",
        frame_digest="a" * 64,
        reference_digest="b" * 64,
        coverage_digest="c" * 64,
        provenance="independent fixture",
        negative_count=3,
        positive_count=3,
        declared_origin_group_count=3,
        conditioning_assumptions="fixture only",
        converged=True,
        iterations=1,
        standing="fitted",
        reason="fixture",
    )
    feature = FeatureInstance(
        algorithm=algorithm,
        applicability=PolicyApplicability(
            release_id=prepared.release_id,
            family=raw["family"],
            subset="fixture",
            assumptions="fixture only",
        ),
        parameters=LinearParameters(
            feature_signature=algorithm.feature_signature,
            names=(FEATURES[0].name,),
            coefficients=(1.0,),
            center=(0.0,),
            scale=(1.0,),
            intercept=7.0,
        ),
        fit=fit,
    )
    calibration = FinalEventCalibration(
        feature_instance_digest=feature.digest,
        event_procedure="independent-complete-reading-logistic-1",
        slope=1.0,
        intercept=0.0,
        fit=fit.model_copy(
            update=dict(
                partition="final_event_calibration",
                frame_digest="d" * 64,
                reference_digest="e" * 64,
            )
        ),
        assumptions="fixture only",
        coverage_digest="f" * 64,
    )
    instance = RecordAcceptanceInstance(
        feature=feature,
        calibration=calibration,
        threshold=0.9,
        threshold_procedure="fixed fixture",
        conditioning_assumptions="fixture only",
    )
    binding = dict(
        instance=instance.model_dump(mode="json"),
        instance_digest=instance.digest,
        instance_canonical_json=canonical_bytes(instance.model_dump(mode="json")).decode(),
        evaluation_id=71,
        evaluation_digest="9" * 64,
    )
    diagnostics = [{"kind": "numeric", "value": 1.0}]
    vector = derive_record_features(prepared, raw, algorithm=algorithm, diagnostics=diagnostics)
    event = dict(
        record_id=raw["record_id"],
        interpretation_id=raw["interpretation_id"],
        feature_instance_digest=feature.digest,
        feature_input_digest=vector.input_digest,
        feature_input_canonical_json=canonical_bytes([raw, diagnostics]).decode(),
        event_procedure=calibration.event_procedure,
        final_event_score=score_record(feature, vector, subset="fixture").compatibility_potential,
        outcome="completed",
        diagnostics=diagnostics,
    )
    return prepared, report(raw), binding, event


def test_overlay_requests_admission_only_for_exact_completed_sealed_event(evaluated_reading):
    from corpus_structure.semantic.record_admission import evaluate_record_admissions

    prepared, report, binding, event = evaluated_reading
    rows = evaluate_record_admissions(
        prepared, (dict(report, record_policy_events=[event]),), [binding]
    )
    assert len(rows) == 1
    assert rows[0].decision == "accepted", rows[0].reason
    assert rows[0].evaluation_id == 71
    assert rows[0].probability_lexical is not None
    assert float(rows[0].probability_lexical) > 0.99
    assert report["records"][0]["standing"] == "candidate"
    for changed in (
        {"outcome": "not_run"},
        {"feature_input_digest": "0" * 64},
        {"feature_input_canonical_json": "[]"},
        {"final_event_score": -8.0},
        {"final_event_score": event["final_event_score"] + 1.0},
        {"event_procedure": "unreleased-coupled-procedure"},
    ):
        candidate = evaluate_record_admissions(
            prepared, (dict(report, record_policy_events=[dict(event, **changed)]),), [binding]
        )
        assert candidate[0].decision == "candidate"


def test_no_fitted_binding_retains_queryable_candidate(evaluated_reading):
    from corpus_structure.semantic.record_admission import evaluate_record_admissions

    prepared, report, _, event = evaluated_reading
    rows = evaluate_record_admissions(prepared, (dict(report, record_policy_events=[event]),), ())
    assert rows[0].decision == "candidate"
    assert rows[0].binding_json is None
