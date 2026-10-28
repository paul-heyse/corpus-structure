"""Pydantic models of ClaimProposalBatch, model-facing and stored forms (D2 §7.3; instruments §2.1).

Structure only. Everything the schema owns (predicates, classes, qualifier names, enum values
such as modality, statement kind, statement role, bind kinds, condition predicates) is a plain
string here and is checked by ``validate`` through ``schema_lookup``, so that an unknown value
is reported as "unknown schema element" rather than as malformed JSON.

Choices recorded in results/s0/instruments_tests.md:

- Formula positions inside condition nodes accept either a value object
  ``{"t": "formula", "latex": ..., "symbols": {...}}`` or a bare LaTeX string (D1 §7 does not
  say which); ``as_formula`` coerces a bare string to a formula value without bindings.
- ``phrase`` and ``unsupported`` condition nodes and ``phrase`` values carry ``text`` plus,
  model-facing, an optional ``sentence`` id; stored, ``start``/``end`` (and ``coarse``). D1 §7
  names a ``span`` field, which the model-facing form cannot have.
- Entity-valued qualifiers and ``pred`` arguments accept ``{"ref": r}``, ``{"t": "entity",
  "ref": r}`` or a bare local-ref string.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, TypeAdapter


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- values (D1 §6)


class SymbolBinding(Strict):
    bind: str  # BindKind (schema enum)
    entity: str | None = None  # variable, family_param: entity local ref
    claim: str | None = None  # param_of, param_expr_of: claim local ref
    param: str | None = None


class FormulaValue(Strict):
    t: Literal["formula"]
    latex: str
    symbols: dict[str, SymbolBinding] = Field(default_factory=dict)


class SetValue(Strict):
    t: Literal["set"]
    latex: str
    symbols: dict[str, SymbolBinding] = Field(default_factory=dict)


class TextValue(Strict):
    t: Literal["text"]
    v: str


class NumberValue(Strict):
    t: Literal["number"]
    v: str
    unit: str | None = None


class BoolValue(Strict):
    t: Literal["bool"]
    v: bool


class EnumValue(Strict):
    t: Literal["enum"]
    enum: str
    v: str


class EntityValue(Strict):
    t: Literal["entity"]
    ref: str


class DateValue(Strict):
    t: Literal["date"]
    v: str


class PhraseValue(Strict):
    t: Literal["phrase"]
    text: str
    sentence: str | None = None  # model-facing
    start: int | None = None  # stored
    end: int | None = None
    coarse: bool | None = None


class IntervalValue(Strict):
    t: Literal["interval"]
    start: Value | None = None
    end: Value | None = None
    start_incl: bool | None = None
    end_incl: bool | None = None


Value = Annotated[
    Union[
        FormulaValue,
        SetValue,
        TextValue,
        NumberValue,
        BoolValue,
        EnumValue,
        EntityValue,
        DateValue,
        IntervalValue,
        PhraseValue,
    ],
    Field(discriminator="t"),
]
IntervalValue.model_rebuild()


class Ref(Strict):
    ref: str


def _object_tag(v: Any) -> str:
    if isinstance(v, dict):
        return "value" if "t" in v else "ref"
    return "value" if hasattr(v, "t") else "ref"


ClaimObject = Annotated[
    Union[Annotated[Ref, Tag("ref")], Annotated[Value, Tag("value")]],
    Discriminator(_object_tag),
]

FormulaArg = Union[FormulaValue, str]
SetArg = Union[SetValue, str]
EntityArg = Union[Ref, EntityValue, str]


def as_formula(x: Any, t: str = "formula") -> dict:
    """A formula/set position as a value dict (bare strings coerced, no bindings)."""
    if isinstance(x, BaseModel):
        x = x.model_dump(exclude_none=True)
    if isinstance(x, str):
        return {"t": t, "latex": x, "symbols": {}}
    return x


def ref_of(x: Any) -> str | None:
    """The local ref named by an entity position, or None."""
    if isinstance(x, BaseModel):
        x = x.model_dump(exclude_none=True)
    if isinstance(x, str):
        return x
    if isinstance(x, dict) and "ref" in x and x.get("t") in (None, "entity"):
        return x["ref"]
    return None


# --------------------------------------------------------------------- conditions (D1 §7)


class AndNode(Strict):
    op: Literal["and"]
    args: list[Condition]


class OrNode(Strict):
    op: Literal["or"]
    args: list[Condition]


class NotNode(Strict):
    op: Literal["not"]
    arg: Condition


class ClaimNode(Strict):
    op: Literal["claim"]
    ref: str


class MemberNode(Strict):
    op: Literal["member"]
    x: FormulaArg
    set: SetArg


class CmpNode(Strict):
    op: Literal["cmp"]
    rel: Literal["<", "<=", "=", "!=", ">", ">="]
    lhs: FormulaArg
    rhs: FormulaArg


class PredNode(Strict):
    op: Literal["pred"]
    name: str  # ConditionPredicate (schema enum)
    args: list[Union[FormulaValue, Ref, EntityValue, str]]


class ForallNode(Strict):
    op: Literal["forall"]
    var: FormulaArg
    set: SetArg
    body: Condition


class PhraseNode(Strict):
    op: Literal["phrase"]
    text: str
    sentence: str | None = None
    start: int | None = None
    end: int | None = None
    coarse: bool | None = None


class UnsupportedNode(Strict):
    op: Literal["unsupported"]
    text: str
    reason: str
    sentence: str | None = None
    start: int | None = None
    end: int | None = None
    coarse: bool | None = None


Condition = Annotated[
    Union[
        AndNode,
        OrNode,
        NotNode,
        ClaimNode,
        MemberNode,
        CmpNode,
        PredNode,
        ForallNode,
        PhraseNode,
        UnsupportedNode,
    ],
    Field(discriminator="op"),
]
for _m in (AndNode, OrNode, NotNode, ForallNode):
    _m.model_rebuild()


# ------------------------------------------------------------------------- batch items

EvidenceRole = Literal["primary", "supporting", "condition", "definition"]


class EvidenceMF(Strict):
    sentence: str
    quote: str
    role: EvidenceRole


class EvidenceStored(Strict):
    start: int
    end: int
    role: EvidenceRole
    coarse: bool | None = None


class EntityMF(Strict):
    local_ref: str
    type: str
    label: str
    scope: Literal["global", "local"]
    extent: Literal["statement", "section"] | None = None
    symbol: str | None = None
    aliases: list[str] = Field(default_factory=list)
    identity: dict[str, Any] = Field(default_factory=dict)


class EntityStored(EntityMF):
    scope_segment: str | None = None


class StatementMF(Strict):
    local_ref: str
    kind: str
    anchor: Union[Literal["unit"], list[str]]


class StatementStored(Strict):
    local_ref: str
    kind: str
    anchor: list[str]


class ClaimMF(Strict):
    local_ref: str
    predicate: str
    subject: str
    object: ClaimObject
    qualifiers: dict[str, Any] = Field(default_factory=dict)  # typed per schema in validate
    statement: str | None = None
    statement_role: str | None = None
    evidence: list[EvidenceMF] = Field(default_factory=list)


class ClaimStored(ClaimMF):
    evidence: list[EvidenceStored] = Field(default_factory=list)


class Alternative(Strict):
    refs: list[str] = Field(min_length=2)
    reason: str


class UnsupportedMF(Strict):
    local_ref: str
    sentence: str
    quote: str
    reason: str


class UnsupportedStored(Strict):
    local_ref: str
    start: int
    end: int
    reason: str
    coarse: bool | None = None


class BatchShell(Strict):
    """Top level only; items are validated one by one so a bad item never hides the others."""

    unit_ref: str
    entities: list[Any] = Field(default_factory=list)
    statements: list[Any] = Field(default_factory=list)
    claims: list[Any] = Field(default_factory=list)
    alternatives: list[Any] = Field(default_factory=list)
    unsupported: list[Any] = Field(default_factory=list)


ITEM_MODELS = {
    "model": {
        "entities": EntityMF,
        "statements": StatementMF,
        "claims": ClaimMF,
        "alternatives": Alternative,
        "unsupported": UnsupportedMF,
    },
    "stored": {
        "entities": EntityStored,
        "statements": StatementStored,
        "claims": ClaimStored,
        "alternatives": Alternative,
        "unsupported": UnsupportedStored,
    },
}

VALUE_ADAPTER = TypeAdapter(Value)
CONDITION_ADAPTER = TypeAdapter(Condition)
ENTITY_ARG_ADAPTER = TypeAdapter(EntityArg)
STR_ADAPTER = TypeAdapter(str)


# ---------------------------------------------------------------- envelope (spike only)


class Envelope(Strict):
    """Spike-only wrapper outside the D2 contract (instruments §2.1)."""

    unit_id: str
    rendition_key: str | None = None
    pass_name: str | None = None
    annotator_model: str | None = None
    date: str | None = None
    form: Literal["model", "stored"] = "model"


def load_batch(src: str | Path | dict) -> tuple[dict | None, dict]:
    """Return (envelope or None, raw batch dict) from a path or a dict.

    An enveloped file is ``{"envelope": {...}, "batch": {...}}``; a bare batch is accepted too.
    """
    if not isinstance(src, dict):
        src = json.loads(Path(src).read_text(encoding="utf-8"))
    if set(src) == {"envelope", "batch"}:
        Envelope.model_validate(src["envelope"])
        return src["envelope"], src["batch"]
    return None, src


def wrap(batch: dict, **envelope: Any) -> dict:
    return {"envelope": Envelope(**envelope).model_dump(), "batch": batch}
