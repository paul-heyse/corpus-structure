"""Shared controlled inputs and builders for record policy support."""

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
    PolicyApplicability,
    RecordAlgorithm,
    RecordFeatures,
)


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
