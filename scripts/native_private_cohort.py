"""One pg_virtualenv host inside the existing qualification process supervisor (stdlib only)."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import pwd
import re
import signal
import socket
import stat
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
        # Match the deployed short-query/bulk-write policy in corpus.conf.
        "jit=off",
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
    """Remove only an acknowledged owned empty directory tree after settlement."""
    owner_path = directory / "private-host-owner.json"
    owner = json.loads(owner_path.read_text())
    uncertain = bool(
        process.get("cleanup_error")
        or (process.get("owned_group_cleanup") or {}).get("group_present_after_cleanup")
        or (process.get("pid") is not None and process.get("returncode") is None)
    )
    if uncertain:
        outcome = {"state": "retained", "reason": "owned cohort process settlement is unconfirmed"}
    else:
        outcome = _remove_owned_empty_tree(owner)
    owner_path.write_text(json.dumps({**owner, **outcome}) + "\n")
    return outcome


def _remove_owned_empty_tree(
    owner: dict[str, Any], *, recover_selected_scratch: bool = False
) -> dict[str, Any]:
    """Remove empty directories, plus known SQLite scratch only after recovery drain."""
    temporary = Path(owner["temporary"])
    base = ROOT / "build/tmp/private-postgresql"
    if temporary.parent != base or base.is_symlink() or base.stat().st_uid != os.getuid():
        raise ValueError("private PostgreSQL temporary root differs from its owned location")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with_owner = (owner["uid"], owner["inode"])
    identity = temporary.lstat()
    if (
        not stat.S_ISDIR(identity.st_mode)
        or (identity.st_uid, identity.st_ino) != with_owner
        or identity.st_uid != os.getuid()
    ):
        raise ValueError("private PostgreSQL temporary ownership changed")
    root = os.open(temporary, flags)
    try:
        if os.fstat(root) != identity:
            raise ValueError("private PostgreSQL temporary ownership changed")

        def inspect_tree(fd, *, selected_scratch=False, top=False):
            children = []
            for name in os.listdir(fd):
                found = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if (
                    selected_scratch
                    and name in {"support.sqlite", "support.sqlite-journal"}
                    and stat.S_ISREG(found.st_mode)
                    and found.st_uid == owner["uid"]
                    and found.st_dev == identity.st_dev
                    and found.st_nlink == 1
                ):
                    children.append((name, found, None))
                    continue
                if (
                    not stat.S_ISDIR(found.st_mode)
                    or found.st_uid != owner["uid"]
                    or found.st_dev != identity.st_dev
                ):
                    raise ValueError(
                        "private temporary residue contains data, a symlink or a foreign directory"
                    )
                child = os.open(name, flags, dir_fd=fd)
                try:
                    if os.fstat(child) != found:
                        raise ValueError("private temporary directory changed during inspection")
                    scratch = bool(
                        recover_selected_scratch
                        and top
                        and re.fullmatch(r"selected-read-[a-z0-9_]{8}", name)
                    )
                    children.append(
                        (name, found, inspect_tree(child, selected_scratch=scratch))
                    )
                finally:
                    os.close(child)
            return children

        def remove_tree(fd, children):
            for name, found, descendants in children:
                if descendants is None:
                    actual = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    if (
                        not stat.S_ISREG(actual.st_mode)
                        or actual.st_nlink != 1
                        or (actual.st_dev, actual.st_ino, actual.st_uid)
                        != (found.st_dev, found.st_ino, found.st_uid)
                    ):
                        raise ValueError("private temporary scratch changed before removal")
                    os.unlink(name, dir_fd=fd)
                    continue
                child = os.open(name, flags, dir_fd=fd)
                try:
                    actual = os.fstat(child)
                    if (actual.st_dev, actual.st_ino, actual.st_uid) != (
                        found.st_dev,
                        found.st_ino,
                        found.st_uid,
                    ):
                        raise ValueError("private temporary directory changed before removal")
                    remove_tree(child, descendants)
                    if os.stat(name, dir_fd=fd, follow_symlinks=False).st_ino != actual.st_ino:
                        raise ValueError("private temporary directory changed before removal")
                    os.rmdir(name, dir_fd=fd)
                finally:
                    os.close(child)

        try:
            children = inspect_tree(root, top=True)
            remove_tree(root, children)
            latest = temporary.lstat()
            if (latest.st_dev, latest.st_ino, latest.st_uid) != (
                identity.st_dev,
                identity.st_ino,
                identity.st_uid,
            ):
                raise ValueError("private PostgreSQL temporary ownership changed")
            temporary.rmdir()
        except (OSError, ValueError) as error:
            if isinstance(error, OSError) and error.errno not in {
                errno.ENOTEMPTY,
                errno.EEXIST,
                errno.ELOOP,
                errno.ENOTDIR,
                errno.ENOENT,
            }:
                raise
            return {"state": "retained", "reason": "pg_virtualenv left owned temporary residue"}
    finally:
        os.close(root)
    return {"state": "removed"}


_RECOVERY = "private-host-cleanup-recovery.json"
_RESIDUE_ERROR = "private PostgreSQL ownership remains unconfirmed"


def _owned_json_bytes(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        identity = os.fstat(stream.fileno())
        if not stat.S_ISREG(identity.st_mode) or identity.st_uid != os.getuid():
            raise ValueError("private recovery receipt is not an owned regular file")
        return stream.read()


def _private_recovery_sources(directory: Path):
    names = {
        "private-cohort.process.json",
        "private-host-owner.json",
        "private-host-child-settlement.json",
    }
    names.update(path.name for path in directory.glob("*.process.json"))
    contents = {name: _owned_json_bytes(directory / name) for name in sorted(names)}
    decoded = {name: json.loads(value) for name, value in contents.items()}
    if any(not isinstance(value, dict) for value in decoded.values()):
        raise ValueError("private recovery receipts must contain objects")
    return {name: hashlib.sha256(value).hexdigest() for name, value in contents.items()}, decoded


def _require_private_drain(original):
    process = original["private-cohort.process.json"]
    children = original["private-host-child-settlement.json"]
    if (
        process.get("cleanup_error") != _RESIDUE_ERROR
        or not process.get("finished")
        or type(process.get("returncode")) is not int
        or process.get("private_temporary_cleanup", {}).get("reason")
        != "pg_virtualenv left owned temporary residue"
        or process.get("owned_group_cleanup", {}).get("group_present_after_cleanup") is not False
        or process.get("owned_group_cleanup", {}).get("descendants_after_leader_exit") is True
        or children.get("state") != "settled"
        or children.get("pending") != {}
    ):
        raise ValueError(
            "private cohort has no acknowledged temporary-only cleanup failure and drained children"
        )
    groups = [process.get("owned_group_cleanup", {}).get("group")]
    if not children.get("owned_groups"):
        raise ValueError("private cohort child identities are unavailable")
    recorded = {f"{name}.process.json" for name in children["owned_groups"]}
    actual = {name for name in original if name.endswith(".process.json")} - {
        "runner.process.json",
        "private-cohort.process.json",
    }
    if recorded != actual:
        raise ValueError("private cohort child inventory is incomplete")
    for name, group in children["owned_groups"].items():
        child = original[f"{name}.process.json"]
        cleanup = child.get("owned_group_cleanup", {})
        if (
            not child.get("finished")
            or child.get("cleanup_error")
            or cleanup.get("group_present_after_cleanup") is not False
            or cleanup.get("descendants_after_leader_exit") is True
            or cleanup.get("group") != group
        ):
            raise ValueError(
                "private cohort child settlement differs from its original process receipt"
            )
        groups.append(group)
    if any(type(group) is not int or group <= 0 for group in groups):
        raise ValueError("private cohort process identities are unavailable")
    for group in groups:
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            continue
        raise ValueError("private cohort process group is still present or ownership is uncertain")


def recovered_private_process(directory: Path, process: dict[str, Any]) -> dict[str, Any]:
    """Read a validated later cleanup observation; original process facts stay intact."""
    path = directory / _RECOVERY
    if not path.exists():
        return process
    sources, original = _private_recovery_sources(directory)
    recovered = json.loads(_owned_json_bytes(path))
    _require_private_drain(original)
    if process != original["private-cohort.process.json"]:
        raise ValueError("private recovery process differs from its original receipt")
    if (
        recovered.get("sources") != sources
        or recovered.get("cleanup") != {"state": "removed"}
        or os.path.lexists(original["private-host-owner.json"]["temporary"])
    ):
        raise ValueError(
            "private temporary recovery differs from original custody or current absence"
        )
    return {
        **process,
        "cleanup_error": None,
        "private_temporary_cleanup": recovered["cleanup"],
        "cleanup_recovery": recovered,
    }


def recover_private_temporary(directory: Path) -> dict[str, Any]:
    """Retry the one acknowledged cleanup; never rewrite the interrupted process receipt."""
    sources, original = _private_recovery_sources(directory)
    process = original["private-cohort.process.json"]
    if (directory / _RECOVERY).exists():
        return recovered_private_process(directory, process)["cleanup_recovery"]
    _require_private_drain(original)
    outcome = _remove_owned_empty_tree(
        original["private-host-owner.json"], recover_selected_scratch=True
    )
    if outcome["state"] != "removed":
        raise ValueError("private temporary residue remains nonempty or ownership is uncertain")
    observation = {
        "sources": sources,
        "cleanup": outcome,
        "recovered_at": time.time(),
        "original_cleanup_error": process["cleanup_error"],
        "original_interruption": process.get("interruption"),
    }
    with (directory / _RECOVERY).open("x") as stream:
        stream.write(json.dumps(observation, indent=2, sort_keys=True) + "\n")
    return observation
