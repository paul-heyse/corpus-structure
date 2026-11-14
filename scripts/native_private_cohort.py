"""One pg_virtualenv host inside the existing qualification process supervisor (stdlib only)."""

from __future__ import annotations

import errno
import json
import os
import pwd
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_INPUTS = frozenset(
    {
        "CREATE_OPTS",
        "INITDB_OPTS",
        "PKGARGS",
        "PGCONF_OPTS",
        "NONROOT",
        "WORKDIR",
        "PWFILE",
        "LOGDIR",
        "PACKAGE",
        "EXIT",
        "run_shell",
        "ENABLE_COREDUMPS",
        "NOSYNC",
        "BASH_ENV",
        "ENV",
        "CDPATH",
        "IFS",
        "SHELLOPTS",
        "BASHOPTS",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "CORPUS_DATABASE",
        "CORPUS_DEPLOYMENT_DATABASE",
        "CORPUS_TEST_NATIVE_AUTH_CRASH",
        "PERL5OPT",
        "PERL5LIB",
        "PERLLIB",
        "PERL_LOCAL_LIB_ROOT",
        "PERL_MB_OPT",
        "PERL_MM_OPT",
    }
)


def private_environment(parent: dict[str, str], temporary: Path) -> dict[str, str]:
    """Normalize creation inputs before pg_virtualenv can consume inherited PGPORT."""
    env = {
        name: value
        for name, value in parent.items()
        if not name.startswith(
            ("PG", "_PG_", "BASH_FUNC_", "CORPUS_DATABASE__", "CORPUS_DEPLOYMENT_DATABASE__")
        )
        and name not in _SCRIPT_INPUTS
    }
    account = pwd.getpwuid(os.getuid()).pw_name
    env.update(
        USER=account, LOGNAME=account, TMPDIR=str(temporary), CORPUS_CI_NATIVE_HOST="private"
    )
    # pg_virtualenv delegates to system postgresql-common programs by name.
    env["PATH"] = os.pathsep.join(
        (
            str(Path(sys.executable).parent),
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        )
    )
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT / "scripts"), env.get("PYTHONPATH")))
    )
    return env


def private_command(
    directory: Path, payload: dict[str, Any], parent: dict[str, str]
) -> tuple[list[str], dict[str, str]]:
    base = ROOT / "build/tmp/private-postgresql"
    base.mkdir(parents=True, mode=0o700, exist_ok=True)
    if base.is_symlink() or base.stat().st_uid != os.getuid():
        raise ValueError("private PostgreSQL temporary root is not owned by this operator")
    temporary = Path(tempfile.mkdtemp(prefix="cohort-", dir=base))
    identity = temporary.stat()
    (directory / "private-host-owner.json").write_text(
        json.dumps(
            {
                "temporary": str(temporary),
                "uid": identity.st_uid,
                "inode": identity.st_ino,
                "state": "allocated",
                "published": "logs and sanitized metadata only",
            }
        )
        + "\n"
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    if port in {5432, 5434}:
        raise ValueError("private host selected a reserved shared port")
    payload = {
        **payload,
        "directory": str(directory),
        "port": port,
        "execution_path": parent.get("PATH", os.defpath),
    }
    (directory / "private-cohort.request.json").write_text(json.dumps(payload) + "\n")
    command = [
        "/usr/bin/pg_virtualenv",
        "-v",
        "18",
        "-t",
        "-c",
        f"--port {port}",
        "-o",
        "shared_preload_libraries=pg_textsearch,pg_stat_statements,auto_explain",
        "-o",
        "max_locks_per_transaction=1024",
        "-o",
        "log_parameter_max_length=0",
        "-o",
        "log_parameter_max_length_on_error=0",
        sys.executable,
        str(ROOT / "python/corpus-structure/tests/native_private_bootstrap.py"),
        str(directory / "private-cohort.request.json"),
    ]
    return command, private_environment(parent, temporary)


def stop_private_cohort(
    child: subprocess.Popen[bytes], directory: Path, stop_group
) -> dict[str, Any]:
    """Cancel the authenticated inner owner before permitting host trap cleanup.

    The pg_virtualenv shell stays alive while the inner owner drains its separate pytest
    group and copies logs. Unknown settlement is retained as live custody, not a host drop.
    """
    result: dict[str, Any] = {"group": child.pid, "signals": []}
    deadline = time.monotonic() + 30
    notified = False
    while child.poll() is None and time.monotonic() < deadline:
        if not notified:
            try:
                with (directory / "private-cohort.inner.json").open() as stream:
                    inner = json.load(stream)
                pid = inner["pid"]
                # A pidfd holds identity through signalling; its recorded parent must
                # still be our owned pg_virtualenv child, not a reused unrelated PID.
                descriptor = os.pidfd_open(pid)
                try:
                    parent = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
                    if parent != child.pid or inner["parent_pid"] != child.pid:
                        raise ValueError("private inner process is outside its owned host")
                    signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                    result["signals"].append("SIGTERM authenticated bootstrap")
                    notified = True
                finally:
                    os.close(descriptor)
            except FileNotFoundError, ProcessLookupError:
                pass
        with suppress(subprocess.TimeoutExpired):
            child.wait(timeout=0.1)
    if child.poll() is None:
        return {
            **result,
            "group_present_after_cleanup": True,
            "private_host_settlement": "unconfirmed; host retained until inner children settle",
        }
    stopped = stop_group(child)
    return {
        **stopped,
        "signals": [*result["signals"], *stopped.get("signals", ())],
        "private_host_settlement": "host exited; inner outcome retained separately",
    }


def finish_private_temporary(directory: Path, process: dict[str, Any]) -> dict[str, Any]:
    """Remove only an acknowledged empty owned root; leave uncertain data outside artifacts."""
    owner_path = directory / "private-host-owner.json"
    owner = json.loads(owner_path.read_text())
    temporary = Path(owner["temporary"])
    uncertain = bool(
        process.get("cleanup_error")
        or (process.get("owned_group_cleanup") or {}).get("group_present_after_cleanup")
        or (process.get("pid") is not None and process.get("returncode") is None)
    )
    if uncertain:
        outcome = {"state": "retained", "reason": "owned cohort process settlement is unconfirmed"}
    else:
        identity = temporary.lstat()
        if temporary.is_symlink() or (identity.st_uid, identity.st_ino) != (
            owner["uid"],
            owner["inode"],
        ):
            raise ValueError("private PostgreSQL temporary ownership changed")
        try:
            temporary.rmdir()
        except OSError as error:
            if error.errno not in {errno.ENOTEMPTY, errno.EEXIST}:
                raise
            outcome = {"state": "retained", "reason": "pg_virtualenv left owned temporary residue"}
        else:
            outcome = {"state": "removed"}
    owner_path.write_text(json.dumps({**owner, **outcome}) + "\n")
    return outcome
