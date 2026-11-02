"""Recoverable alternate-principal effects owned by the existing native test lifecycle.

The shared-cluster adapter is deliberately restricted to 18/corpus. The private journal is
an acquisition record, not qualification evidence. A stamp, never a name alone, authorizes
recovery. One advisory lease serializes edits and excludes every live owner.
"""

from __future__ import annotations

import fcntl
import json
import os
import pwd
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1] / "build" / "native-auth"
CONF = Path("/etc/postgresql/18/corpus")
_LOCK: ContextVar[int | None] = ContextVar("native_auth_effect_lock", default=None)
_RUN: ContextVar[str | None] = ContextVar("native_auth_operation", default=None)
_PHASE: ContextVar[str] = ContextVar("native_auth_phase", default="acquire")


@contextmanager
def effect_lock():
    fd = os.open(ROOT / "effects.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    auxiliary = os.open(ROOT / "privileged.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.close(auxiliary)
    token = None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        token = _LOCK.set(fd)
        yield
    finally:
        if token is not None:
            _LOCK.reset(token)
        os.close(fd)


def run_effect(argv, **kwargs):
    identity = _RUN.get()
    if identity is not None and argv[0] == "sudo":
        guardian = """import fcntl,json,os,signal,subprocess,sys
root,token,phase,*command=sys.argv[1:]
fd=os.open(root+'/privileged.lock',os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(fd,fcntl.LOCK_SH)
with open(root+'/'+token+'.json') as f: record=json.load(f)
if record.get('phase','acquire')!=phase: raise RuntimeError('stale authentication helper')
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,signal.SIG_IGN)
sys.exit(subprocess.run(command).returncode)
"""
        argv = [
            "sudo",
            "-n",
            sys.executable,
            "-c",
            guardian,
            str(ROOT),
            identity,
            _PHASE.get(),
            *argv,
        ]
    fd = _LOCK.get()
    if fd is not None:
        # This waiting process keeps the inherited lock even when sudo closes its copy.
        # After owner death recovery waits until every in-flight effect has settled.
        argv = [
            sys.executable,
            "-c",
            "import subprocess,sys; sys.exit(subprocess.run(sys.argv[1:]).returncode)",
            *argv,
        ]
        kwargs["pass_fds"] = (fd,)
    return subprocess.run(argv, **kwargs)


def pg(sql):
    identity = _RUN.get()
    return run_effect(
        [
            "sudo",
            "-n",
            "-u",
            "postgres",
            "env",
            "PGAPPNAME="
            + ("cs_native_auth_" + identity if identity else "cs_native_auth_recovery"),
            "PGCONNECT_TIMEOUT=5",
            "PGOPTIONS=-c statement_timeout=10000 -c lock_timeout=5000",
            "psql",
            "-XqAt",
            "-p",
            "5434",
            "-h",
            "/var/run/postgresql",
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def edit(path, line, add):
    # Atomic selective edits retain other owners' rows and the file's owner/mode.
    token = re.search(r"cs_reader_([0-9a-f]{32})", line)
    if token is None:
        raise ValueError("authentication edit requires an owned role token")
    temporary = path.parent / f".cs-native-auth-{token.group(1)}-{path.name}.new"
    script = """import os,sys,stat
p,line,add,tmp=sys.argv[1:]
if os.path.islink(p): raise RuntimeError('authentication file is a symlink')
s=os.stat(p)
if os.path.lexists(tmp):
 t=os.lstat(tmp)
 if not stat.S_ISREG(t.st_mode) or t.st_uid not in (0,s.st_uid):
  raise RuntimeError('unowned authentication edit temporary')
 os.unlink(tmp)
with open(p) as f: rows=f.read().splitlines()
if add=='1':
 if line in rows: raise RuntimeError('owned row already exists')
 rows.append(line)
else: rows=[r for r in rows if r!=line]
fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
try:
 os.fchmod(fd,stat.S_IMODE(s.st_mode)); os.fchown(fd,s.st_uid,s.st_gid)
 with os.fdopen(fd,'w') as f: f.write('\\n'.join(rows)+'\\n')
 os.replace(tmp,p)
finally:
 if os.path.exists(tmp): os.unlink(tmp)
"""
    run_effect(
        ["sudo", "-n", "python3", "-c", script, str(path), line, str(int(add)), str(temporary)],
        check=True,
        capture_output=True,
        text=True,
    )


def rows(role, database, operator):
    return (
        (CONF / "semantic_hba.conf", f"local {database} {role} peer map=corpus_semantic"),
        (CONF / "pg_ident.conf", f"corpus_semantic {operator} {role}"),
    )


def save(path, record):
    temporary = path.with_suffix(".new")
    with temporary.open("x") as stream:
        os.chmod(temporary, 0o600)
        json.dump(record, stream)
    temporary.replace(path)


def contains(path, line):
    result = run_effect(
        [
            "sudo",
            "-n",
            "python3",
            "-c",
            "import sys; print(int(sys.argv[2] in open(sys.argv[1]).read().splitlines()))",
            str(path),
            line,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "1"


def recover(path, cluster):
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise RuntimeError("unowned authentication journal")
    record = json.loads(path.read_text())
    role, token = record["role"], record["token"]
    database, operator = record["database"], record["operator"]
    if (
        record["cluster"] != cluster
        or re.fullmatch(r"cs_reader_[0-9a-f]{32}", role) is None
        or token != role.removeprefix("cs_reader_")
        or any(re.fullmatch(r"[a-z_][a-z0-9_-]*", n) is None for n in (database, operator))
    ):
        raise RuntimeError("authentication journal identity mismatch")
    # Fence helpers which were launched before owner death but have not begun effects.
    fd = os.open(ROOT / "privileged.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        path.with_suffix(".new").unlink(missing_ok=True)
        record["phase"] = "recover-" + os.urandom(16).hex()
        save(path, record)
    finally:
        os.close(fd)
    operation = _RUN.set(token)
    phase = _PHASE.set(record["phase"])
    try:
        _recover_effects(path, record)
    finally:
        _PHASE.reset(phase)
        _RUN.reset(operation)


def _recover_effects(path, record):
    role, token = record["role"], record["token"]
    database, operator = record["database"], record["operator"]
    stamp = f"corpus-structure native auth {token}"
    # A dead client/group can leave PostgreSQL finishing submitted SQL. Wait for that
    # operation's server backend before deciding whether its role was committed.
    deadline = time.monotonic() + 15
    while int(
        pg(
            "SELECT count(*) FROM pg_stat_activity WHERE pid<>pg_backend_pid() "
            f"AND application_name='cs_native_auth_{token}'"
        )
    ):
        if time.monotonic() >= deadline:
            raise RuntimeError("owned authentication backend has not settled")
        time.sleep(0.05)
    actual = pg(
        f"SELECT oid || ':' || COALESCE(shobj_description(oid,'pg_authid'),'') "
        f"FROM pg_roles WHERE rolname='{role}'"
    )
    if actual and actual.split(":", 1)[1] != stamp:
        raise RuntimeError("refusing unacknowledged alternate role")
    if (
        actual
        and record.get("role_oid") is not None
        and int(actual.split(":", 1)[0]) != record["role_oid"]
    ):
        raise RuntimeError("alternate role OID changed")
    failures = []
    for file, line in rows(role, database, operator):
        if file.name not in record.get("auth_rows", []):
            continue
        try:
            edit(file, line, False)
        except BaseException as error:
            failures.append(error)
    try:
        pg("SELECT pg_reload_conf()")
    except BaseException as error:
        failures.append(error)
    # Keep the role stamp while any authentication recovery remains outstanding.
    if not failures:
        try:
            if actual:
                pg(f'DROP ROLE "{role}"')
            path.unlink()
            path.with_suffix(".new").unlink(missing_ok=True)
        except BaseException as error:
            failures.append(error)
    if failures:
        raise BaseExceptionGroup("native authentication recovery failures", failures)


@contextmanager
def alternate_reader(server, database):
    endpoint = make_url(server.url)
    if endpoint.host is not None or dict(endpoint.query) != {
        "host": "/var/run/postgresql",
        "port": "5434",
    }:
        raise RuntimeError(
            "shared authentication adapter requires explicit 18/corpus socket target"
        )
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    if ROOT.is_symlink() or ROOT.stat().st_uid != os.getuid() or ROOT.stat().st_mode & 0o077:
        raise RuntimeError("native authentication journal root must be private and owned")
    with server.lease("cs_native_cluster_auth", exclusive=True), effect_lock():
        cluster = pg("SELECT system_identifier FROM pg_control_system()")
        for old in sorted(ROOT.glob("*.json")):
            recover(old, cluster)
        # A pre-publication temporary file cannot have authorized any server effect.
        for abandoned in ROOT.glob("*.new"):
            if (
                re.fullmatch(r"[0-9a-f]{32}\.new", abandoned.name)
                and not abandoned.is_symlink()
                and abandoned.stat().st_uid == os.getuid()
            ):
                abandoned.unlink()
        token = uuid4().hex
        role = "cs_reader_" + token
        operator = pwd.getpwuid(os.getuid()).pw_name
        if any(re.fullmatch(r"[a-z_][a-z0-9_-]*", n) is None for n in (database, operator)):
            raise ValueError("invalid alternate-principal coordinates")
        path = ROOT / f"{token}.json"
        save(
            path,
            dict(role=role, token=token, database=database, operator=operator, cluster=cluster),
        )
        operation = _RUN.set(token)
        failure = None
        try:
            # CREATE and ownership stamp commit atomically, including lost-ack recovery.
            pg(
                f"BEGIN; CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; "
                f"COMMENT ON ROLE {role} IS 'corpus-structure native auth {token}'; "
                f"GRANT corpus_sem_reader TO {role}; COMMIT;"
            )
            record = json.loads(path.read_text())
            record["role_oid"] = int(pg(f"SELECT oid FROM pg_roles WHERE rolname='{role}'"))
            record["auth_rows"] = []
            save(path, record)
            for file, line in rows(role, database, operator):
                if contains(file, line):
                    raise RuntimeError("authentication row predates owned edit")
                record["auth_rows"].append(file.name)
                save(path, record)
                edit(file, line, True)
            pg("SELECT pg_reload_conf()")
            yield role
        except BaseException as error:
            failure = error
            raise
        finally:
            try:
                try:
                    recover(path, cluster)
                except BaseException as cleanup:
                    if failure is not None:
                        raise BaseExceptionGroup(
                            "native authentication acquisition and recovery", [failure, cleanup]
                        ) from None
                    raise
            finally:
                _RUN.reset(operation)
