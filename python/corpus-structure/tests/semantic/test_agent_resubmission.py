"""Historical durable held reports retain exact first-result custody and source uncertainty."""

import pytest
from sqlalchemy import select

from corpus_structure.intervene.semantic import ProposalProtocolRefused
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict, hold_agent_result, release_claim
from semantic.historical_agent_support import HistoricalAgentPublication


@pytest.mark.parametrize("refused", (False, True))
def test_uncertain_first_hold_survives_session_restart_and_terminal_second_report(
    resubmission_case, tmp_path, refused
):
    engine = resubmission_case.writer
    prepared, run, task, locator = resubmission_case.stage.result
    first = HistoricalAgentPublication(engine, run, task, prepared)
    unit = first.unit()
    fabricated = "Zyxwvu qrst nop invented quotation."
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
    with pytest.raises(ProposalProtocolRefused):
        first.session.check(raw, packet_hash=first.packet.hash, schema_hash="wrong")
    with engine.connect() as conn:
        assert (
            conn.scalar(select(table("ops.task").c.error).where(table("ops.task").c.id == task))
            is None
        )
    assert first.publish(raw).disposition == "held"
    with engine.connect() as conn:
        row = (
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
            .mappings()
            .one()
        )
        assert row["error"]["semantic_proposal_first_result"]["result"]["issues"]
        assert not conn.execute(
            select(table("kb.observation").c.id).where(table("kb.observation").c.task_id == task)
        ).first()
    with engine.begin() as conn:
        release_claim(
            conn,
            task_id=task,
            attempt=first.session.attempt,
            holder=first.session.holder,
            reason="historical owner restart",
        )
    second = HistoricalAgentPublication(engine, run, task, prepared)
    assert second.session.attempt == first.session.attempt + 1
    with pytest.raises(OperationConflict), engine.begin() as conn:
        hold_agent_result(
            conn,
            task_id=task,
            attempt=first.session.attempt,
            holder=first.session.holder,
            packet_hash=first.packet.hash,
            clean=False,
            result={},
        )
    assert second.publish(raw).disposition == (
        "completed_refused" if refused else "completed_accepted"
    )
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
