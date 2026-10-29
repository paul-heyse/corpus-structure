"""The keyed candidate set: the complete core claim shape the rule-view builder and keying read.

D5 §8.2; foundations §3.5 (F2e: R04, DA-005, DA-006, DA-007); target model §3, §7. S2's batch
adapter (T2, at submission) and C1's pool loader (T3, at finalize) both produce it, and its
translations are declared in `core/translations.py`. It carries the whole batch:

- the rendition its offsets and segment keys are on, by its `ren` key (`rendition`), so no reader
  needs a context supplied on the side; keying checks it against its `KeyContext`;
- entities, statements, `ExternalReference` nodes (`references`), claims with their
  `establishment`, `derived_from` and `rule`, alternatives and unsupported items.

At submission ids are local refs and keys are `UNKEYED`; at finalize ids are keys. An
`ExternalReference` awaiting consolidation's resolution is `AWAITING`. Both are typed states, never
`None`, and every optional field is absent by `MISSING`. References are typed by kind
(`EntityId`, `StatementId`, `ClaimId`, `SubjectId`). It is in stored form: classes, predicates,
qualifiers, identity slots and enums by their prefixed names; values and evidence as stored. The
grammar's facts at finalize and the derived view attributes are the view builder's arguments, not
fields here.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import MISSING, Field, model_validator

from corpus_structure.core._model import validators
from corpus_structure.core.batch import (
    RenditionKey,
    StoredDescriptor,
    StoredEvidence,
    StoredQualifiers,
)
from corpus_structure.core.canonical import KEY_HEX_DIGITS
from corpus_structure.core.values import (
    ClaimId,
    CoreModel,
    Offset,
    PrefixedName,
    StatementId,
    StoredObject,
    SubjectId,
)
from corpus_structure.core.vocab import (
    Awaiting,
    EntityExtent,
    EntityScope,
    Establishment,
    StatementRole,
    Unkeyed,
)

Id = Annotated[str, Field(min_length=1)]


def _key(*prefixes: str) -> str:
    return rf"^(?:{'|'.join(prefixes)}):[0-9a-f]{{{KEY_HEX_DIGITS}}}$"


EntityKey = Annotated[str, Field(pattern=_key("ent"))]
StatementKey = Annotated[str, Field(pattern=_key("stm"))]
ReferenceKey = Annotated[str, Field(pattern=_key("xrf"))]
ClaimKey = Annotated[str, Field(pattern=_key("clm"))]


UNKEYED: Literal[Unkeyed.UNKEYED] = Unkeyed.UNKEYED
AWAITING: Literal[Awaiting.AWAITING] = Awaiting.AWAITING


def _is_stated(value: object) -> bool:
    return value == Establishment.STATED


class CandidateEntity(CoreModel):
    id: Id
    key: EntityKey | Unkeyed = UNKEYED
    type: PrefixedName
    label: str
    scope: EntityScope
    extent: EntityExtent | MISSING = MISSING  # type: ignore[valid-type]  # a local entity's reach
    scope_segment: str | MISSING = MISSING  # type: ignore[valid-type]  # segment key, local only
    symbol: str | MISSING = MISSING  # type: ignore[valid-type]
    aliases: tuple[str, ...] = ()
    identity: dict[PrefixedName, str] = Field(default_factory=dict)  # slot -> id or literal

    @model_validator(mode="after")
    def _only_local(self) -> Self:
        validators.candidate_entity(self)  # extent, scope_segment: only on a local entity
        return self


class CandidateStatement(CoreModel):
    id: Id
    key: StatementKey | Unkeyed = UNKEYED
    kind: str
    anchor: Annotated[tuple[str, ...], Field(min_length=1)]  # segment keys


class CandidateReference(CoreModel):
    """An `ExternalReference` node (D1 §4.4): its descriptor as stored, its `xrf` key once keyed,
    and the statement consolidation resolved it to, or `AWAITING`. Claims name it where they cite
    it; it is never dropped for being unresolved."""

    id: Id
    key: ReferenceKey | Unkeyed = UNKEYED
    descriptor: StoredDescriptor
    resolved_to: StatementKey | Awaiting = AWAITING


class CandidateClaim(CoreModel):
    id: Id
    key: ClaimKey | Unkeyed = UNKEYED
    predicate: PrefixedName
    subject: SubjectId  # an entity (an ExternalReference included) or a statement
    object: StoredObject  # `{ref: id}` or a value
    qualifiers: StoredQualifiers = Field(default_factory=StoredQualifiers)
    statement: StatementId | MISSING = MISSING  # type: ignore[valid-type]
    statement_role: StatementRole | MISSING = MISSING  # type: ignore[valid-type]
    establishment: Establishment = Field(Establishment.STATED, exclude_if=_is_stated)
    derived_from: Annotated[tuple[ClaimId, ...], Field(min_length=1)] | MISSING = MISSING  # type: ignore[valid-type]
    rule: str | MISSING = Field(MISSING, min_length=1)  # type: ignore[valid-type]
    evidence: tuple[StoredEvidence, ...] = ()

    @model_validator(mode="after")
    def _derivation(self) -> Self:
        validators.candidate_claim(self)  # derived_from and rule exactly when derived
        return self


class CandidateAlternative(CoreModel):
    """Claims the author marks as alternatives of one another (D5 §11, §8.2 `alternative_of`)."""

    refs: Annotated[tuple[ClaimId, ...], Field(min_length=2)]
    reason: str


class CandidateUnsupported(CoreModel):
    """Text the schema cannot express (D1 §8.1), which D5 §5.1 turns into a `core:unschematized`
    claim."""

    id: Id
    start: Offset
    end: Offset
    reason: str
    coarse: bool | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _span(self) -> Self:
        validators.candidate_unsupported(self)
        return self


class KeyedCandidateSet(CoreModel):
    rendition: RenditionKey
    entities: tuple[CandidateEntity, ...] = ()
    statements: tuple[CandidateStatement, ...] = ()
    references: tuple[CandidateReference, ...] = ()
    claims: tuple[CandidateClaim, ...] = ()
    alternatives: tuple[CandidateAlternative, ...] = ()
    unsupported: tuple[CandidateUnsupported, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        seen: set[str] = set()
        for item in (*self.entities, *self.statements, *self.references, *self.claims,
                     *self.unsupported):  # fmt: skip
            if item.id in seen:
                raise ValueError(f"candidate id {item.id!r} is used twice")
            seen.add(item.id)
        return self
