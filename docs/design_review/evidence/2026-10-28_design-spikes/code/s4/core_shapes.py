"""Core shapes (D2 §6 ownership; D1 §6, §7, §10.3): hand-written Pydantic, the same for every domain.

Values are discriminated on ``t``, condition nodes on ``op`` (one named recursive ``Condition`` per
form via ``TypeAliasType``), bindings on ``bind``. Models are frozen with ``extra="forbid"`` and
tuples for sequences. Schema-owned names (predicates, classes, enum values such as modality or
statement kind) are typed by the compiled batch models (``batch_models``), not here; the core types
fix only what D1 fixes (value tags, node ops, bind kinds, comparison relations, evidence roles).

Two batch forms (D2 §7.3): the model-facing form (``…MF``: sentence ids and quotes) and the stored
form (``…St``: offsets and segment keys). Only phrases, phrase/unsupported condition nodes and the
containers that hold them differ between the forms.

Optional fields are absent, never null: they default to None (unvalidated) but a null in input is
rejected, and dumps omit them (``exclude_none``), so equal meaning gives equal JSON (D3 §6.1).

Canonical shapes (S4 variants): an entity reference is ``{"ref": …}`` everywhere (V1), never a value
and never a bare string; a formula or set position takes a value object, never a bare LaTeX string.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypeAliasType


class Core(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ----------------------------------------------------------------------------- bindings (D1 §6.1)


class EntityBinding(Core):
    bind: Literal["variable", "family_param"]
    entity: str


class ClaimBinding(Core):
    bind: Literal["param_of", "param_expr_of"]
    claim: str
    param: str


class BareBinding(Core):
    bind: Literal["free", "constant", "unresolved"]


Binding = Annotated[Union[EntityBinding, ClaimBinding, BareBinding], Field(discriminator="bind")]
BIND_KINDS = ("variable", "family_param", "param_of", "param_expr_of", "free", "constant", "unresolved")

# ------------------------------------------------------------------------------- values (D1 §6)


class EntityRef(Core):
    """A reference to an entity (local ref in batches, key once stored). A position type, not a value."""

    ref: str


class Formula(Core):
    t: Literal["formula"]
    latex: str
    symbols: dict[str, Binding] = Field(default_factory=dict)


class SetValue(Core):
    t: Literal["set"]
    latex: str
    symbols: dict[str, Binding] = Field(default_factory=dict)


class TextValue(Core):
    t: Literal["text"]
    v: str


class NumberValue(Core):
    t: Literal["number"]
    v: str
    unit: str = None  # absent, never null
    basis: str = None  # absent, never null


class BoolValue(Core):
    t: Literal["bool"]
    v: bool


class EnumValue(Core):
    t: Literal["enum"]
    enum: str
    v: str


class DateValue(Core):
    t: Literal["date"]
    v: str


Bound = Annotated[Union[NumberValue, DateValue, Formula], Field(discriminator="t")]


class IntervalValue(Core):
    t: Literal["interval"]
    start: Bound = None  # absent, never null
    end: Bound = None  # absent, never null
    start_incl: bool = None  # absent, never null
    end_incl: bool = None  # absent, never null


class PhraseMF(Core):
    t: Literal["phrase"]
    text: str
    sentence: str = None  # absent, never null


class PhraseSt(Core):
    t: Literal["phrase"]
    text: str
    start: int
    end: int
    coarse: bool = None  # absent, never null


_NEUTRAL = (Formula, SetValue, TextValue, NumberValue, BoolValue, EnumValue, DateValue, IntervalValue)
ValueMF = Annotated[Union[*_NEUTRAL, PhraseMF], Field(discriminator="t")]
ValueSt = Annotated[Union[*_NEUTRAL, PhraseSt], Field(discriminator="t")]

# --------------------------------------------------------------------------- conditions (D1 §7)


# An entity or a formula. A plain (smart-mode) union, exported as anyOf: the two shapes are told apart
# by their required keys (ref against t), not by a shared const, so a oneOf would not be provably
# disjoint for a structured-output backend.
PredArg = Union[EntityRef, Formula]


class ClaimNode(Core):
    op: Literal["claim"]
    ref: str


class MemberNode(Core):
    op: Literal["member"]
    x: Formula
    set: SetValue


class CmpNode(Core):
    op: Literal["cmp"]
    rel: Literal["<", "<=", "=", "!=", ">", ">="]
    lhs: Formula
    rhs: Formula


class PredNode(Core):
    op: Literal["pred"]
    name: str  # a ConditionPredicate value (pack enum), typed by the compiled models
    args: tuple[PredArg, ...] = Field(min_length=1)


class PhraseNodeMF(Core):
    op: Literal["phrase"]
    text: str
    sentence: str = None  # absent, never null


class UnsupportedNodeMF(Core):
    op: Literal["unsupported"]
    text: str
    reason: str
    sentence: str = None  # absent, never null


class PhraseNodeSt(Core):
    op: Literal["phrase"]
    text: str
    start: int
    end: int
    coarse: bool = None  # absent, never null


class UnsupportedNodeSt(Core):
    op: Literal["unsupported"]
    text: str
    reason: str
    start: int
    end: int
    coarse: bool = None  # absent, never null


class AndMF(Core):
    op: Literal["and"]
    args: tuple["ConditionMF", ...]


class OrMF(Core):
    op: Literal["or"]
    args: tuple["ConditionMF", ...]


class NotMF(Core):
    op: Literal["not"]
    arg: "ConditionMF"


class ForallMF(Core):
    op: Literal["forall"]
    var: str
    set: SetValue
    body: "ConditionMF"


class AndSt(Core):
    op: Literal["and"]
    args: tuple["ConditionSt", ...]


class OrSt(Core):
    op: Literal["or"]
    args: tuple["ConditionSt", ...]


class NotSt(Core):
    op: Literal["not"]
    arg: "ConditionSt"


class ForallSt(Core):
    op: Literal["forall"]
    var: str
    set: SetValue
    body: "ConditionSt"


ConditionMF = TypeAliasType(
    "ConditionMF",
    Annotated[
        Union[AndMF, OrMF, NotMF, ClaimNode, MemberNode, CmpNode, PredNode, ForallMF, PhraseNodeMF, UnsupportedNodeMF],
        Field(discriminator="op"),
    ],
)
ConditionSt = TypeAliasType(
    "ConditionSt",
    Annotated[
        Union[AndSt, OrSt, NotSt, ClaimNode, MemberNode, CmpNode, PredNode, ForallSt, PhraseNodeSt, UnsupportedNodeSt],
        Field(discriminator="op"),
    ],
)
for _m in (AndMF, OrMF, NotMF, ForallMF, AndSt, OrSt, NotSt, ForallSt):
    _m.model_rebuild()

NODE_OPS = ("and", "or", "not", "claim", "member", "cmp", "pred", "forall", "phrase", "unsupported")

# ----------------------------------------------------------------------- batch items (D2 §7.3)

EvidenceRole = Literal["primary", "supporting", "condition", "definition"]


class EvidenceMF(Core):
    sentence: str
    quote: str
    role: EvidenceRole


class EvidenceSt(Core):
    start: int
    end: int
    role: EvidenceRole
    coarse: bool = None  # absent, never null


class ScopeSt(Core):
    """The stored form of the scope qualifier: the extent and the segment it resolves to."""

    extent: str
    segment: str


class AlternativeItem(Core):
    refs: tuple[str, ...] = Field(min_length=2)
    reason: str


class UnsupportedMF(Core):
    local_ref: str
    sentence: str
    quote: str
    reason: str


class UnsupportedSt(Core):
    local_ref: str
    start: int
    end: int
    reason: str
    coarse: bool = None  # absent, never null


class CitedSentence(Core):
    """One entry of a citation frame (D1 §10.3): the cited sentence's locator and text."""

    locator: str
    text: str


CitationFrame = dict[str, CitedSentence]

FORM_VALUE = {"model": ValueMF, "stored": ValueSt}
FORM_PHRASE = {"model": PhraseMF, "stored": PhraseSt}
FORM_CONDITION = {"model": ConditionMF, "stored": ConditionSt}
FORM_EVIDENCE = {"model": EvidenceMF, "stored": EvidenceSt}
FORM_UNSUPPORTED = {"model": UnsupportedMF, "stored": UnsupportedSt}

# Tag -> model per form, for the contract test and the annotator reference.
VALUE_MODELS = {
    "model": {m.model_fields["t"].annotation.__args__[0]: m for m in (*_NEUTRAL, PhraseMF)},
    "stored": {m.model_fields["t"].annotation.__args__[0]: m for m in (*_NEUTRAL, PhraseSt)},
}
