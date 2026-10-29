"""D1 values, symbol bindings and condition trees, in both batch forms (D1 §6, §7).

Foundations §3.5.

Every model is frozen with `extra="forbid"` and tuples for sequences. The closed sets (`BindKind`,
`ParseOutcome`) and the cross-field invariants (span order, binding fields) come from the model
(`vocab.py`, `_model/validators.py`; ADR-0020). Optional fields are absent,
never null: they default to `MISSING`, a null is refused, and dumps leave them out, so equal
meaning gives equal JSON (D3 §6.1). Names the schema owns (enum names and values, condition
predicates) are plain strings; the compiled per-predicate models type them (S1).

The authored (model-facing) and stored forms differ only where text is anchored: a `phrase` value
and the `phrase`/`unsupported` condition leaves carry `text` and an optional `sentence` when
authored, and `text`, `start`, `end` and an optional `coarse` when stored. Each form declares its
value union and its named recursive `Condition` (one `$defs` entry, discriminated on `op`) as a
static type alias over static classes, so operations pattern-match on the typed unions with
`typing.assert_never` (R03); the two forms share every other model.

Citation positions are the fields whose declared type is `SentenceId`: its annotation carries the
`CITATION` marker, and `batch.rewrite_citations` finds them by that annotation, never by a JSON key
name.

An entity is referenced in exactly one shape, `EntityRef` `{"ref": …}` (a local ref in a batch,
a key once stored): as a claim object, a `pred` argument, an entity-ranged qualifier. It is not a
value. Formula and set positions take value objects only.

**References are typed by kind** (F2e; R04; DA-006). Every reference position declares what it may
name through its annotation: `EntityId`, `StatementId`, `ClaimId`, or `SubjectId` (an entity or a
statement), each a local ref in a batch and a key once keyed, and each carrying a `Refers` marker
(`ref_kinds` reads it). An `ExternalReference` node (D1 §4.4) is an entity, and it may stand where a
claim is named (a `claim` condition, a binding's claim), since it stands for a statement outside
the batch. Keying resolves each position by its declared kind and refuses a reference of another
kind with a code (`keys.Resolver`); `validate` (S2) owns reference checking for batches (RC19).

**Enum values have a form each** (F2e; X2-01): the authored `AuthoredEnumValue` names its enum by
local name, the stored `StoredEnumValue` by prefixed name, and each refuses the other's.
"""

from __future__ import annotations

import re
import typing
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Final, Literal, Self

