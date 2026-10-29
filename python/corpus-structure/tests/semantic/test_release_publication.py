"""An actual ontology-bound prepared archive supplies the native publication registry."""

from __future__ import annotations

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    fact_key,
    occurrence_key,
    prepare_release,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceRow,
    PublicationBatch,
    SupportRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.releases import activate_release, load_release, persist_release


def test_compiled_pinned_ontology_membership_enforces_native_reports(
    semantic_db_engine, semantic_writer_engine
):
    bundle = SourceBundle(
        "native",
        (
            SourceArtifact(
                "native",
                b"""id: https://example.org/native
name: native
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'xsd:string'}}
enums:
  Terms:
    reachable_from: {source_ontology: terms, source_nodes: ['EX:1'], include_self: true}
classes:
  Thing:
    attributes:
      label: {range: Terms, required: true}
""",
            ),
        ),
    )
    dependencies = ResolvedDependencies(
        artifacts=(
            SourceArtifact("terms", b"format-version: 1.2\n\n[Term]\nid: EX:1\nname: root\n"),
        ),
        ontology_sources=("terms",),
    )
    prepared = prepare_release(bundle, dependencies)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, PreparationProfile(), prepared)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        activate_release(
            conn, "p", prepared.release_id, expected_parent=None, expected_generation=0
        )
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="native", project_id="p", release_id=prepared.release_id
            )
        )
        assert load_release(conn, prepared.release_id) == prepared
        assert conn.execute(select(table("sem.vocabulary_member").c.value)).scalars().all() == [
            "EX:1"
        ]
    cls = prepared.definitions[0]
    prop = cls.properties[0]

    def candidate(entity: str, label: str) -> PublicationBatch:
        rid = prepared.release_id
        fact = fact_key(rid, "native", entity, prop.iri, label, {})
        occurrence = occurrence_key(rid, "native", "source", entity)
        return PublicationBatch(
            rid,
            "native",
            entity,
            entity=(EntityRow(entity),),
            membership=(MembershipRow(entity, cls.iri, "authored type"),),
            typed_value=(ValueRow(entity, "string", text_value=label),),
            fact=(FactRow(fact, entity, prop.iri, entity),),
            occurrence=(OccurrenceRow(occurrence, fact, "source", entity, entity),),
            support=(SupportRow(fact, occurrence),),
            evidence=(EvidenceRow(entity, "urn:source", "line:1", "native-test", "1"),),
            membership_support=(MembershipSupportRow(entity, cls.iri, entity),),
        )

    assert publish_batch(semantic_writer_engine, candidate("known", "EX:1")).data_revision == 1
    with pytest.raises(DBAPIError, match="declared range"):
        publish_batch(semantic_writer_engine, candidate("unknown", "EX:2"))
    with semantic_db_engine.connect() as conn:
        assert conn.execute(select(table("data.entity").c.entity_id)).scalars().all() == ["known"]
        assert conn.execute(select(table("data.typed_value").c.text_value)).scalars().all() == [
            "EX:1"
        ]
