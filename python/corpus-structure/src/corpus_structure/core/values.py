"""D1 values, symbol bindings and condition trees, in both batch forms (D1 §6, §7).

Foundations §3.5.

The classes are generated from the model (`_model/shapes.py`, Stage B, P0-M-5; ADR-0020) and
re-exported here, with the behaviour over them: `ref_kinds`, the form adapters and
`refuse_m11_fields`. Every model is frozen with `extra="forbid"` and tuples for sequences; the
closed sets, the cross-field invariants and the shapes all come from the model. Optional fields are
absent, never null: they default to `MISSING`, a null is refused, and dumps leave them out, so equal
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
name (the model's `ci:refers`): an entity, a statement, a claim, or an entity or a statement (a
subject), each a non-empty local ref in a batch and a key once keyed, its annotation carrying a
`Refers` marker (`ref_kinds` reads it). An `ExternalReference` node (D1 §4.4) is an entity, and it
may stand where a claim is named (a `claim` condition, a binding's claim), since it stands for a
statement outside the batch. Keying resolves each position by its declared kind and refuses a
reference of another kind with a code (`keys.Resolver`); `validate` (S2) owns reference checking for
batches (RC19).

**Enum values have a form each** (F2e; X2-01): the authored `AuthoredEnumValue` names its enum by
local name, the stored `StoredEnumValue` by prefixed name, and each refuses the other's.
"""

from __future__ import annotations

import typing
from typing import Annotated, Any

from pydantic import BaseModel, TypeAdapter

from corpus_structure.core._model.shapes import (
    AuthoredAnd,
    AuthoredCondition,
    AuthoredEnumValue,
    AuthoredForall,
    AuthoredNot,
    AuthoredObject,
    AuthoredOr,
    AuthoredPhrase,
    AuthoredPhraseNode,
    AuthoredUnsupportedNode,
    AuthoredValue,
    BoolValue,
    ClaimNode,
    CmpNode,
    DateValue,
    EntityRef,
    Expression,
    Formula,
    IntervalValue,
    MemberNode,
    NumberValue,
    PredArg,
    PredNode,
    SetValue,
    StoredAnd,
    StoredCondition,
    StoredEnumValue,
    StoredForall,
    StoredNot,
    StoredObject,
    StoredOr,
    StoredPhrase,
    StoredPhraseNode,
    StoredUnsupportedNode,
    StoredValue,
    SymbolBinding,
    TextValue,
)
from corpus_structure.core._model.types import (
    CITATION,
    LOCAL_NAME,
    PREFIXED_NAME,
    SENTENCE_ID,
    CoreModel,
    LocalName,
    Offset,
    PrefixedName,
    Refers,
    SentenceId,
)
from corpus_structure.core.shape_support import refuse_m11_fields
from corpus_structure.core.vocab import RefKind

__all__ = [
    "CITATION", "LOCAL_NAME", "PREFIXED_NAME", "SENTENCE_ID", "AuthoredAnd", "AuthoredCondition",
    "AuthoredEnumValue", "AuthoredForall", "AuthoredNot", "AuthoredObject", "AuthoredOr",
    "AuthoredPhrase", "AuthoredPhraseNode", "AuthoredUnsupportedNode", "AuthoredValue",
    "BoolValue", "ClaimNode", "CmpNode", "CoreModel", "DateValue", "EntityRef", "Expression",
    "Formula", "IntervalValue", "LocalName", "MemberNode", "NumberValue", "Offset", "PredArg",
    "PredNode", "PrefixedName", "RefKind", "Refers", "SentenceId", "SetValue", "StoredAnd",
    "StoredCondition", "StoredEnumValue", "StoredForall", "StoredNot", "StoredObject", "StoredOr",
    "StoredPhrase", "StoredPhraseNode", "StoredUnsupportedNode", "StoredValue", "SymbolBinding",
    "TextValue", "refuse_m11_fields",
]  # fmt: skip


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


def _members(alias: Any) -> tuple[type[CoreModel], ...]:
    return typing.get_args(typing.get_args(alias.__value__)[0])


# The value classes both forms share (every value but enum values and phrases).
NEUTRAL_VALUES: tuple[type[CoreModel], ...] = tuple(
    c for c in _members(AuthoredValue) if c in _members(StoredValue)
)

VALUE_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "authored": TypeAdapter(AuthoredValue),
    "stored": TypeAdapter(StoredValue),
}
CONDITION_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "authored": TypeAdapter(AuthoredCondition),
    "stored": TypeAdapter(StoredCondition),
}
