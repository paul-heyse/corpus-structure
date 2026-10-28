"""The keyed candidate set: the core claim shape the rule-view builder reads at both call sites.

D5 §8.2; foundations §3.5. S2's batch adapter (at submission) and C1's pool (at finalize) both
produce it. At submission, ids are local refs and keys are null; at finalize, ids are keys. The
grammar's facts at finalize and the derived view attributes are the view builder's arguments,
not fields here. Qualifiers, values and evidence are in stored form.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from corpus_structure.core.batch import StoredEvidence, StoredQualifiers
from corpus_structure.core.values import CoreModel, StoredObject
from corpus_structure.core.vocab import EntityScope, Establishment, StatementRole

Id = Annotated[str, Field(min_length=1)]


class CandidateEntity(CoreModel):
    id: Id
    key: str | None = None
    type: str
    label: str
    scope: EntityScope
    scope_segment: str | None = None  # segment key, for a local entity
    symbol: str | None = None
    aliases: tuple[str, ...] = ()
    identity: dict[str, str] = Field(default_factory=dict)  # slot -> entity id or literal

    @model_validator(mode="after")
    def _segment_iff_local(self) -> Self:
        if (self.scope is EntityScope.LOCAL) != (self.scope_segment is not None):
            raise ValueError("a candidate entity has a scope_segment exactly when it is local")
        return self


class CandidateStatement(CoreModel):
    id: Id
    key: str | None = None
    kind: str
    # Segment keys, or "outside": a statement the unit refers to but that lies outside it, kept
    # with key None until consolidation resolves it to the statement it names.
    anchor: Literal["outside"] | Annotated[tuple[str, ...], Field(min_length=1)]


class CandidateClaim(CoreModel):
    id: Id
    key: str | None = None
    predicate: str
    subject: Id  # an entity or statement id
    object: StoredObject  # `{ref: id}` or a value
    qualifiers: StoredQualifiers = Field(default_factory=StoredQualifiers)
    statement: Id | None = None
    statement_role: StatementRole | None = None
    establishment: Establishment = Establishment.STATED
    evidence: tuple[StoredEvidence, ...] = ()


class KeyedCandidateSet(CoreModel):
    entities: tuple[CandidateEntity, ...] = ()
    statements: tuple[CandidateStatement, ...] = ()
    claims: tuple[CandidateClaim, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        seen: set[str] = set()
        for item in (*self.entities, *self.statements, *self.claims):
            if item.id in seen:
                raise ValueError(f"candidate id {item.id!r} is used twice")
            seen.add(item.id)
        return self
