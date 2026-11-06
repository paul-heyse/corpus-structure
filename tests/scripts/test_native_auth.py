"""Failure-injection tests for native alternate-principal ownership and recovery."""

from __future__ import annotations

import json
import os
import pwd
import re
import select
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import native_auth

_REAL_EDIT = native_auth.edit


class FakeServer:
    url = "postgresql://postgres@/postgres?host=/var/run/postgresql&port=5434"

    @contextmanager
    def lease(self, _name: str, *, exclusive: bool = False):
        assert exclusive
        yield


class FakeCluster:
    def __init__(self) -> None:
        self.cluster = "test-system-identifier"
        self.roles: dict[str, dict[str, Any]] = {}
        self.rows: dict[str, set[str]] = {
            "semantic_hba.conf": {"# unrelated hba row"},
            "pg_ident.conf": {"# unrelated ident row"},
        }
        self.next_oid = 40000
        self.fail_create = False
        self.fail_reload = 0
        self.fail_add_at: int | None = None
        self.fail_remove = 0
        self.add_count = 0

    def pg(self, sql: str) -> str:
        if sql == "SELECT system_identifier FROM pg_control_system()":
            return self.cluster
        if sql.startswith("SELECT count(*) FROM pg_stat_activity"):
            return "0"
        if "FROM pg_roles WHERE rolname=" in sql:
            match = re.search(r"rolname='([^']+)'", sql)
            assert match is not None
            role = match.group(1)
            record = self.roles.get(role)
            if sql.startswith("SELECT oid FROM pg_roles"):
                return "" if record is None else str(record["oid"])
            return "" if record is None else f"{record['oid']}:{record['comment']}"
        if sql.startswith("BEGIN; CREATE ROLE "):
            if self.fail_create:
                raise RuntimeError("role create failed before acknowledgement")
            role_match = re.search(r"CREATE ROLE ([a-z0-9_]+)", sql)
            stamp_match = re.search(r"IS '([^']+)'", sql)
            assert role_match is not None and stamp_match is not None
            role = role_match.group(1)
            stamp = stamp_match.group(1)
            self.roles[role] = {"oid": self.next_oid, "comment": stamp}
            self.next_oid += 1
            return ""
        if sql == "SELECT pg_reload_conf()":
            if self.fail_reload:
                self.fail_reload -= 1
                raise RuntimeError("configuration reload failed")
            return "t"
        if sql.startswith("DROP ROLE "):
            match = re.search(r'DROP ROLE "([^\"]+)"', sql)
            assert match is not None
            role = match.group(1)
            self.roles.pop(role, None)
            return ""
        raise AssertionError(f"unexpected SQL: {sql}")

    def edit(self, path: Path, line: str, add: bool) -> None:
        rows = self.rows[path.name]
        if add:
            self.add_count += 1
            if self.fail_add_at == self.add_count:
                raise RuntimeError("authentication row addition failed")
            if line in rows:
                raise RuntimeError("owned row already exists")
            rows.add(line)
        else:
            if self.fail_remove:
                self.fail_remove -= 1
                raise RuntimeError("authentication row removal failed")
            rows.discard(line)

    def contains(self, path: Path, line: str) -> bool:
        return line in self.rows[path.name]


@pytest.fixture
def cluster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeCluster:
    state = FakeCluster()
    root = tmp_path / "journal"
    monkeypatch.setattr(native_auth, "ROOT", root)
    monkeypatch.setattr(native_auth, "CONF", tmp_path / "conf")
    monkeypatch.setattr(native_auth, "pg", state.pg)
    monkeypatch.setattr(native_auth, "edit", state.edit)
    monkeypatch.setattr(native_auth, "contains", state.contains)
    return state


def test_role_creation_failure_removes_unacknowledged_journal_and_auth_rows(
    cluster: FakeCluster,
) -> None:
    cluster.fail_create = True
    with (
        pytest.raises(RuntimeError, match="role create failed"),
        native_auth.alternate_reader(FakeServer(), "ci_test_1"),
    ):
        pytest.fail("creation failure must not yield a login")
    assert cluster.roles == {}
    assert cluster.rows == {
        "semantic_hba.conf": {"# unrelated hba row"},
        "pg_ident.conf": {"# unrelated ident row"},
    }
    assert list(native_auth.ROOT.glob("*.json")) == []


