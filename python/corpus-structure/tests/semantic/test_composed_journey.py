"""An admitted composed binding across the native source/MCP/cut/result/read boundaries."""

import anyio
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import QuerySpec, read_session

from .agent_scenarios import build_resubmission_case, lease_and_read
from .inventory_reading import inventory_evidence, inventory_reports, inventory_supports


def test_composed_source_submission_final_cut_and_explanation(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    prepared, run, task, locator = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    session = SemanticAgentSession(semantic_writer_engine, run)

    async def submit():
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
            assert result is not None and result["submission_disposition"] == "completed_accepted"

    anyio.run(submit)
    completed = finalize_bound_run(semantic_writer_engine, run, "composed-result")
    assert completed.realization_id == "composed-result"
    with semantic_reader_engine.connect() as conn:
        result = (
            conn.execute(
                select(table("ops.completed_result")).where(
                    table("ops.completed_result").c.run_id == run
                )
            )
            .mappings()
            .one()
        )
        assert result["release_id"] == prepared.release_id and result["source_receipts"]
    with read_session(semantic_reader_engine, "composed-result") as reader:
        cls = reader.class_handle("Person")
        facts = reader.query(QuerySpec(cls, reader.property_handle(cls, "name"), "accepted"))
        assert len(facts.rows) == 1 and facts.rows[0].object == "Alice"
        explanation = reader.explain(facts.rows[0].fact_id)
        assert (
            inventory_supports(reader, explanation.fact_id)
            and inventory_evidence(reader, explanation.fact_id)
            and inventory_reports(reader, explanation.fact_id)
        )


def test_composed_private_evaluation_cannot_commit_without_result(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.operations import seal_cut

    prepared, run, task, _ = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    # Complete the otherwise idle agent task through its actual scoped claim/completion route.
    from corpus_structure.semantic.operations import claim_tasks, complete_task

    with semantic_writer_engine.begin() as conn:
        config = conn.scalar(
            select(table("ops.task").c.method_config_id).where(table("ops.task").c.id == task)
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="empty", agent=True)[0]
        completed = complete_task(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="empty",
            prepared=prepared,
            observations=(),
            outcome="empty",
        )
        assert completed.receipt.protocol == "empty"
        cut = seal_cut(conn, run, "final", final=True)
    with (
        pytest.raises(DBAPIError, match="completed EvaluationResult"),
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:output)"),
            dict(cut=cut, output="unfinished"),
        )
    with semantic_db_engine.connect() as conn:
        assert not conn.scalar(
            select(table("data.realization").c.realization_id).where(
                table("data.realization").c.realization_id == "unfinished"
            )
        )
        assert (
            conn.scalar(select(table("ops.run").c.status).where(table("ops.run").c.id == run))
            == "consolidating"
        )
