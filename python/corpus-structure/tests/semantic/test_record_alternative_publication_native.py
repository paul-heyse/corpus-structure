"""Actual current record-field alternatives and scientific value alternatives stay distinct."""

from decimal import Decimal

from evaluate.declared_record_native_support import run_readings

from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAlternative, DdoRichFact
from corpus_structure.semantic.rich_queries import ClaimsQuery
from semantic.record_publication_native_support import (
    publish_authored, publish_readings, query_publication, rich_publication as rich_publication,
)


def test_unresolved_field_alternative_retains_separate_literal_evidence_in_native_product(rich_publication):
    journey = rich_publication
    source = journey.sources[0]
    readings = run_readings(journey, (source,), policy=None,
        variant="unresolved-value-alternative", inference="actual-field-alternative")
    ((raw_product, raw),) = readings.raw
    records = [member["body"] for member in raw["members"]
        if member["body"]["candidate_type"] == "record"]
    unresolved = [record for record in records
        if next(field for field in record["fields"] if field["role"] == "value")["state"] == "unresolved"]
    assert len(unresolved) == 2
    for record in unresolved:
        field = next(field for field in record["fields"] if field["role"] == "value")
        assert "value" not in field
        (alternative,) = field["alternatives"]
        assert alternative["value"]["lexical"] == "12"
        assert field["evidence_sets"] != alternative["evidence_sets"]
        evidence = {item["set_id"]: item for item in record["evidence_sets"]}
        assert {evidence[key]["usage"] for key in field["evidence_sets"]} == {"context"}
        assert {evidence[key]["usage"] for key in alternative["evidence_sets"]} == {"literal"}
        assert all(anchor["pin"] == raw["source_pin"] for anchor in record["anchors"])
    selected = publish_readings(journey, readings, source=source, inference="retained-field-alternative")
    assert selected.admission.selected_reading_ids == ()
    assert raw_product["id"] in {reference.product_id for reference in selected.consolidation.input_population}
    assert query_publication(selected, ClaimsQuery(name="claims"))["rows"] == []


def test_native_scientific_disagreement_retains_both_values_and_withholds_selection(rich_publication):
    selected = publish_authored(rich_publication, (
        {"kind": "number", "number": Decimal(1)}, {"kind": "number", "number": Decimal(2)},
    ), inference="actual-scientific-value-alternative")
    assert selected.admission.selected_fact_ids == selected.admission.selected_occurrence_ids == ()
    alternatives = [packet.body for packet in selected.admission.members if isinstance(packet.body, DdoRichAlternative)]
    facts = [packet.body for packet in selected.admission.members if isinstance(packet.body, DdoRichFact)]
    assert len(facts) == 2 and len(alternatives) == 1
    assert alternatives[0].completeness == "complete" and alternatives[0].faithful is True
    assert alternatives[0].origin == "value-disagreement"
    assert set(alternatives[0].fact_ids) == {fact.fact_id for fact in facts}
    assert alternatives[0].source_members
    assert all(reference.kind == "authored" for origin in alternatives[0].source_members
        for reference in origin.support_references)
    assert query_publication(selected, ClaimsQuery(name="claims"))["rows"] == []
    assert len(query_publication(selected, ClaimsQuery(name="claims", population="retained"))["rows"]) == 2
