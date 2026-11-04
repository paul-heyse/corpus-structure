"""Pure finite M1 policy/fitting behavior; no native acceptance or quality qualification."""

from copy import deepcopy

import numpy as np
import pytest
from pydantic import ValidationError
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

from corpus_structure.evaluate.record_fitting import (
    FeatureFitObservation,
    FinalEventObservation,
    FittingFrame,
    WholeReadingLabel,
    fit_final_event_calibration,
    fit_whole_reading_features,
)
from corpus_structure.semantic.record_contracts import evidence_set_identity
from corpus_structure.semantic.record_policy import (
    FEATURES,
    FeatureInstance,
    FinalEventCalibration,
    LinearParameters,
    PolicyApplicability,
    RecordAcceptanceInstance,
    RecordAlgorithm,
    RecordFeatures,
    assess_record_admission,
    derive_record_features,
    score_record,
)

from .test_record_contracts import bind, finish, release_inputs, table_record


def algorithm(**changes):
    return RecordAlgorithm(features=(FEATURES[0],), **changes)


def applicability():
    return PolicyApplicability(
        release_id="release:test",
        family="table",
        subset="native-tables",
        assumptions="fixed source cut",
    )


def vector(index, value, *, algo=None):
    algo = algo or algorithm()
    return RecordFeatures(
        record_id=f"record:{index}",
        interpretation_id=f"reading:{index}",
        release_id="release:test",
        family="table",
        feature_signature=algo.feature_signature,
        names=tuple(feature.name for feature in algo.features),
        values=(float(value),),
        input_digest="a" * 64,
    )


def frame(ids, *, calibration=False):
    return FittingFrame(
        frame_digest=("b" if calibration else "a") * 64,
        reference_digest=("d" if calibration else "c") * 64,
        coverage_digest="e" * 64,
        event_ids=tuple(ids),
        provenance="independent evaluator fixture",
        assumptions="complete fixed eligible/scored frame; no-output source census separate",
    )


def training(*, algo=None, weights=None):
    algo = algo or algorithm()
    values = (-3.0, -2.0, -1.0, 1.0, 2.0, 3.0)
    weights = weights or (1.0,) * len(values)
    observations = tuple(
        FeatureFitObservation(
            features=vector(index, value, algo=algo),
            label=WholeReadingLabel(
                event_id=f"reading:{index}",
                origin_group=f"source:{index % 3}",
                correct=index >= 3,
                sample_weight=weight,
            ),
        )
        for index, (value, weight) in enumerate(zip(values, weights, strict=True))
    )
    return observations, frame(row.label.event_id for row in observations)


def fitted():
    rows, selected = training()
    result = fit_whole_reading_features(
        rows, algorithm=algorithm(), applicability=applicability(), frame=selected
    )
    assert result.instance is not None
    return result.instance


def calibrated(feature):
    rows = tuple(
        FinalEventObservation(
            feature_instance_digest=feature.digest,
            event_procedure="uncoupled-whole-reading-1",
            final_event_score=float(score),
            label=WholeReadingLabel(
                event_id=f"cal:{index}", origin_group=f"source:{index % 3}", correct=index >= 3
            ),
        )
        for index, score in enumerate((-4, -2, -1, 1, 2, 4))
    )
    result = fit_final_event_calibration(
        rows,
        feature=feature,
        frame=frame((row.label.event_id for row in rows), calibration=True),
        event_procedure="uncoupled-whole-reading-1",
    )
    assert result.calibration is not None
    return result.calibration


def test_actual_record_features_preserve_missing_raw_inputs_and_role_universe():
    raw, contexts = table_record()
    record = bind(raw, contexts)
    prepared = release_inputs()[2]
    features = derive_record_features(prepared, record)
    values = dict(zip(features.names, features.values, strict=True))
    assert values["present_fraction"] == 6 / 8
    assert values["located_fraction"] == 6 / 8
    assert values["exact_anchor_fraction"] == 5 / 7
    assert values["unresolved_fraction"] == 0
    assert values["diagnostic_count"] is None
    assert "provider.raw_confidence" in features.unavailable
    with_diagnostics = derive_record_features(prepared, record, diagnostics=())
    assert with_diagnostics.values[-1] == 0
    assert with_diagnostics.input_digest != features.input_digest
    broken = deepcopy(raw)
    broken["fields"] = broken["fields"][:-1]
    with pytest.raises(ValueError, match="complete released role"):
        derive_record_features(prepared, broken)


