"""The database fixtures (foundations §3.1; store note §1) on the test server."""

from __future__ import annotations

import os

from sqlalchemy import Connection, Engine, text

MARKER = "f1_isolation_probe"
_committed: list[str] = []


def test_session_database_is_cloned_from_the_migrated_template(db: Connection, db_server) -> None:
    assert db.execute(text("SELECT current_database()")).scalar_one() == f"ci_test_{os.getpid()}"
    assert db_server.exists(db_server.current)
    assert db_server.current.startswith("cs_tpl_")
    extensions = db.execute(text("SELECT extname FROM pg_extension ORDER BY 1")).scalars().all()
    assert {"pg_textsearch", "vector"} <= set(extensions)


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


def test_sweep_touches_only_stale_test_databases_and_old_templates(db_server) -> None:
    dead, live, old = "ci_test_999999999", f"ci_test_{os.getppid()}_9", "cs_tpl_0000000000000000"
    other = "other_test_tpl_f1"  # another project's database on a shared server
    for name in (dead, live, old, other):
        db_server.create(name, "template0")
    try:
        dropped = db_server.sweep()
        assert dead in dropped and old in dropped
        assert live not in dropped and other not in dropped
        assert db_server.current not in dropped
        assert not db_server.exists(dead) and not db_server.exists(old)
        assert db_server.exists(live) and db_server.exists(other)
    finally:
        for name in (dead, live, old, other):
            db_server.drop(name)