@pytest.mark.parametrize("failure", ["second_edit", "first_reload"])
def test_partial_authentication_setup_is_recovered(cluster: FakeCluster, failure: str) -> None:
    if failure == "second_edit":
        cluster.fail_add_at = 2
        expected = "authentication row addition failed"
    else:
        cluster.fail_reload = 1
        expected = "configuration reload failed"
    with (
        pytest.raises(RuntimeError, match=expected),
        native_auth.alternate_reader(FakeServer(), "ci_test_2"),
    ):
        pytest.fail("partial setup must not yield a login")
    assert cluster.roles == {}
    assert cluster.rows == {
        "semantic_hba.conf": {"# unrelated hba row"},
        "pg_ident.conf": {"# unrelated ident row"},
    }
    assert list(native_auth.ROOT.glob("*.json")) == []


def test_body_and_recovery_failures_are_grouped_and_journal_is_retryable(
    cluster: FakeCluster,
) -> None:
    with (
        pytest.raises(ExceptionGroup) as caught,
        native_auth.alternate_reader(FakeServer(), "ci_test_3"),
    ):
        cluster.fail_remove = 1
        raise ValueError("test body failed")

    def leaves(group: BaseExceptionGroup) -> list[BaseException]:
        return [
            leaf
            for error in group.exceptions
            for leaf in (leaves(error) if isinstance(error, BaseExceptionGroup) else [error])
        ]

    failures = leaves(caught.value)
    assert any(isinstance(error, ValueError) for error in failures)
    assert any("authentication row removal failed" in str(error) for error in failures)
    journal = next(native_auth.ROOT.glob("*.json"))
    assert journal.exists()
    # Failed recovery keeps the stamped role and remaining row for the next invocation.
    assert len(cluster.roles) == 1
    assert any(line.startswith("local ci_test_3 ") for line in cluster.rows["semantic_hba.conf"])

    with native_auth.alternate_reader(FakeServer(), "ci_test_4"):
        assert len(cluster.roles) == 1
    assert cluster.roles == {}
    assert list(native_auth.ROOT.glob("*.json")) == []
    assert cluster.rows == {
        "semantic_hba.conf": {"# unrelated hba row"},
        "pg_ident.conf": {"# unrelated ident row"},
    }


def _write_journal(
    root: Path,
    *,
    cluster_id: str,
    role: str,
    token: str,
    database: str = "ci_test_5",
    operator: str = "operator",
) -> Path:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / f"{token}.json"
    path.write_text(
        json.dumps(
            {
                "role": role,
                "token": token,
                "database": database,
                "operator": operator,
                "cluster": cluster_id,
                "role_oid": 41234,
                "auth_rows": ["semantic_hba.conf", "pg_ident.conf"],
            }
        )
    )
    return path


@pytest.mark.parametrize("mismatch", ["role_stamp", "cluster"])
def test_wrong_role_stamp_or_cluster_preserves_journal_role_and_rows(
    cluster: FakeCluster, mismatch: str
) -> None:
    token = "a" * 32
    role = "cs_reader_" + token
    stamp = f"corpus-structure native auth {token}"
    cluster.roles[role] = {"oid": 41234, "comment": stamp if mismatch == "cluster" else "other"}
    cluster.rows["semantic_hba.conf"].add(f"local ci_test_5 {role} peer map=corpus_semantic")
    cluster.rows["pg_ident.conf"].add(f"corpus_semantic operator {role}")
    path = _write_journal(
        native_auth.ROOT,
        cluster_id="another-system" if mismatch == "cluster" else cluster.cluster,
        role=role,
        token=token,
    )
    with pytest.raises(RuntimeError, match=r"identity mismatch|unacknowledged"):
        native_auth.recover(path, cluster.cluster)
    assert path.exists()
    assert cluster.roles[role]["comment"] == (stamp if mismatch == "cluster" else "other")
    assert any(role in line for line in cluster.rows["semantic_hba.conf"])
    assert any(role in line for line in cluster.rows["pg_ident.conf"])


def test_symlink_journal_is_refused_without_touching_target(
    cluster: FakeCluster, tmp_path: Path
) -> None:
    target = tmp_path / "outside.json"
    target.write_text("{}")
    native_auth.ROOT.mkdir(parents=True)
    link = native_auth.ROOT / "linked.json"
    link.symlink_to(target)
    with pytest.raises(RuntimeError, match="unowned authentication journal"):
        native_auth.recover(link, cluster.cluster)
    assert target.read_text() == "{}"
    assert cluster.roles == {}
    assert cluster.rows == {
        "semantic_hba.conf": {"# unrelated hba row"},
        "pg_ident.conf": {"# unrelated ident row"},
    }


