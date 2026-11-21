"""Operation-event fitting on an explicitly shared development corpus.

Labels are evaluator inputs. Finite runtime parameters carry frame provenance, never
labels or permission to publish. In-sample diagnostics answer a development question;
they establish neither held-out performance nor calibrated factual correctness.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Literal, Protocol, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from corpus_structure.methods.contextual_embeddings import numeric_identity
from corpus_structure.semantic.operation_policy import (
    DEFAULT_OPERATION_EVENT,
    OperationEvent,
    OperationEventAlgorithm,
    OperationEventParameters,
    operation_score_numerical_policy,
)
from corpus_structure.semantic.operation_policy import (
    score_operation_event as score_operation_event,
)


class EventContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


EventJudgment = Literal["supported", "unsupported", "ambiguous", "unassessed"]
AttachmentFacet = Literal[
    "attachment_head", "attachment_tail", "attachment_direction", "attachment_scope"
]


class NumericEventObservation(Protocol):
    """Only values used by the shared numerical algorithm."""

    @property
    def event_id(self) -> str: ...
    @property
    def features(self) -> Sequence[float]: ...
    @property
    def judgment(self) -> EventJudgment: ...


class NumericEventFrame(Protocol):
    """The frame owner authenticates population/provenance and commits its identity."""

    @property
    def fit_digest(self) -> str: ...
    @property
    def fit_origin_group_count(self) -> int | None: ...
    @property
    def observations(self) -> Sequence[NumericEventObservation]: ...
    @property
    def event(self) -> OperationEvent: ...
    @property
    def event_version(self) -> str: ...
    @property
    def producer_version(self) -> str: ...
    @property
    def feature_names(self) -> tuple[str, ...]: ...
    @property
    def corpus_id(self) -> str: ...
    @property
    def rubric_digest(self) -> str: ...
    @property
    def reference_digest(self) -> str: ...


class OperationEventSighting(EventContract):
    origin_task_id: int = Field(gt=0)
    source_view_id: int = Field(gt=0)
    contribution_id: str = Field(min_length=1)
    judgment: EventJudgment
    facets: dict[AttachmentFacet, EventJudgment]
    disagreements: tuple[AttachmentFacet, ...]


class OperationEventObservation(EventContract):
    event_id: str = Field(min_length=1)
    contribution_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    features: tuple[FiniteFloat, ...]
    judgment: EventJudgment
    origin_group: str | None = None
    sightings: tuple[OperationEventSighting, ...] = ()


class UnavailableOperationEventFeatures(EventContract):
    event_id: str
    reason: Literal["missing_common_passage", "incomparable_endpoint_anchors"]
    sightings: tuple[OperationEventSighting, ...] = ()


class OperationEventFrame(EventContract):
    protocol: Literal["operation-event-development-1"] = "operation-event-development-1"
    event: OperationEvent = DEFAULT_OPERATION_EVENT
    event_version: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    rubric_digest: str = Field(min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")
    reference_digest: str = Field(min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")
    corpus_id: str = Field(min_length=1)
    feature_names: tuple[str, ...] = Field(min_length=1)
    event_ids: tuple[str, ...]
    observations: tuple[OperationEventObservation, ...]
    feature_unavailable: tuple[UnavailableOperationEventFeatures, ...] | None = None
    assessment_mode: Literal["in_sample_development"] = "in_sample_development"

    @model_validator(mode="after")
    def population(self) -> Self:
        if len(set(self.feature_names)) != len(self.feature_names) or any(
            not n for n in self.feature_names
        ):
            raise ValueError("event features require distinct names")
        if self.event_ids != tuple(o.event_id for o in self.observations) or len(
            set(self.event_ids)
        ) != len(self.event_ids):
            raise ValueError("event frame requires exact ordered distinct membership")
        if any(len(o.features) != len(self.feature_names) for o in self.observations):
            raise ValueError("event feature shape differs from declared order")
        if self.event != DEFAULT_OPERATION_EVENT and (
            self.feature_unavailable is None or any(not o.origin_group for o in self.observations)
        ):
            raise ValueError("attachment event requires authenticated origin and feature coverage")
        if self.feature_unavailable is not None:
            unavailable = {row.event_id for row in self.feature_unavailable}
            if len(unavailable) != len(self.feature_unavailable) or unavailable.intersection(
                self.event_ids
            ):
                raise ValueError("unavailable events must be distinct from scored events")
        return self

    @property
    def fit_digest(self) -> str:
        """Legacy frame identity remains owned here until its actual callers retire."""
        value = self.model_dump(mode="json")
        if self.feature_unavailable is None:
            del value["feature_unavailable"]
        for unavailable in value.get("feature_unavailable", ()):
            if not unavailable["sightings"]:
                del unavailable["sightings"]
        for observation in value["observations"]:
            if observation["origin_group"] is None:
                del observation["origin_group"]
            if not observation["sightings"]:
                del observation["sightings"]
        return numeric_identity("frame", value).removeprefix("frame:")

    @property
    def fit_origin_group_count(self) -> int | None:
        if self.event == DEFAULT_OPERATION_EVENT:
            return None
        return len({o.origin_group for o in self.observations if o.origin_group is not None})


class EventPrediction(EventContract):
    event_id: str = Field(min_length=1)
    judgment: Literal["supported", "unsupported", "ambiguous", "unassessed"]
    prior_probability: FiniteFloat = Field(ge=0, le=1)
    fitted_probability: FiniteFloat | None = Field(default=None, ge=0, le=1)


class OperationEventFitResult(EventContract):
    protocol: Literal["operation-event-fit-result-1"] = "operation-event-fit-result-1"
    status: Literal["fitted", "unavailable", "failed"]
    reason: str
    frame_digest: str
    assessment_mode: Literal["in_sample_development"] = "in_sample_development"
    origin_requirement: Literal["none"] = "none"
    observations: int
    labeled: int
    positive: int
    negative: int
    origin_groups: int | None = None
    warnings: tuple[str, ...] = ()
    iterations: int | None = None
    parameters: OperationEventParameters | None = None
    predictions: tuple[EventPrediction, ...] = ()
    prior_brier: FiniteFloat | None = None
    fitted_brier: FiniteFloat | None = None
    prior_log_loss: FiniteFloat | None = None
    fitted_log_loss: FiniteFloat | None = None

    @model_validator(mode="after")
    def result_invariants(self) -> Self:
        if (
            min(self.observations, self.labeled, self.positive, self.negative) < 0
            or self.labeled != self.positive + self.negative
            or self.labeled > self.observations
        ):
            raise ValueError("operation fit class counts differ from observation population")
        if self.predictions and (
            len(self.predictions) != self.observations
            or len({p.event_id for p in self.predictions}) != len(self.predictions)
            or sum(p.judgment == "supported" for p in self.predictions) != self.positive
            or sum(p.judgment == "unsupported" for p in self.predictions) != self.negative
        ):
            raise ValueError("operation fit predictions differ from declared event population")
        if self.status == "fitted":
            if (
                self.parameters is None
                or not self.positive
                or not self.negative
                or len(self.predictions) != self.observations
                or any(p.fitted_probability is None for p in self.predictions)
                or self.parameters.frame_digest != self.frame_digest
            ):
                raise ValueError("fitted operation result requires complete parameters/predictions")
        elif self.parameters is not None or any(
            p.fitted_probability is not None for p in self.predictions
        ):
            raise ValueError(
                "nonfitted operation result cannot carry fitted parameters/probabilities"
            )
        return self


def _fit_operation_event(
    frame: NumericEventFrame, algorithm: OperationEventAlgorithm | None = None
) -> OperationEventFitResult:
    algorithm = algorithm or OperationEventAlgorithm()
    digest = frame_digest(frame)
    labeled = [o for o in frame.observations if o.judgment in {"supported", "unsupported"}]
    y = np.asarray([o.judgment == "supported" for o in labeled], dtype=bool)
    positive = int(y.sum())
    negative = len(y) - positive
    base = dict(
        frame_digest=digest,
        observations=len(frame.observations),
        labeled=len(labeled),
        positive=positive,
        negative=negative,
        origin_groups=frame.fit_origin_group_count,
    )
    if not labeled:
        return OperationEventFitResult(
            **base,
            status="unavailable",
            reason="No independently judged binary events; ambiguous/unassessed are not negatives.",
        )
    x = np.asarray([o.features for o in labeled], dtype=float)
    all_x = np.asarray([o.features for o in frame.observations], dtype=float)
    prior = DummyClassifier(strategy="prior").fit(x, y)
    prior_values = prior.predict_proba(all_x)
    if not isinstance(prior_values, np.ndarray):
        raise ValueError("single operation-event fit requires one probability matrix")
    prior_p = (
        prior_values[:, list(prior.classes_).index(True)]
        if True in prior.classes_
        else np.zeros(len(all_x))
    )

    def predictions(fitted=None):
        return tuple(
            EventPrediction(
                event_id=o.event_id,
                judgment=o.judgment,
                prior_probability=float(prior_p[i]),
                fitted_probability=None if fitted is None else float(fitted[i]),
            )
            for i, o in enumerate(frame.observations)
        )

    p = np.full(len(y), positive / len(y))
    metrics = dict(
        prior_brier=float(brier_score_loss(y, p)),
        prior_log_loss=float(log_loss(y, p, labels=[False, True])),
    )
    if not positive or not negative:
        return OperationEventFitResult(
            **base,
            **metrics,
            status="unavailable",
            reason="Logistic fitting requires both correctness classes; prior retained.",
            predictions=predictions(),
        )
    pipeline = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "event",
                LogisticRegression(
                    C=algorithm.regularization_c,
                    solver=algorithm.solver,
                    tol=algorithm.tolerance,
                    max_iter=algorithm.max_iterations,
                    l1_ratio=0,
                ),
            ),
        ]
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        pipeline.fit(x, y)
    diagnostics = tuple(str(w.message) for w in caught)
    estimator = pipeline.named_steps["event"]
    scaler = pipeline.named_steps["scale"]
    iterations = int(np.max(estimator.n_iter_))
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        return OperationEventFitResult(
            **base,
            **metrics,
            status="failed",
            reason="Operation optimizer did not converge; no runtime parameters admitted.",
            warnings=diagnostics,
            iterations=iterations,
            predictions=predictions(),
        )
    parameters = OperationEventParameters(
        numerical=operation_score_numerical_policy(),
        algorithm=algorithm,
        event=frame.event,
        event_version=frame.event_version,
        producer_version=frame.producer_version,
        feature_names=frame.feature_names,
        frame_digest=digest,
        corpus_id=frame.corpus_id,
        rubric_digest=frame.rubric_digest,
        reference_digest=frame.reference_digest,
        means=tuple(scaler.mean_),
        scales=tuple(scaler.scale_),
        coefficients=tuple(estimator.coef_[0]),
        intercept=float(estimator.intercept_[0]),
    )
    fitted = pipeline.predict_proba(all_x)[:, list(estimator.classes_).index(True)]
    labeled_p = pipeline.predict_proba(x)[:, list(estimator.classes_).index(True)]
    return OperationEventFitResult(
        **base,
        **metrics,
        status="fitted",
        reason="Same-corpus development fit and diagnostics; no held-out or calibration claim.",
        warnings=diagnostics,
        iterations=iterations,
        parameters=parameters,
        predictions=predictions(fitted),
        fitted_brier=float(brier_score_loss(y, labeled_p)),
        fitted_log_loss=float(log_loss(y, labeled_p, labels=[False, True])),
    )


def fit_operation_event(
    frame: NumericEventFrame, algorithm: OperationEventAlgorithm | None = None
) -> OperationEventFitResult:
    try:
        return _fit_operation_event(frame, algorithm)
    except (ValueError, ArithmeticError) as error:
        return OperationEventFitResult(
            status="failed",
            reason=f"Numerical fitting failed: {type(error).__name__}: {error}",
            frame_digest=frame_digest(frame),
            observations=len(frame.observations),
            origin_groups=frame.fit_origin_group_count,
            labeled=sum(o.judgment in {"supported", "unsupported"} for o in frame.observations),
            positive=sum(o.judgment == "supported" for o in frame.observations),
            negative=sum(o.judgment == "unsupported" for o in frame.observations),
        )


def frame_digest(frame: NumericEventFrame) -> str:
    """Use the exact identity supplied by this frame's canonical owner."""
    return frame.fit_digest
