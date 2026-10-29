"""Observation payloads by kind, and the operations JSON (D3 §6.2, §6.3; foundations §3.5).

One model per observation kind, registered in `PAYLOADS` by kind. Writers validate once here and
store `model_dump(mode="json")`. Values inside payloads are stored-form values. Fields D3 leaves
open (markup values, record anchors, link features, decorations) are raw JSON. The classes,
their closed sets and cross-field invariants and `PAYLOADS` are generated from the model's
`system` payload classes (`_model/shapes.py`, Stage B, P0-M-5; ADR-0020) and re-exported here
beside `validate_payload` and the trigger metrics' adapter.
"""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from corpus_structure.core._model.shapes import (
    PAYLOADS,
    AttributePayload,
    AuthorMarkupPayload,
    ClaimProposalPayload,
    ClassificationPayload,
    Cost,
    GoldenBatchPayload,
    InterventionRefs,
    InterventionTarget,
    JudgmentPayload,
    JudgmentTarget,
    LabelledSpan,
    LabelScore,
    LinkPayload,
    MentionAt,
    MentionPayload,
    MentionRef,
    NewEntity,
    PolicyAction,
    RecordField,
    RecordPayload,
    RejectedItem,
    RelationPayload,
    ScopePayload,
    SpanPayload,
    SynthesizedClaim,
    ValuePayload,
    VerificationDetail,
    VerificationPayload,
)
from corpus_structure.core._model.types import CoreModel, Score, SegmentKey
from corpus_structure.core.vocab import ObservationKind

__all__ = [
    "PAYLOADS",
    "TRIGGER_METRICS",
    "AttributePayload",
    "AuthorMarkupPayload",
    "ClaimProposalPayload",
    "ClassificationPayload",
    "Cost",
    "GoldenBatchPayload",
    "InterventionRefs",
    "InterventionTarget",
    "JudgmentPayload",
    "JudgmentTarget",
    "LabelScore",
    "LabelledSpan",
    "LinkPayload",
    "MentionAt",
    "MentionPayload",
    "MentionRef",
    "NewEntity",
    "PolicyAction",
    "RecordField",
    "RecordPayload",
    "RejectedItem",
    "RelationPayload",
    "ScopePayload",
    "Score",
    "SegmentKey",
    "SpanPayload",
    "SynthesizedClaim",
    "TriggerMetrics",
    "ValuePayload",
    "VerificationDetail",
    "VerificationPayload",
    "validate_payload",
]

TriggerMetrics = dict[str, int | float | bool | str]  # `ops.task.trigger_metrics`, as evaluated
TRIGGER_METRICS = TypeAdapter(TriggerMetrics)


def validate_payload(kind: ObservationKind | str, payload: Any) -> CoreModel:
    """The payload of an observation of `kind`, validated by its model."""
    return PAYLOADS[ObservationKind(kind)].model_validate(payload)
