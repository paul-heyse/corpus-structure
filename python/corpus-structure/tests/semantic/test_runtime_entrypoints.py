"""Current native target entrypoints retain credentials and refuse unadmitted execution."""

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
    for purpose in ("write", "read", "evaluate", "fit", "admit", "maintenance"):
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


def test_db_migrate_uses_current_target_root_and_refuses_legacy(commit_db_engine):
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


def test_current_archive_admission_refuses_schema_only_release_before_effects(commit_db_engine):
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.releases import ReleaseConflict, persist_release
    from semantic.releases_support import source_bundle

    bundle = source_bundle()
    dependencies = ResolvedDependencies()
    profile = PreparationProfile()
    prepared = prepare_release(bundle, dependencies, profile)
    assert profile.version == "semantic-1"
    assert not any(artifact.kind == "data_operations.json" for artifact in prepared.artifacts)
    with commit_db_engine.begin() as conn:
        # Pure schema preparation grants no executable operation model. Refusal
        # occurs at the actual current archive admission boundary, before effects.
        with pytest.raises(
            ReleaseConflict, match="execution projection requires current declared data operations"
        ), conn.begin_nested():
            persist_release(conn, bundle, dependencies, profile, prepared)
        releases = table("sem.release")
        assert conn.scalar(
            select(releases.c.release_id).where(releases.c.release_id == prepared.release_id)
        ) is None
        projects = table("data.project")
        assert conn.scalar(
            select(projects.c.project_id).where(projects.c.project_id == "unbound-execution")
        ) is None
        demands = table("ops.data_demand")
        assert conn.execute(
            select(demands.c.id).where(demands.c.project_id == "unbound-execution")
        ).all() == []
