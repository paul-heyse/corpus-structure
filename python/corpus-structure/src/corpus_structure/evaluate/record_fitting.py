"""Evaluator-side whole-reading fitting and separately held-out final-event calibration.

These local numerical operations do not read protected references, authorize principals,
seal native custody or certify model quality. Callers obtain labels through the existing
protected routes. Production contracts contain parameters/provenance, never these labels.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Self

import numpy as np
import sklearn
from numpy.typing import NDArray
from pydantic import Field, FiniteFloat, model_validator
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from corpus_structure.semantic.record_policy import (
    Digest,
    FeatureInstance,
    FinalEventCalibration,
    FitDiagnostics,
    FrozenContract,
    LinearParameters,
    Nonempty,
    PolicyApplicability,
    RecordAlgorithm,
    RecordFeatures,
)


class WholeReadingLabel(FrozenContract):
    """One independent full-reading correctness judgment, not a field label."""

    event_id: Nonempty
    origin_group: Nonempty
    correct: bool
    sample_weight: Annotated[FiniteFloat, Field(gt=0)] = 1.0


class FeatureFitObservation(FrozenContract):
    features: RecordFeatures
    label: WholeReadingLabel


class FinalEventObservation(FrozenContract):
    """One final-event score after the declared interpretation/constraint procedure."""

    feature_instance_digest: Digest
    event_procedure: Nonempty
    final_event_score: FiniteFloat
    label: WholeReadingLabel


class FittingFrame(FrozenContract):
    """Predeclared complete eligible/scored event membership; includes low-score readings.

    This descriptor is not proof of completeness. Native authenticates it against actual
    completed prediction/source closure. Coverage (including no-output sources) is separate
    from scored-event membership and cannot be inferred by counting accepted predictions.
    """

    frame_digest: Digest
    reference_digest: Digest
    coverage_digest: Digest
    event_ids: tuple[Nonempty, ...]
    provenance: Nonempty
    assumptions: Nonempty

    @model_validator(mode="after")
    def unique_membership(self) -> Self:
        if len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("fitting frame repeats a final-event identity")
        return self


class FeatureFitResult(FrozenContract):
    diagnostics: FitDiagnostics
    instance: FeatureInstance | None = None


class CalibrationFitResult(FrozenContract):
    diagnostics: FitDiagnostics
    calibration: FinalEventCalibration | None = None


def _membership(labels: Sequence[WholeReadingLabel], frame: FittingFrame) -> None:
    ids = tuple(label.event_id for label in labels)
    if len(ids) != len(set(ids)) or ids != frame.event_ids:
        raise ValueError("fit must cover the exact ordered complete eligible/scored event frame")


@dataclass(frozen=True)
class _NumericalFit:
    coefficients: NDArray[np.float64]
    intercept: float
    center: NDArray[np.float64]
    scale: NDArray[np.float64]


def _fit(
    values: np.ndarray,
    labels: Sequence[WholeReadingLabel],
    *,
    algorithm: RecordAlgorithm,
    frame: FittingFrame,
    partition: Literal["feature_fit", "final_event_calibration"],
) -> tuple[_NumericalFit | None, FitDiagnostics]:
    _membership(labels, frame)
    positive = sum(label.correct for label in labels)
    negative = len(labels) - positive
    declared_origin_groups = len({label.origin_group for label in labels})

    def diagnostic(
        reason: str,
        *,
        converged: bool = False,
        iterations: int = 0,
    ) -> FitDiagnostics:
        return FitDiagnostics(
            partition=partition,
            frame_digest=frame.frame_digest,
            reference_digest=frame.reference_digest,
            coverage_digest=frame.coverage_digest,
            provenance=frame.provenance,
            negative_count=negative,
            positive_count=positive,
            declared_origin_group_count=declared_origin_groups,
            conditioning_assumptions=frame.assumptions,
            converged=converged,
            iterations=iterations,
            standing="fitted" if converged else "provisional",
            reason=reason,
            library_version=f"scikit-learn-{sklearn.__version__}",
        )

    if min(positive, negative) < algorithm.minimum_per_class:
        return None, diagnostic("insufficient whole-reading class support")
    if declared_origin_groups < algorithm.minimum_origin_groups:
        return None, diagnostic("insufficient declared origin groups")
    weights = np.asarray([label.sample_weight for label in labels], dtype=np.float64)
    if not np.isfinite(weights.sum()):
        raise ValueError("sample weights have nonfinite total weight")
    if sklearn.__version__ != "1.9.1":
        raise RuntimeError("released fitting algorithm requires scikit-learn 1.9.1")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        center = np.mean(values, axis=0)
        scale = np.std(values, axis=0)
        scale = np.where(scale == 0, 1.0, scale)
        scaled = (values - center) / scale
    if not all(np.all(np.isfinite(array)) for array in (center, scale, scaled)):
        return None, diagnostic("nonfinite feature scaling")
    estimator = LogisticRegression(
        C=algorithm.inverse_regularization,
        l1_ratio=algorithm.l1_ratio,
        solver=algorithm.solver,
        tol=algorithm.tolerance,
        max_iter=algorithm.max_iterations,
        fit_intercept=True,
        class_weight=None,
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ConvergenceWarning)
        estimator.fit(
            scaled,
            np.asarray([int(label.correct) for label in labels]),
            sample_weight=weights,
        )
    iterations = int(np.max(estimator.n_iter_))
    converged = not any(issubclass(w.category, ConvergenceWarning) for w in captured)
    converged = converged and iterations < algorithm.max_iterations
    converged = converged and np.array_equal(estimator.classes_, np.asarray([0, 1]))
    converged = converged and all(
        np.all(np.isfinite(array)) for array in (estimator.coef_, estimator.intercept_)
    )
    if not converged:
        return None, diagnostic(
            "solver did not establish finite converged binary parameters", iterations=iterations
        )
    return (
        _NumericalFit(estimator.coef_[0], float(estimator.intercept_[0]), center, scale),
        diagnostic(
            "finite converged whole-reading binary fit; quality unestablished",
            converged=True,
            iterations=iterations,
        ),
    )


def fit_whole_reading_features(
    observations: Sequence[FeatureFitObservation],
    *,
    algorithm: RecordAlgorithm,
    applicability: PolicyApplicability,
    frame: FittingFrame,
) -> FeatureFitResult:
    """Fit L2 logistic compatibility scores to binary full-reading correctness labels.

    Grouped feature names/signature and training-derived scaling are explicit. Sample
    weights affect the regularized fit; no implicit class balancing or duplicated votes
    are introduced. Labels and origin groups remain evaluator-side only.
    """
    names = tuple(feature.name for feature in algorithm.features)
    for observation in observations:
        vector = observation.features
        if (vector.release_id, vector.family) != (applicability.release_id, applicability.family):
            raise ValueError("training reading is outside declared release/family applicability")
        if vector.names != names or vector.feature_signature != algorithm.feature_signature:
            raise ValueError("training feature signature/order differs from released algorithm")
        if observation.label.event_id != vector.interpretation_id:
            raise ValueError("whole-reading label does not bind the scored interpretation")
        if any(value is None for value in vector.values):
            raise ValueError("training raw feature unavailable; imputation is not declared")
    values = np.asarray([row.features.values for row in observations], dtype=np.float64).reshape(
        len(observations), len(names)
    )
    fitted, diagnostics = _fit(
        values,
        tuple(row.label for row in observations),
        algorithm=algorithm,
        frame=frame,
        partition="feature_fit",
    )
    if fitted is None:
        return FeatureFitResult(diagnostics=diagnostics)
    parameters = LinearParameters(
        feature_signature=algorithm.feature_signature,
        names=names,
        coefficients=tuple(float(value) for value in fitted.coefficients),
        center=tuple(float(value) for value in fitted.center),
        scale=tuple(float(value) for value in fitted.scale),
        intercept=fitted.intercept,
    )
    return FeatureFitResult(
        diagnostics=diagnostics,
        instance=FeatureInstance(
            algorithm=algorithm,
            applicability=applicability,
            parameters=parameters,
            fit=diagnostics,
        ),
    )


def fit_final_event_calibration(
    observations: Sequence[FinalEventObservation],
    *,
    feature: FeatureInstance,
    frame: FittingFrame,
    event_procedure: str,
) -> CalibrationFitResult:
    """Fit a separate sigmoid to held-out final-event scores, including unaccepted ones.

    The native evaluator route must authenticate partition, complete frozen score frame,
    independent judgments, feature-instance digest and source closure. A caller-authored
    frame is insufficient to grant calibrated production standing or acceptance.
    """
    if (
        frame.frame_digest == feature.fit.frame_digest
        or frame.reference_digest == feature.fit.reference_digest
    ):
        raise ValueError("final-event calibration requires a separate held-out frame/reference")
    if any(
        row.feature_instance_digest != feature.digest or row.event_procedure != event_procedure
        for row in observations
    ):
        raise ValueError("calibration score differs from frozen feature instance/event procedure")
    values = np.asarray([row.final_event_score for row in observations], dtype=np.float64).reshape(
        len(observations), 1
    )
    fitted, diagnostics = _fit(
        values,
        tuple(row.label for row in observations),
        algorithm=feature.algorithm,
        frame=frame,
        partition="final_event_calibration",
    )
    if fitted is None:
        return CalibrationFitResult(diagnostics=diagnostics)
    slope = float(fitted.coefficients[0] / fitted.scale[0])
    intercept = float(fitted.intercept - slope * fitted.center[0])
    return CalibrationFitResult(
        diagnostics=diagnostics,
        calibration=FinalEventCalibration(
            feature_instance_digest=feature.digest,
            event_procedure=event_procedure,
            slope=slope,
            intercept=intercept,
            fit=diagnostics,
            assumptions=frame.assumptions,
            coverage_digest=frame.coverage_digest,
        ),
    )
