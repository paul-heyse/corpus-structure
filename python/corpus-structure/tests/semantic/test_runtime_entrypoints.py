"""Current default MCP follows new runs without losing immutable task bindings."""

from contextlib import contextmanager

import anyio
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from sqlalchemy import select, text
from typer.testing import CliRunner

from corpus_structure.intervene.semantic_server import SemanticProjectSession, build_semantic_server
from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalRefused
from corpus_structure.semantic.runtime import open_runtime_engine, resolve_source_binding

from .agent_scenarios import build_resubmission_case, lease_and_read


def test_application_settings_resolve_original_credentials_before_clone_substitution(
    native_settings, semantic_db_engine, semantic_application_settings
):
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.runtime import connection_settings

    clone = semantic_db_engine.url.database
    assert clone is not None
    for purpose in ("write", "read", "evaluate", "admit", "maintenance"):
        expected = make_url(connection_settings(native_settings, purpose).database.url)
        actual = make_url(connection_settings(semantic_application_settings, purpose).database.url)
        assert actual.database == clone
        assert (actual.username, actual.password) == (expected.username, expected.password)
        assert (actual.host, actual.port, actual.query) == (
            expected.host,
            expected.port,
            expected.query,
        )
    with (
        open_runtime_engine(
            semantic_application_settings, "clone-settings-control", purpose="write", max_size=1
        ) as engine,
        engine.connect() as conn,
    ):
        assert conn.exec_driver_sql("SELECT current_database(), current_user").one() == (
            clone,
            "corpus_sem_writer",
        )


def test_environment_change_preserves_active_mcp_submission_binding(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_application_settings,
    tmp_path,
    monkeypatch,
):
    prepared, run, task, locator = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )
    database = semantic_application_settings.database
    monkeypatch.setenv("CORPUS_DATABASE__URL", database.url)
    monkeypatch.setenv("CORPUS_DATABASE__MAINTENANCE_URL", database.maintenance_url)
    monkeypatch.setenv("CORPUS_DATABASE__READER_URL", database.reader_url or "")
    monkeypatch.setenv("CORPUS_DATABASE__EVALUATOR_URL", database.evaluator_url or "")
    monkeypatch.setenv("CORPUS_DATABASE__ADMISSION_URL", database.admission_url or "")
    monkeypatch.setenv("CORPUS_RUNTIME__DEFAULT_PROJECT", "resubmit")

    async def journey():
        # Do not inject Settings/session/engine: environment acquisition belongs to the lifespan.
        async with Client(build_semantic_server()) as client:
            unit = await lease_and_read(client, run, task)
            monkeypatch.setenv("CORPUS_RUNTIME__DEFAULT_PROJECT", "changed-project")
            batch = {
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
                                "quote": "Alice is here.",
                                "role": "primary",
                            }
                        ],
                    }
                ],
            }
            result = (
                await client.call_tool("propose_claims", {"task_id": task, "batch": batch})
            ).structured_content
            assert result is not None
            assert result["status"] == "done" and not result["task_open"]
            assert result["submission_disposition"] == "completed_accepted"
            assert (await client.call_tool("queue_status", {"run": run})).structured_content
        async with Client(build_semantic_server()) as client:
            with pytest.raises(ToolError, match="does not belong to this semantic project"):
                await client.call_tool("queue_status", {"run": run})

    anyio.run(journey)
    with semantic_db_engine.connect() as conn:
        observation = table("kb.observation")
        tasks = table("ops.task")
        assert conn.execute(
            select(observation.c.task_id, tasks.c.run_id, observation.c.release_id)
            .join(tasks, tasks.c.id == observation.c.task_id)
            .where(observation.c.task_id == task)
        ).all() == [(task, run, prepared.release_id)]
        row = conn.execute(select(tasks.c.run_id, tasks.c.status).where(tasks.c.id == task)).one()
        assert row == (run, "done")


