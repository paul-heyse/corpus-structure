"""Finite operation-event parameters and applicability; no labels or publication authority."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

OperationEvent = Literal["defined_by_correctness", "defining_text_attachment_correctness"]

DEFAULT_OPERATION_EVENT: OperationEvent = "defined_by_correctness"


class EventContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class OperationEventAlgorithm(EventContract):
    algorithm: Literal["scaled-logistic-operation-event-1"] = "scaled-logistic-operation-event-1"
    regularization_c: FiniteFloat = Field(default=1.0, gt=0)
    solver: Literal["lbfgs"] = "lbfgs"
    tolerance: FiniteFloat = Field(default=1e-6, gt=0)
    max_iterations: int = Field(default=2000, ge=1)
    weights: Literal["unit"] = "unit"


class OperationEventParameters(EventContract):
    algorithm: OperationEventAlgorithm
    event: OperationEvent
    event_version: str
    producer_version: str
    feature_names: tuple[str, ...]
    frame_digest: str = Field(pattern="^[0-9a-f]{64}$")
    corpus_id: str = Field(min_length=1)
    rubric_digest: str = Field(pattern="^[0-9a-f]{64}$")
    reference_digest: str = Field(pattern="^[0-9a-f]{64}$")
    assessment_mode: Literal["in_sample_development"] = "in_sample_development"
    means: tuple[FiniteFloat, ...]
    scales: tuple[FiniteFloat, ...]
    coefficients: tuple[FiniteFloat, ...]
    intercept: FiniteFloat

    @model_validator(mode="after")
    def shape(self) -> Self:
        n = len(self.feature_names)
        if len(set(self.feature_names)) != n or any(not name for name in self.feature_names):
            raise ValueError("operation parameter features must be distinct and named")
        if (
            not n
            or any(len(v) != n for v in (self.means, self.scales, self.coefficients))
            or any(v <= 0 for v in self.scales)
        ):
            raise ValueError("operation parameters have inconsistent scaling/feature shape")
        return self


def score_operation_event(
    parameters: OperationEventParameters,
    features: tuple[float, ...],
    *,
    corpus_id: str,
    event_version: str,
    producer_version: str,
    event: OperationEvent = DEFAULT_OPERATION_EVENT,
) -> float:
    import numpy as np
    from scipy.special import expit

    if (corpus_id, event, event_version, producer_version) != (
        parameters.corpus_id,
        parameters.event,
        parameters.event_version,
        parameters.producer_version,
    ):
        raise ValueError("operation score applicability differs from fitted corpus/event/producer")
    if len(features) != len(parameters.feature_names) or not np.isfinite(features).all():
        raise ValueError("operation feature shape or finite values differ")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        x = (np.asarray(features) - parameters.means) / parameters.scales
        linear = np.dot(x, parameters.coefficients) + parameters.intercept
    return float(expit(linear))
