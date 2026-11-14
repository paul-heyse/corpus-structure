"""The database fixtures (foundations §3.1, §3.9; store note §1) on the test server."""

from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

import pytest
from native_refusals import native_refusal
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from corpus_structure.settings import DatabaseSettings
from native_test_support import database_name, rollback_case, rollback_connection
from test_prerequisites import PrerequisiteUnavailable

MARKER = "f1_isolation_probe"


def test_native_read_refuses_writes_with_read_only_sqlstate(native_read):
    with native_refusal("25006"):
        native_read.exec_driver_sql("CREATE TABLE public.read_class_forbidden(value int)")


@pytest.mark.parametrize("borrower", ["maintenance", "principal"])
def test_rollback_case_refuses_consumer_commit(
    native_rollback, native_server, native_settings, borrower
):
    database = native_rollback.connection.engine.url.database
    with (
        pytest.raises(RuntimeError, match="borrowed outer transaction"),
        rollback_case(native_server, native_settings, database) as case,
    ):
        if borrower == "maintenance":
            case.connection.commit()
        else:
            with case.principal("write") as connection:
                connection.commit()


def test_rollback_case_preserves_actual_login_and_read_only_reader(native_rollback):
    with native_rollback.principal("write", isolation_level="REPEATABLE READ") as writer:
        assert writer.exec_driver_sql("SELECT session_user").scalar_one() == "corpus_sem_writer"
        assert (
            writer.exec_driver_sql("SHOW transaction_isolation").scalar_one() == "repeatable read"
        )
    with native_rollback.reader.connect() as reader:
        assert reader.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "on"
        with native_refusal("25006"):
            reader.exec_driver_sql("INSERT INTO sem.release DEFAULT VALUES")


def test_rollback_reader_observes_only_committed_state(native_rollback):
    native_rollback.connection.exec_driver_sql(
        "CREATE TABLE public.uncommitted_case_probe(value int)"
    )
    native_rollback.connection.exec_driver_sql(
        "INSERT INTO public.uncommitted_case_probe VALUES(91)"
    )
    assert (
        native_rollback.connection.exec_driver_sql(
            "SELECT value FROM public.uncommitted_case_probe"
        ).scalar_one()
        == 91
    )
    with native_rollback.reader.connect() as reader:
        assert (
            reader.exec_driver_sql(
                "SELECT to_regclass('public.uncommitted_case_probe')"
            ).scalar_one()
            is None
        )


def test_commit_clone_factory_lends_fresh_isolated_databases(commit_clone):
    with commit_clone() as left, commit_clone() as right:
        with left.begin() as connection:
            left_oid = connection.exec_driver_sql(
                "SELECT oid FROM pg_database WHERE datname=current_database()"
            ).scalar_one()
            connection.exec_driver_sql("CREATE TABLE public.commit_isolation_probe(value int)")
            connection.exec_driver_sql("INSERT INTO public.commit_isolation_probe VALUES(7)")
        with right.connect() as connection:
            right_oid = connection.exec_driver_sql(
                "SELECT oid FROM pg_database WHERE datname=current_database()"
            ).scalar_one()
            assert right_oid != left_oid
            assert (
                connection.exec_driver_sql(
                    "SELECT to_regclass('public.commit_isolation_probe')"
                ).scalar_one()
                is None
            )


def test_isolated_infrastructure_writes_do_not_reach_shared_base(
    infrastructure_engine, infrastructure_commit_engine
):
    with infrastructure_commit_engine.begin() as connection:
        isolated = connection.exec_driver_sql(
            "SELECT oid FROM pg_database WHERE datname=current_database()"
        ).scalar_one()
        connection.exec_driver_sql("CREATE TABLE public.infrastructure_isolation_probe(value int)")
        connection.exec_driver_sql("INSERT INTO public.infrastructure_isolation_probe VALUES(3)")
    with infrastructure_engine.connect() as connection:
        shared = connection.exec_driver_sql(
            "SELECT oid FROM pg_database WHERE datname=current_database()"
        ).scalar_one()
        assert shared != isolated
        assert (
            connection.exec_driver_sql(
                "SELECT to_regclass('public.infrastructure_isolation_probe')"
            ).scalar_one()
            is None
        )


