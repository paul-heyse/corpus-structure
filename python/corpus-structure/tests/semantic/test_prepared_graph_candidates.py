"""Independent ownership and complete-universe expectations for local preparation."""

from dataclasses import replace

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic

from corpus_structure.semantic._operation_ids import CutId, RunId
from corpus_structure.semantic.analytics import CandidateInput
from corpus_structure.semantic.domain_operations import CutInput
from corpus_structure.semantic.ontology import (
    _add_isolated_triples,
    _qualified_shape_triples,
    qualified_projection_shapes,
)
from corpus_structure.semantic.publication import (
    EvidenceRow,
    FactRow,
    OccurrenceEvidenceRow,
    OccurrenceRow,
    PublicationBatch,
)
from corpus_structure.semantic.query import SnapshotBinding

from .test_analytics import prepared_inputs


def test_cached_shapes_produce_isolated_graphs_and_prepare_once():
    _qualified_shape_triples.cache_clear()
    first = qualified_projection_shapes()
    before = _qualified_shape_triples.cache_info()
    second = qualified_projection_shapes()
    assert _qualified_shape_triples.cache_info().hits == before.hits + 1
    assert isomorphic(first, second)
    assert {n for triple in first for n in triple if isinstance(n, BNode)}.isdisjoint(
        n for triple in second for n in triple if isinstance(n, BNode)
    )
    first.remove((None, None, None))
    assert len(second) > 0
    assert isomorphic(second, qualified_projection_shapes())


def test_independent_shape_blank_nodes_do_not_collide():
    shared = BNode("same-author-local-name")
    predicate = URIRef("urn:p")
    destination = Graph().add((shared, predicate, Literal("core")))
    source = Graph().add((shared, predicate, Literal("external")))
    _add_isolated_triples(destination, source)
    assert len(set(destination.subjects(predicate))) == 2
    assert list(source) == [(shared, predicate, Literal("external"))]


def cut_input():
    from corpus_structure.semantic import PreparationProfile, prepare_release
    from corpus_structure.semantic.composed import composed_dependencies

    bundle, dependencies, _ = prepared_inputs()
    prepared = prepare_release(
        bundle, composed_dependencies(dependencies), PreparationProfile(version="semantic-2")
    )
    batch = PublicationBatch(
        prepared.release_id,
        "output",
        "cut",
        fact=(FactRow("f", "entity", "property", "value"),),
        occurrence=(
            OccurrenceRow("o2", "f", "source", "item2", "value"),
            OccurrenceRow("o1", "f", "source", "item1", "value"),
        ),
        evidence=(
            EvidenceRow("e1", "page", "loc", "method", "1"),
            EvidenceRow("e2", "page", "loc", "method", "1"),
        ),
        occurrence_evidence=(OccurrenceEvidenceRow("o2", "e2"), OccurrenceEvidenceRow("o2", "e1")),
    )
    return prepared, CutInput(
        CutId(1),
        RunId(2),
        "p",
        prepared,
        "output",
        (),
        (),
        batch,
        {},
        {},
        SnapshotBinding(prepared.release_id, "source", 0, "cut:1"),
    )


def test_admitted_builder_preserves_complete_occurrences_and_ordered_evidence():
    prepared, cut = cut_input()
    packet = CandidateInput.from_admitted_cut(prepared, cut, decision_universe="policy")
    assert packet.relations["candidate_input"].to_pylist() == [
        {
            "fact_id": "f",
            "occurrence_id": "o2",
            "evidence": [{"evidence_id": "e2"}, {"evidence_id": "e1"}],
        },
        {"fact_id": "f", "occurrence_id": "o1", "evidence": []},
    ]
    external = packet.relations["candidate_input"]
    assert (
        CandidateInput.from_cut(prepared, cut, candidates=external, decision_universe="policy")
        .relations["candidate_input"]
        .equals(external)
    )
    with pytest.raises(ValueError, match="complete cut occurrence/evidence universe"):
        CandidateInput.from_cut(
            prepared, cut, candidates=external.slice(0, 1), decision_universe="policy"
        )


def test_admitted_builder_refuses_out_of_universe_links_and_duplicate_occurrences():
    prepared, cut = cut_input()
    for batch in (
        replace(cut.batch, occurrence=(*cut.batch.occurrence, cut.batch.occurrence[0])),
        replace(cut.batch, occurrence_evidence=(OccurrenceEvidenceRow("foreign", "e1"),)),
        replace(cut.batch, occurrence_evidence=(OccurrenceEvidenceRow("o1", "foreign"),)),
    ):
        with pytest.raises(ValueError, match=r"duplicate occurrences|outside cut source universe"):
            CandidateInput.from_admitted_cut(
                prepared, replace(cut, batch=batch), decision_universe="policy"
            )


def test_external_validation_shapes_do_not_leak_into_next_validation():
    from corpus_structure.semantic.ontology import validate_projected_graph

    from .test_ontology import _bound_projection

    projection = _bound_projection(
        "r",
        "z",
        0,
        "graph-validation",
        ({"id": "urn:occ", "subject": "urn:s", "predicate": "urn:p", "object": "v"},),
        {"urn:s": {"kind": "entity"}},
        {},
    )
    shapes = Graph().parse(
        data="""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
<urn:only-this-call> a sh:NodeShape; sh:targetClass rdf:Statement; sh:closed true .
""",
        format="turtle",
    )
    assert not validate_projected_graph(projection, shapes).conforms
    assert validate_projected_graph(projection).conforms