def test_default_project_mcp_observes_run_created_after_startup(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    session = SemanticProjectSession(semantic_writer_engine, "resubmit")
    server = build_server(session)

    async def journey():
        async with Client(server) as client:
            first = (await client.call_tool("queue_status", {})).structured_content
            assert first is not None and first["queues"] == []
            prepared, run, task, locator = build_resubmission_case(
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


def test_supervisor_handoff_distinguishes_waiting_from_lost_active_session(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    semantic_application_settings,
    tmp_path,
):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.orchestrate.commands import bound_status, cancel_bound_run
    from corpus_structure.orchestrate.liveness import (
        record_supervisor,
        run_supervisor,
        supervisor_connection,
    )
    from corpus_structure.semantic.operations import seal_cut, start_run

    _, run, _, _ = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "liveness.pdf"
    )
    settings = semantic_application_settings
    settings = settings.model_copy(
        update={"database": settings.database.model_copy(update={"pool_max_size": 1})}
    )

    def status(expected):
        with semantic_reader_engine.connect() as reader:
            progress = bound_status(reader, run, project_id="resubmit")
        assert progress.run is not None
        assert progress.run.supervisor == expected
        assert progress.orphaned == (
            [run] if expected == "orphaned" else None if expected == "unassessed" else []
        )

    status("unassessed")
    with open_runtime_engine(settings, purpose="write", timeout=3) as engine:
        with engine.begin() as writer:
            start_run(writer, run)
        with (
            engine.connect() as writer,
            pytest.raises(DBAPIError, match="requires the active session lease"),
        ):
            record_supervisor(writer, run, waiting=False)
        with (
            semantic_reader_engine.connect() as reader,
            pytest.raises(DBAPIError, match="permission denied"),
        ):
            record_supervisor(reader, run, waiting=False)
        with supervisor_connection(engine) as supervisor, run_supervisor(supervisor, run):
            record_supervisor(supervisor, run, waiting=False)
            supervisor.commit()
            status("active")
            with engine.begin() as writer:
                seal_cut(writer, run, "source-ready")
            record_supervisor(supervisor, run, waiting=True)
            supervisor.commit()
        status("waiting")
        with supervisor_connection(engine) as supervisor, run_supervisor(supervisor, run):
            record_supervisor(supervisor, run, waiting=False)
            supervisor.commit()
            status("active")
            supervisor.invalidate()
        status("orphaned")
        assert cancel_bound_run(engine, run).run_id == run
        status("terminal")


def test_default_mcp_and_direct_share_protected_direction_log(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_application_settings,
    tmp_path,
    monkeypatch,
):
    import json

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState

    _, run, _, _ = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )
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
        app,
        ["direct", "Retain unresolved conflicts.", "--project", "resubmit", "--json"],
        obj=CliState(lambda: semantic_application_settings),
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

    from psycopg.errors import CheckViolation
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.operations import end_source_run

    statement = text("SELECT ops.record_direction(:run,:actor,:session,CAST(:body AS jsonb))")
    valid = dict(
        run=run,
        actor="independent:writer",
        session="independent:session",
        body=json.dumps(dict(text="Keep uncertainty.", scope="all", project_id="resubmit")),
    )
    # Direct writers retain the same scope/input guards independently of the tool facade.
    for changed in (
        {"actor": ""},
        {"session": ""},
        {"body": json.dumps(dict(text="Keep uncertainty.", scope="all", project_id="other"))},
        {"body": json.dumps(dict(scope="all", project_id="resubmit"))},
    ):
        with semantic_writer_engine.begin() as conn:
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                conn.execute(statement, valid | changed)
            assert isinstance(refused.value.orig, CheckViolation)
            assert refused.value.orig.sqlstate == "23514"
            assert "direction run binding differs" in str(refused.value.orig)
            assert len(conn.execute(select(log.c.id).where(log.c.run_id == run)).all()) == 2

    with semantic_writer_engine.begin() as conn:
        end_source_run(conn, run)
    with semantic_writer_engine.begin() as conn:
        with pytest.raises(DBAPIError) as inactive, conn.begin_nested():
            conn.execute(statement, valid)
        assert isinstance(inactive.value.orig, CheckViolation)
        assert inactive.value.orig.sqlstate == "23514"
        assert "run no longer active" in str(inactive.value.orig)
        assert len(conn.execute(select(log.c.id).where(log.c.run_id == run)).all()) == 2


