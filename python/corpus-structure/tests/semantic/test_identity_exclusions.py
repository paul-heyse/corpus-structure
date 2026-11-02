"""Actual source-task publication of grounded identity exclusions."""

import json

import anyio
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table

from .test_agent_resubmission import lease_and_read, source_task


def exclusion_result(
    admin,
    writer,
    tmp_path,
    *,
    finalize=True,
    citations=1,
    keyed=False,
    global_names=False,
    local_ids=("p", "q"),
):
    prepared, run, task, locator = source_task(
        admin,
        writer,
        tmp_path / "exclusions.html",
        composed=True,
        identity_keyed=keyed,
        global_names=global_names,
    )
    session = SemanticAgentSession(writer, run)

    async def submit():
        async with Client(build_semantic_server(session)) as client:
            unit = await lease_and_read(client, run, task)
            response = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "entities": [
                            {
                                "id": ref,
                                "class_iri": "https://example.org/Person",
                                "label": "Alice",
                                "attributes": [
                                    {
                                        "predicate": "https://example.org/name",
                                        "value": {"kind": "text", "text": "Alice"},
                                    }
                                ]
                                if keyed
                                else [],
                            }
                            for ref in local_ids
                        ],
                        "identity_exclusions": [
                            {
                                "id": "different",
                                "left": {"kind": "local", "target": local_ids[0]},
                                "right": {"kind": "local", "target": local_ids[1]},
                                "reason": "separate source identities",
                                "evidence": [
                                    {
                                        "sentence": unit["sentences"][0]["id"],
                                        "quote": "Alice is here.",
                                        "role": "primary",
                                    },
                                    *(
                                        [
                                            {
                                                "sentence": unit["sentences"][0]["id"],
                                                "quote": "Alice",
                                                "role": "supporting",
                                            }
                                        ]
                                        if citations == 2
                                        else []
                                    ),
                                ],
                            }
                        ],
                    },
                },
            )
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted", (
                json.dumps(response.structured_content, indent=2)
            )

    anyio.run(submit)
    if not finalize:
        from corpus_structure.semantic.operations import seal_cut

        with writer.begin() as conn:
            cut = seal_cut(conn, run, "evaluation", final=True)
        return prepared, run, cut, None
    result = finalize_bound_run(writer, run, "excluded-result")
    with writer.connect() as conn:
        cut = conn.scalar(
            select(table("ops.input_cut").c.id)
            .where(table("ops.input_cut").c.run_id == run)
            .order_by(table("ops.input_cut").c.id.desc())
            .limit(1)
        )
    return prepared, run, cut, result


def test_exclusion_only_entities_publish_grounded_memberships(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, _cut, _result = exclusion_result(
        semantic_db_engine, semantic_writer_engine, tmp_path
    )
    with semantic_writer_engine.connect() as conn:
        exclusions = conn.execute(select(table("data.identity_exclusion"))).mappings().all()
        assert len(exclusions) == 1
        assert exclusions[0]["left_entity_id"] != exclusions[0]["right_entity_id"]
        assert exclusions[0]["reason"] == "separate source identities"
        assert len(conn.execute(select(table("data.entity_source"))).all()) == 2
        assert len(conn.execute(select(table("data.membership_support"))).all()) == 2
        assert len(conn.execute(select(table("data.identity_exclusion_evidence"))).all()) == 1


def test_mandatory_identity_conflict_refuses_actual_cut_without_partial_output(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    import pytest

    from corpus_structure.semantic.domain_operations import (
        IdentityResolutionConflict,
        consolidate_cut,
    )

    _, run, cut, _ = exclusion_result(
        semantic_db_engine, semantic_writer_engine, tmp_path, finalize=False, keyed=True
    )
    with pytest.raises(IdentityResolutionConflict) as conflict:
        consolidate_cut(semantic_writer_engine, cut, "contradictory-result")
    assert conflict.value.code == "identity_conflict"
    assert conflict.value.exclusion_id == "different"
    with semantic_writer_engine.connect() as conn:
        assert not conn.scalar(
            select(table("data.realization").c.realization_id).where(
                table("data.realization").c.realization_id == "contradictory-result"
            )
        )
        assert conn.scalar(select(table("kb.observation").c.id)) is not None
        assert (
            conn.scalar(
                select(table("ops.run").c.result_realization_id).where(table("ops.run").c.id == run)
            )
            is None
        )


def test_known_input_exclusions_follow_participating_endpoints(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    import json

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.orchestrate.semantic import queue_agent
    from corpus_structure.semantic.operations import OperationBinding, create_run

    prepared, old_run, _, first = exclusion_result(
        semantic_db_engine, semantic_writer_engine, tmp_path, global_names=True
    )
    assert first is not None
    with semantic_writer_engine.begin() as conn:
        previous = (
            conn.execute(select(table("ops.run")).where(table("ops.run").c.id == old_run))
            .mappings()
            .one()
        )
        config = previous["options"]["agent_configs"]["extract"]
        run = create_run(
            conn,
            project_id="resubmit",
            binding=OperationBinding(
                prepared.release_id, first.realization_id, first.data_revision, b"{}"
            ),
            kind="full",
            options={"agent_configs": {"extract": config}},
            code_commit="test",
        )
        from pathlib import Path

        from pdf_acceptance_support import publish_controlled_pdf_views

        views, selected = table("kb.source_view"), table("ops.run_source_view")
        old_view = (
            conn.execute(
                select(views)
                .join(selected, selected.c.source_view_id == views.c.id)
                .where(selected.c.run_id == old_run)
            )
            .mappings()
            .one()
        )
        document = (
            conn.execute(
                select(table("kb.document")).where(
                    table("kb.document").c.id == old_view["document_id"]
                )
            )
            .mappings()
            .one()
        )
    (view,) = publish_controlled_pdf_views(
        semantic_writer_engine,
        prepared=prepared,
        run_id=run,
        document_id=old_view["document_id"],
        original=Path(document["original_path"]).read_bytes(),
        paragraphs=("Alice is here.",),
        keys=("source.html#known-people",),
    )
    with semantic_writer_engine.begin() as conn:
        locator = view.ref.key
        (task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=config,
            units=(UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, locator),),
        )
        inherited = (
            conn.execute(
                select(table("data.identity_exclusion")).where(
                    table("data.identity_exclusion").c.realization_id == first.realization_id
                )
            )
            .mappings()
            .one()
        )
        endpoints = (inherited["left_entity_id"], inherited["right_entity_id"])

    async def submit_known():
        async with Client(
            build_semantic_server(SemanticAgentSession(semantic_writer_engine, run))
        ) as client:
            unit = await lease_and_read(client, run, task)
            response = await client.call_tool(
                "propose_claims",
                {
                    "task_id": task,
                    "batch": {
                        "unit_ref": locator,
                        "claims": [
                            {
                                "id": "c" + str(i),
                                "subject": entity,
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
                            for i, entity in enumerate(endpoints)
                        ],
                    },
                },
            )
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted", (
                json.dumps(response.structured_content, indent=2)
            )

    anyio.run(submit_known)
    second = finalize_bound_run(semantic_writer_engine, run, "inherited-result")
    with semantic_writer_engine.connect() as conn:
        row = (
            conn.execute(
                select(table("data.identity_exclusion")).where(
                    table("data.identity_exclusion").c.realization_id == second.realization_id
                )
            )
            .mappings()
            .one()
        )
        assert (row["left_entity_id"], row["right_entity_id"]) == endpoints
        assert row["observation_id"] == inherited["observation_id"]
        assert row["exclusion_id"] != inherited["exclusion_id"]