def test_journal_root_symlink_is_refused(cluster: FakeCluster, tmp_path: Path) -> None:
    original = native_auth.ROOT
    original.mkdir(parents=True)
    original.rmdir()
    target = tmp_path / "elsewhere"
    target.mkdir(mode=0o700)
    original.symlink_to(target, target_is_directory=True)
    with (
        pytest.raises(RuntimeError, match="journal root must be private"),
        native_auth.alternate_reader(FakeServer(), "ci_test_6"),
    ):
        pytest.fail("symlink root must not acquire shared authentication")
    assert list(target.iterdir()) == []
    assert cluster.roles == {}


def test_prepublication_orphan_is_removed_but_unowned_temporary_is_preserved(
    cluster: FakeCluster,
) -> None:
    native_auth.ROOT.mkdir(parents=True)
    native_auth.ROOT.chmod(0o700)
    token = "d" * 32
    orphan = native_auth.ROOT / f"{token}.new"
    orphan.write_text('{"truncated":')
    other = native_auth.ROOT / "operator-notes.new"
    other.write_text("leave this alone")
    linked_target = native_auth.ROOT.parent / "linked-target"
    linked_target.write_text("keep target")
    linked = native_auth.ROOT / f"{'e' * 32}.new"
    linked.symlink_to(linked_target)

    with native_auth.alternate_reader(FakeServer(), "ci_test_8"):
        assert not orphan.exists()
        assert other.read_text() == "leave this alone"
        assert linked.is_symlink()
        assert linked_target.read_text() == "keep target"
    assert other.read_text() == "leave this alone"
    assert linked.is_symlink()
    assert linked_target.read_text() == "keep target"


def test_malformed_final_journal_is_preserved_and_blocks_new_acquisition(
    cluster: FakeCluster,
) -> None:
    native_auth.ROOT.mkdir(parents=True)
    native_auth.ROOT.chmod(0o700)
    token = "f" * 32
    journal = native_auth.ROOT / f"{token}.json"
    contents = '{"partial":'
    journal.write_text(contents)
    with (
        pytest.raises(json.JSONDecodeError),
        native_auth.alternate_reader(FakeServer(), "ci_test_9"),
    ):
        pytest.fail("malformed committed journal must block acquisition")
    assert journal.read_text() == contents
    assert cluster.roles == {}
    assert cluster.rows == {
        "semantic_hba.conf": {"# unrelated hba row"},
        "pg_ident.conf": {"# unrelated ident row"},
    }


