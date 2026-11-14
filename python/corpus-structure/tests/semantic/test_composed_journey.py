"""An admitted composed binding across the native source/MCP/cut/result/read boundaries."""

import json
from collections import Counter
from hashlib import sha256

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import QuerySpec, read_session
from semantic.agent_scenarios import ResubmissionRecipe, lease_and_read
from semantic.inventory_reading import inventory_evidence, inventory_reports, inventory_supports


@pytest.mark.parametrize("resubmission_case", [ResubmissionRecipe(composed=True)], indirect=True)
def test_composed_source_submission_final_cut_and_explanation(resubmission_case, tmp_path):
    commit_writer_engine = resubmission_case.writer
    commit_reader_engine = resubmission_case.reader
    prepared, run, task, locator = resubmission_case.stage.result
    session = SemanticAgentSession(commit_writer_engine, run)

    packet = {}

    async def submit():
        async with Client(build_semantic_server(session)) as client:
            unit = await lease_and_read(client, run, task)
            packet.update(unit)
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
    completed = finalize_bound_run(commit_writer_engine, run, "composed-result")
    assert completed.realization_id == "composed-result"
    with commit_reader_engine.connect() as conn:
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
    with read_session(commit_reader_engine, "composed-result") as reader:
        cls = reader.class_handle("Person")
        facts = reader.query(QuerySpec(cls, reader.property_handle(cls, "name"), "accepted"))
        assert len(facts.rows) == 1 and facts.rows[0].object == "Alice"
        explanation = reader.explain(facts.rows[0].fact_id)
        supports = inventory_supports(reader, explanation.fact_id)
        evidence = inventory_evidence(reader, explanation.fact_id)
        reports = inventory_reports(reader, explanation.fact_id)
        # Acquire only the immutable input report identity; the semantic answers below
        # come from this hand-authored paragraph/proposal, not the consolidator.
        with commit_reader_engine.connect() as conn:
            observation = (
                conn.execute(
                    select(table("kb.observation")).where(
                        table("kb.observation").c.task_id == task,
                        table("kb.observation").c.payload_definition == "AgentStoredBatch",
                    )
                )
                .mappings()
                .one()
            )
        source = observation["observation_key"]
        sentence = packet["sentences"][0]
        located = dict(
            sentence=sentence["id"],
            quote="Alice is here.",
            role="primary",
            placement="exact_cited",
            matches=1,
            picked=False,
            timeouts=[],
            outcome="located",
            locator=sentence["locator"],
            start=0,
            end=14,
        )

        def encoded(value):
            return json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()

        # This spells out the identity tuple independently of production key helpers.
        occurrence = (
            "occ:"
            + sha256(
                encoded([prepared.release_id, "composed-result", source, "claims/0"])
            ).hexdigest()
        )
        evidence_id = "evidence:" + sha256(encoded([source, "claims", 0, 0, located])).hexdigest()
        assert Counter(
            (
                row.occurrence_id,
                row.source,
                row.item,
                row.evidence_ids,
                row.context,
                tuple((c.evidence_id, c.role) for c in row.citation_roles),
            )
            for row in supports
        ) == Counter(
            {(occurrence, source, "claims/0", (evidence_id,), None, ((evidence_id, "primary"),)): 1}
        )
        assert Counter(
            (row.evidence_id, row.source_uri, row.locator, row.provider, row.operation_version)
            for row in evidence
        ) == Counter(
            {
                (
                    evidence_id,
                    "source.html",
                    encoded(
                        dict(locator=sentence["locator"], start=0, end=14, role="primary")
                    ).decode(),
                    "agent.opus",
                    "semantic-7",
                ): 1
            }
        )
        assert len(evidence) == 1 and evidence[0].source is not None
        custody = evidence[0].source
        assert (
            custody.observation_key,
            custody.task_id,
            custody.run_id,
            custody.payload_definition,
            custody.kind,
        ) == (source, task, run, "AgentStoredBatch", "claim_proposal")
        assert Counter(
            (row.observation_key, row.observation_id, row.root_fact_id) for row in reports
        ) == Counter({(source, observation["id"], explanation.fact_id): 1})
        assert reports[0].payload["unit_ref"] == locator
        assert reports[0].payload["entities"] == [
            dict(id="person", class_iri="https://example.org/Person")
        ]
        claims = reports[0].payload["claims"]
        assert len(claims) == 1
        assert {
            k: claims[0][k]
            for k in (
                "id",
                "subject",
                "predicate",
                "object",
                "qualification",
                "establishment",
                "evidence",
            )
        } == dict(
            id="name",
            subject="person",
            predicate="https://example.org/name",
            object=dict(kind="text", text="Alice"),
            qualification=dict(modality="asserted", polarity=True),
            establishment="stated",
            evidence=[located],
        )


@pytest.mark.parametrize("resubmission_case", [ResubmissionRecipe(composed=True)], indirect=True)
def test_composed_private_evaluation_cannot_commit_without_result(resubmission_case, tmp_path):
    commit_db_engine = resubmission_case.admin
    commit_writer_engine = resubmission_case.writer
    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.operations import seal_cut

    prepared, run, task, _ = resubmission_case.stage.result
    # Complete the otherwise idle agent task through its actual scoped claim/completion route.
    from corpus_structure.semantic.operations import claim_tasks, complete_task

    with commit_writer_engine.begin() as conn:
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
        commit_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:output)"),
            dict(cut=cut, output="unfinished"),
        )
    with commit_db_engine.connect() as conn:
        assert not conn.scalar(
            select(table("data.realization").c.realization_id).where(
                table("data.realization").c.realization_id == "unfinished"
            )
        )
        assert (
            conn.scalar(select(table("ops.run").c.status).where(table("ops.run").c.id == run))
            == "consolidating"
        )
