"""The database fixtures (foundations §3.1, §3.9; store note §1) on the test server."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from corpus_structure.settings import DatabaseSettings
from native_test_support import rollback_connection
from test_prerequisites import PrerequisiteUnavailable

MARKER = "f1_isolation_probe"


def test_session_database_is_cloned_from_the_migrated_template(
    db: Connection, db_server, semantic_head_template
) -> None:
    assert db.execute(text("SELECT current_database()")).scalar_one() == f"ci_test_{os.getpid()}"
    from corpus_structure.semantic.migrations import current_revision, head_revision

    assert db_server.exists(semantic_head_template.name)
    assert semantic_head_template.name.startswith("cs_sem_head_")
    assert current_revision(db) == head_revision()
    assert db.scalar(text("SELECT to_regclass('meta.model_revision')")) is None
    extensions = dict(db.execute(text("SELECT extname, extversion FROM pg_extension")).all())
    assert {"pg_textsearch", "vector", "pg_stat_statements", "pg_jsonschema"} <= set(extensions)
    assert db_server.expected.items() <= extensions.items()


@pytest.mark.parametrize("exceptional", [False, True])
def test_outer_transaction_rolls_back_its_observed_write(db_engine: Engine, exceptional: bool):
    class BodyFailure(Exception):
        pass

    def write():
        with rollback_connection(db_engine) as conn:
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
    with db_engine.connect() as fresh:
        assert fresh.scalar(text("SELECT to_regclass(:t)"), {"t": MARKER}) is None


def test_committing_db_commits_on_its_own_clone(committing_db: Engine, db_engine: Engine) -> None:
    with committing_db.begin() as conn:
        conn.execute(text("CREATE TABLE committed (v int)"))
        conn.execute(text("INSERT INTO committed VALUES (7)"))
    with committing_db.connect() as other:
        assert other.execute(text("SELECT v FROM committed")).scalar_one() == 7
        name = other.execute(text("SELECT current_database()")).scalar_one()
    assert name.startswith(f"ci_test_{os.getpid()}_")
    with db_engine.connect() as session:
        assert session.execute(text("SELECT to_regclass('committed')")).scalar_one() is None


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


def test_sweep_honours_leases_and_template_age(
    db_support, db_server, semantic_head_template
) -> None:
    dead, live = "ci_test_999999999", "ci_test_999999998_9"
    held, aged = "cs_tpl_1111111111111111", "cs_tpl_0000000000000000"
    unstamped, fresh = "cs_tpl_3333333333333333", "cs_tpl_2222222222222222"
    other = "other_test_tpl_f1"  # another project's database on a shared server
    names = (dead, live, held, aged, unstamped, fresh, other)
    old = datetime.now(UTC) - 2 * db_support.TEMPLATE_RETENTION
    for name in names:
        with db_server.lease(name):
            db_server.create(name, "template0")
    db_server.stamp(held, old)
    db_server.stamp(aged, old)
    db_server.stamp(fresh)
    try:
        # Another live session: a lease on its template and on its session name.
        with db_server.lease(held, "ci_test_999999998"):
            dropped = db_server.sweep()
        # Sweeping a shared server can also remove eligible residue from another
        # completed fixture. Assert this test's entire owned universe independently.
        assert set(dropped).intersection(names) == {dead, aged, unstamped}
        assert all(db_server.exists(name) for name in (live, held, fresh, other))
        assert db_server.exists(semantic_head_template.name)
        # Released and aged, the held template goes on the next sweep.
        assert held in db_server.sweep()
    finally:
        for name in names:
            db_server.drop(name)


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
    from uuid import uuid4

    from corpus_structure.semantic.migrations import current_revision, head_revision

    template_name = f"cs_sem_head_{os.getpid()}_{uuid4().hex[:12]}"
    clone_name = f"cs_sem_test_{os.getpid()}_{uuid4().hex[:12]}"
    server = db_support.PgAdmin(db_server.url, db_server.template)
    with server.semantic_template(template_name) as template:
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
            server.database(clone_name, template.name, policy=template.policy) as engine,
            engine.connect() as conn,
        ):
            assert current_revision(conn) == head_revision()
            assert conn.scalar(text("SELECT to_regclass('sem.release')")) is not None
            assert conn.scalar(text("SELECT to_regclass('meta.model_revision')")) is None
        assert not server.exists(clone_name)
    assert not server.exists(template_name)