def _run_privileged_python_locally(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run the bounded edit payload as the current user against a temporary test fixture."""
    assert argv[:3] == ["sudo", "-n", "python3"]
    return subprocess.run([sys.executable, *argv[3:]], **kwargs)


def _seed_recovery(
    cluster: FakeCluster, token: str, database: str = "ci_test_10"
) -> tuple[Path, str, list[tuple[Path, str]]]:
    role = "cs_reader_" + token
    operator = pwd.getpwuid(os.getuid()).pw_name
    owned_rows = list(native_auth.rows(role, database, operator))
    native_auth.CONF.mkdir(parents=True, exist_ok=True)
    for path, line in owned_rows:
        path.write_text(f"# unrelated {path.name}\n{line}\n")
        path.chmod(0o640)
    cluster.roles[role] = {
        "oid": 41234,
        "comment": f"corpus-structure native auth {token}",
    }
    journal = _write_journal(
        native_auth.ROOT,
        cluster_id=cluster.cluster,
        role=role,
        token=token,
        database=database,
        operator=operator,
    )
    return journal, role, owned_rows


def test_recovery_removes_owned_regular_edit_temporary_and_preserves_other_rows(
    cluster: FakeCluster, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_auth, "edit", _REAL_EDIT)
    monkeypatch.setattr(native_auth, "run_effect", _run_privileged_python_locally)
    token = "1" * 32
    journal, role, owned_rows = _seed_recovery(cluster, token)
    hba_path, _ = owned_rows[0]
    temporary = hba_path.parent / f".cs-native-auth-{token}-{hba_path.name}.new"
    temporary.write_text("interrupted atomic edit")
    temporary.chmod(0o600)

    native_auth.recover(journal, cluster.cluster)

    assert not temporary.exists()
    assert not journal.exists()
    assert role not in cluster.roles
    for path, _line in owned_rows:
        assert path.read_text() == f"# unrelated {path.name}\n"
        assert path.stat().st_mode & 0o777 == 0o640


def test_recovery_refuses_and_preserves_symlink_edit_temporary(
    cluster: FakeCluster, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(native_auth, "edit", _REAL_EDIT)
    monkeypatch.setattr(native_auth, "run_effect", _run_privileged_python_locally)
    token = "2" * 32
    journal, role, owned_rows = _seed_recovery(cluster, token)
    hba_path, hba_line = owned_rows[0]
    temporary = hba_path.parent / f".cs-native-auth-{token}-{hba_path.name}.new"
    target = tmp_path / "unrelated-target"
    target.write_text("preserve target")
    temporary.symlink_to(target)

    with pytest.raises(BaseExceptionGroup, match="recovery failures"):
        native_auth.recover(journal, cluster.cluster)

    assert temporary.is_symlink() and temporary.resolve() == target
    assert target.read_text() == "preserve target"
    assert hba_line in hba_path.read_text()
    assert journal.exists()
    assert role in cluster.roles
    assert not any(line in path.read_text() for path, line in owned_rows[1:])


def test_effect_lock_waits_for_inflight_helper_after_owner_death(tmp_path: Path) -> None:
    """A real flock inherited by the supervisor outlives its owner until the helper settles."""
    if os.name != "posix":
        pytest.skip("native auth effect locking uses POSIX flock")
    root = tmp_path / "native-auth"
    root.mkdir(mode=0o700)
    started = tmp_path / "helper-started"
    release = tmp_path / "release-helper"
    committed = tmp_path / "effect-committed"
    attempting = tmp_path / "recovery-attempting"
    entered = tmp_path / "recovery-entered"
    repository = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(repository / "scripts"), *filter(None, [os.environ.get("PYTHONPATH")])]
        ),
    }
    helper_source = """
import sys,time
from pathlib import Path
started,release,committed=map(Path,sys.argv[1:])
started.write_text('running')
deadline=time.monotonic()+20
while not release.exists():
    if time.monotonic()>deadline: raise TimeoutError('test did not release helper')
    time.sleep(.01)
committed.write_text('finished before lock release')
"""
    owner_source = """
import sys
from pathlib import Path
import native_auth
native_auth.ROOT=Path(sys.argv[1])
with native_auth.effect_lock():
    native_auth.run_effect([sys.executable,'-c',sys.argv[2],*sys.argv[3:]],check=True)
"""
    recovery_source = """
import sys,time
from pathlib import Path
import native_auth
root,attempting,entered,committed=map(Path,sys.argv[1:])
native_auth.ROOT=root
attempting.write_text('waiting for owner effect')
with native_auth.effect_lock():
    if not committed.exists(): raise SystemExit('effect was not settled before recovery entered')
    entered.write_text('entered after effect settled')
"""
    owner = subprocess.Popen(
        [
            sys.executable,
            "-c",
            owner_source,
            str(root),
            helper_source,
            str(started),
            str(release),
            str(committed),
        ],
        cwd=repository,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    recovery: subprocess.Popen[bytes] | None = None
    try:
        deadline = time.monotonic() + 10
        while not started.exists() and time.monotonic() < deadline:
            if owner.poll() is not None:
                error_stream = owner.stderr
                details = error_stream.read() if error_stream is not None else "stderr unavailable"
                raise AssertionError(f"owner exited before helper start: {details}")
            time.sleep(0.01)
        assert started.exists(), "the privileged-effect stand-in did not start"
        os.kill(owner.pid, signal.SIGKILL)
        assert owner.wait(timeout=5) == -signal.SIGKILL

        recovery = subprocess.Popen(
            [
                sys.executable,
                "-c",
                recovery_source,
                str(root),
                str(attempting),
                str(entered),
                str(committed),
            ],
            cwd=repository,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 10
        while not attempting.exists() and time.monotonic() < deadline:
            if recovery.poll() is not None:
                error_stream = recovery.stderr
                details = error_stream.read() if error_stream is not None else "stderr unavailable"
                raise AssertionError(f"recovery exited before waiting: {details}")
            time.sleep(0.01)
        assert attempting.exists(), "recovery process did not attempt the effect lock"
        time.sleep(0.15)
        assert not entered.exists(), (
            "recovery entered while the in-flight helper still owned effects"
        )

        release.write_text("finish helper")
        error_stream = recovery.stderr
        assert error_stream is not None
        assert recovery.wait(timeout=10) == 0, error_stream.read()
        assert committed.read_text() == "finished before lock release"
        assert entered.read_text() == "entered after effect settled"
    finally:
        release.touch(exist_ok=True)
        for process in (owner, recovery):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)


def test_changed_persisted_role_oid_preserves_all_effects(cluster: FakeCluster) -> None:
    token = "b" * 32
    role = "cs_reader_" + token
    stamp = f"corpus-structure native auth {token}"
    cluster.roles[role] = {"oid": 41235, "comment": stamp}
    cluster.rows["semantic_hba.conf"].add(f"local ci_test_5 {role} peer map=corpus_semantic")
    cluster.rows["pg_ident.conf"].add(f"corpus_semantic operator {role}")
    path = _write_journal(
        native_auth.ROOT,
        cluster_id=cluster.cluster,
        role=role,
        token=token,
    )
    with pytest.raises(RuntimeError, match="OID changed"):
        native_auth.recover(path, cluster.cluster)
    assert path.exists()
    assert cluster.roles[role] == {"oid": 41235, "comment": stamp}
    assert any(role in line for line in cluster.rows["semantic_hba.conf"])
    assert any(role in line for line in cluster.rows["pg_ident.conf"])


def test_preexisting_owned_row_is_never_claimed_or_removed(
    cluster: FakeCluster, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    token = "c" * 32
    role = "cs_reader_" + token
    monkeypatch.setattr(native_auth, "uuid4", lambda: SimpleNamespace(hex=token))
    path, line = native_auth.rows(role, "ci_test_7", pwd.getpwuid(os.getuid()).pw_name)[0]
    cluster.rows[path.name].add(line)
    with (
        pytest.raises(RuntimeError, match="predates owned edit"),
        native_auth.alternate_reader(FakeServer(), "ci_test_7"),
    ):
        pytest.fail("preexisting auth row must refuse acquisition")
    assert line in cluster.rows["semantic_hba.conf"]
    assert cluster.roles == {}
    assert list(native_auth.ROOT.glob("*.json")) == []


@pytest.mark.shared_cluster_fault
@pytest.mark.skipif(
    os.environ.get("CORPUS_TEST_NATIVE_AUTH_CRASH") != "1",
    reason="opt-in shared-cluster SIGKILL recovery control",
)
@pytest.mark.db
def test_sigkill_owner_is_recovered_by_the_next_pgadmin_context() -> None:
    """Opt-in control against the explicitly configured 18/corpus auth adapter."""
    if os.name != "posix":
        pytest.skip("the shared-cluster auth adapter and SIGKILL control require POSIX")

    from sqlalchemy import text

    from corpus_structure.settings import Settings
    from native_test_support import PgAdmin, lock_sql, server_url

    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    database = settings.database.template
    child_source = """
import time
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, server_url
settings = Settings()
server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
with server.alternate_reader(settings.database.template) as role:
    print(role, flush=True)
    while True:
        time.sleep(0.1)
"""
    repository = Path(__file__).resolve().parents[2]
    python_path = os.pathsep.join(
        [
            str(repository / "scripts"),
            str(repository / "python/corpus-structure/src"),
            *filter(None, [os.environ.get("PYTHONPATH")]),
        ]
    )
    env = {**os.environ, "PYTHONPATH": python_path}

    # Recover any prior owned journal before this narrowly named death control starts.
    with server.alternate_reader(database):
        pass

    child = subprocess.Popen(
        [sys.executable, "-c", child_source],
        cwd=repository,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    owned_role: str | None = None
    journal: Path | None = None
    try:
        assert child.stdout is not None
        ready, _, _ = select.select([child.stdout], [], [], 60)
        if not ready:
            raise AssertionError("alternate-principal child did not acquire a role within 60s")
        owned_role = child.stdout.readline().strip()
        if owned_role is None or not owned_role.startswith("cs_reader_"):
            stderr = child.stderr.read() if child.stderr is not None else ""
            raise AssertionError(f"alternate-principal child failed before yielding: {stderr}")
        journal = native_auth.ROOT / f"{owned_role.removeprefix('cs_reader_')}.json"
        record = json.loads(journal.read_text())
        assert record["role"] == owned_role and record["role_oid"] > 0
        assert record["cluster"]
        assert set(record["auth_rows"]) == {"semantic_hba.conf", "pg_ident.conf"}
        with server.connect() as conn:
            observed = conn.execute(
                text(
                    "SELECT oid,shobj_description(oid,'pg_authid') FROM pg_roles "
                    "WHERE rolname=:role"
                ),
                {"role": owned_role},
            ).one()
        assert observed == (
            record["role_oid"],
            f"corpus-structure native auth {record['token']}",
        )
        for path, line in native_auth.rows(owned_role, database, record["operator"]):
            assert native_auth.contains(path, line)
        with server.connect() as conn:
            owns_lock = conn.execute(
                text(lock_sql("pg_try_advisory_lock")), {"name": "cs_native_cluster_auth"}
            ).scalar_one()
            if owns_lock:
                conn.execute(
                    text(lock_sql("pg_advisory_unlock")), {"name": "cs_native_cluster_auth"}
                )
        assert not owns_lock, "a concurrent native auth owner acquired the exclusive lease"

        os.kill(child.pid, signal.SIGKILL)
        assert child.wait(timeout=15) == -signal.SIGKILL
        assert journal.exists()

        # The next exact PgAdmin ownership context recovers the killed owner's rows and role.
        with server.alternate_reader(database):
            pass
        assert not journal.exists()
        with server.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": owned_role}
                ).first()
                is None
            )
        for path, line in native_auth.rows(owned_role, database, record["operator"]):
            assert not native_auth.contains(path, line)
    finally:
        if child.poll() is None:
            os.kill(child.pid, signal.SIGKILL)
            child.wait(timeout=15)
        if journal is not None and journal.exists():
            # Keep the shared fixture recoverable if an assertion aborts after ownership.
            with server.alternate_reader(database):
                pass


@pytest.mark.shared_cluster_fault
@pytest.mark.skipif(
    os.environ.get("CORPUS_TEST_NATIVE_AUTH_CRASH") != "1",
    reason="opt-in shared-cluster delayed-backend SIGKILL recovery control",
)
@pytest.mark.db
def test_killed_owner_waits_for_tagged_postgres_backend_before_recovery() -> None:
    """A dead client cannot let recovery race SQL still executing on its tagged backend."""
    if os.name != "posix":
        pytest.skip("the shared-cluster auth adapter and SIGKILL control require POSIX")

    from uuid import uuid4

    from sqlalchemy import text

    from corpus_structure.settings import Settings
    from native_test_support import PgAdmin, server_url

    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    database = settings.database.template
    repository = Path(__file__).resolve().parents[2]
    token = uuid4().hex
    role = "cs_reader_" + token
    journal = native_auth.ROOT / f"{token}.json"
    child_source = """
import sys
from types import SimpleNamespace
import native_auth
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, server_url
token,database=sys.argv[1:]
native_auth.uuid4=lambda: SimpleNamespace(hex=token)
original_pg=native_auth.pg
def delayed_pg(sql):
    if sql.startswith('BEGIN; CREATE ROLE '):
        return original_pg('SELECT pg_sleep(5); ' + sql)
    return original_pg(sql)
native_auth.pg=delayed_pg
settings=Settings()
server=PgAdmin(server_url(settings), settings.database.template, settings=settings)
with server.alternate_reader(database) as owned_role:
    print(owned_role,flush=True)
    import time
    time.sleep(30)
"""
    python_path = os.pathsep.join(
        [
            str(repository / "scripts"),
            str(repository / "python/corpus-structure/src"),
            *filter(None, [os.environ.get("PYTHONPATH")]),
        ]
    )
    env = {**os.environ, "PYTHONPATH": python_path}
    with server.alternate_reader(database):
        pass

    child = subprocess.Popen(
        [sys.executable, "-c", child_source, token, database],
        cwd=repository,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 60
        active_backend = 0
        while time.monotonic() < deadline:
            if child.poll() is not None:
                stderr = child.stderr.read() if child.stderr is not None else ""
                stdout = child.stdout.read() if child.stdout is not None else ""
                raise AssertionError(
                    f"delayed backend child exited early ({child.returncode}); "
                    f"stdout={stdout!r}; stderr={stderr!r}"
                )
            active_backend = int(
                native_auth.pg(
                    "SELECT count(*) FROM pg_stat_activity WHERE pid<>pg_backend_pid() "
                    f"AND application_name='cs_native_auth_{token}' "
                    "AND query LIKE '%pg_sleep(5)%'"
                )
            )
            if active_backend:
                break
            time.sleep(0.05)
        assert active_backend, "did not observe the child PostgreSQL operation"
        assert journal.exists()
        record = json.loads(journal.read_text())
        assert record["role"] == role
        assert "role_oid" not in record  # SIGKILL occurred before post-CREATE acknowledgement.

        os.killpg(child.pid, signal.SIGKILL)
        assert child.wait(timeout=15) == -signal.SIGKILL

        # The next ownership context waits for the operation-tagged backend, then removes any
        # committed stamped role before publishing and cleaning its own fresh context.
        with server.alternate_reader(database):
            pass
        assert not journal.exists()
        with server.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
                ).first()
                is None
            )
            assert (
                conn.execute(
                    text(
                        "SELECT 1 FROM pg_stat_activity WHERE pid<>pg_backend_pid() "
                        "AND application_name=:name"
                    ),
                    {"name": f"cs_native_auth_{token}"},
                ).first()
                is None
            )
        for path, line in native_auth.rows(role, database, record["operator"]):
            assert not native_auth.contains(path, line)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=15)
        if journal.exists():
            with server.alternate_reader(database):
                pass


@pytest.mark.shared_cluster_fault
@pytest.mark.skipif(
    os.environ.get("CORPUS_TEST_NATIVE_AUTH_CRASH") != "1",
    reason="opt-in shared-cluster partial-authentication failure controls",
)
@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("after_create", "injected after role create"),
        ("first_edit", "injected after first auth edit"),
        ("second_edit", "injected after second auth edit"),
        ("reload", "injected after reload"),
    ],
)
@pytest.mark.db
def test_actual_partial_auth_effects_are_recovered(stage: str, expected: str) -> None:
    """Each injected failure follows a committed native effect and must unwind its exact owner."""
    if os.name != "posix":
        pytest.skip("the shared-cluster auth adapter requires POSIX")

    from uuid import uuid4

    from sqlalchemy import text

    from corpus_structure.settings import Settings
    from native_test_support import PgAdmin, server_url

    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    database = settings.database.template
    repository = Path(__file__).resolve().parents[2]
    token = uuid4().hex
    role = "cs_reader_" + token
    journal = native_auth.ROOT / f"{token}.json"
    child_source = """
import sys
from types import SimpleNamespace
import native_auth
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, server_url
stage,database,token=sys.argv[1:]
native_auth.uuid4=lambda: SimpleNamespace(hex=token)
original_pg=native_auth.pg
original_edit=native_auth.edit
fired=False
edits=0
def injected_pg(sql):
    global fired
    result=original_pg(sql)
    if stage=='after_create' and sql.startswith('BEGIN; CREATE ROLE ') and not fired:
        fired=True
        raise RuntimeError('injected after role create')
    if stage=='reload' and sql=='SELECT pg_reload_conf()' and not fired:
        fired=True
        raise RuntimeError('injected after reload')
    return result
def injected_edit(path,line,add):
    global edits,fired
    result=original_edit(path,line,add)
    if add:
        edits+=1
        expected=1 if stage=='first_edit' else 2
        if stage in ('first_edit','second_edit') and edits==expected and not fired:
            fired=True
            raise RuntimeError('injected after '+('first' if edits==1 else 'second')+' auth edit')
    return result
native_auth.pg=injected_pg
native_auth.edit=injected_edit
settings=Settings()
server=PgAdmin(server_url(settings),settings.database.template,settings=settings)
try:
    with server.alternate_reader(database):
        raise AssertionError('injection stage did not stop acquisition')
except RuntimeError as error:
    if str(error) not in ('injected after role create','injected after first auth edit',
                          'injected after second auth edit','injected after reload'):
        raise
    if not fired:
        raise AssertionError('expected injection was not reached')
else:
    raise AssertionError('expected injected native failure')
print('RECOVERED',flush=True)
"""
    python_path = os.pathsep.join(
        [
            str(repository / "scripts"),
            str(repository / "python/corpus-structure/src"),
            *filter(None, [os.environ.get("PYTHONPATH")]),
        ]
    )
    env = {**os.environ, "PYTHONPATH": python_path}
    with server.alternate_reader(database):
        pass

    child = subprocess.Popen(
        [sys.executable, "-c", child_source, stage, database, token],
        cwd=repository,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=60)
        assert child.returncode == 0, (
            f"child rc={child.returncode}; stdout={stdout}; stderr={stderr}"
        )
        assert stdout.strip() == "RECOVERED", stderr
        assert not journal.exists()
        with server.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
                ).first()
                is None
            )
        operator = pwd.getpwuid(os.getuid()).pw_name
        for path, line in native_auth.rows(role, database, operator):
            assert not native_auth.contains(path, line)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.communicate(timeout=15)
        if journal.exists():
            with server.alternate_reader(database):
                pass


@pytest.mark.shared_cluster_fault
@pytest.mark.skipif(
    os.environ.get("CORPUS_TEST_NATIVE_AUTH_CRASH") != "1",
    reason="opt-in root-helper SIGTERM recovery control",
)
@pytest.mark.db
def test_killed_owner_waits_for_privileged_file_helper_then_removes_late_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The root guardian settles its helper before recovery can clean its acquired row."""
    if os.name != "posix":
        pytest.skip("the shared-cluster auth adapter requires POSIX")

    from uuid import uuid4

    from sqlalchemy import text

    from corpus_structure.settings import Settings
    from native_test_support import PgAdmin, server_url

    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    database = settings.database.template
    repository = Path(__file__).resolve().parents[2]
    configuration = tmp_path / "auth-conf"
    configuration.mkdir(mode=0o700)
    (configuration / "semantic_hba.conf").write_text("# unrelated hba\n")
    (configuration / "pg_ident.conf").write_text("# unrelated ident\n")
    for path in configuration.iterdir():
        path.chmod(0o640)
    monkeypatch.setattr(native_auth, "CONF", configuration)

    token = uuid4().hex
    role = "cs_reader_" + token
    journal = native_auth.ROOT / f"{token}.json"
    helper_ready = tmp_path / "root-file-helper-ready"
    child_source = """
import os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import native_auth
from corpus_structure.settings import Settings
from native_test_support import PgAdmin,server_url
root,configuration,marker,database,token=sys.argv[1:]
native_auth.ROOT=Path(root)
native_auth.CONF=Path(configuration)
native_auth.uuid4=lambda: SimpleNamespace(hex=token)
original_run_effect=native_auth.run_effect
wrapper='''import subprocess,sys,time
from pathlib import Path
marker,*command=sys.argv[1:]
Path(marker).write_text("helper started")
time.sleep(5)
subprocess.run(command,check=True)
'''
def delayed(argv,**kwargs):
    script=argv[4] if len(argv)>4 and argv[:3]==['sudo','-n','python3'] else ''
    if script.startswith('import os,sys,stat') and argv[7]=='1':
        argv=['sudo','-n',sys.executable,'-c',wrapper,marker,*argv]
    return original_run_effect(argv,**kwargs)
native_auth.run_effect=delayed
settings=Settings()
server=PgAdmin(server_url(settings),settings.database.template,settings=settings)
with server.alternate_reader(database):
    raise AssertionError('owner should be terminated during its privileged helper')
"""
    python_path = os.pathsep.join(
        [
            str(repository / "scripts"),
            str(repository / "python/corpus-structure/src"),
            *filter(None, [os.environ.get("PYTHONPATH")]),
        ]
    )
    env = {**os.environ, "PYTHONPATH": python_path}
    with server.alternate_reader(database):
        pass

    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            child_source,
            str(native_auth.ROOT),
            str(configuration),
            str(helper_ready),
            database,
            token,
        ],
        cwd=repository,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 60
        while not helper_ready.exists() and time.monotonic() < deadline:
            if child.poll() is not None:
                stderr = child.stderr.read() if child.stderr is not None else ""
                stdout = child.stdout.read() if child.stdout is not None else ""
                raise AssertionError(
                    f"owner exited before privileged helper start ({child.returncode}); "
                    f"stdout={stdout!r}; stderr={stderr!r}"
                )
            time.sleep(0.02)
        assert helper_ready.read_text() == "helper started"
        record = json.loads(journal.read_text())
        assert record["role"] == role
        assert record["auth_rows"] == ["semantic_hba.conf"]
        with server.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
                ).first()
                is not None
            )

        # Catchable group termination kills the owner and its operator-side wrappers; the
        # privileged guardian remains alive to complete the in-flight helper under its SH lock.
        os.killpg(child.pid, signal.SIGTERM)
        assert child.wait(timeout=10) == -signal.SIGTERM

        # Recovery blocks on the guardian, then removes the row it finished installing.
        with server.alternate_reader(database):
            pass
        assert not journal.exists()
        assert (configuration / "semantic_hba.conf").read_text() == "# unrelated hba\n"
        assert (configuration / "pg_ident.conf").read_text() == "# unrelated ident\n"
        temporary = configuration / f".cs-native-auth-{token}-semantic_hba.conf.new"
        assert not temporary.exists()
        with server.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
                ).first()
                is None
            )
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=10)
        if journal.exists():
            with server.alternate_reader(database):
                pass


