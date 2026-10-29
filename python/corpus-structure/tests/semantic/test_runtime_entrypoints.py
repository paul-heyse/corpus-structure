"""Current default MCP follows new runs without losing immutable task bindings."""

from contextlib import contextmanager

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import select, text
from typer.testing import CliRunner

from corpus_structure.intervene.semantic_server import SemanticProjectSession
from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.metadata import table
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
            released = (
                await client.call_tool("release", {"task_id": task, "reason": "retry"})
            ).structured_content
            assert released is not None and released["released"]
            assert task not in session.sessions

    anyio.run(journey)


def test_db_migrate_uses_semantic_history_and_refuses_legacy(semantic_db_engine):
    from corpus_structure.cli.db import DbRefused, _migrate
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID
    from corpus_structure.semantic.migrations import head_revision

    report = _migrate(semantic_db_engine, "owned-test", False)
    assert report.revision == head_revision()
    assert report.model_revision == PHYSICAL_MODEL_ID
    assert report.applied == []
    with semantic_db_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA meta"))
        conn.execute(text("CREATE TABLE meta.project(id bigint)"))
    with pytest.raises(DbRefused, match="legacy database refused"):
        _migrate(semantic_db_engine, "owned-test", False)


def test_default_mcp_and_direct_share_protected_direction_log(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    import json

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.app import app

    _, run, _, _ = source_task(semantic_db_engine, semantic_writer_engine, tmp_path / "source.html")
    session = SemanticProjectSession(semantic_writer_engine, "resubmit")

    async def record():
        async with Client(build_server(session)) as client:
            result = (
                await client.call_tool("record_direction", {"text": "Preserve exact quotations."})
            ).structured_content
            assert result is not None and result["project"] == "resubmit"
            assert result["file"] == "ops.intervention"

    anyio.run(record)

    @contextmanager
    def engine(settings, **kwargs):
        yield semantic_writer_engine

    monkeypatch.setattr(orchestrate, "ENGINE", engine)
    result = CliRunner().invoke(
        app, ["direct", "Retain unresolved conflicts.", "--project", "resubmit", "--json"]
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert json.loads(result.stdout)["project"] == "resubmit"
    with semantic_writer_engine.connect() as conn:
        log = table("ops.intervention")
        rows = conn.execute(
            select(log.c.body, log.c.actor).where(log.c.run_id == run).order_by(log.c.id)
        ).all()
        assert [row.body["text"] for row in rows] == [
            "Preserve exact quotations.",
            "Retain unresolved conflicts.",
        ]
        assert [row.actor for row in rows] == ["agent:session", "human:operator"]
        assert all(row.body["scope"] == "all" for row in rows)


def test_default_cli_mcp_stdio_starts_with_protocol_response(semantic_db_engine):
    import json
    import os
    import select as readiness
    import subprocess
    import sys

    app_url = semantic_db_engine.url.set(
        drivername="postgresql", username="corpus_sem_writer"
    ).render_as_string(hide_password=False)
    env = {**os.environ, "CORPUS_DATABASE__URL": app_url}
    proc = subprocess.Popen(
        [sys.executable, "-c", "from corpus_structure.cli.app import main; main()", "mcp", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    try:
        assert proc.stdin is not None and proc.stdout is not None
        hello = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "semantic-smoke", "version": "1"},
            },
        }
        proc.stdin.write(json.dumps(hello) + "\n")
        proc.stdin.flush()
        assert readiness.select([proc.stdout], [], [], 30)[0], "semantic stdio handshake timed out"
        reply = json.loads(proc.stdout.readline())
        assert reply["id"] == 1 and "result" in reply
    finally:
        proc.kill()
        proc.communicate(timeout=10)


def test_default_status_and_task_listing_do_not_select_another_project(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    import json

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState
    from corpus_structure.settings import Settings

    _, run, _, _ = source_task(semantic_db_engine, semantic_writer_engine, tmp_path / "source.html")

    @contextmanager
    def engine(settings, **kwargs):
        yield semantic_writer_engine

    monkeypatch.setattr(orchestrate, "ENGINE", engine)
    runner = CliRunner()
    for command in ("tasks", "status"):
        result = runner.invoke(app, [command, "--json"], obj=CliState(lambda: Settings()))
        assert result.exit_code == 0, (result.output, result.exception)
        body = json.loads(result.stdout)
        if command == "tasks":
            assert body["run_id"] is None and body["tasks"] == []
        else:
            assert body["progress"]["run"] is None
        selected = runner.invoke(app, [command, "--project", "resubmit", "--json"])
        assert selected.exit_code == 0, (selected.output, selected.exception)
        result = json.loads(selected.stdout)
        assert (
            result["run_id"] if command == "tasks" else result["progress"]["run"]["run_id"]
        ) == run