def test_execution_admission_refuses_genuine_unbound_semantic1_before_run(semantic_db_engine):
    from psycopg.errors import CheckViolation
    from sqlalchemy import insert
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.releases import persist_release

    from .test_releases import source_bundle

    bundle = source_bundle()
    dependencies = ResolvedDependencies()
    profile = PreparationProfile()
    prepared = prepare_release(bundle, dependencies, profile)
    assert profile.version == "semantic-1" and prepared.execution_model_id is None
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="unbound-direction"))
        # Schema artifacts remain archivable, but cannot acquire a realization or
        # run. The atomic native admission boundary now precedes direction writes.
        with pytest.raises(DBAPIError) as refused, conn.begin_nested():
            conn.execute(
                insert(table("data.realization")).values(
                    project_id="unbound-direction",
                    realization_id="unbound-direction-input",
                    release_id=prepared.release_id,
                )
            )
        assert isinstance(refused.value.orig, CheckViolation)
        assert refused.value.orig.sqlstate == "23514"
        assert "execution requires a current composed release" in str(refused.value.orig)
        releases, realizations, runs = (
            table("sem.release"),
            table("data.realization"),
            table("ops.run"),
        )
        assert (
            conn.scalar(
                select(releases.c.profile).where(releases.c.release_id == prepared.release_id)
            )
            == "semantic-1"
        )
        assert (
            conn.execute(
                select(realizations.c.realization_id).where(
                    realizations.c.project_id == "unbound-direction"
                )
            ).all()
            == []
        )
        assert (
            conn.execute(select(runs.c.id).where(runs.c.project_id == "unbound-direction")).all()
            == []
        )
        assert conn.execute(select(table("ops.intervention").c.id)).all() == []