@pytest.mark.shared_cluster_fault
@pytest.mark.skipif(
    os.environ.get("CORPUS_TEST_NATIVE_AUTH_CRASH") != "1",
    reason="opt-in privileged guardian generation-fence control",
)
def test_stale_guardian_generation_refuses_a_late_privileged_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An old recovery helper cannot perform a privileged effect in a newer generation."""
    if os.name != "posix":
        pytest.skip("the privileged guardian requires POSIX")

    root = tmp_path / "native-auth"
    root.mkdir(mode=0o700)
    token = "9" * 32
    journal = root / f"{token}.json"
    journal.write_text(json.dumps({"phase": "recover-new-generation"}))
    journal.chmod(0o600)
    (root / "privileged.lock").touch(mode=0o600)
    marker = tmp_path / "late-effect-ran"
    monkeypatch.setattr(native_auth, "ROOT", root)
    operation = native_auth._RUN.set(token)
    phase = native_auth._PHASE.set("recover-old-generation")
    try:
        result = native_auth.run_effect(
            [
                "sudo",
                "-n",
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')",
                str(marker),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        native_auth._PHASE.reset(phase)
        native_auth._RUN.reset(operation)

    assert result.returncode != 0
    assert "stale authentication helper" in result.stderr
    assert not marker.exists()
