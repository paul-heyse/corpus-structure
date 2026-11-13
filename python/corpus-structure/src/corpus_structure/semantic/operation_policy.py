"""Finite operation-event parameters and applicability; no labels or publication authority."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import log1p
from typing import Literal, Self

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


def read_defining_text_features(
    conn, *, project_id: str, run_id: int, cut_id: int, task_id: int, contribution_id: str
) -> DefiningTextFeatures:
    """Reconstruct runtime features from an exact completed, authorized occurrence."""
    from sqlalchemy import select

    from .contribution_queries import read_source_contributions
    from .metadata import table
    from .query import bind_completed_result
    from .refusals import SemanticRefusal
    from .source_views import load_source_view

    session = bind_completed_result(conn, run_id)
    runs = table("ops.run")
    if (
        session.completed_cut_id != cut_id
        or conn.scalar(select(runs.c.project_id).where(runs.c.id == run_id)) != project_id
    ):
        raise SemanticRefusal("defining-text features require the exact project and completed cut")
    selectors = dict(
        prepared=session.prepared,
        run_id=run_id,
        cut_id=cut_id,
        selected_task_id=task_id,
        include_details=True,
    )
    selected = read_source_contributions(conn, contribution_id=contribution_id, **selectors)
    if len(selected.contributions) != 1:
        raise SemanticRefusal("defining-text attachment is outside the selected task")
    relation = selected.contributions[0]
    if not relation["cut_member"] or (relation["kind"], relation["semantic_type"]) != (
        "relation",
        "definition.defining_text_attachment",
    ):
        raise SemanticRefusal("selected contribution is not an exact defining-text attachment")
    operations = table("kb.source_contribution_operation")
    producer = conn.scalar(
        select(operations.c.question).where(
            operations.c.task_id == relation["origin_task_id"],
            operations.c.operation_key == relation["operation_key"],
        )
    )
    if producer != "propose_returned_role_attachments":
        raise SemanticRefusal("defining-text attachment lacks its released group producer")
    roles = {endpoint["role"]: endpoint["contribution_id"] for endpoint in relation["endpoints"]}
    if len(relation["endpoints"]) != 2 or roles.keys() != {"term", "defining_text"}:
        raise SemanticRefusal("defining-text attachment lacks exact directed endpoints")
    observed = read_source_contributions(conn, contribution_ids=tuple(roles.values()), **selectors)
    by_id = {row["contribution_id"]: row for row in observed.contributions if row["cut_member"]}
    if any(
        key not in by_id
        or (by_id[key]["kind"], by_id[key]["semantic_type"]) != ("proposal", "definition." + role)
        or by_id[key]["pin"] != relation["pin"]
        for role, key in roles.items()
    ):
        raise SemanticRefusal("defining-text attachment endpoints differ from the selected source")
    source = load_source_view(conn, relation["source_view_id"], analysis=False)
    return defining_text_features(
        source.ref.id,
        source.text,
        source.pieces,
        by_id[roles["term"]]["anchors"],
        by_id[roles["defining_text"]]["anchors"],
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


# Domain meaning is colocated with the typed callable. The closed compiler reads
# this literal without importing this module or NumPy/SciPy.
score_operation_event__data_operation__ = {
    "id": "urn:corpus:operation:score-operation-event",
    "profile": "derivation",
    "subject": "fitted-operation-event",
    "context": ["corpus_id", "event", "event_version", "producer_version"],
    "roles": [
        {
            "name": "parameters",
            "parameter": "parameters",
            "kind": "urn:corpus:kind:operation-event-parameters",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "exact",
                "identity_requirements": ["episode"],
                "source": "fitted-corpus-event-producer",
                "coverage": "ordered-feature-schema",
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
                "coverage": "all-fitted-features",
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
    "kinds": [
        {
            "id": "urn:corpus:kind:operation-event-parameters",
            "python": "corpus_structure.semantic.operation_policy.OperationEventParameters",
            "scope": "corpus-event-producer",
            "invariants": ["finite-nonzero-scales", "matching-feature-shape"],
            "interpretation": "operation-event-parameters-v1",
        }
    ],
    "applicability": ["exact-fitted-corpus-event-version-producer"],
    "invariants": ["finite-features", "matching-feature-shape", "probability-in-unit-interval"],
    "coverage": "one-score-for-complete-feature-vector",
    "outcomes": ["scored", "invalid-applicability", "invalid-feature-shape", "numerical-failure"],
    "precision": "numpy-float64-scipy-expit-finite-errors-raised-v1",
    "dependencies": [],
    "effects": [],
    "capabilities": {
        "forms": ["scalar"],
        "preparation": "fitted-parameters",
        "cancellation": "call-boundary",
        "ownership": "immutable-inputs",
    },
    "behavior": "operation-event-logistic-score-v1",
    "parameters": {},
    "binding": {"operator": "scan", "roles": ["parameters", "features"]},
    "opaque": [
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
    "bound_inputs": [],
}
