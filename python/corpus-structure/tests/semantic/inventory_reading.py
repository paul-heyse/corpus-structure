"""Test consumers explicitly traverse bounded inventories and request immutable bodies.

These helpers only assemble actual relation rows. Tests keep their independent semantic
expectations, including source identities, absent populations and authored invalid inputs.
"""

from corpus_structure.semantic.query import (
    AlternativeGroup,
    Assessment,
    CitationRole,
    Derivation,
    Evidence,
    OccurrenceContext,
    OccurrenceSupport,
)
from corpus_structure.semantic.refusals import decode_semantic_reason
from corpus_structure.semantic.scientific_evidence_schema import parse_scientific_assessment_reason


def inventory_items(session, fact_id, collection):
    items, token = [], None
    while True:
        page = session.inventory(fact_id, collection, continuation=token)
        assert page.binding == session.binding and page.root == fact_id
        items.extend(page.items)
        token = page.next_page_token
        if token is None:
            assert page.population_complete
            return tuple(items)
        assert not page.population_complete


def inventory_supports(session, fact_id):
    links = inventory_items(session, fact_id, "support_evidence")
    contexts = {
        row["occurrence_id"]: OccurrenceContext(
            statement_entity_id=row["statement_entity_id"], statement_role=row["statement_role"]
        )
        for row in inventory_items(session, fact_id, "occurrence_contexts")
    }
    citations = inventory_items(session, fact_id, "citation_roles")
    return tuple(
        OccurrenceSupport(
            **{
                key: row[key]
                for key in (
                    "occurrence_id",
                    "source",
                    "item",
                    "report_object_value_id",
                    "report_qualification_value_id",
                )
            },
            evidence_ids=tuple(
                link["evidence_id"]
                for link in links
                if link["occurrence_id"] == row["occurrence_id"]
            ),
            context=contexts.get(row["occurrence_id"]),
            citation_roles=tuple(
                CitationRole(evidence_id=c["evidence_id"], role=c["role"])
                for c in citations
                if c["occurrence_id"] == row["occurrence_id"]
            ),
        )
        for row in inventory_items(session, fact_id, "supports")
    )


def inventory_evidence(session, fact_id):
    return tuple(
        Evidence(**{key: row[key] for key in Evidence.model_fields if key in row})
        for row in inventory_items(session, fact_id, "evidence")
    )


def inventory_reports(session, fact_id):
    return tuple(
        session.source_report(fact_id, row["observation_key"])
        for row in inventory_items(session, fact_id, "source_reports")
    )


def inventory_assessments(session, fact_id):
    return tuple(
        Assessment(
            **{
                key: row[key]
                for key in Assessment.model_fields
                if key not in {"scientific_evidence", "semantic_reason"}
            },
            semantic_reason=decode_semantic_reason(row.get("semantic_reason")),
            scientific_evidence=parse_scientific_assessment_reason(row["reason"])
            if row["operation_id"] == "scientific.value_equivalence"
            else None,
        )
        for row in inventory_items(session, fact_id, "assessments")
    )


def inventory_alternatives(session, fact_id):
    members = inventory_items(session, fact_id, "alternative_members")
    return tuple(
        AlternativeGroup(
            **{key: row[key] for key in AlternativeGroup.model_fields if key != "member_fact_ids"},
            member_fact_ids=tuple(
                member["fact_id"] for member in members if member["group_id"] == row["group_id"]
            ),
        )
        for row in inventory_items(session, fact_id, "alternatives")
    )


def inventory_derivations(session, fact_id):
    premises = inventory_items(session, fact_id, "derivation_premises")
    return tuple(
        Derivation(
            derivation_id=row["derivation_id"],
            rule=row["rule"],
            rule_version=row["rule_version"],
            premise_fact_ids=tuple(
                p["premise_fact_id"]
                for p in sorted(premises, key=lambda p: p["position"])
                if p["derivation_id"] == row["derivation_id"]
            ),
        )
        for row in inventory_items(session, fact_id, "derivations")
    )
