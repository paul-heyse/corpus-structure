"""Finite typed queries over one decoded, explicitly selected rich admission.

The graph owns a retained identity universe. Its selected fact/occurrence/reading
headers own conclusions; possessing another retained member grants no such standing.
Every result is relative to this whole product, never a complete corpus assertion.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as Date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_serializer

from corpus_structure.core.vocab import CaseRule

from .alias_policy import label_normalizer
from .data_operation_identity import semantic_value
from .data_operation_json import DdoJsonValue, json_bytes
from .data_operation_ports import _untrusted_value
from .identity import canonical_bytes
from .refusals import SemanticRefusal
from .rich_graph_validation import RichGraphState
from .rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichCollectionValue,
    DdoRichConsolidation,
    DdoRichEntity,
    DdoRichFact,
    DdoRichOccurrence,
    DdoRichQualificationMeaning,
    DdoRichRecordValue,
    DdoRichSourceReadingAssertion,
)


class RichQueryRefused(SemanticRefusal):
    """An exact rich query lacks its declared scope or admitted work/response capacity."""


class QueryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    population: Literal["selected", "retained"] = "selected"
    include_suppositions: bool = False


class EntityQuery(QueryOptions):
    name: Literal["entity"]
    key: str | None = None
    class_name: str | None = None


class ClaimsQuery(QueryOptions):
    name: Literal["claims"]
    subject: str | None = None
    predicate: str | None = None
    object_entity: str | None = None
    fact_id: str | None = None


class StatementQuery(QueryOptions):
    name: Literal["statement"]
    product_id: str = Field(min_length=1)
    member_id: str | None


class EvidenceQuery(QueryOptions):
    name: Literal["evidence"]
    fact_id: str | None = None
    occurrence_id: str | None = None


class SourceReadingsQuery(QueryOptions):
    name: Literal["source_readings"]
    record_id: str | None = None


class OwnershipAtQuery(QueryOptions):
    name: Literal["ownership_at"]
    asset: str = Field(min_length=1)
    date: Date

    @field_serializer("date")
    def date_on_wire(self, value: Date) -> str:
        return value.isoformat()


class FamilyProfileQuery(QueryOptions):
    name: Literal["family_profile", "transformations_of"]
    family: str = Field(min_length=1)


class ConstructionProfileQuery(QueryOptions):
    name: Literal["construction_profile"]
    construction: str = Field(min_length=1)


class ParameterMappingQuery(QueryOptions):
    name: Literal["parameter_mapping"]
    family: str = Field(min_length=1)
    construction: str = Field(min_length=1)


class FamiliesWhereQuery(QueryOptions):
    name: Literal["families_where"]
    predicate: str = Field(min_length=1)
    value: DdoJsonValue = None


class RelationsQuery(QueryOptions):
    name: Literal["relations_between"]
    a: str = Field(min_length=1)
    b: str = Field(min_length=1)
    depth: int = Field(default=4, strict=True, ge=1, le=4)
    max_edges: int = Field(default=100000, strict=True, ge=1, le=1000000)
    max_frontier: int = Field(default=20000, strict=True, ge=1, le=100000)
    max_state_bytes: int = Field(default=8388608, strict=True, ge=1, le=33554432)


type RichQuery = Annotated[
    EntityQuery
    | ClaimsQuery
    | StatementQuery
    | EvidenceQuery
    | SourceReadingsQuery
    | OwnershipAtQuery
    | FamilyProfileQuery
    | ConstructionProfileQuery
    | ParameterMappingQuery
    | FamiliesWhereQuery
    | RelationsQuery,
    Field(discriminator="name"),
]
RichQueryName = Literal[
    "entity",
    "claims",
    "statement",
    "evidence",
    "source_readings",
    "ownership_at",
    "family_profile",
    "construction_profile",
    "families_where",
    "parameter_mapping",
    "transformations_of",
    "relations_between",
]
QUERY_NAMES = frozenset(TypeAdapter(RichQuery).json_schema()["discriminator"]["mapping"])


@dataclass(frozen=True)
class RichQueryRow:
    value: dict[str, Any]


def ownership_applicability(
    interval: dict | None, at: Date
) -> Literal["established", "not_applicable", "unknown"]:
    """Source-stated bounds only: partial/symbolic dates and unknown inclusivity stay unknown."""
    if interval is None:
        return "unknown"
    for name, inclusive in (("start", "start_incl"), ("end", "end_incl")):
        value = interval.get(name)
        if value is None:
            continue
        if not isinstance(value, dict) or value.get("kind") != "partial_date":
            return "unknown"
        raw = value.get("lexical")
        if not isinstance(raw, str) or len(raw) != 10:
            return "unknown"
        try:
            bound = Date.fromisoformat(raw)
        except ValueError:
            return "unknown"
        if (name == "start" and at < bound) or (name == "end" and at > bound):
            return "not_applicable"
        if at == bound:
            if interval.get(inclusive) is None:
                return "unknown"
            if interval.get(inclusive) is False:
                return "not_applicable"
    return "established"


def statement_key(reference) -> str | None:
    return (
        None
        if reference is None
        else canonical_bytes([reference.product_id, reference.member_id]).decode()
    )


class RichGraphIndex:
    """Bounded indexes over actual accepted or explicitly private rich graph meaning."""

    def __init__(
        self,
        state: RichGraphState,
        *,
        max_members: int = 100000,
        max_nested_members: int = 1000,
    ):
        if not isinstance(state.graph, (DdoRichAdmission, DdoRichConsolidation)):
            raise RichQueryRefused("rich interpretation requires its actual typed graph whole")
        selection = (
            state.graph if isinstance(state.graph, DdoRichAdmission) else state.graph.eligibility
        )
        if len(state.members) > max_members or max_members < 1 or max_nested_members < 1:
            raise RichQueryRefused("rich query graph exceeds the admitted member capacity")
        self.state, self.max_nested_members = state, max_nested_members
        self.entities = {
            key: value for key, value in state.members.items() if isinstance(value, DdoRichEntity)
        }
        self.facts = {
            key: value for key, value in state.members.items() if isinstance(value, DdoRichFact)
        }
        self.occurrences = {
            key: value
            for key, value in state.members.items()
            if isinstance(value, DdoRichOccurrence)
        }
        self.readings = {
            key: value
            for key, value in state.members.items()
            if isinstance(value, DdoRichSourceReadingAssertion)
        }
        self.selected_facts = frozenset(selection.selected_fact_ids)
        self.selected_occurrences = frozenset(selection.selected_occurrence_ids)
        self.selected_readings = (
            frozenset(state.graph.selected_reading_ids)
            if isinstance(state.graph, DdoRichAdmission)
            else frozenset()
        )
        self.scientific_representatives = {
            row.fact_id: row for row in selection.scientific_representatives
        }
        if (
            not self.selected_facts <= self.facts.keys()
            or not self.selected_occurrences <= self.occurrences.keys()
            or not self.selected_readings <= self.readings.keys()
        ):
            raise RichQueryRefused("rich selection headers refer outside their actual typed graph")
        if any(
            self.occurrences[key].fact_id not in self.selected_facts
            for key in self.selected_occurrences
        ):
            raise RichQueryRefused("selected rich occurrence lacks its actual selected fact")
        self.by_fact = defaultdict(list)
        self.selected_by_subject = defaultdict(list)
        for key in sorted(self.selected_facts):
            self.selected_by_subject[self.facts[key].subject_entity].append(key)
        self.definiens = defaultdict(set)
        for occurrence in sorted(self.occurrences.values(), key=lambda value: value.occurrence_id):
            self.by_fact[occurrence.fact_id].append(occurrence)
            if occurrence.statement is not None and occurrence.statement_role == "definiens":
                self.definiens[
                    (
                        statement_key(occurrence.statement),
                        self.facts[occurrence.fact_id].subject_entity,
                    )
                ].add(occurrence.fact_id)
        self.normalize = label_normalizer(state.prepared)
        self.class_metadata = {
            row.name: json.loads(row.body)
            for row in state.prepared.registry_rows
            if row.kind == "operation_class"
        }
        self._objects = {}
        self._qualifications = {}
        self.unknowns: dict[str, dict] = {}

    def iri(self, value: str) -> str:
        definition = self.state.prepared.index.definitions.get(value)
        return definition.iri if definition is not None else self.state.prepared.expand_name(value)

    def is_a(self, entity: DdoRichEntity, iri: str) -> bool:
        target = self.state.prepared.index.by_iri.get(iri)
        return target is not None and any(
            (definition := self.state.definition(contract)).iri == iri
            or target.name in definition.ancestors
            for contract in entity.class_contracts
        )

    def resolve(self, value: str, *, class_name: str | None = None) -> tuple[str, ...]:
        entities = tuple(
            entity
            for entity in self.entities.values()
            if class_name is None or self.is_a(entity, self.iri(class_name))
        )
        if any(entity.entity_id == value for entity in entities):
            return (value,)
        matches = set()
        for entity in entities:
            for basis in entity.identities:
                if basis.label is None:
                    continue
                definition = self.state.definition(basis.class_contract)
                case = (
                    CaseRule.FOLD
                    if self.class_metadata.get(definition.name, {}).get("cs:case") == "casefold"
                    else CaseRule.PRESERVE
                )
                if self.normalize(value, definition.iri, case) == self.normalize(
                    basis.label, definition.iri, case
                ):
                    matches.add(entity.entity_id)
        return tuple(sorted(matches))

    def object(self, fact_id: str):
        if fact_id not in self._objects:
            fact = self.facts[fact_id]
            definition, prop, _ = self.state.property(fact.property_contract)
            self._objects[fact_id] = self.state.property_value(
                fact.object_value, definition, prop, item=prop.multivalued
            )
        return self._objects[fact_id]

    def object_entity(self, fact_id: str) -> str | None:
        fact = self.facts[fact_id]
        _, prop, _ = self.state.property(fact.property_contract)
        value = self.object(fact_id)
        if not prop.inlined and prop.range in self.state.prepared.index.definitions:
            return value
        raw = _untrusted_value(value)
        return raw.get("target") if isinstance(raw, dict) and raw.get("kind") == "entity" else None

    def qualification(self, occurrence):
        if occurrence.occurrence_id not in self._qualifications:
            self._qualifications[occurrence.occurrence_id] = self.state.value(
                occurrence.observed_qualification_value
            )
        return self._qualifications[occurrence.occurrence_id]

    def included(self, options: QueryOptions, *, premises=False) -> tuple[str, ...]:
        pool = self.facts if premises or options.population == "retained" else self.selected_facts
        result = []
        for identifier in sorted(pool):
            occurrences = self.by_fact[identifier]
            if not premises and options.population == "selected":
                occurrences = [
                    item for item in occurrences if item.occurrence_id in self.selected_occurrences
                ]
            if (
                options.include_suppositions
                or premises
                or not occurrences
                or any(
                    _untrusted_value(self.qualification(item)).get("modality") != "supposed"
                    for item in occurrences
                )
            ):
                result.append(identifier)
        return tuple(result)

    def values(self, roots) -> tuple[dict, ...]:
        pending, found = list(roots), {}
        while pending:
            identifier = pending.pop()
            if identifier in found:
                continue
            if len(found) >= self.max_nested_members:
                raise RichQueryRefused("rich answer exceeds the nested typed-value capacity")
            body = self.state.members[identifier]
            found[identifier] = body.model_dump(mode="python")
            if isinstance(body, (DdoRichRecordValue, DdoRichQualificationMeaning)):
                pending.extend(field.value_id for field in body.fields)
            elif isinstance(body, DdoRichCollectionValue):
                pending.extend(entry.value_id for entry in body.entries)
        return tuple(found[key] for key in sorted(found))

    def entity_record(self, entity_id: str) -> dict:
        entity = self.entities[entity_id]
        return dict(
            entity=entity.model_dump(mode="python"),
            classes=[self.state.definition(contract).iri for contract in entity.class_contracts],
            standing="resolved-identity",
            selected_fact_ids=self.selected_by_subject[entity_id],
            values=self.values(
                field.value_id for basis in entity.identities for field in basis.fields
            ),
        )

    def claim_record(self, fact_id: str) -> dict:
        fact = self.facts[fact_id]
        occurrences = self.by_fact[fact_id]
        if len(occurrences) > self.max_nested_members:
            raise RichQueryRefused("rich claim exceeds the nested occurrence capacity")
        roots = [
            fact.object_value,
            fact.qualification_meaning,
            *(item.observed_qualification_value for item in occurrences),
        ]
        representative = self.scientific_representatives.get(fact_id)
        return dict(
            fact=fact.model_dump(mode="python"),
            selected=fact_id in self.selected_facts,
            scientific_representative=None
            if representative is None
            else representative.model_dump(mode="python"),
            object=semantic_value(_untrusted_value(self.object(fact_id))),
            occurrences=[
                dict(
                    **item.model_dump(mode="python"),
                    selected=item.occurrence_id in self.selected_occurrences,
                    qualification=semantic_value(_untrusted_value(self.qualification(item))),
                )
                for item in occurrences
            ],
            values=self.values(roots),
        )

    def claim_records(self, identifiers):
        identifiers = tuple(identifiers)
        if len(identifiers) > self.max_nested_members:
            raise RichQueryRefused("rich answer exceeds the nested claim capacity")
        rows, size = [], 0
        for identifier in identifiers:
            row = self.claim_record(identifier)
            size += len(json_bytes(row))
            if size > 8 * 1024 * 1024:
                raise RichQueryRefused("rich answer exceeds the nested claim byte capacity")
            rows.append(row)
        return rows

    def visible_occurrences(self, fact_id: str, options: QueryOptions):
        return tuple(
            item
            for item in self.by_fact[fact_id]
            if options.population == "retained" or item.occurrence_id in self.selected_occurrences
        )

    def condition_refs(self, fact_id: str, options: QueryOptions) -> frozenset[str]:
        from .reference_positions import collect_references

        references = set()
        for occurrence in self.visible_occurrences(fact_id, options):
            qualification = self.qualification(occurrence)
            references.update(
                item.target
                for item in collect_references(
                    self.state.prepared, type(qualification).__name__, qualification
                )
                if item.kind == "fact"
            )
        return frozenset(references)


class RichQueryIndex(RichGraphIndex):
    """Public named knowledge queries require the actual selected accepted whole."""

    def __init__(self, state: RichGraphState, **limits):
        if not isinstance(state.graph, DdoRichAdmission):
            raise RichQueryRefused("rich queries require the actual selected accepted whole")
        super().__init__(state, **limits)


def query_rows(index: RichQueryIndex, query: RichQuery):
    if query.name in {
        "family_profile",
        "construction_profile",
        "families_where",
        "parameter_mapping",
        "transformations_of",
        "relations_between",
    }:
        from .rich_statistics_queries import statistics_rows

        yield from statistics_rows(index, query)
        return
    if isinstance(query, EntityQuery):
        keys = (
            sorted(index.entities)
            if query.key is None
            else index.resolve(query.key, class_name=query.class_name)
        )
        for key in keys:
            if query.class_name is None or index.is_a(
                index.entities[key], index.iri(query.class_name)
            ):
                yield RichQueryRow(index.entity_record(key))
    elif isinstance(query, ClaimsQuery):
        subjects = None if query.subject is None else index.resolve(query.subject)
        objects = None if query.object_entity is None else index.resolve(query.object_entity)
        for key in index.included(query):
            fact = index.facts[key]
            if (
                (query.fact_id is not None and key != query.fact_id)
                or (subjects is not None and fact.subject_entity not in subjects)
                or (query.predicate is not None and fact.predicate != index.iri(query.predicate))
                or (objects is not None and index.object_entity(key) not in objects)
            ):
                continue
            yield RichQueryRow(index.claim_record(key))
    elif isinstance(query, OwnershipAtQuery):
        assets = set(index.resolve(query.asset, class_name="Asset"))
        for key in index.included(query):
            fact = index.facts[key]
            if fact.predicate != index.iri("toy:owns") or index.object_entity(key) not in assets:
                continue
            for occurrence in index.visible_occurrences(key, query):
                qualification = _untrusted_value(index.qualification(occurrence))
                if not query.include_suppositions and qualification.get("modality") == "supposed":
                    continue
                interval = qualification.get("valid_time")
                yield RichQueryRow(
                    dict(
                        claim=index.claim_record(key),
                        occurrence=occurrence.model_dump(mode="python"),
                        qualification=semantic_value(qualification),
                        interval=semantic_value(interval),
                        applicability=ownership_applicability(interval, query.date),
                    )
                )
    elif isinstance(query, StatementQuery):
        key = canonical_bytes([query.product_id, query.member_id]).decode()
        claims = [
            identifier
            for identifier in index.included(query)
            if any(
                statement_key(item.statement) == key
                for item in index.visible_occurrences(identifier, query)
            )
        ]
        if len(claims) > index.max_nested_members:
            raise RichQueryRefused("statement exceeds the nested claim capacity")
        if claims:
            refs = {
                canonical_bytes(
                    item.statement.model_dump(mode="python")
                ): item.statement.model_dump(mode="python")
                for identifier in claims
                for item in index.visible_occurrences(identifier, query)
                if statement_key(item.statement) == key
            }
            yield RichQueryRow(
                dict(
                    statement_key=key,
                    sources=[refs[item] for item in sorted(refs)],
                    claims=index.claim_records(claims),
                )
            )
    elif isinstance(query, EvidenceQuery):
        for key in index.included(query):
            if query.fact_id is not None and query.fact_id != key:
                continue
            for occurrence in index.by_fact[key]:
                if (
                    query.occurrence_id is not None
                    and query.occurrence_id != occurrence.occurrence_id
                ):
                    continue
                if (
                    query.population == "selected"
                    and occurrence.occurrence_id not in index.selected_occurrences
                ):
                    continue
                yield RichQueryRow(
                    dict(
                        fact_id=key,
                        occurrence=occurrence.model_dump(mode="python"),
                        availability="retained-source-references",
                        source_body_retrieval="not_run",
                    )
                )
    elif isinstance(query, SourceReadingsQuery):
        pool = index.readings if query.population == "retained" else index.selected_readings
        for key in sorted(pool):
            reading = index.readings[key]
            if query.record_id is not None and reading.record_id != query.record_id:
                continue
            yield RichQueryRow(
                dict(
                    assertion=reading.model_dump(mode="python"),
                    selected=key in index.selected_readings,
                    reading=semantic_value(
                        _untrusted_value(index.state.value(reading.reading_value))
                    ),
                    values=index.values((reading.reading_value,)),
                    scientific_truth="not-established",
                )
            )
    else:
        raise RichQueryRefused("unsupported current rich query")