def test_infrastructure_acquisition_needs_no_semantic_head_or_roles(
    native_server, request, monkeypatch
):
    def forbidden(*args, **kwargs):
        pytest.fail("infrastructure acquisition requested semantic preparation")

    monkeypatch.setattr(native_server, "semantic_ready", forbidden)
    monkeypatch.setattr(native_server, "deployment_key", forbidden)
    heads = native_server.names("cs_sem_head_")
    sessions = native_server.names("ci_test_")
    engine = request.getfixturevalue("infrastructure_commit_engine")
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 17").scalar_one() == 17
    assert native_server.names("cs_sem_head_") == heads
    assert native_server.names("ci_test_") == sessions
    assert "semantic_head_template" not in request.fixturenames


def test_explicit_semantic_acquisition_keeps_role_prerequisite(db_support, monkeypatch):
    server = db_support.PgAdmin("postgresql:///unacquired", "unacquired", expected={})

    def missing(_roles):
        raise PrerequisiteUnavailable("postgres-roles", "injected missing semantic role")

    monkeypatch.setattr(server, "check_roles", missing)
    with (
        pytest.raises(PrerequisiteUnavailable, match="missing semantic role"),
        server.deployment(key=uuid4().hex),
    ):
        pytest.fail("missing semantic roles must refuse before acquisition")


def test_session_database_is_cloned_from_the_migrated_template(
    native_read: Connection, db_server, semantic_head_template
) -> None:
    assert (
        native_read.execute(text("SELECT current_database()")).scalar_one()
        == f"ci_test_{os.getpid()}"
    )
    from corpus_structure.semantic.migrations import current_revision, head_revision

    assert db_server.exists(semantic_head_template.name)
    assert semantic_head_template.name.startswith("cs_sem_head_")
    assert current_revision(native_read) == head_revision()
    assert native_read.scalar(text("SELECT to_regclass('meta.model_revision')")) is None
    extensions = dict(
        native_read.execute(text("SELECT extname, extversion FROM pg_extension")).all()
    )
    assert {"pg_textsearch", "vector", "pg_stat_statements", "pg_jsonschema"} <= set(extensions)
    assert db_server.expected.items() <= extensions.items()


@pytest.mark.parametrize("exceptional", [False, True])
def test_outer_transaction_rolls_back_its_observed_write(
    infrastructure_engine: Engine, exceptional: bool
):
    class BodyFailure(Exception):
        pass

    def write():
        with rollback_connection(infrastructure_engine) as conn:
            conn.execute(text(f"CREATE TABLE {MARKER} (v int)"))
            conn.execute(text(f"INSERT INTO {MARKER} VALUES (1)"))
            assert conn.execute(text(f"SELECT v FROM {MARKER}")).scalar_one() == 1
            if exceptional:
                raise BodyFailure("after observed write")

    if exceptional:
        with pytest.raises(BodyFailure, match="after observed write"):
            write()
    else:
        write()
    with infrastructure_engine.connect() as fresh:
        assert fresh.scalar(text("SELECT to_regclass(:t)"), {"t": MARKER}) is None


# --- Extension versions (DA-018) ---------------------------------------------------------------


def seeded_record(tmp_path: Path, text_: str) -> Path:
    path = tmp_path / "extensions.txt"
    path.write_text(text_)
    return path


def test_the_record_names_every_extension_of_the_template(db_support) -> None:
    record = db_support.expected_extensions()
    assert set(record) == {"pg_textsearch", "vector", "pg_stat_statements", "pg_jsonschema"}
    assert record["pg_textsearch"] == "1.5.1" and record["vector"] == "0.8.7"


def test_a_malformed_record_line_is_refused(db_support, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"extensions\.txt:2"):
        db_support.expected_extensions(seeded_record(tmp_path, "# c\nvector\n"))
    with pytest.raises(ValueError, match=r"extensions\.txt:2"):
        db_support.expected_extensions(seeded_record(tmp_path, "vector 1\nvector 2\n"))


def test_a_seeded_version_mismatch_fails_the_fixture_check(
    db_support, db_server, tmp_path: Path
) -> None:
    record = seeded_record(tmp_path, "pg_textsearch 1.5.1  # as installed\nvector 0.0.1\n")
    seeded = db_support.PgAdmin(
        db_server.url, db_server.template, db_support.expected_extensions(record)
    )
    with pytest.raises(PrerequisiteUnavailable, match=r"vector 0\.8\.7 \(expected 0\.0\.1\)"):
        seeded.check()
    absent = db_support.PgAdmin(db_server.url, db_server.template, {"no_such_extension": "1.0"})
    with pytest.raises(
        PrerequisiteUnavailable, match=r"no_such_extension absent \(expected 1\.0\)"
    ):
        absent.check()


