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
from semantic.domain_scenarios import build_domain_case
from semantic.proposals_support import batch, prepared


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
    commit_db_engine, commit_writer_engine, commit_reader_engine, tmp_path, packets, expected
):
    # This consumer authors its own report_count, global_person_identity, statement_packets variant beyond the shared default/prefix.
    _prepared, run, cut = build_domain_case(
        commit_db_engine,
        commit_writer_engine,
        tmp_path / "source.html",
        report_count=2,
        global_person_identity=True,
        statement_packets=packets,
    )
    from pdf_acceptance_support import independent_pdf_address

    from corpus_structure.semantic.source_views import selected_source_views

    with commit_reader_engine.connect() as conn:
        views = selected_source_views(conn, run)
        assert len(views) == expected
        expected_locations = {
            independent_pdf_address(conn, run, view.key, start=0, end=14) for view in views
        }
    observations = table("kb.observation")
    with commit_reader_engine.connect() as conn:
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
    result = consolidate_cut(commit_writer_engine, cut, "statement-output")
    assert consolidate_cut(commit_writer_engine, cut, "statement-output").receipt == result.receipt
    with read_session(commit_reader_engine, "statement-output") as reader:
        cls = reader.class_handle("SourceStatement")
        locations = reader.query(QuerySpec(cls, reader.property_handle(cls, "locator"), "fact"))
        assert len({row.subject.entity_id for row in locations.rows}) == expected
        assert {row.object for row in locations.rows} == expected_locations
    with commit_reader_engine.connect() as conn:
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
    resubmission_historical_source, tmp_path, monkeypatch
):
    commit_writer_engine = resubmission_historical_source.writer
    import anyio
    from fastmcp import Client

    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        build_semantic_server,
    )
    from corpus_structure.semantic import source_frames
    from corpus_structure.semantic.operations import seal_cut
    from semantic.agent_scenarios import lease_and_read, queue_resubmission_agent

    # Model a task completed by the earlier server, before source-frame capture existed.
    # The real packet builder, native task/hash custody and submission transaction remain active.
    with monkeypatch.context() as earlier:
        earlier.setattr(source_frames, "capture_source_frame", lambda conn, task_id, packet: None)
        _, run, task, locator = queue_resubmission_agent(
            resubmission_historical_source.stage, commit_writer_engine
        ).result
        session = SemanticAgentSession(commit_writer_engine, run)

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
    with commit_writer_engine.begin() as conn:
        seal_cut(conn, run, "evaluation", final=True)
        before = conn.execute(
            select(
                table("kb.observation").c.observation_key, table("kb.observation").c.payload
            ).where(table("kb.observation").c.task_id == task)
        ).one()
        packet_hash = conn.execute(
            select(table("ops.task").c.packet_hash).where(table("ops.task").c.id == task)
        ).scalar_one()
    assert source_frames.backfill_source_frames(commit_writer_engine, run) == 1
    assert source_frames.backfill_source_frames(commit_writer_engine, run) == 0
    with commit_writer_engine.connect() as conn:
        captured = (
            conn.execute(
                select(table("ops.native_source_frame")).where(
                    table("ops.native_source_frame").c.task_id == task
                )
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
    resubmission_case, tmp_path
):
    commit_writer_engine = resubmission_case.writer
    from sqlalchemy import event

    from corpus_structure.semantic.source_frames import load_source_frames

    prepared, run, task, _ = resubmission_case.stage.result
    from corpus_structure.orchestrate.semantic import agent_packet

    with commit_writer_engine.begin() as conn:
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
    assert len(statements) == 1
