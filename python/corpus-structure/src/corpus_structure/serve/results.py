"""Typed semantic answers; identifiers retain their actual semantic authority."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.semantic.query import (
    EntityReference,
    Evidence,
    FactStanding,
    QueryRow,
    ValueNode,
)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityAnswer(Answer):
    entity: EntityReference
    properties: tuple[QueryRow, ...] = ()
    properties_population_complete: bool = True
    properties_query: dict[str, str] | None = None
    values: tuple[ValueNode, ...] = ()


class ClaimAnswer(Answer):
    fact: QueryRow
    values: tuple[ValueNode, ...] = ()


class EvidenceAnswer(Answer):
    standing: FactStanding
    fact_id: str
    evidence: Evidence


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
    population_complete: bool = True
    claims_query: dict[str, JsonValue] | None = None
