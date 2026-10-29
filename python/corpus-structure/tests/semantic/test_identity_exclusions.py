"""Actual source-task publication of grounded identity exclusions."""
import anyio
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from .test_agent_resubmission import lease_and_read, source_task


def exclusion_result(admin, writer, tmp_path, *, finalize=True, citations=1):
    prepared, run, task, locator = source_task(admin, writer, tmp_path / "exclusions.html", composed=True)
    session = SemanticAgentSession(writer, run)
    async def submit():
        async with Client(build_semantic_server(session)) as client:
            unit = await lease_and_read(client, run, task)
            response = await client.call_tool("propose_claims", {"task_id": task, "batch": {
                "unit_ref": locator,
                "entities": [{"id": ref, "class_iri": "https://example.org/Person", "label": "Alice"} for ref in ("p", "q")],
                "identity_exclusions": [{"id": "different", "left": {"kind": "local", "target": "p"},
                    "right": {"kind": "local", "target": "q"}, "reason": "separate source identities",
                    "evidence": [{"sentence": unit["sentences"][0]["id"], "quote": "Alice is here.", "role": "primary"}, *([{ "sentence": unit["sentences"][0]["id"], "quote": "Alice", "role": "supporting"}] if citations == 2 else [])]}]}})
            assert response.structured_content is not None
            assert response.structured_content["submission_disposition"] == "completed_accepted"
    anyio.run(submit)
    if not finalize:
        from corpus_structure.semantic.operations import seal_cut
        with writer.begin() as conn:
            cut = seal_cut(conn, run, "evaluation", final=True)
        return prepared, run, cut, None
    result = finalize_bound_run(writer, run, "excluded-result")
    with writer.connect() as conn:
        cut = conn.scalar(select(table("ops.input_cut").c.id).where(table("ops.input_cut").c.run_id == run).order_by(table("ops.input_cut").c.id.desc()).limit(1))
    return prepared, run, cut, result


def test_exclusion_only_entities_publish_grounded_memberships(semantic_db_engine, semantic_writer_engine, tmp_path):
    prepared, run, cut, result = exclusion_result(semantic_db_engine, semantic_writer_engine, tmp_path)
    with semantic_writer_engine.connect() as conn:
        exclusions = conn.execute(select(table("data.identity_exclusion"))).mappings().all()
        assert len(exclusions) == 1
        assert exclusions[0]["left_entity_id"] != exclusions[0]["right_entity_id"]
        assert exclusions[0]["reason"] == "separate source identities"
        assert len(conn.execute(select(table("data.entity_source"))).all()) == 2
        assert len(conn.execute(select(table("data.membership_support"))).all()) == 2
        assert len(conn.execute(select(table("data.identity_exclusion_evidence"))).all()) == 1
