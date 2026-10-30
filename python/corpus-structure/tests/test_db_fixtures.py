"""The database fixtures (foundations §3.1, §3.9; store note §1) on the test server."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from corpus_structure.settings import DatabaseSettings
from test_prerequisites import PrerequisiteUnavailable

MARKER = "f1_isolation_probe"
_committed: list[str] = []


def test_session_database_is_cloned_from_the_migrated_template(db: Connection, db_server) -> None:
    assert db.execute(text("SELECT current_database()")).scalar_one() == f"ci_test_{os.getpid()}"
    assert db_server.exists(db_server.current)
    assert db_server.current.startswith("cs_tpl_")
    extensions = dict(db.execute(text("SELECT extname, extversion FROM pg_extension")).all())
    assert {"pg_textsearch", "vector", "pg_stat_statements"} <= set(extensions)
    assert db_server.expected.items() <= extensions.items()


def test_a_write_inside_the_outer_transaction(db: Connection) -> None:
    db.execute(text(f"CREATE TABLE {MARKER} (v int)"))
    db.execute(text(f"INSERT INTO {MARKER} VALUES (1)"))
    assert db.execute(text(f"SELECT count(*) FROM {MARKER}")).scalar_one() == 1


def test_the_rolled_back_write_is_invisible_to_the_next_test(db: Connection) -> None:
    found = db.execute(text("SELECT to_regclass(:t)"), {"t": MARKER}).scalar_one()
    assert found is None


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
    _committed.append(name)


def test_the_committing_clone_was_dropped(db_server) -> None:
    assert _committed, "runs after test_committing_db_commits_on_its_own_clone"
    assert not db_server.exists(_committed[0])


# --- Extension versions (DA-018) ---------------------------------------------------------------


def seeded_record(tmp_path: Path, text_: str) -> Path:
    path = tmp_path / "extensions.txt"
    path.write_text(text_)
    return path


def test_the_record_names_every_extension_of_the_template(db_support) -> None:
    record = db_support.expected_extensions()
    assert set(record) == {"pg_textsearch", "vector", "pg_stat_statements"}
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


def test_the_template_name_changes_with_the_extension_versions(db_support, db_server) -> None:
    installed = db_server.installed()
    assert db_server.current == db_support.template_name(installed)
    assert db_support.template_name(dict(installed)) == db_server.current
    upgraded = {**installed, "vector": "0.8.8"}
    added = {**installed, "postgis": "3.6.0"}
    names = {db_support.template_name(v) for v in (installed, upgraded, added)}
    assert len(names) == 3


# --- Sweep retention (DA-019) -----------------------------------------------------------------


def test_sweep_honours_leases_and_template_age(db_support, db_server) -> None:
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
        assert sorted(dropped) == sorted([dead, aged, unstamped])
        assert all(db_server.exists(name) for name in (live, held, fresh, other))
        assert db_server.exists(db_server.current)
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


def test_legacy_template_cold_build_retains_completed_template_and_removes_scratch(
    db_support, db_server
) -> None:
    from uuid import uuid4

    server = db_support.PgAdmin(db_server.url, db_server.template)
    server.current = "cs_tpl_" + uuid4().hex[:16]
    scratch = server.current + "_build"
    try:
        with server.lease(server.current) as lease:
            server.ensure_template(lease)
            assert server.exists(server.current)
            assert not server.exists(scratch)
            with server.connect(server.current) as conn:
                assert conn.exec_driver_sql(
                    "SELECT to_regclass('meta.model_revision')"
                ).scalar_one()
    finally:
        server.drop(scratch)
        server.drop(server.current)
