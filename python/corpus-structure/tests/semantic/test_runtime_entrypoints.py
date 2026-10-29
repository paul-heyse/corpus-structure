"""Current default MCP follows new runs without losing immutable task bindings."""

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import text

from corpus_structure.intervene.semantic_server import SemanticProjectSession
from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.proposals import ProposalRefused
from corpus_structure.semantic.runtime import resolve_source_binding

from .test_agent_resubmission import source_task


def test_default_project_mcp_observes_run_created_after_startup(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    session = SemanticProjectSession(semantic_writer_engine, "resubmit")
    server = build_server(session)

    async def journey():
        async with Client(server) as client:
            first = (await client.call_tool("queue_status", {})).structured_content
            assert first is not None and first["queues"] == []
            prepared, run, task, locator = source_task(
                semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
            )
            with semantic_writer_engine.connect() as conn:
                assert resolve_source_binding(conn, "resubmit") == (prepared.release_id, "input")
            queued = (await client.call_tool("queue_next", {})).structured_content
            assert queued is not None
            assert [(row["run_id"], row["task_id"]) for row in queued["tasks"]] == [(run, task)]
            assert session.active(task).packet.frame.unit_ref == locator
            # Explicit selection cannot escape the process's configured project.
            with pytest.raises(ProposalRefused, match="does not belong"):
                session.for_run(run + 1000)
            released = (await client.call_tool("release", {"task_id": task, "reason": "retry"})).structured_content
            assert released is not None and released["released"]
            assert task not in session.sessions

    anyio.run(journey)


def test_db_migrate_uses_semantic_history_and_refuses_legacy(semantic_db_engine):
    from corpus_structure.cli.db import DbRefused, _migrate
    from corpus_structure.semantic.migrations import head_revision
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID

    report = _migrate(semantic_db_engine, "owned-test", False)
    assert report.revision == head_revision()
    assert report.model_revision == PHYSICAL_MODEL_ID
    assert report.applied == []
    with semantic_db_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA meta"))
        conn.execute(text("CREATE TABLE meta.project(id bigint)"))
    with pytest.raises(DbRefused, match="legacy database refused"):
        _migrate(semantic_db_engine, "owned-test", False)
