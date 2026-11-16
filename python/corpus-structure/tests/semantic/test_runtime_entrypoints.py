"""Current default MCP follows new runs without losing immutable task bindings."""

from contextlib import contextmanager

import pytest
from sqlalchemy import select, text
from typer.testing import CliRunner

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine


def test_application_settings_resolve_original_credentials_before_clone_substitution(
    native_settings, commit_db_engine, commit_application_settings
):
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.runtime import connection_settings

    clone = commit_db_engine.url.database
    assert clone is not None
    for purpose in ("write", "read", "evaluate", "admit", "maintenance"):
        expected = make_url(connection_settings(native_settings, purpose).database.url)
        actual = make_url(connection_settings(commit_application_settings, purpose).database.url)
        assert actual.database == clone
        assert (actual.username, actual.password) == (expected.username, expected.password)
        assert (actual.host, actual.port, actual.query) == (
            expected.host,
            expected.port,
            expected.query,
        )
    with (
        open_runtime_engine(
            commit_application_settings, "clone-settings-control", purpose="write", max_size=1
        ) as engine,
        engine.connect() as conn,
    ):
        assert conn.exec_driver_sql("SELECT current_database(), current_user").one() == (
            clone,
            "corpus_sem_writer",
        )


def test_db_migrate_uses_semantic_history_and_refuses_legacy(commit_db_engine):
    from corpus_structure.cli.db import DbRefused, _migrate
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID
    from corpus_structure.semantic.migrations import head_revision

    report = _migrate(commit_db_engine, "owned-test", False)
    assert report.revision == head_revision()
    assert report.model_revision == PHYSICAL_MODEL_ID
    assert report.applied == []
    with commit_db_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA meta"))
        conn.execute(text("CREATE TABLE meta.project(id bigint)"))
    with pytest.raises(DbRefused, match="legacy database refused"):
        _migrate(commit_db_engine, "owned-test", False)


def test_supervisor_handoff_distinguishes_waiting_from_lost_active_session(
    resubmission_case, tmp_path, resubmission_application_settings
):
    commit_reader_engine = resubmission_case.reader
    commit_application_settings = resubmission_application_settings
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.orchestrate.liveness import (
        observe_supervisor,
        record_supervisor,
        run_supervisor,
        supervisor_connection,
    )
    from corpus_structure.semantic.operations import seal_cut, start_run

    _, run, _, _ = resubmission_case.stage.result
    settings = commit_application_settings
    settings = settings.model_copy(
        update={"database": settings.database.model_copy(update={"pool_max_size": 1})}
    )

    def custody(expected):
        with commit_reader_engine.connect() as reader:
            assert observe_supervisor(reader, run) == expected

    custody((False, None))
    with open_runtime_engine(settings, purpose="write", timeout=3) as engine:
        with engine.begin() as writer:
            start_run(writer, run)
        with (
            engine.connect() as writer,
            pytest.raises(DBAPIError, match="requires the active session lease"),
        ):
            record_supervisor(writer, run, waiting=False)
        with (
            commit_reader_engine.connect() as reader,
            pytest.raises(DBAPIError, match="permission denied"),
        ):
            record_supervisor(reader, run, waiting=False)
        with supervisor_connection(engine) as supervisor, run_supervisor(supervisor, run):
            record_supervisor(supervisor, run, waiting=False)
            supervisor.commit()
            custody((True, False))
            with engine.begin() as writer:
                seal_cut(writer, run, "source-ready")
            record_supervisor(supervisor, run, waiting=True)
            supervisor.commit()
        custody((False, True))
        with supervisor_connection(engine) as supervisor, run_supervisor(supervisor, run):
            record_supervisor(supervisor, run, waiting=False)
            supervisor.commit()
            custody((True, False))
            supervisor.invalidate()
        custody((False, False))


def test_direct_retains_protected_direction_scope_guards(
    resubmission_case, tmp_path, monkeypatch, resubmission_application_settings
):
    commit_writer_engine = resubmission_case.writer
    commit_application_settings = resubmission_application_settings
    import json

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState

    _, run, _, _ = resubmission_case.stage.result

    @contextmanager
    def engine(settings, **kwargs):
        yield commit_writer_engine

    monkeypatch.setattr(orchestrate, "ENGINE", engine)
    result = CliRunner().invoke(
        app,
        ["direct", "Retain unresolved conflicts.", "--project", "resubmit", "--json"],
        obj=CliState(lambda: commit_application_settings),
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert json.loads(result.stdout)["project"] == "resubmit"
    with commit_writer_engine.connect() as conn:
        log = table("ops.intervention")
        rows = conn.execute(
            select(log.c.body, log.c.actor).where(log.c.run_id == run).order_by(log.c.id)
        ).all()
        assert [row.body["text"] for row in rows] == ["Retain unresolved conflicts."]
        assert [row.actor for row in rows] == ["human:operator"]
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
        with commit_writer_engine.begin() as conn:
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                conn.execute(statement, valid | changed)
            assert isinstance(refused.value.orig, CheckViolation)
            assert refused.value.orig.sqlstate == "23514"
            assert "direction run binding differs" in str(refused.value.orig)
            assert len(conn.execute(select(log.c.id).where(log.c.run_id == run)).all()) == 1

    with commit_writer_engine.begin() as conn:
        end_source_run(conn, run)
    with commit_writer_engine.begin() as conn:
        with pytest.raises(DBAPIError) as inactive, conn.begin_nested():
            conn.execute(statement, valid)
        assert isinstance(inactive.value.orig, CheckViolation)
        assert inactive.value.orig.sqlstate == "23514"
        assert "run no longer active" in str(inactive.value.orig)
        assert len(conn.execute(select(log.c.id).where(log.c.run_id == run)).all()) == 1


def test_execution_admission_refuses_genuine_unbound_semantic1_before_run(commit_db_engine):
    from psycopg.errors import CheckViolation
    from sqlalchemy import insert
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.releases import persist_release
    from semantic.releases_support import source_bundle

    bundle = source_bundle()
    dependencies = ResolvedDependencies()
    profile = PreparationProfile()
    prepared = prepare_release(bundle, dependencies, profile)
    assert profile.version == "semantic-1" and prepared.execution_model_id is None
    with commit_db_engine.begin() as conn:
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


def test_default_status_and_task_listing_do_not_select_another_project(
    resubmission_case, tmp_path, monkeypatch, resubmission_application_settings
):
    commit_writer_engine = resubmission_case.writer
    commit_application_settings = resubmission_application_settings
    import json

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState

    _, run, _, _ = resubmission_case.stage.result

    @contextmanager
    def engine(settings, **kwargs):
        yield commit_writer_engine

    monkeypatch.setattr(orchestrate, "ENGINE", engine)
    runner = CliRunner()
    for command in ("tasks", "status"):
        result = runner.invoke(
            app,
            [command, "--json"],
            obj=CliState(lambda: commit_application_settings),
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
            obj=CliState(lambda: commit_application_settings),
        )
        assert selected.exit_code == 0, (selected.output, selected.exception)
        result = json.loads(selected.stdout)
        assert (
            result["run_id"] if command == "tasks" else result["progress"]["run"]["run_id"]
        ) == run
