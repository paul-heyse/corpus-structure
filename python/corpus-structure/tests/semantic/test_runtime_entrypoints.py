"""Current default MCP follows new runs without losing immutable task bindings."""

import pytest
from sqlalchemy import select, text

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
        conn.execute(insert(table("data.project")).values(project_id="unbound-execution"))
        # Schema artifacts remain archivable, but cannot acquire a realization or
        # run. The atomic native admission boundary precedes execution.
        with pytest.raises(DBAPIError) as refused, conn.begin_nested():
            conn.execute(
                insert(table("data.realization")).values(
                    project_id="unbound-execution",
                    realization_id="unbound-execution-input",
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
                    realizations.c.project_id == "unbound-execution"
                )
            ).all()
            == []
        )
        assert (
            conn.execute(select(runs.c.id).where(runs.c.project_id == "unbound-execution")).all()
            == []
        )
