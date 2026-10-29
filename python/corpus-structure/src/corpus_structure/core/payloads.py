"""Observation payloads by kind, and the operations JSON (D3 §6.2, §6.3; foundations §3.5).

One model per observation kind, registered in `PAYLOADS` by kind. Writers validate once here and
store `model_dump(mode="json")`. Values inside payloads are stored-form values. Fields D3 leaves
open (markup values, record anchors, link features, decorations) are raw JSON. The closed sets and
the cross-field invariants come from the model's `system` payload classes (`vocab.py`,
`_model/validators.py`; ADR-0020).
"""

from __future__ import annotations

from typing import Annotated, Any, Self

from pydantic import MISSING, Field, JsonValue, TypeAdapter, model_validator

from corpus_structure.core._model import validators
from corpus_structure.core.batch import (
    AuthoredBatch,
    CitationFrame,
    PrefixedName,
    StoredBatch,
    StoredEvidence,
)
from corpus_structure.core.canonical import KEY_HEX_DIGITS
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
    MathKind,
    ObservationKind,
    PolicyThen,
    RuleSeverity,
    ScopeExtent,
    VerificationVerdict,
)

Score = Annotated[float, Field(ge=0, le=1)]
SegmentKey = Annotated[str, Field(pattern=rf"^seg:[0-9a-f]{{{KEY_HEX_DIGITS}}}$")]


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
    """`ops.intervention.target`; a `promotion` targets the run it promotes. `ref` is the target's
    key, or its id's decimal text for a target named by id (a run): the kind says which."""

    kind: InterventionTargetKind
    ref: str = Field(min_length=1)


TriggerMetrics = dict[str, int | float | bool | str]  # `ops.task.trigger_metrics`, as evaluated


class GoldenBatchPayload(CoreModel):
    """A golden pass's authored batch with one version of its citation frame (`eval.golden_pass`
    and `eval.citation_frame`, D3 §7): the shape the pass's `payload_schema_id` names for both."""

    batch: AuthoredBatch
    citation_frame: CitationFrame


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
    # each attribute group (D2 §5) to the label it chose and its score (the model's GroupScore)
    attributes: dict[str, LabelScore] | MISSING = MISSING  # type: ignore[valid-type]
    # the segment key of the math span the mention lies in (D4 M06; M09's symbol occurrences)
    math_ref: SegmentKey | MISSING = MISSING  # type: ignore[valid-type]
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
    math_kind: MathKind | MISSING = MISSING  # type: ignore[valid-type]


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


class LinkPayload(CoreModel):
    """An entity-link candidate: the mention (M14) or the pair (M15), and the candidate entity's
    key or the new entity it proposes, exactly one of each."""

    mention_ref: MentionRef | MISSING = MISSING  # type: ignore[valid-type]
    pair: tuple[str, str] | MISSING = MISSING  # type: ignore[valid-type]
    candidate: str | MISSING = Field(MISSING, min_length=1)  # type: ignore[valid-type]
    new: NewEntity | MISSING = MISSING  # type: ignore[valid-type]
    score: Score
    features: dict[str, JsonValue]
    rank: int | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _one_subject(self) -> Self:
        validators.link_payload(self)  # mention_ref or pair; candidate or new
        return self


class RejectedItem(CoreModel):
    item: JsonValue
    reason: str


SchemaVersion = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]  # the D2 §2 hash


class ClaimProposalPayload(CoreModel):
    """A stored batch with its derivation (R06, DA-009): the schema version whose compiled models
    derived it, always; for authored proposals also the batch as written, its frame and the version
    of the quote cascade that located it, the three together. A derived claim's `derived_from`
    and `rule` are on the claim itself (M23)."""

    batch: StoredBatch
    schema_version: SchemaVersion
    authored: AuthoredBatch | MISSING = MISSING  # type: ignore[valid-type]
    citation_frame: CitationFrame | MISSING = MISSING  # type: ignore[valid-type]
    cascade_version: str | MISSING = Field(MISSING, min_length=1)  # type: ignore[valid-type]
    rationale: str | MISSING = MISSING  # type: ignore[valid-type]
    rejected: tuple[RejectedItem, ...] | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _together(self) -> Self:
        validators.claim_proposal_payload(self)  # the authority and its derivation together
        return self


class JudgmentTarget(CoreModel):
    """What a judgment is about: an observation by its id's decimal text, or a claim or group by
    its key with that key's scheme (readers compare keys only within one scheme or through a
    carry-over map; foundations §3.6)."""

    kind: JudgmentTargetKind
    ref: str = Field(min_length=1)
    key_scheme: int | MISSING = Field(MISSING, ge=1)  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _scheme_of_a_key(self) -> Self:
        validators.judgment_target(self)  # a key's scheme, exactly when the target is a key
        return self


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
