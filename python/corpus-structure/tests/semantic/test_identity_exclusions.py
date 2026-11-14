"""Actual source-task publication of grounded identity exclusions."""

import json

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from semantic.agent_scenarios import ExclusionRecipe

from .agent_scenarios import lease_and_read


def test_exclusion_only_entities_publish_grounded_memberships(exclusion_case, tmp_path):
    commit_writer_engine = exclusion_case.writer
    _prepared, _run, _cut, _result = exclusion_case.stage.result
    with commit_writer_engine.connect() as conn:
        exclusions = conn.execute(select(table("data.identity_exclusion"))).mappings().all()
        assert len(exclusions) == 1
        assert exclusions[0]["reason"] == "separate source identities"
        sources = conn.execute(select(table("data.entity_source"))).mappings().all()
        assert len(sources) == 2
        grounded = {row["local_id"]: row["entity_id"] for row in sources}
        assert set(grounded) == {"p", "q"} and grounded["p"] != grounded["q"]
        assert {exclusions[0]["left_entity_id"], exclusions[0]["right_entity_id"]} == {
            grounded["p"],
            grounded["q"],
        }
        memberships = conn.execute(select(table("data.membership"))).mappings().all()
        assert len(memberships) == 2
        # Source identity is checked by its own controls; this consumer must ground
        # each of the two authored entities in the stated class, exactly once.
        assert {
            (row["entity_id"], row["class_id"], row["establishment"]) for row in memberships
        } == {
            (grounded["p"], "https://example.org/Person", "agent_asserted"),
            (grounded["q"], "https://example.org/Person", "agent_asserted"),
        }
        assert not conn.execute(select(table("data.fact"))).all()
        assert not conn.execute(select(table("data.occurrence"))).all()
        assert not conn.execute(select(table("data.membership_support"))).all()
        assert len(conn.execute(select(table("data.identity_exclusion_evidence"))).all()) == 1


@pytest.mark.parametrize(
    "exclusion_case", [ExclusionRecipe(finalize=False, keyed=True)], indirect=True
)
def test_mandatory_identity_conflict_refuses_actual_cut_without_partial_output(
    exclusion_case, tmp_path
):
    commit_writer_engine = exclusion_case.writer
    import pytest

    from corpus_structure.semantic.domain_operations import (
        IdentityResolutionConflict,
        consolidate_cut,
    )

    _, run, cut, _ = exclusion_case.stage.result
    with pytest.raises(IdentityResolutionConflict) as conflict:
        consolidate_cut(commit_writer_engine, cut, "contradictory-result")
    assert conflict.value.code == "identity_conflict"
    assert conflict.value.exclusion_id == "different"
    with commit_writer_engine.connect() as conn:
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


@pytest.mark.parametrize(
    "exclusion_case",
    [ExclusionRecipe(finalize=True, global_names=True, attribute_assertions=True)],
    indirect=True,
)
def test_known_input_exclusions_follow_participating_endpoints(exclusion_case, tmp_path):
    commit_writer_engine = exclusion_case.writer
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.orchestrate.semantic import queue_agent
    from corpus_structure.semantic.operations import OperationBinding, create_run

    prepared, old_run, _, first = exclusion_case.stage.result
    assert first is not None
    with commit_writer_engine.begin() as conn:
        previous = (
            conn.execute(select(table("ops.run")).where(table("ops.run").c.id == old_run))
            .mappings()
            .one()
        )
        config = previous["options"]["agent_configs"]["agent.opus/extract"]
        run = create_run(
            conn,
            project_id="resubmit",
            binding=OperationBinding(
                prepared.release_id, first.realization_id, first.data_revision, b"{}"
            ),
            kind="full",
            options={"agent_configs": {"agent.opus/extract": config}},
            code_commit="test",
        )
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
        from corpus_structure.semantic._operation_ids import DocumentId
        from corpus_structure.semantic.operations import read_original

        original = read_original(conn, DocumentId(old_view["document_id"]), prepared=prepared)
    (view,) = publish_controlled_pdf_views(
        commit_writer_engine,
        prepared=prepared,
        run_id=run,
        document_id=old_view["document_id"],
        original=original,
        paragraphs=("Alice is here.",),
    )
    from .primary_native_support import bind_primary_agent_run

    with commit_writer_engine.begin() as conn:
        run, config = bind_primary_agent_run(conn, run, prepared, (view.ref.id,), config)
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
            build_semantic_server(SemanticAgentSession(commit_writer_engine, run))
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
    second = finalize_bound_run(commit_writer_engine, run, "inherited-result")
    with commit_writer_engine.connect() as conn:
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
