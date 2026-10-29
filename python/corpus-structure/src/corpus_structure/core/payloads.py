"""Observation payloads by kind, and the operations JSON (D3 §6.2, §6.3; foundations §3.5).

One model per observation kind, registered in `PAYLOADS` by kind. Writers validate once here and
store `model_dump(mode="json")`. Values inside payloads are stored-form values. Fields D3 leaves
open (markup values, record anchors, link features, decorations) are raw JSON. The closed sets and
the cross-field invariants come from the model's `system` payload classes (`vocab.py`,
`_model/validators.py`; ADR-0020).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import MISSING, Field, JsonValue, TypeAdapter, model_validator

from corpus_structure.core._model import validators
from corpus_structure.core.batch import (
    AuthoredBatch,
    CitationFrame,
    PrefixedName,
    StoredBatch,
    StoredEvidence,
)
from corpus_structure.core.values import (
    CoreModel,
    Offset,
    StoredObject,
    StoredValue,
)
from corpus_structure.core.vocab import (
    BindKind,
    InterventionTargetKind,
    JudgmentConfidence,
    JudgmentDecision,
    JudgmentTargetKind,
    MarkupKind,
    ObservationKind,
    PolicyThen,
    RuleSeverity,
    ScopeExtent,
    VerificationVerdict,
)

Score = Annotated[float, Field(ge=0, le=1)]


# --- Operations JSON (D3 §6.3) -----------------------------------------------------------------


class MentionRef(CoreModel):
    """A mention by its task and ordinal; the task is absent inside the same task."""

    task: int | MISSING = MISSING  # type: ignore[valid-type]
    ordinal: Offset


class Cost(CoreModel):
    """`ops.task.cost`."""

    wall_ms: Offset
    gpu_ms: Offset | MISSING = MISSING  # type: ignore[valid-type]
    tokens_in: Offset | MISSING = MISSING  # type: ignore[valid-type]
    tokens_out: Offset | MISSING = MISSING  # type: ignore[valid-type]
    model: str | MISSING = MISSING  # type: ignore[valid-type]


class PolicyAction(CoreModel):
    """`ops.policy_rule.action`: a named configuration `<method>/<name>`, a limit, then."""

    method: str = Field(pattern=r"^[a-z][a-z0-9_.]*/[A-Za-z0-9_.-]+$")
    limit: int = Field(ge=1)
    then: PolicyThen


class InterventionTarget(CoreModel):
    """`ops.intervention.target`; a `promotion` targets the run it promotes."""

    kind: InterventionTargetKind
    ref: str | int


TriggerMetrics = dict[str, int | float | bool | str]  # `ops.task.trigger_metrics`, as evaluated


# --- Payloads (D3 §6.2) ------------------------------------------------------------------------


class _Span(CoreModel):
    start: Offset
    end: Offset

    @model_validator(mode="after")
    def _span(self) -> Self:
        validators.span_payload(self)
        return self


class SynthesizedClaim(CoreModel):
    """The claim a block's containment states (the source profile's `details_kinds.synthesize`)."""

    predicate: PrefixedName
    object: StoredObject
    evidence: Annotated[tuple[StoredEvidence, ...], Field(min_length=1)]


class AuthorMarkupPayload(CoreModel):
    markup: MarkupKind
    value: JsonValue
    target: str | MISSING = MISSING  # type: ignore[valid-type]
    synthesize: SynthesizedClaim | MISSING = MISSING  # type: ignore[valid-type]


class LabelScore(CoreModel):
    label: str
    score: Score


class MentionPayload(_Span):
    label: str
    text: str
    attributes: dict[str, LabelScore] | MISSING = MISSING  # type: ignore[valid-type]
    math_ref: MentionRef | MISSING = MISSING  # type: ignore[valid-type]
    math: dict[str, JsonValue] | MISSING = MISSING  # type: ignore[valid-type]  # M09 decoration


class LabelledSpan(_Span):
    label: str


class RelationPayload(CoreModel):
    label: str
    head: LabelledSpan
    tail: LabelledSpan
    joint: bool | MISSING = MISSING  # type: ignore[valid-type]
    feasible: bool | MISSING = MISSING  # type: ignore[valid-type]


class RecordField(_Span):
    text: str
    score: Score


class RecordPayload(CoreModel):
    structure: str
    fields: dict[str, tuple[RecordField, ...]]
    anchor: JsonValue | MISSING = MISSING  # type: ignore[valid-type]


class AttributePayload(CoreModel):
    mention_ref: MentionRef
    group: str
    value: JsonValue


class ClassificationPayload(CoreModel):
    task: str
    labels: tuple[LabelScore, ...]
    feasible: bool | MISSING = MISSING  # type: ignore[valid-type]
    violations: JsonValue | MISSING = MISSING  # type: ignore[valid-type]


class ValuePayload(CoreModel):
    value: StoredValue
    parse_error: str | MISSING = MISSING  # type: ignore[valid-type]
    math_kind: Literal["formula", "relation", "membership", "set"] | MISSING = MISSING  # type: ignore[valid-type]


class MentionAt(_Span):
    """A mention ref with the mention's offsets, so a reused task's refs match by offsets."""

    mention_ref: MentionRef


class ScopePayload(_Span):
    mention_ref: MentionRef
    binding_site: MentionAt
    scope_segment: str = Field(min_length=1)
    extent: ScopeExtent
    binding: BindKind | MISSING = MISSING  # type: ignore[valid-type]
    reopens: MentionAt | MISSING = MISSING  # type: ignore[valid-type]


class NewEntity(CoreModel):
    type: str
    label: str


class NewCandidate(CoreModel):
    new: NewEntity


class LinkPayload(CoreModel):
    mention_ref: MentionRef | MISSING = MISSING  # type: ignore[valid-type]
    pair: tuple[str, str] | MISSING = MISSING  # type: ignore[valid-type]
    candidate: str | NewCandidate
    score: Score
    features: dict[str, JsonValue]
    rank: int | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _one_subject(self) -> Self:
        validators.link_payload(self)  # mention_ref (M14) or pair (M15)
        return self


class RejectedItem(CoreModel):
    item: JsonValue
    reason: str


class ClaimProposalPayload(CoreModel):
    """A stored batch; for authored proposals also the batch as written and its frame."""

    batch: StoredBatch
    authored: AuthoredBatch | MISSING = MISSING  # type: ignore[valid-type]
    citation_frame: CitationFrame | MISSING = MISSING  # type: ignore[valid-type]
    rationale: str | MISSING = MISSING  # type: ignore[valid-type]
    rejected: tuple[RejectedItem, ...] | MISSING = MISSING  # type: ignore[valid-type]
    establishment: Literal["derived"] | MISSING = MISSING  # type: ignore[valid-type]
    derived_from: tuple[str, ...] | MISSING = MISSING  # type: ignore[valid-type]
    rule: str | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _together(self) -> Self:
        validators.claim_proposal_payload(self)  # the authored pair; M23's derivation
        return self


class JudgmentTarget(CoreModel):
    kind: JudgmentTargetKind
    ref: str | int


class JudgmentPayload(CoreModel):
    target: JudgmentTarget
    decision: JudgmentDecision
    rationale: str
    guideline_version: str
    chosen: tuple[str, ...] | MISSING = MISSING  # type: ignore[valid-type]
    faithful: bool | MISSING = MISSING  # type: ignore[valid-type]
    confidence: JudgmentConfidence | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _chosen_for_choose(self) -> Self:
        validators.judgment_payload(self)
        return self


class VerificationDetail(CoreModel):
    """What M19 writes for a failing rule."""

    rule: str
    severity: RuleSeverity
    message: str


class VerificationPayload(CoreModel):
    claim_key: str
    verifier: str
    verdict: VerificationVerdict
    detail: VerificationDetail | dict[str, JsonValue] | MISSING = MISSING  # type: ignore[valid-type]
    counterexample: JsonValue | MISSING = MISSING  # type: ignore[valid-type]


PAYLOADS: dict[ObservationKind, type[CoreModel]] = {
    ObservationKind.AUTHOR_MARKUP: AuthorMarkupPayload,
    ObservationKind.MENTION: MentionPayload,
    ObservationKind.RELATION: RelationPayload,
    ObservationKind.RECORD: RecordPayload,
    ObservationKind.ATTRIBUTE: AttributePayload,
    ObservationKind.CLASSIFICATION: ClassificationPayload,
    ObservationKind.VALUE: ValuePayload,
    ObservationKind.SCOPE: ScopePayload,
    ObservationKind.LINK: LinkPayload,
    ObservationKind.CLAIM_PROPOSAL: ClaimProposalPayload,
    ObservationKind.JUDGMENT: JudgmentPayload,
    ObservationKind.VERIFICATION: VerificationPayload,
}

TRIGGER_METRICS = TypeAdapter(TriggerMetrics)


def validate_payload(kind: ObservationKind | str, payload: Any) -> CoreModel:
    """The payload of an observation of `kind`, validated by its model."""
    return PAYLOADS[ObservationKind(kind)].model_validate(payload)
