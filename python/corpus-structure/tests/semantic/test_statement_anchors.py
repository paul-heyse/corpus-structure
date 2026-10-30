"""Packet-local statement handles resolve to immutable rendition coordinates."""

import pytest
from sqlalchemy import select

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import (
    ProposalFrame,
    ProposalRefused,
    ProposalSentence,
    locate_proposal,
    statement_anchor,
)
from corpus_structure.semantic.query import QuerySpec, read_session
from corpus_structure.semantic.source_projection import statement_identity

from .test_domain_operations import fixture
from .test_proposals import batch, prepared


def test_local_statement_anchor_is_normalized_without_rewriting_authored_report():
    release = prepared()
    raw = batch()
    raw["statements"][0]["anchor"] = "s1"
    frame = ProposalFrame(
        "page#one", "Alice is here.", (ProposalSentence("s1", "page#sentence", 0, 14),)
    )
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
    first = ProposalFrame(
        "page#one",
        "Alice is here.Alice is here.",
        (ProposalSentence("s1", "page#sentence", 0, 14),),
    )
    second = ProposalFrame("page#two", first.text, (ProposalSentence("s1", "page#two", 14, 28),))
    left = statement_identity("release", "output", "rendition", statement_anchor("s1", first))
    right = statement_identity("release", "output", "rendition", statement_anchor("s1", second))
    assert left != right
    assert left == statement_identity(
        "release", "output", "rendition", statement_anchor("page#sentence", first)
    )


@pytest.mark.parametrize("packets,expected", [("different", 2), ("same", 1)])
def test_recorded_local_handles_are_resolved_at_sealed_cut_without_mutation(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, packets, expected
):
    _prepared, run, cut = fixture(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        two_reports=True,
        statement_packets=packets,
    )
    observations = table("kb.observation")
    with semantic_reader_engine.connect() as conn:
        before = conn.execute(
            select(observations.c.observation_key, observations.c.payload)
            .where(
                observations.c.task_id.in_(
                    select(table("ops.task").c.id).where(table("ops.task").c.run_id == run)
                )
            )
            .order_by(observations.c.id)
        ).all()
    assert all(row.payload["statements"][0]["anchor"] == "s1" for row in before)
    result = consolidate_cut(semantic_writer_engine, cut, "statement-output")
    assert (
        consolidate_cut(semantic_writer_engine, cut, "statement-output").receipt == result.receipt
    )
    with read_session(semantic_reader_engine, "statement-output") as reader:
        cls = reader.class_handle("SourceStatement")
        locations = reader.query(QuerySpec(cls, reader.property_handle(cls, "locator"), "fact"))
        assert len({row.subject.entity_id for row in locations.rows}) == expected
        assert {row.object for row in locations.rows} == (
            {"page#sentence", "page#two"} if packets == "different" else {"page#sentence"}
        )
    with semantic_reader_engine.connect() as conn:
        after = conn.execute(
            select(observations.c.observation_key, observations.c.payload)
            .where(
                observations.c.task_id.in_(
                    select(table("ops.task").c.id).where(table("ops.task").c.run_id == run)
                )
            )
            .order_by(observations.c.id)
        ).all()
    assert after == before


def test_backfill_reconstructs_original_packet_hash_without_rewriting_source(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    import anyio
    from fastmcp import Client

    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        build_semantic_server,
    )
    from corpus_structure.semantic import source_frames
    from corpus_structure.semantic.operations import seal_cut

    from .test_agent_resubmission import lease_and_read, source_task

    # Model a task completed by the earlier server, before source-frame capture existed.
    # The real packet builder, native task/hash custody and submission transaction remain active.
    with monkeypatch.context() as earlier:
        earlier.setattr(source_frames, "capture_source_frame", lambda conn, task_id, packet: None)
        _, run, task, locator = source_task(
            semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
        )
        session = SemanticAgentSession(semantic_writer_engine, run)

        async def complete():
            async with Client(build_semantic_server(session)) as client:
                unit = await lease_and_read(client, run, task)
                result = (
                    await client.call_tool(
                        "propose_claims",
                        {
                            "task_id": task,
                            "batch": {
                                "unit_ref": locator,
                                "entities": [
                                    {"id": "person", "class_iri": "https://example.org/Person"}
                                ],
                                "claims": [
                                    {
                                        "id": "name",
                                        "subject": "person",
                                        "predicate": "https://example.org/name",
                                        "object": {"kind": "text", "text": "Alice"},
                                        "qualification": {"modality": "asserted", "polarity": True},
                                        "establishment": "stated",
                                        "evidence": [
                                            {
                                                "sentence": unit["sentences"][0]["id"],
                                                "quote": "Alice is here.",
                                                "role": "primary",
                                            }
                                        ],
                                    }
                                ],
                            },
                        },
                    )
                ).structured_content
                assert result is not None and result["status"] == "done"

        anyio.run(complete)
    with semantic_writer_engine.begin() as conn:
        seal_cut(conn, run, "evaluation", final=True)
        before = conn.execute(
            select(
                table("kb.observation").c.observation_key, table("kb.observation").c.payload
            ).where(table("kb.observation").c.task_id == task)
        ).one()
        packet_hash = conn.execute(
            select(table("ops.task").c.packet_hash).where(table("ops.task").c.id == task)
        ).scalar_one()
    assert source_frames.backfill_source_frames(semantic_writer_engine, run) == 1
    assert source_frames.backfill_source_frames(semantic_writer_engine, run) == 0
    with semantic_writer_engine.connect() as conn:
        captured = (
            conn.execute(
                select(table("ops.source_frame")).where(table("ops.source_frame").c.task_id == task)
            )
            .mappings()
            .one()
        )
        assert captured["packet_hash"] == packet_hash and captured["unit_ref"] == locator
        after = conn.execute(
            select(
                table("kb.observation").c.observation_key, table("kb.observation").c.payload
            ).where(table("kb.observation").c.task_id == task)
        ).one()
        assert after == before


def test_bulk_frames_deduplicate_origins_and_preserve_exact_coordinates(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from sqlalchemy import event
    from .test_agent_resubmission import source_task
    from corpus_structure.semantic.source_frames import load_source_frames

    prepared, run, task, _ = source_task(semantic_db_engine, semantic_writer_engine, tmp_path / "frame.html")
    from corpus_structure.orchestrate.semantic import agent_packet
    with semantic_writer_engine.begin() as conn:
        packet = agent_packet(conn, run, task, prepared)
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(conn, "before_cursor_execute", record)
        try:
            frames = load_source_frames(conn, [task] * 1025)
        finally:
            event.remove(conn, "before_cursor_execute", record)
    assert list(frames) == [task]
    assert frames[task] == packet.frame
    assert len(statements) == 3
