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

from .test_record_contracts import bind, release_inputs, table_record


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
