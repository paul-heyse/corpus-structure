"""Native durable automated resubmission; uncertain source reports never become located facts."""

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationConflict,
    hold_agent_result,
    release_claim,
)
from semantic.agent_scenarios import lease_and_read


@pytest.mark.parametrize("refused", (False, True))
def test_uncertain_first_hold_survives_session_restart_and_terminal_second_report(
    resubmission_case, tmp_path, refused
):
    commit_writer_engine = resubmission_case.writer
    _prepared, run, task, locator = resubmission_case.stage.result
    engine = commit_writer_engine
    first = SemanticAgentSession(engine, run)
    fabricated = "Zyxwvu qrst nop invented quotation."

    async def journey():
        async with Client(build_semantic_server(first)) as client:
            unit = await lease_and_read(client, run, task)
            raw = {
                "unit_ref": locator,
                "entities": [{"id": "person", "class_iri": "https://example.org/Person"}],
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
                                "quote": fabricated,
                                "role": "primary",
                            }
                        ],
                    }
                ],
            }
            if refused:
                raw["claims"][0]["predicate"] = "https://example.org/not-declared"
                raw["claims"][0]["evidence"][0]["quote"] = "Alice is here."
            protocol = (
                await client.call_tool(
                    "propose_claims", {"task_id": task, "batch": raw, "schema_hash": "wrong"}
                )
            ).structured_content
            assert protocol is not None
            assert protocol["status"] == "held"
            assert protocol["submission_disposition"] == "refused_context"
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        select(table("ops.task").c.error).where(table("ops.task").c.id == task)
                    ).scalar_one()
                    is None
                )
            held = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": raw})
            ).structured_content
            assert held is not None
            assert held["status"] == "held" and held["rejected"] and held["task_open"]
            assert held["submission_disposition"] == "held"
            with engine.connect() as conn:
                row = (
                    conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
                    .mappings()
                    .one()
                )
                first_attempt = row["attempt"]
                packet = row["packet_hash"]
                assert row["error"]["semantic_proposal_first_result"]["result"]["issues"]
                assert not conn.execute(
                    select(table("kb.observation").c.id).where(
                        table("kb.observation").c.task_id == task
                    )
                ).first()
        # Release the old host's ownership through the protected transition. A replacement
        # host reclaims a new attempt while the durable first submission stays available.
        with engine.begin() as conn:
            release_claim(
                conn,
                task_id=task,
                attempt=first_attempt,
                holder=first.holder,
                reason="session restart",
            )
        second = SemanticAgentSession(engine, run)
        async with Client(build_semantic_server(second)) as client:
            await lease_and_read(client, run, task, expect_previous=True)
            with pytest.raises(OperationConflict), engine.begin() as conn:
                hold_agent_result(
                    conn,
                    task_id=task,
                    attempt=first_attempt,
                    holder=first.holder,
                    packet_hash=packet,
                    clean=False,
                    result={},
                )
            terminal = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": raw})
            ).structured_content
            assert terminal is not None
            assert (
                terminal["status"] == "done" and not terminal["task_open"] and terminal["rejected"]
            )
            repeated = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": raw})
            ).structured_content
            assert repeated is not None
            assert repeated["status"] == "not_open"
            assert terminal["submission_disposition"] == (
                "completed_refused" if refused else "completed_accepted"
            )

    anyio.run(journey)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                select(table("kb.observation")).where(table("kb.observation").c.task_id == task)
            )
            .mappings()
            .all()
        )
        assert len(rows) == 1
        if refused:
            from corpus_structure.semantic.observations import source_python

            assert (
                rows[0]["payload_definition"] == "SourceObservation"
                and rows[0]["kind"] == "semantic_proposal_refused"
            )
            original = source_python(rows[0]["payload"]["payload"])
            assert (
                original["authored"]["claims"][0]["predicate"] == "https://example.org/not-declared"
            )
        else:
            assert rows[0]["payload_definition"] == "AgentStoredBatch"
            evidence = rows[0]["payload"]["claims"][0]["evidence"][0]
            assert evidence["quote"] == fabricated and evidence["outcome"] in (
                "unlocated",
                "coarse",
            )
        envelope = conn.execute(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == task
            )
        ).scalar_one()
        assert envelope["first_result"]["attempt"] == 1 and envelope["result"]["issues"]
    from corpus_structure.orchestrate.commands import finalize_bound_run

    result = finalize_bound_run(engine, run, "evaluated-uncertain")
    with engine.connect() as conn:
        assert not conn.execute(
            select(table("data.fact").c.fact_id).where(
                table("data.fact").c.realization_id == result.realization_id,
                table("data.fact").c.property_id == "https://example.org/name",
            )
        ).first()
        assert conn.execute(
            select(table("data.coverage").c.coverage_id).where(
                table("data.coverage").c.realization_id == result.realization_id,
                table("data.coverage").c.family == ("claim_proposal" if refused else "claim"),
                table("data.coverage").c.outcome == ("failed" if refused else "partial"),
            )
        ).first()
