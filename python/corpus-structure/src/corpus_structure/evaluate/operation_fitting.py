"""Operation-event fitting on an explicitly shared development corpus.

Labels are evaluator inputs. Finite runtime parameters carry frame provenance, never
labels or permission to publish. In-sample diagnostics answer a development question;
they establish neither held-out performance nor calibrated factual correctness.
"""

from __future__ import annotations

import warnings
from hashlib import sha256
from typing import Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_policy import (
    OperationEventAlgorithm,
    OperationEventParameters,
)
from corpus_structure.semantic.operation_policy import (
    score_operation_event as score_operation_event,
)


class EventContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class OperationEventObservation(EventContract):
    event_id: str = Field(min_length=1)
    contribution_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    features: tuple[FiniteFloat, ...]
    judgment: Literal["supported", "unsupported", "ambiguous", "unassessed"]


class OperationEventFrame(EventContract):
    protocol: Literal["operation-event-development-1"] = "operation-event-development-1"
    event: Literal["defined_by_correctness"] = "defined_by_correctness"
    event_version: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    rubric_digest: str = Field(pattern="^[0-9a-f]{64}$")
    reference_digest: str = Field(pattern="^[0-9a-f]{64}$")
    corpus_id: str = Field(min_length=1)
    feature_names: tuple[str, ...] = Field(min_length=1)
    event_ids: tuple[str, ...]
    observations: tuple[OperationEventObservation, ...]
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
        return self


class NativeOperationEventFrame(EventContract):
    protocol: Literal["native-operation-event-frame-1"]
    project_id: str = Field(min_length=1)
    evaluation_id: int = Field(gt=0)
    run_id: int = Field(gt=0)
    cut_id: int = Field(gt=0)
    release_id: str = Field(min_length=1)
    set_id: int = Field(gt=0)
    evaluation_digest: str = Field(pattern="^[0-9a-f]{64}$")
    reference_snapshot: tuple[dict[str, object], ...]
    source_frame_digest: str = Field(pattern="^[0-9a-f]{64}$")
    frame: OperationEventFrame


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
    frame: OperationEventFrame, algorithm: OperationEventAlgorithm | None = None
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
    frame: OperationEventFrame, algorithm: OperationEventAlgorithm | None = None
) -> OperationEventFitResult:
    try:
        return _fit_operation_event(frame, algorithm)
    except (ValueError, ArithmeticError) as error:
        return OperationEventFitResult(
            status="failed",
            reason=f"Numerical fitting failed: {type(error).__name__}: {error}",
            frame_digest=frame_digest(frame),
            observations=len(frame.observations),
            labeled=sum(o.judgment in {"supported", "unsupported"} for o in frame.observations),
            positive=sum(o.judgment == "supported" for o in frame.observations),
            negative=sum(o.judgment == "unsupported" for o in frame.observations),
        )


def frame_digest(frame: OperationEventFrame) -> str:
    """Hash numeric meaning identically to the native binary64 identity codec."""
    import struct

    value = frame.model_dump(mode="json")
    for observation in value["observations"]:
        observation["features"] = [
            {"native_float64": struct.pack("!d", feature).hex()}
            for feature in observation["features"]
        ]
    return sha256(canonical_bytes(value)).hexdigest()


def read_native_frame(
    conn, *, project_id: str, evaluation_id: int
) -> tuple[dict, OperationEventFrame]:
    """Capture protected labels plus exact completed source/cut/C premises."""
    import json

    from sqlalchemy import text

    value = conn.execute(
        text("SELECT eval.operation_event_fit_frame(:p,:e)"),
        {"p": project_id, "e": evaluation_id},
    ).scalar_one()
    native = NativeOperationEventFrame.model_validate_json(json.dumps(value))
    if native.project_id != project_id or native.evaluation_id != evaluation_id:
        raise ValueError("native operation frame differs from selected project/evaluation")
    return value, native.frame


def fit_native_operation_event(
    engine, *, project_id: str, evaluation_id: int, algorithm: OperationEventAlgorithm | None = None
) -> dict:
    """CPU fitting owns no database snapshot; immutable write rechecks all premises."""
    import json

    from sqlalchemy import text

    with engine.begin() as conn:
        native_frame, frame = read_native_frame(
            conn, project_id=project_id, evaluation_id=evaluation_id
        )
    result = fit_operation_event(frame, algorithm)
    with engine.begin() as conn:
        identity = conn.execute(
            text(
                "SELECT eval.record_operation_event_fit(:p,:e,CAST(:f AS jsonb),CAST(:r AS jsonb))"
            ),
            {
                "p": project_id,
                "e": evaluation_id,
                "f": json.dumps(native_frame),
                "r": result.model_dump_json(),
            },
        ).scalar_one()
        return read_native_fit(conn, project_id=project_id, fit_id=identity, protected=True)


def read_native_fit(conn, *, project_id: str, fit_id: int, protected: bool = False) -> dict:
    """Owned parameter-only export or explicitly protected diagnostic/label read."""
    import json

    from sqlalchemy import text

    value = conn.execute(
        text("SELECT eval.read_operation_event_fit(:p,:i,:s)"),
        {"p": project_id, "i": fit_id, "s": protected},
    ).scalar_one()
    if protected:
        result = OperationEventFitResult.model_validate_json(json.dumps(value["result"]))
        frame = OperationEventFrame.model_validate_json(json.dumps(value["frame"]["frame"]))
        if result.frame_digest != frame_digest(frame):
            raise ValueError("immutable operation fit differs from its selected event frame")
    elif value["parameters"] is not None:
        OperationEventParameters.model_validate_json(json.dumps(value["parameters"]))
    return value


def operation_event_fitting_native_sql() -> str:
    from pathlib import Path

    return (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("semantic/sql/operation_event_fitting.sql")
        .read_text()
    )
