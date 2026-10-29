"""Packet-local statement handles resolve to immutable rendition coordinates."""

import pytest
from sqlalchemy import select

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalFrame, ProposalRefused, ProposalSentence, locate_proposal, statement_anchor
from corpus_structure.semantic.query import QuerySpec, read_session
from corpus_structure.semantic.source_projection import statement_identity

from .test_domain_operations import fixture
from .test_proposals import batch, prepared


def test_local_statement_anchor_is_normalized_without_rewriting_authored_report():
    release = prepared()
    raw = batch()
    raw["statements"][0]["anchor"] = "s1"
    frame = ProposalFrame("page#one", "Alice is here.", (ProposalSentence("s1", "page#sentence", 0, 14),))
    result = locate_proposal(release, raw, frame)
    assert result.authored.model_dump()["statements"][0]["anchor"] == "s1"
    assert result.stored.model_dump()["statements"][0]["anchor"] == "page#sentence"
    with pytest.raises(ProposalRefused, match="not declared"):
        statement_anchor("s99", frame)
    with pytest.raises(ProposalRefused, match="not declared"):
        statement_anchor("invented location", frame)
    assert statement_anchor(frame.unit_ref, frame) == "page#one"
    assert statement_anchor("page#sentence", frame) == "page#sentence"


def test_same_local_handle_has_distinct_source_identity_across_frames():
    first = ProposalFrame("page#one", "Alice is here.Alice is here.",
                          (ProposalSentence("s1", "page#sentence", 0, 14),))
    second = ProposalFrame("page#two", first.text, (ProposalSentence("s1", "page#two", 14, 28),))
    left = statement_identity("release", "output", "rendition", statement_anchor("s1", first))
    right = statement_identity("release", "output", "rendition", statement_anchor("s1", second))
    assert left != right
    assert left == statement_identity("release", "output", "rendition", statement_anchor("page#sentence", first))


@pytest.mark.parametrize("packets,expected", [("different", 2), ("same", 1)])
def test_recorded_local_handles_are_resolved_at_sealed_cut_without_mutation(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, packets, expected
):
    _prepared, run, cut = fixture(semantic_db_engine, semantic_writer_engine, tmp_path / "source.html",
                                 two_reports=True, statement_packets=packets)
    observations = table("kb.observation")
    with semantic_reader_engine.connect() as conn:
        before = conn.execute(select(observations.c.observation_key, observations.c.payload)
                              .where(observations.c.task_id.in_(select(table("ops.task").c.id).where(table("ops.task").c.run_id == run)))
                              .order_by(observations.c.id)).all()
    assert all(row.payload["statements"][0]["anchor"] == "s1" for row in before)
    result = consolidate_cut(semantic_writer_engine, cut, "statement-output")
    assert consolidate_cut(semantic_writer_engine, cut, "statement-output").receipt == result.receipt
    with read_session(semantic_reader_engine, "statement-output") as reader:
        cls = reader.class_handle("SourceStatement")
        locations = reader.query(QuerySpec(cls, reader.property_handle(cls, "locator"), "fact"))
        assert len({row.subject.entity_id for row in locations.rows}) == expected
        assert {row.object for row in locations.rows} == ({"page#sentence", "page#two"} if packets == "different" else {"page#sentence"})
    with semantic_reader_engine.connect() as conn:
        after = conn.execute(select(observations.c.observation_key, observations.c.payload)
                             .where(observations.c.task_id.in_(select(table("ops.task").c.id).where(table("ops.task").c.run_id == run)))
                             .order_by(observations.c.id)).all()
    assert after == before