def test_json_instance_is_immutable_and_digest_binds_parameters_and_order():
    feature = fitted()
    encoded = feature.model_dump_json()
    reconstructed = FeatureInstance.model_validate_json(encoded)
    assert reconstructed == feature
    assert reconstructed.digest == feature.digest
    assert '"correct"' not in encoded
    assert '"origin_group"' not in encoded
    with pytest.raises(ValidationError, match="frozen"):
        feature.parameters.__setattr__("intercept", 2.0)
    changed = feature.model_dump(mode="python")
    changed["parameters"]["intercept"] += 0.5
    assert FeatureInstance.model_validate(changed).digest != feature.digest
    changed["parameters"]["names"] = ("made_up_confidence",)
    with pytest.raises(ValueError, match="algorithm"):
        FeatureInstance.model_validate(changed)


@pytest.mark.parametrize(
    "name,value",
    [
        ("intercept", float("nan")),
        ("coefficients", (float("inf"),)),
        ("scale", (0.0,)),
        ("positive_class", 0),
    ],
)
def test_parameters_refuse_nonfinite_wrong_positive_class_or_scaling(name, value):
    raw = fitted().parameters.model_dump(mode="python")
    raw[name] = value
    with pytest.raises(ValidationError):
        LinearParameters.model_validate(raw)


def test_feature_order_solver_weights_and_missing_inputs_are_checked():
    with pytest.raises(ValidationError):
        RecordAlgorithm(features=(FEATURES[0], FEATURES[0]))
    with pytest.raises(ValidationError):
        RecordAlgorithm.model_validate({"solver": "saga"})
    with pytest.raises(ValidationError, match="L2"):
        RecordAlgorithm(l1_ratio=0.5)
    with pytest.raises(ValidationError):
        WholeReadingLabel(event_id="event", origin_group="source", correct=True, sample_weight=0.0)
    feature = fitted()
    missing = vector(0, 1).model_dump(mode="python")
    missing["values"] = (None,)
    with pytest.raises(ValueError, match="unavailable"):
        score_record(feature, RecordFeatures.model_validate(missing), subset="native-tables")
    with pytest.raises(ValueError, match="applicability"):
        score_record(feature, vector(0, 1), subset="invented-subset")
    wrong_order = vector(0, 1).model_dump(mode="python")
    wrong_order["names"] = ("located_fraction",)
    with pytest.raises(ValueError, match="order"):
        score_record(feature, RecordFeatures.model_validate(wrong_order), subset="native-tables")


def test_exported_prediction_matches_public_sklearn_binary_fit_with_weights():
    weights = (1.0, 2.0, 1.0, 1.0, 3.0, 1.0)
    rows, selected = training(weights=weights)
    result = fit_whole_reading_features(
        rows, algorithm=algorithm(), applicability=applicability(), frame=selected
    )
    assert result.instance is not None
    feature = result.instance
    values = np.asarray([-3, -2, -1, 1, 2, 3], dtype=np.float64).reshape(-1, 1)
    reference = LogisticRegression(C=1.0, l1_ratio=0.0, solver="lbfgs", tol=1e-8, max_iter=1000)
    scaled = (values - values.mean()) / values.std()
    reference.fit(scaled, [0, 0, 0, 1, 1, 1], sample_weight=np.asarray(weights))
    for row, expected in zip(rows, reference.predict_proba(scaled)[:, 1], strict=True):
        actual = score_record(feature, row.features, subset="native-tables")
        assert actual.uncalibrated_probability == pytest.approx(expected)
        assert actual.standing == "provisional_whole_reading_score"


def test_insufficient_labels_and_nonconvergence_remain_provisional():
    rows, selected = training()
    few = rows[:3]
    insufficient = fit_whole_reading_features(
        few,
        algorithm=algorithm(),
        applicability=applicability(),
        frame=frame(row.label.event_id for row in few),
    )
    assert insufficient.instance is None
    assert insufficient.diagnostics.standing == "provisional"
    limited_algorithm = algorithm(max_iterations=1)
    limited_rows, selected = training(algo=limited_algorithm)
    limited = fit_whole_reading_features(
        limited_rows, algorithm=limited_algorithm, applicability=applicability(), frame=selected
    )
    assert limited.instance is None
    assert not limited.diagnostics.converged
    with pytest.raises(ValueError, match="complete eligible"):
        fit_whole_reading_features(
            rows[:-1], algorithm=algorithm(), applicability=applicability(), frame=selected
        )