def test_extension_version_changes_are_refused_before_current_template_bootstrap(
    db_support, db_server
) -> None:
    installed = db_server.installed()
    assert db_server.check() == installed
    changed = {**installed, "vector": "0.0.0"}
    added = {**installed, "nonexistent_extension": "1.0"}
    for expected in (changed, added):
        server = db_support.PgAdmin(db_server.url, db_server.template, expected)
        with pytest.raises(PrerequisiteUnavailable, match="extensions differ") as caught:
            server.check()
        assert caught.value.category == "postgres-extensions"


# --- Sweep retention (DA-019) -----------------------------------------------------------------


def test_sweep_honours_each_kind_own_lease_and_retained_heads(db_server, semantic_head_template):
    swept_kinds = (
        "session",
        "infra",
        "infra_case",
        "test",
        "bare",
        "revision",
        "init",
        "build",
        "run_private_head",
        "stale",
        "seed",
    )
    names = [
        database_name(kind, pid=999999999, key=uuid4().hex, run=uuid4().hex).name
        for kind in swept_kinds
    ]
    held = database_name("test").name
    retained = database_name("reusable_head", key=uuid4().hex).name
    untagged = database_name("test").name
    other = "other_" + database_name("test").name
    created = [*names, held, retained, other]
    with ExitStack() as cleanup:
        for name in created:
            db_server.create(name, "template0")
            cleanup.callback(db_server.drop, name)
        with db_server.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{untagged}" TEMPLATE template0')

        def drop_untagged():
            with db_server.connect() as conn:
                conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{untagged}"')

        cleanup.callback(drop_untagged)
        with db_server.lease(held):
            result = db_server.sweep()
            assert set(result.dropped).intersection(created) == set(names)
            assert held in result.skipped
            assert all(db_server.exists(name) for name in (held, retained, other, untagged))
            assert db_server.exists(semantic_head_template.name)
        assert held in db_server.sweep().dropped


def test_sweep_reports_connected_residue_then_drops_after_disconnect(db_server):
    name, later = sorted(database_name("bare").name for _ in range(2))
    with ExitStack() as cleanup:
        for candidate in (name, later):
            db_server.create(candidate, "template0")
            cleanup.callback(db_server.drop, candidate)
        with db_server.connect(name) as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
            result = db_server.sweep()
            assert name in result.skipped
            assert name not in result.dropped
            assert later in result.dropped
            assert db_server.exists(name)
        result = db_server.sweep()
        assert name in result.dropped
        assert name not in result.skipped


# --- Coordinates (DA-020) ---------------------------------------------------------------------


def test_server_url_follows_the_settings_environment(
    db_support, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql://someone@db.example:6543/corpus_x")
    monkeypatch.setenv("CORPUS_DATABASE__MAINTENANCE_URL", "postgresql://maint@")
    assert db_support.server_url() == "postgresql+psycopg://maint@db.example:6543/postgres"


def test_server_url_follows_the_settings_default(
    db_support, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CORPUS_DATABASE__URL", raising=False)
    monkeypatch.delenv("CORPUS_DATABASE__MAINTENANCE_URL", raising=False)
    admin = make_url(db_support.server_url())
    default = make_url(DatabaseSettings().sqlalchemy_url)
    assert admin.database == "postgres"
    assert (admin.host, admin.port, admin.query) == (default.host, default.port, default.query)
    assert admin.username is None and admin.password is None


def test_current_template_cold_build_is_sealed_and_disposed(db_support, db_server) -> None:
    from corpus_structure.semantic.migrations import current_revision, head_revision

    clone_name = database_name("test").name
    server = db_support.PgAdmin(db_server.url, db_server.template)
    with server.deployment(key=uuid4().hex, run_id=uuid4().hex, run_private=True) as template:
        template_name = template.name
        assert server.exists(template_name)
        with server.connect() as conn:
            assert conn.execute(
                text("SELECT datallowconn,datistemplate FROM pg_database WHERE datname=:name"),
                {"name": template_name},
            ).one() == (False, False)
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM pg_stat_activity WHERE datname=:name"),
                    {"name": template_name},
                )
                == 0
            )
        with (
            template.clone(clone_name) as engine,
            engine.connect() as conn,
        ):
            assert current_revision(conn) == head_revision()
            assert conn.scalar(text("SELECT to_regclass('sem.release')")) is not None
            assert conn.scalar(text("SELECT to_regclass('meta.model_revision')")) is None
        assert not server.exists(clone_name)
    assert server.exists(template_name)
    assert template_name in server.sweep().dropped
    assert not server.exists(template_name)
