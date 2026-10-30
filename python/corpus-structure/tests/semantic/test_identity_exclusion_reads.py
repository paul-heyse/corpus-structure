"""Restricted snapshot -> complete exclusion closure -> qualified RDF and Arrow/DuckDB."""

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError
from rdflib import URIRef
from rdflib.namespace import OWL, RDF
from sqlalchemy import select

from corpus_structure.semantic.analytics import AnalysisScope, load_packet
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.ontology import CS, validate_projected_graph
from corpus_structure.semantic.query import read_session


def test_identity_exclusion_snapshot_reader_and_columnar_closure(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from .test_identity_exclusions import exclusion_result

    _prepared, _run, _cut, result = exclusion_result(
        semantic_db_engine, semantic_writer_engine, tmp_path
    )
    assert result is not None
    with read_session(semantic_reader_engine, result.realization_id) as session:
        rows = session.identity_exclusions()
        assert len(rows) == 1
        exclusion = rows[0]
        assert exclusion.binding == session.binding
        assert exclusion.left.entity.entity_id != exclusion.right.entity.entity_id
        assert {exclusion.left.target, exclusion.right.target} == {"p", "q"}
        assert exclusion.left.kind == exclusion.right.kind == "local"
        assert exclusion.observation_key
        assert exclusion.local_id
        assert exclusion.operation_id == "resolve_identity"
        assert exclusion.operation_version == "semantic-domain-3"
        assert exclusion.evidence
        for evidence in exclusion.evidence:
            assert evidence.source is not None
            assert evidence.source.observation_id == exclusion.observation_id
        assert session.identity_exclusions(exclusion.left.entity.entity_id) == rows
        assert session.identity_exclusions("not-in-this-snapshot") == ()
        with pytest.raises(ValidationError):
            exclusion.__setattr__("reason", "mutated")
        with pytest.raises(FrozenInstanceError):
            exclusion.binding.__setattr__("data_revision", 999)
        projection = session.identity_exclusion_graph(exclusion.right.entity.entity_id)
        graph = projection.graph()
        assert set(graph.subjects(RDF.type, CS.IdentityExclusion)) == {
            URIRef(exclusion.exclusion_id)
        }
        assert not list(graph.triples((None, OWL.differentFrom, None)))
        assert validate_projected_graph(projection).conforms
        fact = table("data.fact")
        fact_id = session.connection.scalar(
            select(fact.c.fact_id)
            .where(
                fact.c.release_id == session.binding.release_id,
                fact.c.realization_id == session.binding.realization_id,
                fact.c.subject_id == exclusion.left.entity.entity_id,
            )
            .limit(1)
        )
        assert fact_id is not None
        explanation = session.explain(fact_id)
        assert explanation.identity_exclusions == rows

        uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
            hide_password=False
        )
        packet = load_packet(session, uri)
        assert {"identity_exclusion", "identity_exclusion_evidence"} <= packet.relations.keys()
        captured = packet.to_table("identity_exclusion")
        assert captured["exclusion_id"].to_pylist() == [exclusion.exclusion_id]
        assert packet.relations["identity_exclusion_evidence"].num_rows == len(exclusion.evidence)
    with AnalysisScope(packet) as scope:
        detached = scope.connection.sql(
            "SELECT x.exclusion_id,x.left_entity_id,x.right_entity_id,e.evidence_id "
            "FROM identity_exclusion x JOIN identity_exclusion_evidence e "
            "USING(release_id,realization_id,exclusion_id)"
        ).to_arrow_table()
        assert detached.num_rows == len(exclusion.evidence)
        assert detached["exclusion_id"].to_pylist() == [exclusion.exclusion_id] * detached.num_rows
    assert detached["left_entity_id"][0].as_py() == exclusion.left.entity.entity_id