from pydantic import (
    MISSING,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from corpus_structure.core._model import validators
from corpus_structure.core.canonical import CANONICAL_DECIMAL, canonical_decimal
from corpus_structure.core.vocab import BindKind, ParseOutcome, Relation

SENTENCE_ID = r"^[sc][0-9]+$"
# The stored form names every schema element (class, predicate, qualifier, identity slot, enum) by
# its prefixed name; the authored form keeps local names (coordinator ruling, 2026-10-28, from X2).
PREFIXED_NAME = r"^[a-z][a-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$"
LOCAL_NAME = r"^[A-Za-z_][A-Za-z0-9_]*$"
ISO_8601 = (
    r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?"
    r"(Z|[+-][0-9]{2}:[0-9]{2})?)?)?)?$"
)
_DECIMAL = re.compile(CANONICAL_DECIMAL)


class _Citation:
    """The marker on `SentenceId`'s annotation: a field of this type cites a sentence."""

    def __repr__(self) -> str:
        return "CITATION"


CITATION: Final = _Citation()
SentenceId = Annotated[str, Field(pattern=SENTENCE_ID), CITATION]
Offset = Annotated[int, Field(ge=0)]
PrefixedName = Annotated[str, Field(pattern=PREFIXED_NAME)]
LocalName = Annotated[str, Field(pattern=LOCAL_NAME)]


class RefKind(StrEnum):
    """What a reference names: an entity (an `ExternalReference` node is one), a statement or a
    claim."""

    ENTITY = "entity"
    STATEMENT = "statement"
    CLAIM = "claim"


@dataclass(frozen=True, slots=True)
class Refers:
    """The marker on a reference type's annotation: the kinds the position may name."""

    kinds: frozenset[RefKind]


def _refers(*kinds: RefKind) -> Refers:
    return Refers(frozenset(kinds))


EntityId = Annotated[str, Field(min_length=1), _refers(RefKind.ENTITY)]
StatementId = Annotated[str, Field(min_length=1), _refers(RefKind.STATEMENT)]
ClaimId = Annotated[str, Field(min_length=1), _refers(RefKind.CLAIM)]
SubjectId = Annotated[str, Field(min_length=1), _refers(RefKind.ENTITY, RefKind.STATEMENT)]


def ref_kinds(model: type[BaseModel], name: str) -> frozenset[RefKind]:
    """The kinds a model field's references may name (its `Refers` marker, through unions and
    tuples), empty when the field is no reference."""
    info = model.model_fields[name]
    found = [m for m in info.metadata if isinstance(m, Refers)]
    return found[0].kinds if found else _kinds(info.annotation)


def _kinds(annotation: object) -> frozenset[RefKind]:
    if typing.get_origin(annotation) is Annotated:
        base, *metadata = typing.get_args(annotation)
        marked = [m for m in metadata if isinstance(m, Refers)]
        return marked[0].kinds if marked else _kinds(base)
    out: frozenset[RefKind] = frozenset()
    for arg in typing.get_args(annotation):
        out |= _kinds(arg)
    return out


class CoreModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- References and bindings -------------------------------------------------------------------


class EntityRef(CoreModel):
    """The one entity-reference shape: a local ref in a batch, an entity key once stored."""

    ref: EntityId


class SymbolBinding(CoreModel):
    """How one symbol of a formula is bound (D1 §6.1); the kind decides which fields it has."""

    bind: BindKind
    entity: EntityId | MISSING = MISSING  # type: ignore[valid-type]
    claim: ClaimId | MISSING = MISSING  # type: ignore[valid-type]
    param: str | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _fields_of_kind(self) -> Self:
        validators.symbol_binding(self)
        return self


# --- Values that are the same in both forms ----------------------------------------------------


class _Expression(CoreModel):
    t: Literal["formula", "set"]
    latex: str
    symbols: dict[str, SymbolBinding] = Field(default_factory=dict)
    # Added by M11 in consolidation; refused in both batch forms (`refuse_m11_fields`).
    sympy: str | MISSING = MISSING  # type: ignore[valid-type]
    parse: ParseOutcome | MISSING = MISSING  # type: ignore[valid-type]


class Formula(_Expression):
    t: Literal["formula"]  # type: ignore[assignment]


class SetValue(_Expression):
    t: Literal["set"]  # type: ignore[assignment]


class TextValue(CoreModel):
    t: Literal["text"]
    v: str


class NumberValue(CoreModel):
    """A number as its D1 §6.2 canonical decimal; `unit` and `basis` as the source states them."""

    t: Literal["number"]
    v: str = Field(json_schema_extra={"pattern": f"^(?:{CANONICAL_DECIMAL})$"})
    unit: str | MISSING = MISSING  # type: ignore[valid-type]
    basis: str | MISSING = MISSING  # type: ignore[valid-type]

    @field_validator("v")
    @classmethod
    def _canonical(cls, v: str) -> str:
        if _DECIMAL.fullmatch(v):
            return v
        try:
            spelled = canonical_decimal(v)
        except ValueError:
            raise ValueError(f"{v!r} is not a decimal number") from None
        raise ValueError(f"{v!r} is not a canonical decimal; write {spelled!r}")


class BoolValue(CoreModel):
    t: Literal["bool"]
    v: bool


class EnumValue(CoreModel):
    """A member of a schema enum; the base of the two forms, which differ in how they name the
    enum."""

    t: Literal["enum"]
    enum: str
    v: str


class AuthoredEnumValue(EnumValue):
    """The authored enum value: the enum by its local name (`ParameterRole`)."""

    enum: LocalName  # type: ignore[assignment]


class StoredEnumValue(EnumValue):
    """The stored enum value: the enum by its prefixed name (`stat:ParameterRole`)."""

    enum: PrefixedName  # type: ignore[assignment]


class DateValue(CoreModel):
    t: Literal["date"]
    v: str = Field(pattern=ISO_8601)


Bound = Annotated[NumberValue | DateValue | Formula, Field(discriminator="t")]


class IntervalValue(CoreModel):
    """An interval; an absent bound is unbounded."""

    t: Literal["interval"]
    start: Bound | MISSING = MISSING  # type: ignore[valid-type]
    end: Bound | MISSING = MISSING  # type: ignore[valid-type]
    start_incl: bool | MISSING = MISSING  # type: ignore[valid-type]
    end_incl: bool | MISSING = MISSING  # type: ignore[valid-type]


NEUTRAL_VALUES: tuple[type[CoreModel], ...] = (
    TextValue, NumberValue, BoolValue, Formula, SetValue, DateValue, IntervalValue,
)  # fmt: skip


# --- Leaves that are the same in both forms ----------------------------------------------------


class ClaimNode(CoreModel):
    op: Literal["claim"]
    ref: ClaimId


class MemberNode(CoreModel):
    op: Literal["member"]
    x: Formula
    set: SetValue


class CmpNode(CoreModel):
    op: Literal["cmp"]
    rel: Relation
    lhs: Formula
    rhs: Formula


# A plain union: the two shapes differ by their required keys (`ref` against `t`).
PredArg = EntityRef | Formula


class PredNode(CoreModel):
    op: Literal["pred"]
    name: str
    args: tuple[PredArg, ...] = Field(min_length=1)


# --- Form-specific anchored text ---------------------------------------------------------------


class AuthoredPhrase(CoreModel):
    t: Literal["phrase"]
    text: str
    sentence: SentenceId | MISSING = MISSING  # type: ignore[valid-type]


class StoredPhrase(CoreModel):
    t: Literal["phrase"]
    text: str
    start: Offset
    end: Offset
    coarse: bool | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _span(self) -> Self:
        validators.phrase_value(self)
        return self


class AuthoredPhraseNode(CoreModel):
    op: Literal["phrase"]
    text: str
    sentence: SentenceId | MISSING = MISSING  # type: ignore[valid-type]


class AuthoredUnsupportedNode(AuthoredPhraseNode):
    op: Literal["unsupported"]  # type: ignore[assignment]
    reason: str


class StoredPhraseNode(CoreModel):
    op: Literal["phrase"]
    text: str
    start: Offset
    end: Offset
    coarse: bool | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _span(self) -> Self:
        validators.phrase_node(self)
        return self


class StoredUnsupportedNode(StoredPhraseNode):
    op: Literal["unsupported"]  # type: ignore[assignment]
    reason: str


# --- The two forms' unions --------------------------------------------------------------------
#
# Declared statically, one class per recursive node and form, so operations pattern-match on them
# with `typing.assert_never` checking exhaustiveness (R03). The recursive alias of each form is one
# named `$defs` entry, discriminated on `op`.


class AuthoredAnd(CoreModel):
    op: Literal["and"]
    args: tuple[AuthoredCondition, ...]


class AuthoredOr(CoreModel):
    op: Literal["or"]
    args: tuple[AuthoredCondition, ...]


class AuthoredNot(CoreModel):
    op: Literal["not"]
    arg: AuthoredCondition


class AuthoredForall(CoreModel):
    op: Literal["forall"]
    var: str
    set: SetValue
    body: AuthoredCondition


class StoredAnd(CoreModel):
    op: Literal["and"]
    args: tuple[StoredCondition, ...]


class StoredOr(CoreModel):
    op: Literal["or"]
    args: tuple[StoredCondition, ...]


class StoredNot(CoreModel):
    op: Literal["not"]
    arg: StoredCondition


class StoredForall(CoreModel):
    op: Literal["forall"]
    var: str
    set: SetValue
    body: StoredCondition


type AuthoredValue = Annotated[
    TextValue | NumberValue | BoolValue | AuthoredEnumValue | Formula | SetValue | DateValue
    | IntervalValue | AuthoredPhrase,
    Field(discriminator="t"),
]  # fmt: skip
type StoredValue = Annotated[
    TextValue | NumberValue | BoolValue | StoredEnumValue | Formula | SetValue | DateValue
    | IntervalValue | StoredPhrase,
    Field(discriminator="t"),
]  # fmt: skip
type AuthoredCondition = Annotated[
    AuthoredAnd | AuthoredOr | AuthoredNot | AuthoredForall | ClaimNode | MemberNode | CmpNode
    | PredNode | AuthoredPhraseNode | AuthoredUnsupportedNode,
    Field(discriminator="op"),
]  # fmt: skip
type StoredCondition = Annotated[
    StoredAnd | StoredOr | StoredNot | StoredForall | ClaimNode | MemberNode | CmpNode | PredNode
    | StoredPhraseNode | StoredUnsupportedNode,
    Field(discriminator="op"),
]  # fmt: skip

for _node in (AuthoredAnd, AuthoredOr, AuthoredNot, AuthoredForall,
              StoredAnd, StoredOr, StoredNot, StoredForall):  # fmt: skip
    _node.model_rebuild()

# Claim objects: an entity reference or a value of the form.
AuthoredObject = EntityRef | AuthoredValue
StoredObject = EntityRef | StoredValue

VALUE_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "authored": TypeAdapter(AuthoredValue),
    "stored": TypeAdapter(StoredValue),
}
CONDITION_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "authored": TypeAdapter(AuthoredCondition),
    "stored": TypeAdapter(StoredCondition),
}


def refuse_m11_fields(value: Any, path: str = "$") -> list[str]:
    """Paths of formula or set values that carry `sympy` or `parse`, which no batch may hold."""
    found: list[str] = []
    if isinstance(value, _Expression):
        for name in ("sympy", "parse"):
            if getattr(value, name) is not MISSING:
                found.append(f"{path}.{name}")
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            found += refuse_m11_fields(getattr(value, name), f"{path}.{name}")
        for name, extra in (value.__pydantic_extra__ or {}).items():
            found += refuse_m11_fields(extra, f"{path}.{name}")
    elif isinstance(value, dict):
        for key, item in value.items():
            found += refuse_m11_fields(item, f"{path}.{key}")
    elif isinstance(value, tuple | list):
        for i, item in enumerate(value):
            found += refuse_m11_fields(item, f"{path}[{i}]")
    return found
