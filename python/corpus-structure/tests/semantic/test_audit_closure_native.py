"""Native adversarial publication must preserve own support and component meaning."""
from dataclasses import replace
from hashlib import sha256

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.domain_operations import PolicyDecision, VERSION, _cut_input, consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.publication import OccurrenceEvidenceRow, ScientificRepresentativeRow, publish_on_connection

from .domain_scenarios import build_domain_case


def test_native_attribute_cannot_borrow_another_claims_evidence(semantic_db_engine, semantic_writer_engine, tmp_path):
    _, _, cut = build_domain_case(semantic_db_engine, semantic_writer_engine, tmp_path / "source.pdf", attribute_assertions=True)
    inputs = _cut_input(semantic_writer_engine, cut, "hostile")
    occurrence = next(row for row in inputs.batch.occurrence if row.item.startswith("entities/"))
    claim = next(row for row in inputs.batch.occurrence if row.item == "claims/0")
    borrowed = next(row.evidence_id for row in inputs.batch.occurrence_evidence if row.occurrence_id == claim.occurrence_id)
    batch = replace(inputs.batch, occurrence_evidence=(
        *(row for row in inputs.batch.occurrence_evidence if row.occurrence_id != occurrence.occurrence_id),
        OccurrenceEvidenceRow(occurrence.occurrence_id, borrowed),
    )).bind_preparation(inputs.prepared)
    with pytest.raises(DBAPIError, match="attribute support differs|outside bound source"):
        with semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn, conn.begin():
            conn.execute(text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": cut, "out": "hostile"})
            publish_on_connection(conn, batch)


def test_native_source_derived_assertion_is_refused_before_receipt_commit(semantic_db_engine, semantic_writer_engine, tmp_path):
    _, _, cut = build_domain_case(semantic_db_engine, semantic_writer_engine, tmp_path / "source.pdf")
    inputs = _cut_input(semantic_writer_engine, cut, "hostile")
    batch = replace(inputs.batch, occurrence_establishment=tuple(replace(row, establishment="derived") for row in inputs.batch.occurrence_establishment)).bind_preparation(inputs.prepared)
    with pytest.raises(DBAPIError, match="source-admissible"):
        with semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn, conn.begin():
            conn.execute(text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": cut, "out": "hostile"})
            publish_on_connection(conn, batch)


def test_native_representatives_cannot_invent_an_equivalence_component(semantic_db_engine, semantic_writer_engine, tmp_path):
    prepared, _, cut = build_domain_case(semantic_db_engine, semantic_writer_engine, tmp_path / "source.pdf")

    class FabricatedComponent:
        release_id = prepared.release_id
        version = VERSION

        def evaluate(self, inputs, scope, fused):
            facts = sorted(row.fact_id for row in inputs.batch.fact)
            assert len(facts) > 1
            component = "component:" + sha256(canonical_bytes(facts)).hexdigest()
            return PolicyDecision(frozenset(facts), (), scientific_representative=tuple(
                ScientificRepresentativeRow(fact, facts[0], "min-fact-id-1", component) for fact in facts
            ))

    with pytest.raises(DBAPIError, match="component differs from admitted equivalence"):
        consolidate_cut(semantic_writer_engine, cut, "hostile", policy=FabricatedComponent())