def test_final_event_sigmoid_binds_frozen_instance_and_heldout_frame():
    feature = fitted()
    calibration = calibrated(feature)
    assert calibration.fit.partition == "final_event_calibration"
    assert calibration.feature_instance_digest == feature.digest
    assert expit(calibration.slope * -2 + calibration.intercept) < expit(
        calibration.slope * 2 + calibration.intercept
    )
    assert FinalEventCalibration.model_validate_json(calibration.model_dump_json()) == calibration
    invalid = calibration.model_dump(mode="python")
    invalid["feature_instance_digest"] = "f" * 64
    with pytest.raises(ValueError, match="frozen feature"):
        RecordAcceptanceInstance(
            feature=feature,
            calibration=FinalEventCalibration.model_validate(invalid),
            threshold=0.9,
            threshold_procedure="predeclared",
            conditioning_assumptions="fixed cut",
        )
    with pytest.raises(ValueError, match="held-out"):
        fit_final_event_calibration((), feature=feature, frame=frame(()), event_procedure="event")


def test_whole_record_requires_calibration_and_native_authority_and_refuses_unresolved():
    raw, _ = table_record()
    prepared = release_inputs()[2]
    feature = fitted()
    data = feature.model_dump(mode="python")
    data["applicability"]["release_id"] = prepared.release_id
    feature = FeatureInstance.model_validate(data)
    raw["policy_version"] = feature.algorithm.version
    instance = RecordAcceptanceInstance(
        feature=feature,
        threshold=0.6,
        threshold_procedure="fixed threshold before final assessment",
        conditioning_assumptions="native source custody required",
    )
    refused = assess_record_admission(
        prepared,
        raw,
        instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert "no_final_event_calibration" in refused.blockers
    assert refused.standing == "candidate"
    calibrated_instance = RecordAcceptanceInstance(
        feature=feature,
        calibration=calibrated(feature),
        threshold=0.6,
        threshold_procedure="fixed threshold before final assessment",
        conditioning_assumptions="native source custody required",
    )
    # The two optional absent fields lack located inspection evidence in this fixture.
    proposal = assess_record_admission(
        prepared,
        raw,
        calibrated_instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert proposal.standing == "candidate"
    assert proposal.required_authority == "native-evaluator-authorized-exact-instance-binding"
    assert "accepted" not in proposal.model_dump()
    broken = deepcopy(raw)
    broken["fields"][0]["state"] = "unresolved"
    broken["fields"][0]["evidence_sets"] = ()
    broken["fields"][0]["evidence_status"] = "unavailable"
    refusal = assess_record_admission(
        prepared,
        broken,
        calibrated_instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert "required_role_not_present:table" in refusal.blockers
    assert "unresolved_meaning:table" in refusal.blockers
    assert "missing_located_evidence:table" in refusal.blockers
    assert not refusal.eligible_for_native_validation


@pytest.mark.parametrize("state", ["unresolved", "unstated"])
def test_row_label_remains_meaning_changing_without_a_required_present_gate(state):
    raw, contexts = table_record()
    prepared = release_inputs()[2]
    feature_data = fitted().model_dump(mode="python")
    feature_data["applicability"]["release_id"] = prepared.release_id
    feature = FeatureInstance.model_validate(feature_data)
    raw["policy_version"] = feature.algorithm.version
    raw["standing"] = "candidate"
    label = next(field for field in raw["fields"] if field["role"] == "row_label")
    old_set = label["evidence_sets"][0]
    inspection = dict(
        role="row_label", ordering="ordered", usage="context",
        anchors=(raw["anchors"][0]["anchor_id"],),
    )
    inspection["set_id"] = evidence_set_identity(inspection)
    raw["evidence_sets"] = tuple(
        inspection if row["set_id"] == old_set else row for row in raw["evidence_sets"]
    )
    label.clear()
    label.update(
        role="row_label", kind="literal", state=state, meaning_changing=True,
        evidence_status="available", evidence_sets=(inspection["set_id"],),
        reason="controlled independently located row-label inspection",
    )
    finish(raw)
    candidate = bind(raw, contexts)
    instance = RecordAcceptanceInstance(
        feature=feature, calibration=calibrated(feature), threshold=0.6,
        threshold_procedure="fixed threshold before final assessment",
        conditioning_assumptions="native source custody required",
    )
    proposal = assess_record_admission(
        prepared, candidate, instance, subset="native-tables", final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert "required_role_not_present:row_label" not in proposal.blockers
    assert "missing_located_evidence:row_label" not in proposal.blockers
    assert ("unresolved_meaning:row_label" in proposal.blockers) is (state == "unresolved")
    if state == "unresolved":
        assert not proposal.eligible_for_native_validation


def test_calibration_without_binary_support_cannot_export_a_map():
    feature = fitted()
    rows = tuple(
        FinalEventObservation(
            feature_instance_digest=feature.digest,
            event_procedure="uncoupled-whole-reading-1",
            final_event_score=float(index - 5),
            label=WholeReadingLabel(
                event_id=f"all-wrong:{index}",
                origin_group=f"source:{index}",
                correct=False,
            ),
        )
        for index in range(4)
    )
    result = fit_final_event_calibration(
        rows,
        feature=feature,
        frame=frame((row.label.event_id for row in rows), calibration=True),
        event_procedure="uncoupled-whole-reading-1",
    )
    assert result.calibration is None
    assert result.diagnostics.standing == "provisional"
    with pytest.raises(ValueError, match="event procedure"):
        fit_final_event_calibration(
            rows,
            feature=feature,
            frame=frame((row.label.event_id for row in rows), calibration=True),
            event_procedure="different-coupled-event-procedure",
        )


def policy_for_reading(prepared, row):
    data = fitted().model_dump(mode="python")
    data["algorithm"]["version"] = row["policy_version"]
    data["applicability"]["release_id"] = prepared.release_id
    data["applicability"]["family"] = row["family"]
    feature = FeatureInstance.model_validate(data)
    return RecordAcceptanceInstance(
        feature=feature,
        calibration=calibrated(feature),
        threshold=0.6,
        threshold_procedure="predeclared finite-cut threshold",
        conditioning_assumptions="finite supplied source cut; native custody still required",
    )


@pytest.mark.parametrize("state", ["unstated", "inapplicable"])
def test_nonpresent_literal_inspection_scope_supports_complete_candidate_lowering(state):
    from .test_record_assertions import inputs, lower, record, seal

    overrides = {
        role: {
            "state": "present",
            "value": {"kind": "native_location", "pointer": "#/inspected/" + role},
        }
        for role in ("table", "cell")
    }
    overrides.update(
        {
            role: {
                "state": "present",
                "pieces": text,
                "original": text,
                "value": {"kind": "text", "text": text},
            }
            for role, text in (
                ("row_label", "Group A"),
                ("header_path", "Count"),
                ("cell_value", "12"),
            )
        }
    )
    row = record(overrides=overrides)
    caption = next(field for field in row["fields"] if field["role"] == "caption")
    caption["state"] = state
    seal(row)
    prepared = inputs()[2]
    instance = policy_for_reading(prepared, row)
    proposal = assess_record_admission(
        prepared,
        row,
        instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert proposal.blockers == ()
    assert proposal.eligible_for_native_validation
    assert proposal.standing == "candidate"
    lowered = lower(row)
    assert lowered.diagnostics == ()
    assert len(lowered.assertions) == 8
    assert lowered.batch.selection == ()
    # A present literal still needs exact value evidence, unlike the inspected absence.
    cell_value = next(field for field in row["fields"] if field["role"] == "cell_value")
    value_set = next(item for item in row["evidence_sets"] if item["role"] == "cell_value")
    value_anchor = next(
        anchor for anchor in row["anchors"] if anchor["anchor_id"] == value_set["anchors"][0]
    )
    value_anchor["precision"] = "item"
    assert cell_value["state"] == "present"
    refusal = assess_record_admission(
        prepared,
        row,
        instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert "unlocated_field_evidence:cell_value" in refusal.blockers
    assert not refusal.eligible_for_native_validation


def test_supplemental_transformed_role_requires_its_own_located_support():
    from .test_record_assertions import inputs, record

    overrides = {
        role: {
            "state": "present",
            "pieces": text,
            "original": text,
            "value": {"kind": "text", "text": text},
        }
        for role, text in (("referent", "bottle"), ("property", "volume"))
    }
    overrides["original_value"] = {
        "state": "present",
        "pieces": "12",
        "original": "12",
        "value": {"kind": "decimal", "lexical": "12"},
    }
    overrides["value_role"] = {
        "state": "present",
        "pieces": "average",
        "value": {"kind": "measurement_value_role", "label": "mean"},
    }
    row = record("MeasurementRecordFields", overrides=overrides)
    prepared = inputs()[2]
    instance = policy_for_reading(prepared, row)
    supported = assess_record_admission(
        prepared,
        row,
        instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert supported.blockers == ()
    assert supported.eligible_for_native_validation
    supplemental = next(field for field in row["fields"] if field["role"] == "normalized_value")
    assert not supplemental["meaning_changing"]
    supplemental["evidence_status"] = "unavailable"
    supplemental["evidence_sets"] = ()
    proposal = assess_record_admission(
        prepared,
        row,
        instance,
        subset="native-tables",
        final_event_score=100.0,
        event_procedure="uncoupled-whole-reading-1",
    )
    assert "missing_located_evidence:normalized_value" in proposal.blockers
    assert not proposal.eligible_for_native_validation


@pytest.mark.parametrize("minimum,expected", [(1, "fitted"), (2, "provisional")])
def test_declared_origin_minimum_scopes_both_fits_without_claiming_independence(minimum, expected):
    algo = algorithm(minimum_origin_groups=minimum)
    original, selected = training(algo=algo)
    assumption = (
        "Finite supplied source cut only; no unseen-origin claim. "
        "Native checks fit/calibration partition and origin disjointness."
    )
    frame_data = selected.model_dump(mode="python")
    frame_data["assumptions"] = assumption
    selected = FittingFrame.model_validate(frame_data)
    single_origin = tuple(
        FeatureFitObservation(
            features=row.features,
            label=WholeReadingLabel(
                event_id=row.label.event_id,
                origin_group="source:GS",
                correct=row.label.correct,
                sample_weight=row.label.sample_weight,
            ),
        )
        for row in original
    )
    result = fit_whole_reading_features(
        single_origin, algorithm=algo, applicability=applicability(), frame=selected
    )
    assert result.diagnostics.standing == expected
    assert result.diagnostics.declared_origin_group_count == 1
    assert result.diagnostics.conditioning_assumptions == assumption
    assert (result.instance is not None) == (minimum == 1)
    # A supported feature fit isolates the calibration minimum when the default refuses GS.
    feature = result.instance
    if feature is None:
        feature = fit_whole_reading_features(
            original, algorithm=algo, applicability=applicability(), frame=selected
        ).instance
    assert feature is not None
    rows = tuple(
        FinalEventObservation(
            feature_instance_digest=feature.digest,
            event_procedure="uncoupled-whole-reading-1",
            final_event_score=float(index - 2.5),
            label=WholeReadingLabel(
                event_id=f"single-cal:{index}",
                origin_group="source:Forbes",
                correct=index >= 3,
            ),
        )
        for index in range(6)
    )
    calibration_frame = frame((row.label.event_id for row in rows), calibration=True)
    calibration_data = calibration_frame.model_dump(mode="python")
    calibration_data["assumptions"] = assumption
    calibration_result = fit_final_event_calibration(
        rows,
        feature=feature,
        frame=FittingFrame.model_validate(calibration_data),
        event_procedure="uncoupled-whole-reading-1",
    )
    assert calibration_result.diagnostics.standing == expected
    assert calibration_result.diagnostics.declared_origin_group_count == 1
    assert calibration_result.diagnostics.conditioning_assumptions == assumption
    assert (calibration_result.calibration is not None) == (minimum == 1)
    if result.instance is not None:
        changed = result.instance.model_dump(mode="python")
        changed["algorithm"]["minimum_origin_groups"] = 2
        with pytest.raises(ValidationError, match="fitted support"):
            FeatureInstance.model_validate(changed)
    with pytest.raises(ValidationError):
        algorithm(minimum_origin_groups=0)
