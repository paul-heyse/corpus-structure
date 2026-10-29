"""Release-bound occurrence assembly; acceptance policy stays with the domain operation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from pydantic import BaseModel

from .identity import _meaning, canonical_bytes, occurrence_key
from .publication import (
    EntityRow, EvidenceRow, FactRow, MembershipRow, MembershipSupportRow,
    OccurrenceRow, OccurrenceEvidenceRow, OccurrenceEstablishmentRow,
    PublicationBatch, RoleRow, SelectionRow, SupportRow, ValueRow,
)
from .types import PreparedRelease


@dataclass(frozen=True)
class SourceItem:
    """One located source item, before fact grouping; item identity must survive retries."""
    subject: str
    class_name: str
    property_name: str
    object: Any
    qualification: dict[str, Any]
    source: str
    item: str
    establishment: str
    evidence: tuple[EvidenceRow, ...]
    qualification_class: str = "Qualification"


def assemble(
    prepared: PreparedRelease, realization_id: str, batch_id: str,
    items: tuple[SourceItem, ...], *, selected: frozenset[str] = frozenset(),
) -> PublicationBatch:
    """Lower typed values and retain every source occurrence without choosing scientific truth.

    ``selected`` contains fact IDs selected by the domain policy, not confidence cutoffs.
    The publisher independently enforces applicability, range and accepted-state constraints.
    """
    definitions = {d.name: d for d in prepared.definitions}
    entities: dict[str, EntityRow] = {}
    memberships: dict[tuple[str, str], MembershipRow] = {}
    values: dict[str, ValueRow] = {}
    roles: dict[tuple[str, str, int], RoleRow] = {}
    facts: dict[str, FactRow] = {}
    occurrences: dict[str, OccurrenceRow] = {}
    establishments: dict[str, OccurrenceEstablishmentRow] = {}
    evidence: dict[str, EvidenceRow] = {}
    occurrence_evidence: set[OccurrenceEvidenceRow] = set()
    membership_support: set[MembershipSupportRow] = set()
    supports: set[SupportRow] = set()

    def plain(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return {k: plain(v) for k, v in value if k in value.model_fields_set}
        if isinstance(value, (tuple, list)):
            return [plain(v) for v in value]
        if isinstance(value, dict):
            return {k: plain(v) for k, v in value.items()}
        return value

    def representation(value: Any) -> Any:
        if isinstance(value, Decimal):
            return ["decimal-report", str(value)]
        if isinstance(value, datetime):
            return ["datetime-report", value.isoformat()]
        if isinstance(value, date):
            return ["date-report", value.isoformat()]
        if isinstance(value, dict):
            return ["mapping", [[key, representation(item)] for key, item in sorted(value.items())]]
        if isinstance(value, (tuple, list)):
            return ["sequence", [representation(item) for item in value]]
        return _meaning(value)

    def lower(value: Any, range_name: str | None = None, inlined: bool = False) -> str:
        raw = plain(value)
        identity = [range_name, representation(raw)]
        key = 'value:' + sha256(canonical_bytes(identity)).hexdigest()
        if key in values:
            return key
        if range_name in definitions and not inlined:
            if not isinstance(raw, str):
                raise ValueError('non-inlined entity reference requires an identifier')
            entities[raw] = EntityRow(raw)
            row = ValueRow(key, 'entity', entity_id=raw)
        elif isinstance(value, BaseModel):
            definition = definitions[type(value).__name__]
            props = {p.name: p for p in definition.properties}
            row = ValueRow(key, 'record', datatype=definition.iri)
            for name, item in value:
                if name not in value.model_fields_set:
                    continue
                prop = props[name]
                if prop.collection_key:
                    child = lower(item, prop.range, True)
                elif prop.multivalued:
                    child = 'value:' + sha256(canonical_bytes([prop.range, prop.inlined, representation(plain(item))])).hexdigest()
                    values[child] = ValueRow(child, 'sequence')
                    for index, member in enumerate(item):
                        roles[child, 'item', index] = RoleRow(child, 'item', index, lower(member, prop.range, prop.inlined))
                else:
                    child = lower(item, prop.range, prop.inlined)
                roles[key, name, 0] = RoleRow(key, name, 0, child)
        elif isinstance(raw, bool):
            row = ValueRow(key, 'boolean', boolean_value=raw)
        elif isinstance(raw, int):
            row = ValueRow(key, 'integer', text_value=str(raw))
        elif isinstance(raw, Decimal):
            row = ValueRow(key, 'decimal', decimal_lexical=str(raw))
        elif isinstance(raw, float):
            row = ValueRow(key, 'float', text_value=raw.hex())
        elif isinstance(raw, datetime):
            row = ValueRow(key, 'datetime', text_value=raw.astimezone(UTC).isoformat())
        elif isinstance(raw, date):
            row = ValueRow(key, 'date', text_value=raw.isoformat())
        elif isinstance(raw, str):
            row = ValueRow(key, 'string', text_value=raw)
        elif isinstance(raw, dict):
            row = ValueRow(key, 'mapping')
            for name, member in value.items():
                roles[key, name, 0] = RoleRow(key, name, 0, lower(member, range_name, inlined))
        elif isinstance(raw, list):
            row = ValueRow(key, 'sequence')
            for position, item in enumerate(value):
                roles[key, 'item', position] = RoleRow(key, 'item', position, lower(item))
        else:
            raise ValueError('untyped/null values require a declared semantic representation')
        values[key] = row
        return key

    for item in items:
        if item.establishment not in {'stated', 'agent_asserted'}:
            raise ValueError('source assembly requires explicit source establishment; inference publishes proofs')
        if not item.evidence:
            raise ValueError('source item requires located evidence')
        definition = definitions[item.class_name]
        prop = next(p for p in definition.properties if p.name == item.property_name)
        obj = prepared.property_adapter(item.class_name, item.property_name, item=prop.multivalued).validate_python(item.object, strict=True)
        prepared.qualification_definition(item.qualification_class)
        qualification = prepared.validate_python(item.qualification_class, item.qualification)
        object_id = lower(obj, prop.range, prop.inlined)
        qualification_id = lower(qualification, item.qualification_class, True)
        fact_id = prepared.fact_identity(realization_id, item.subject, prop.iri, plain(obj), plain(qualification), qualification_class=item.qualification_class)
        occurrence_id = occurrence_key(prepared.release_id, realization_id, item.source, item.item)
        occurrence = OccurrenceRow(occurrence_id, fact_id, item.source, item.item, object_id, qualification_id)
        if occurrence_id in occurrences and occurrences[occurrence_id] != occurrence:
            raise ValueError('source item identity cannot bind different content')
        entities[item.subject] = EntityRow(item.subject)
        previous = memberships.get((item.subject, definition.iri))
        membership_basis = 'stated' if item.establishment == 'stated' or (previous is not None and previous.establishment == 'stated') else 'agent_asserted'
        memberships[item.subject, definition.iri] = MembershipRow(item.subject, definition.iri, membership_basis)
        fact = FactRow(fact_id, item.subject, prop.iri, object_id, qualification_id)
        if fact_id in facts:
            fact = min((facts[fact_id], fact), key=lambda row: (row.object_value_id, row.qualification_value_id or ''))
        facts[fact_id] = fact
        occurrences[occurrence_id] = occurrence
        establishment = OccurrenceEstablishmentRow(occurrence_id, item.establishment)
        if occurrence_id in establishments and establishments[occurrence_id] != establishment:
            raise ValueError('source item identity cannot bind different establishment')
        establishments[occurrence_id] = establishment
        supports.add(SupportRow(fact_id, occurrence_id))
        for ref in item.evidence:
            if ref.evidence_id in evidence and evidence[ref.evidence_id] != ref:
                raise ValueError('evidence identity cannot bind different content')
            evidence[ref.evidence_id] = ref
            occurrence_evidence.add(OccurrenceEvidenceRow(occurrence_id, ref.evidence_id))
            membership_support.add(MembershipSupportRow(item.subject, definition.iri, ref.evidence_id))
    if not selected.issubset(facts):
        raise ValueError('selection names facts outside this assembly')
    return PublicationBatch(
        prepared.release_id, realization_id, batch_id,
        entity=tuple(entities[k] for k in sorted(entities)),
        membership=tuple(memberships[k] for k in sorted(memberships)),
        typed_value=tuple(values[k] for k in sorted(values)),
        value_role=tuple(roles[k] for k in sorted(roles)),
        fact=tuple(facts[k] for k in sorted(facts)),
        occurrence=tuple(occurrences[k] for k in sorted(occurrences)),
        support=tuple(sorted(supports, key=lambda s: (s.fact_id,s.occurrence_id))),
        selection=tuple(SelectionRow(k) for k in sorted(selected)),
        evidence=tuple(evidence[k] for k in sorted(evidence)),
        occurrence_evidence=tuple(sorted(occurrence_evidence, key=lambda s:(s.occurrence_id,s.evidence_id))),
        membership_support=tuple(sorted(membership_support, key=lambda s:(s.entity_id,s.class_id,s.evidence_id))),
        occurrence_establishment=tuple(establishments[k] for k in sorted(establishments)),
    )
