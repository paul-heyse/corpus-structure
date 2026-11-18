"""Finite operation-event parameters and applicability; no labels or publication authority."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import log1p
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

OperationEvent = Literal["defined_by_correctness", "defining_text_attachment_correctness"]

DEFAULT_OPERATION_EVENT: OperationEvent = "defined_by_correctness"

ATTACHMENT_EVENT_VERSION = "defining-text-attachment-scope-features-2"
ATTACHMENT_FEATURE_NAMES = (
    "term_log_length",
    "content_log_length",
    "signed_passage_separation",
    "declared_cue",
)
_DEFINITION_CUE = re.compile(r"\b(?:is defined as|is called|we call|denoted by)\b")
_FEATURE_WHITESPACE = (
    "\t\n\v\f\r \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005"
    "\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)


@dataclass(frozen=True)
class DefiningTextFeatures:
    features: tuple[float, float, float, float] | None
    reason: Literal["missing_common_passage", "incomparable_endpoint_anchors"] | None = None


def defining_text_features(
    source_view_id: int,
    body: str,
    pieces: Sequence[Mapping],
    term: Sequence[Mapping],
    content: Sequence[Mapping],
) -> DefiningTextFeatures:
    """Map exact native anchors into their single common projected passage."""
    if not body:
        return DefiningTextFeatures(None, "missing_common_passage")

    def extent(anchors):
        spans = []
        for anchor in anchors:
            start, end = anchor.get("start"), anchor.get("end")
            if (
                anchor.get("pin", {}).get("source_view_id") != source_view_id
                or (anchor.get("space"), anchor.get("precision")) != ("native", "exact")
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start < end
            ):
                return None
            positions = [
                piece["start"]
                for piece in pieces
                if piece["kind"] == "native_text"
                and piece.get("source_field", "text") == "text"
                and "cell_index" not in piece
                and piece["item_ref"] == anchor["pointer"]
                and end <= piece["end"] - piece["start"]
            ]
            if len(positions) != 1:
                return None
            begin, finish = positions[0] + start, positions[0] + end
            if finish > len(body) or body[begin:finish] != anchor["source_piece"]:
                return None
            spans.append((begin, finish))
        if not spans:
            return None
        spans.sort()
        low, high = spans[0]
        length = high - low
        for start, end in spans[1:]:
            length += max(0, end - max(start, high))
            high = max(high, end)
        return low, high, length

    term_extent, content_extent = extent(term), extent(content)
    if term_extent is None or content_extent is None:
        return DefiningTextFeatures(None, "incomparable_endpoint_anchors")
    return defining_text_feature_values(body, term_extent, content_extent)


def defining_text_feature_values(
    body: str, term_extent: tuple[int, int, int], content_extent: tuple[int, int, int]
) -> DefiningTextFeatures:
    """Existing arithmetic after the source owner establishes exact common-passage spans.

    Extents are passage-relative (start, end, union character length). This numeric
    function grants neither source custody nor linguistic correctness.
    """
    if not body or any(
        not 0 <= start < end <= len(body) or not 0 < length <= end - start
        for start, end, length in (term_extent, content_extent)
    ):
        raise ValueError("defining-text features require exact nonempty passage extents")
    t0, t1, term_length = term_extent
    c0, c1, content_length = content_extent
    separation = c0 - t1 if c0 >= t1 else c1 - t0 if t0 >= c1 else 0
    normalized = " ".join(
        token for token in re.split("[" + _FEATURE_WHITESPACE + "]+", body.casefold()) if token
    )
    return DefiningTextFeatures(
        (
            log1p(term_length),
            log1p(content_length),
            separation / len(body),
            float(_DEFINITION_CUE.search(normalized) is not None),
        )
    )


class EventContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class OperationEventAlgorithm(EventContract):
    algorithm: Literal["scaled-logistic-operation-event-1"] = "scaled-logistic-operation-event-1"
    regularization_c: FiniteFloat = Field(default=1.0, gt=0)
    solver: Literal["lbfgs"] = "lbfgs"
    tolerance: FiniteFloat = Field(default=1e-6, gt=0)
    max_iterations: int = Field(default=2000, ge=1)
    weights: Literal["unit"] = "unit"


class OperationScoreNumericalPolicy(EventContract):
    """The actual native arithmetic policy; canonical result equality stays exact."""

    version: Literal["operation-score-numerics-v1"] = "operation-score-numerics-v1"
    numpy_version: str = Field(min_length=1)
    scipy_version: str = Field(min_length=1)
    dtype: Literal["float64"] = "float64"
    device: Literal["cpu"] = "cpu"
    backend: Literal["numpy-scipy-native"] = "numpy-scipy-native"
    preprocessing: Literal["fitted-centering-and-scaling"] = "fitted-centering-and-scaling"
    overflow: Literal["raise"] = "raise"
    invalid: Literal["raise"] = "raise"
    divide: Literal["raise"] = "raise"
    underflow: Literal["ignore"] = "ignore"
    result_equality: Literal["exact-canonical-value"] = "exact-canonical-value"
    nondeterminism: Literal["backend-dependent-result-bits"] = "backend-dependent-result-bits"


def operation_score_numerical_policy() -> OperationScoreNumericalPolicy:
    import numpy as np
    import scipy

    return OperationScoreNumericalPolicy(
        numpy_version=np.__version__, scipy_version=scipy.__version__
    )


class OperationEventParameters(EventContract):
    numerical: OperationScoreNumericalPolicy
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
    return OperationEventScore().run(
        parameters,
        features,
        corpus_id=corpus_id,
        event_version=event_version,
        producer_version=producer_version,
        event=event,
    )


class OperationEventScore:
    """Declared score owner with its original static native acquisition method."""

    __data_operation__: ClassVar[dict] = {
        "id": "urn:corpus:operation:score-operation-event",
        "profile": "derivation",
        "subject": "fitted-operation-event",
        "subject_definition": {
            "id": "fitted-operation-event",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": ["corpus_id", "event", "event_version", "producer_version"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "parameters",
                "parameter": "parameters",
                "kind": "urn:corpus:kind:operation-event:parameters",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "source": "frozen-source-set",
                    "source_set": "operation-event-parameters",
                    "coverage": {"role": "parameters", "description": "ordered-feature-schema"},
                },
            },
            {
                "name": "features",
                "parameter": "features",
                "kind": "float",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "source": "same-event-subject",
                    "coverage": {"role": "features", "description": "all-fitted-features"},
                },
            },
            {
                "name": "probability",
                "kind": "float",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {
                "kind": "binding",
                "reference": "urn:corpus:operation:score-operation-event/binding",
                "interpretation": "binding-expression-v1",
                "parameters": {},
            },
            {"kind": "documentation", "text": "exact-fitted-corpus-event-version-producer"},
        ],
        "invariants": [
            {"kind": "documentation", "text": "finite-features"},
            {"kind": "documentation", "text": "matching-feature-shape"},
            {"kind": "documentation", "text": "probability-in-unit-interval"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "one-score-for-complete-feature-vector",
        },
        "outcomes": ["scored", "invalid-applicability", "invalid-feature-shape", "numerical-failure"],
        "state_dimensions": [{"name": "completion", "values": ["pending", "success", "failed"]}],
        "transitions": [
            {"dimension": "completion", "before": "pending", "after": "success", "outcome": "scored"},
            {
                "dimension": "completion",
                "before": "pending",
                "after": "failed",
                "outcome": "invalid-applicability",
            },
            {
                "dimension": "completion",
                "before": "pending",
                "after": "failed",
                "outcome": "invalid-feature-shape",
            },
            {
                "dimension": "completion",
                "before": "pending",
                "after": "failed",
                "outcome": "numerical-failure",
            },
        ],
        "precision_description": None,
        "numerical_policy": {
            "asset": "operation-score/numerical-policy",
            "pointer": "/policy",
            "kind": "urn:corpus:kind:operation-event:OperationScoreNumericalPolicy",
        },
        "assets": [
            {
                "reference": "operation-score-policy",
                "contract": "operation-score/numerical-policy",
                "role": "numerical-policy",
            }
        ],
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "operation-event-logistic-score-v1",
        "parameters": {
            "corpus_id": {"value_type": "string", "required": True},
            "event_version": {"value_type": "string", "required": True},
            "producer_version": {"value_type": "string", "required": True},
            "event": {"value_type": "string", "default": "defined_by_correctness"},
        },
        "binding": {"operator": "scan", "roles": ["parameters", "features"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.operation_policy.operation_score_numerical_policy",
                "contract": "operation-score/numerical-policy",
                "role": "checked-native-arithmetic-policy",
            },
            {
                "reference": "numpy",
                "contract": "numpy-float64-array-arithmetic-v1",
                "role": "numerical-algorithm",
            },
            {
                "reference": "scipy.special.expit",
                "contract": "scipy-expit-v1",
                "role": "numerical-algorithm",
            },
            {
                "reference": "pydantic",
                "contract": "pydantic2-operation-event-ingress-v1",
                "role": "typed-validation",
            },
            {"reference": "typing", "contract": "python-3.14-typing-v1", "role": "type-interpretation"},
        ],
        "bound_inputs": ["parameters"],
    }

    def run(
        self,
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

        policy = parameters.numerical
        if policy != operation_score_numerical_policy():
            raise ValueError(
                "operation score numerical policy differs from the selected native libraries"
            )
        if (corpus_id, event, event_version, producer_version) != (
            parameters.corpus_id,
            parameters.event,
            parameters.event_version,
            parameters.producer_version,
        ):
            raise ValueError("operation score applicability differs from fitted corpus/event/producer")
        if len(features) != len(parameters.feature_names) or not np.isfinite(features).all():
            raise ValueError("operation feature shape or finite values differ")
        with np.errstate(
            over=policy.overflow, invalid=policy.invalid, divide=policy.divide, under=policy.underflow
        ):
            x = (np.asarray(features, dtype=policy.dtype) - parameters.means) / parameters.scales
            linear = np.dot(x, parameters.coefficients) + parameters.intercept
            result = float(expit(linear))
        if not np.isfinite(result) or not 0 <= result <= 1:
            raise ValueError("operation score is not a finite probability")
        return result

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.evaluate.declared_operation_events import acquire_score_port

        return acquire_score_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
