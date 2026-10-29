"""Typed semantic answers; identifiers retain their actual semantic authority."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.query import EntityReference, Evidence, QueryRow, ValueNode


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityAnswer(Answer):
    entity: EntityReference
    properties: tuple[QueryRow, ...] = ()
    values: tuple[ValueNode, ...] = ()


class ClaimAnswer(Answer):
    fact: QueryRow
    values: tuple[ValueNode, ...] = ()


class EvidenceAnswer(Answer):
    fact_id: str
    evidence: Evidence


class FindAnswer(Answer):
    entity: EntityAnswer | None = None
    source_uri: str | None = None
    locator: str | None = None
    text: str | None = None
    score: float = 0


class TransformationAnswer(Answer):
    conclusion: ClaimAnswer
    premises: tuple[ClaimAnswer, ...]
    definiens: tuple[ClaimAnswer, ...] = ()


class RelationAnswer(Answer):
    depth: int
    claims: tuple[ClaimAnswer, ...]


class FamilyAnswer(Answer):
    family: EntityReference
    claim: ClaimAnswer


class StatementAnswer(Answer):
    statement: EntityReference
    claims: tuple[ClaimAnswer, ...]
    proofs: tuple[ClaimAnswer, ...] = ()