@pytest.mark.parametrize("mode", ["complete", "early_exit", "tool_failure", "cancelled"])
def test_current_cli_stdio_journey_and_settlement(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_application_settings,
    tmp_path,
    monkeypatch,
    mode,
):
    import os
    import sys
    from pathlib import Path

    from fastmcp.client.transports import StdioTransport

    prepared, run, task, locator = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", composed=True
    )
    command = str(Path(sys.executable).with_name("ci"))
    processes = []
    original_open = anyio.open_process

    async def observed_open(argv, *args, **kwargs):
        process = await original_open(argv, *args, **kwargs)
        if argv[0] == command:
            processes.append(process)
        return process

    monkeypatch.setattr(anyio, "open_process", observed_open)
    database = semantic_application_settings.database
    env = {
        "CORPUS_DATABASE__URL": database.url,
        "CORPUS_DATABASE__MAINTENANCE_URL": database.maintenance_url,
        "CORPUS_DATABASE__READER_URL": database.reader_url or "",
        "CORPUS_DATABASE__EVALUATOR_URL": database.evaluator_url or "",
        "CORPUS_DATABASE__ADMISSION_URL": database.admission_url or "",
        "CORPUS_RUNTIME__DEFAULT_PROJECT": "resubmit",
    }
    transport = StdioTransport(
        command=command,
        args=["mcp", "serve", "--semantic-run", str(run)],
        env=env,
        cwd=str(Path(__file__).resolve().parents[4]),
        keep_alive=False,
        log_file=tmp_path / "stdio-stderr.log",
    )

    def writer_principals():
        with semantic_db_engine.connect() as conn:
            return (
                conn.exec_driver_sql(
                    "SELECT usename FROM pg_stat_activity WHERE datname=current_database() "
                    "AND application_name='ci-mcp-semantic'"
                )
                .scalars()
                .all()
            )

    async def journey():
        with anyio.CancelScope() as cancellation:
            async with Client(transport) as client:
                names = {tool.name for tool in await client.list_tools()}
                assert {"queue_next", "read_unit", "read_instructions", "propose_claims"} <= names
                assert writer_principals() == []
                if mode == "early_exit":
                    return
                assert (await client.call_tool("queue_status", {"run": run})).structured_content
                assert writer_principals() == []
                if mode == "cancelled":
                    cancellation.cancel()
                    await anyio.sleep(0)
                unit = await lease_and_read(client, run, task)
                assert set(writer_principals()) == {"corpus_sem_writer"}
                if mode == "tool_failure":
                    with pytest.raises(
                        ToolError,
                        match="task is not leased by this session or has already finished",
                    ):
                        await client.call_tool("read_unit", {"task_id": task + 1000000, "part": 1})
                    return
                batch = {
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
                                    "quote": "Alice is here.",
                                    "role": "primary",
                                }
                            ],
                        }
                    ],
                }
                result = (
                    await client.call_tool("propose_claims", {"task_id": task, "batch": batch})
                ).structured_content
                assert (
                    result is not None and result["submission_disposition"] == "completed_accepted"
                )
                assert result["rejected"] == []
                assert result["accepted"]["claims"] == 1
        assert processes and processes[0].pid != os.getpid()

    anyio.run(journey)
    assert len(processes) == 1 and processes[0].returncode is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(processes[0].pid, 0)
    with semantic_db_engine.connect() as conn:
        assert (
            conn.exec_driver_sql(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND application_name='ci-mcp-semantic'"
            ).scalar_one()
            == 0
        )
        task_row = conn.execute(
            select(table("ops.task").c.status).where(table("ops.task").c.id == task)
        ).scalar_one()
        if mode == "complete":
            assert task_row == "done"
            observations = (
                conn.execute(
                    select(table("kb.observation")).where(table("kb.observation").c.task_id == task)
                )
                .mappings()
                .all()
            )
            assert len(observations) == 1
            observation = observations[0]
            assert observation["release_id"] == prepared.release_id
            assert observation["payload_definition"] == "AgentStoredBatch"
            claims = observation["payload"]["claims"]
            assert len(claims) == 1
            assert claims[0]["predicate"] == "https://example.org/name"
            assert claims[0]["object"] == {"kind": "text", "text": "Alice"}
            assert claims[0]["qualification"] == {"modality": "asserted", "polarity": True}
        else:
            assert task_row != "done"


def test_default_status_and_task_listing_do_not_select_another_project(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_application_settings,
    tmp_path,
    monkeypatch,
):
    import json

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState

    _, run, _, _ = build_resubmission_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )

    @contextmanager
    def engine(settings, **kwargs):
        yield semantic_writer_engine

    monkeypatch.setattr(orchestrate, "ENGINE", engine)
    runner = CliRunner()
    for command in ("tasks", "status"):
        result = runner.invoke(
            app,
            [command, "--json"],
            obj=CliState(lambda: semantic_application_settings),
        )
        assert result.exit_code == 0, (result.output, result.exception)
        body = json.loads(result.stdout)
        if command == "tasks":
            assert body["run_id"] is None and body["tasks"] == []
        else:
            assert body["progress"]["run"] is None
        selected = runner.invoke(
            app,
            [command, "--project", "resubmit", "--json"],
            obj=CliState(lambda: semantic_application_settings),
        )
        assert selected.exit_code == 0, (selected.output, selected.exception)
        result = json.loads(selected.stdout)
        assert (
            result["run_id"] if command == "tasks" else result["progress"]["run"]["run_id"]
        ) == run
