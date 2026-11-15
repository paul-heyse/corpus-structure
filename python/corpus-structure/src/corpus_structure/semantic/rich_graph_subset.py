"""Finite typed rich member closure for an actual admission decision."""

import networkx as nx

from .rich_knowledge_contracts import (
    DdoRichAlternative,
    DdoRichAssessment,
    DdoRichCasefoldText,
    DdoRichCollectionValue,
    DdoRichDiagnostic,
    DdoRichEntity,
    DdoRichEntityValue,
    DdoRichFact,
    DdoRichIdentityExclusion,
    DdoRichIdentityResolution,
    DdoRichOccurrence,
    DdoRichOccurrenceDecision,
    DdoRichQualificationMeaning,
    DdoRichRecordValue,
    DdoRichScalarValue,
    DdoRichSourceReadingAssertion,
)

_VALUE_TYPES = (
    DdoRichScalarValue,
    DdoRichEntityValue,
    DdoRichRecordValue,
    DdoRichCollectionValue,
    DdoRichQualificationMeaning,
    DdoRichCasefoldText,
)


def rich_member_dependencies(body):
    """Actual local typed member references; external provenance is not a local edge."""
    if isinstance(body, (DdoRichScalarValue, DdoRichCasefoldText, DdoRichDiagnostic)):
        return ()
    if isinstance(body, DdoRichEntityValue):
        return (body.entity_id,)
    if isinstance(body, (DdoRichRecordValue, DdoRichQualificationMeaning)):
        return tuple(field.value_id for field in body.fields)
    if isinstance(body, DdoRichCollectionValue):
        return tuple(entry.value_id for entry in body.entries)
    if isinstance(body, DdoRichEntity):
        return tuple(field.value_id for basis in body.identities for field in basis.fields)
    if isinstance(body, DdoRichIdentityResolution):
        return (body.resolved_entity_id, *body.matched_entity_ids)
    if isinstance(body, DdoRichIdentityExclusion):
        return tuple(
            value for value in (body.left_entity_id, body.right_entity_id) if value is not None
        )
    if isinstance(body, DdoRichOccurrenceDecision):
        return (
            body.occurrence_id,
            body.fact_id,
            *(
                finding.assessment_id
                for finding in body.findings
                if finding.assessment_id is not None
            ),
        )
    if isinstance(body, DdoRichFact):
        return (body.subject_entity, body.object_value, body.qualification_meaning)
    if isinstance(body, DdoRichOccurrence):
        return (body.fact_id, body.observed_qualification_value, *body.dependencies)
    if isinstance(body, DdoRichSourceReadingAssertion):
        return (body.reading_value,)
    if isinstance(body, DdoRichAlternative):
        return body.fact_ids
    if isinstance(body, DdoRichAssessment):
        return body.occurrences
    raise ValueError("rich closure has no declared member relationship owner")


def admitted_rich_members(consolidation, *, accepted_readings: frozenset[str]):
    """Remove rejected reading assertions and their exclusive typed value closure."""
    packets = {packet.member_id: packet for packet in consolidation.members}
    if len(packets) != len(consolidation.members):
        raise ValueError("rich closure repeats a member identity")
    edges = nx.DiGraph(backend="networkx")
    edges.add_nodes_from(packets)
    for identifier, packet in packets.items():
        for target in rich_member_dependencies(packet.body):
            if target not in packets:
                raise ValueError("rich closure contains an unresolved actual member reference")
            edges.add_edge(identifier, target)
    readings = {
        identifier
        for identifier, packet in packets.items()
        if isinstance(packet.body, DdoRichSourceReadingAssertion)
    }
    if not accepted_readings <= readings:
        raise ValueError("rich admission selected an unavailable actual reading assertion")
    roots = {
        identifier
        for identifier, packet in packets.items()
        if not isinstance(packet.body, (*_VALUE_TYPES, DdoRichSourceReadingAssertion))
    } | accepted_readings
    reached = set(roots)
    for root in roots:
        reached.update(nx.descendants(edges, root))
    if reached & readings != accepted_readings:
        raise ValueError("rich graph dependencies require an unaccepted reading assertion")
    return tuple(packets[identifier] for identifier in sorted(reached))
