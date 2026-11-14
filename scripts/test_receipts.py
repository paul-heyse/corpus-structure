"""Run qualification with durable native artifacts, or classify existing receipts (stdlib only).

SP-10 owns required selections and applicability. This module records what actually ran; it
never interprets the number of skips as provider coverage or invents an assertion for a crash.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SESSION_TIMEOUT = 14400
TEST_TIMEOUT = 900


@dataclass
class RunControl:
    """One invocation's sticky cancellation; signal handlers never interrupt cleanup."""

    started: float = field(default_factory=time.time)
    interruption: str | None = None
    interrupted_at: float | None = None
    signals: list[str] = field(default_factory=list)

    def cancel(self, reason: str) -> None:
        if self.interruption is None:
            self.interruption = reason
            self.interrupted_at = time.time()

    def signal(self, number: int, _frame: object) -> None:
        name = signal.Signals(number).name
        self.signals.append(name)
        self.cancel(name)

    def persist(self, directory: Path) -> None:
        write_json(
            directory / "runner.process.json",
            {
                "pid": os.getpid(),
                "started": self.started,
                "finished": time.time(),
                "interruption": self.interruption,
                "interrupted_at": self.interrupted_at,
                "signals": self.signals,
            },
        )


_CONTROL: ContextVar[RunControl | None] = ContextVar("qualification_control", default=None)


@contextmanager
def supervision(directory: Path) -> Generator[RunControl]:
    existing = _CONTROL.get()
    if existing is not None:
        yield existing
        return
    control = RunControl()
    token = _CONTROL.set(control)
    previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        for number in previous:
            signal.signal(number, control.signal)
        yield control
    finally:
        try:
            control.persist(directory)
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
            _CONTROL.reset(token)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


@contextmanager
def _open_receipt(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f"receipt entry is not a regular file: {path.name}")
        yield stream


def read_json(path: Path) -> dict[str, Any]:
    with _open_receipt(path) as stream:
        return json.load(stream)


def read_stream(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        with _open_receipt(path) as stream:
            for index, line in enumerate(stream, 1):
                try:
                    data = json.loads(line)
                    if not isinstance(data, dict):
                        raise ValueError("event must be an object")
                    events.append(data)
                except ValueError as error:
                    errors.append(f"{path.name}:{index}: {error}")
                if not line.endswith("\n"):
                    errors.append(f"{path.name}:{index}: truncated line")
    except FileNotFoundError:
        return events, [f"missing stream: {path.name}"]
    return events, errors


def run_process(
    argv: list[str],
    directory: Path,
    prefix: str,
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout: float = SESSION_TIMEOUT,
    group_cleanup: Callable[[subprocess.Popen[bytes]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bound the owned process group; never signal application/database processes by name."""
    with supervision(directory) as control:
        return _run_process(
            argv,
            directory,
            prefix,
            control,
            cwd=cwd,
            env=env,
            timeout=timeout,
            group_cleanup=group_cleanup,
        )


def _run_process(
    argv: list[str],
    directory: Path,
    prefix: str,
    control: RunControl,
    *,
    cwd: Path,
    env: dict[str, str] | None,
    timeout: float,
    group_cleanup: Callable[[subprocess.Popen[bytes]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "argv": argv,
        "cwd": str(cwd),
        "timeout_seconds": timeout,
        "started": time.time(),
    }
    child: subprocess.Popen[bytes] | None = None
    try:
        if control.interruption is not None:
            result["interruption"] = control.interruption
            result["cancelled"] = True
            result["returncode"] = None
            return result
        with (
            (directory / f"{prefix}.stdout").open("xb") as stdout,
            (directory / f"{prefix}.stderr").open("xb") as stderr,
        ):
            child = subprocess.Popen(
                argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True
            )
            result["pid"] = child.pid
            deadline = time.monotonic() + timeout
            while child.poll() is None and control.interruption is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    result["interruption"] = "TimeoutExpired"
                    break
                with suppress(subprocess.TimeoutExpired):
                    child.wait(timeout=min(0.1, remaining))
            if control.interruption is not None:
                result["interruption"] = control.interruption
    except OSError as error:
        result["launch_error"] = str(error)
        result["returncode"] = None
    finally:
        if child is not None:
            # Always settle the authenticated start_new_session group, including abrupt exits.
            try:
                result["owned_group_cleanup"] = (group_cleanup or _stop_group)(child)
            except Exception as error:
                result["cleanup_error"] = f"{type(error).__name__}: {error}"
                control.cancel("owned process group cleanup failed")
            result["returncode"] = child.poll()
            if (result.get("owned_group_cleanup") or {}).get("group_present_after_cleanup"):
                control.cancel("owned process group remains after cleanup")
        if control.interruption is not None:
            result["interruption"] = control.interruption
            result["cancelled"] = True
        result["finished"] = time.time()
        write_json(directory / f"{prefix}.process.json", result)
    return result


def _group_present(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    return True


def _stop_group(child: subprocess.Popen[bytes]) -> dict[str, Any]:
    leader_exited = child.poll() is not None
    present = _group_present(child.pid)
    result: dict[str, Any] = {
        "group": child.pid,
        "descendants_after_leader_exit": leader_exited and present,
        "signals": [],
    }
    if present:
        with suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGTERM)
            result["signals"].append("SIGTERM")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _group_present(child.pid):
            child.poll()  # Reap the leader while allowing descendants bounded TERM grace.
            time.sleep(0.05)
        if _group_present(child.pid):
            with suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
                result["signals"].append("SIGKILL")
    child.wait(timeout=5)
    result["group_present_after_cleanup"] = _group_present(child.pid)
    return result


def _git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def _file_hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def source_identity() -> dict[str, Any]:
    untracked = _git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    return {
        "head": _git("rev-parse", "HEAD").decode().strip(),
        "status": _git("status", "--porcelain=v1").decode(),
        "tracked_diff_sha256": hashlib.sha256(_git("diff", "HEAD", "--binary")).hexdigest(),
        "untracked_sha256": {
            name: _file_hash(ROOT / name) for name in untracked if name and (ROOT / name).is_file()
        },
    }


_INVOCATION_PACKAGES = (
    "pytest",
    "pytest-xdist",
    "pytest-reportlog",
    "hypothesis",
    "psycopg",
    "SQLAlchemy",
)


def invocation_context(native_host: str = "shared") -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    for package in _INVOCATION_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "source": source_identity(),
        "python": sys.version,
        "versions": versions,
        "native_host": native_host,
    }


def native_bindings(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize physical routes and roles without repeating isolated databases per node."""
    bindings = {}
    for event in events:
        context = event.get("context")
        if not isinstance(context, dict):
            continue
        acquired = context.get("acquired")
        requested = context.get("requested")
        if not isinstance(acquired, dict) or not isinstance(requested, dict):
            continue
        binding = {
            key: acquired.get(key)
            for key in (
                "host",
                "port",
                "server_started",
                "server_version",
                "current_user",
                "session_user",
                "revision",
                "policy_ref",
            )
        }
        binding["purpose"] = requested.get("purpose")
        bindings[json.dumps(binding, sort_keys=True)] = binding
    return [bindings[key] for key in sorted(bindings)]


def run_python(
    directory: Path,
    args: list[str],
    *,
    timeout: float = SESSION_TIMEOUT,
    test_timeout: float = TEST_TIMEOUT,
    cwd: Path = ROOT,
    managed: bool = False,
    evidence_selection: str | None = None,
    native_host: str = "shared",
    python_only: bool = True,
) -> dict[str, Any]:
    if native_host not in {"shared", "private"}:
        raise ValueError("unknown native host mode")
    if native_host == "private" and "--collect-only" not in args:
        from native_private_cohort import (
            finish_private_temporary,
            private_command,
            stop_private_cohort,
        )

        command, environment = private_command(
            directory,
            {
                "pytest_args": args,
                "timeout": timeout,
                "test_timeout": test_timeout,
                "cwd": str(cwd),
                "managed": managed,
                "evidence_selection": evidence_selection,
                "python_only": python_only,
            },
            dict(os.environ),
        )
        process = run_process(
            command,
            directory,
            "private-cohort",
            cwd=cwd,
            env=environment,
            timeout=timeout,
            group_cleanup=lambda child: stop_private_cohort(child, directory, _stop_group),
        )
        try:
            process["private_temporary_cleanup"] = finish_private_temporary(directory, process)
            if process["private_temporary_cleanup"]["state"] != "removed":
                process["cleanup_error"] = "private PostgreSQL ownership remains unconfirmed"
        except (OSError, ValueError) as error:
            process["cleanup_error"] = f"private temporary ownership: {error}"
        write_json(directory / "private-cohort.process.json", process)
        invocation_path = directory / "invocation.json"
        if invocation_path.is_file():
            invocation = read_json(invocation_path)
            child_path = directory / "private-host-child-settlement.json"
            invocation["native_host_lifecycle"] = {
                "process_returncode": process.get("returncode"),
                "interruption": process.get("interruption"),
                "owned_group_cleanup": process.get("owned_group_cleanup"),
                "temporary_cleanup": process.get("private_temporary_cleanup"),
                "child_settlement": read_json(child_path) if child_path.is_file() else None,
                "logs": sorted(
                    str(path.relative_to(directory))
                    for path in (directory / "private-host-logs").glob("*.log")
                ),
            }
            write_json(invocation_path, invocation)
        return process
    env = dict(os.environ)
    if native_host == "private":
        env["CORPUS_CI_NATIVE_HOST"] = "private"
    if managed:
        for name in (
            "PYTEST_ADDOPTS",
            "PYTEST_PLUGINS",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
            "PYTEST_XDIST_AUTO_NUM_WORKERS",
        ):
            env.pop(name, None)
    # A fresh pytest session owns its worker identity; nested xdist workers set theirs.
    for name in ("PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "PYTEST_XDIST_TESTRUNUID"):
        env.pop(name, None)
    env["QUALIFICATION_RECEIPT_DIR"] = str(directory)
    env["HYPOTHESIS_PROFILE"] = "ci"
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT / "scripts"), env.get("PYTHONPATH")])
    )
    argv = [
        sys.executable,
        "-m",
        "pytest",
        *args,
        *(
            ["--qualification-evidence", evidence_selection]
            if evidence_selection is not None
            else []
        ),
        "-p",
        "qualification_plugin",
        "--report-log",
        str(directory / "reportlog.jsonl"),
        "--junitxml",
        str(directory / "pytest.junit.xml"),
        "-rA",
        "--hypothesis-profile=ci",
        "-o",
        f"faulthandler_timeout={test_timeout}",
        "-o",
        "faulthandler_exit_on_timeout=true",
    ]
    return run_process(argv, directory, "pytest", cwd=cwd, env=env, timeout=timeout)


def run_rust(directory: Path, *, timeout: float = SESSION_TIMEOUT) -> None:
    for prefix, argv in (
        ("rustc", ["rustc", "--version"]),
        ("nextest-version", ["cargo", "nextest", "--version"]),
        (
            "nextest-list",
            ["cargo", "nextest", "list", "--release", "--workspace", "--message-format", "json"],
        ),
    ):
        process = run_process(argv, directory, prefix, timeout=timeout)
        if _cancelled(process):
            write_json(
                directory / "rust-state.json",
                {
                    "status": "incomplete",
                    "applicability": "unknown",
                    "functional_coverage": False,
                    "reason": "cancelled before Rust test execution",
                },
            )
            return
    try:
        listing = read_json(directory / "nextest-list.stdout")
        target = Path(listing["rust-build-meta"]["target-directory"]).resolve()
    except (OSError, ValueError, KeyError, TypeError) as error:
        _rust_report_unavailable(
            directory, f"nextest target directory could not be established: {error}"
        )
        return
    junit = target / "nextest" / "qualification" / "junit.xml"
    junit.parent.mkdir(parents=True, exist_ok=True)
    with supervision(directory) as control, (junit.parent / ".junit.lock").open("a") as lock:
        deadline = time.monotonic() + timeout
        while not control.interruption:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    _rust_report_unavailable(
                        directory, "timed out waiting for the nextest report lock"
                    )
                    return
                time.sleep(0.05)
        else:
            _rust_report_unavailable(
                directory, control.interruption or "nextest lock wait interrupted"
            )
            return
        # Hold the lock through copy so another invocation cannot replace this report
        # between nextest exiting and receipt capture.
        before = junit.stat().st_mtime_ns if junit.exists() else None
        run_process(
            [
                "cargo",
                "nextest",
                "run",
                "--release",
                "--workspace",
                "--profile",
                "qualification",
                "--no-tests=warn",
            ],
            directory,
            "nextest",
            env={**os.environ, "INSTA_UPDATE": "no"},
            timeout=timeout,
        )
        if junit.exists() and junit.stat().st_mtime_ns != before:
            shutil.copyfile(junit, directory / "nextest.junit.xml")


def _rust_report_unavailable(directory: Path, reason: str) -> None:
    write_json(
        directory / "rust-state.json",
        {
            "status": "incomplete",
            "applicability": "unknown",
            "functional_coverage": False,
            "reason": reason,
        },
    )


def _cancelled(process: dict[str, Any]) -> bool:
    control = _CONTROL.get()
    return (
        bool(control and control.interruption)
        or bool(process.get("cancelled"))
        or process.get("interruption")
        in {
            "KeyboardInterrupt",
            "SIGINT",
            "SIGTERM",
        }
    )


def _properties(reports: list[dict[str, Any]]) -> dict[str, Any]:
    properties = {}
    prerequisites = []
    for report in reports:
        for key, value in report.get("user_properties", []):
            if key == "qualification_prerequisites":
                for entry in value:
                    if entry not in prerequisites:
                        prerequisites.append(entry)
            else:
                properties[key] = value
    if prerequisites:
        properties["qualification_prerequisites"] = prerequisites
    return properties


def _prerequisites(properties: dict[str, Any]) -> list[dict[str, str]]:
    entries = list(properties.get("qualification_prerequisites", []))
    if "qualification_prerequisite" in properties:
        legacy = {
            "name": properties["qualification_prerequisite"],
            "reason": properties.get("qualification_reason", "external prerequisite unavailable"),
        }
        if legacy not in entries:
            entries.append(legacy)
    return entries


def _failed_prerequisite(report: dict[str, Any]) -> bool:
    return report.get("when") == "setup" and bool(_prerequisites(_properties([report])))


def _node_status(
    reports: list[dict[str, Any]], started: bool, finished: bool, *, provider_required: bool = False
) -> dict[str, Any]:
    properties = _properties(reports)
    failed = [report for report in reports if report.get("outcome") == "failed"]
    skipped = [report for report in reports if report.get("outcome") == "skipped"]
    successful_phases = {
        report.get("when") for report in reports if report.get("outcome") == "passed"
    }
    reason: object = None
    if failed:
        # A prerequisite annotates the failed setup itself, not an unrelated teardown failure.
        unexpected = [report for report in failed if not _failed_prerequisite(report)]
        status = "failed" if unexpected else "blocked"
        reason = properties.get("qualification_reason")
    elif (started or reports) and not finished:
        status = "incomplete"
    elif skipped:
        status = (
            "inapplicable"
            if properties.get("qualification_optional") and not provider_required
            else "blocked"
        )
        reason = properties.get("qualification_reason") or skipped[0].get("longrepr")
    elif {"setup", "call", "teardown"} <= successful_phases and finished:
        status = "passed"
    elif started or reports:
        status = "incomplete"
    else:
        status = "not_run"
    return {"status": status, "reason": reason, "properties": properties, "reports": reports}


def _complete_native_context(event: dict[str, Any]) -> bool:
    """Complete item-bound acquisition identity, not deployment/policy reproducibility.

    Revision, policy and scenario metadata are optional observations. A bare bootstrap or
    historical migration acquisition can legitimately have none of them.
    """
    if event.get("scope") != "test" or not isinstance(event.get("nodeid"), str):
        return False
    context = event.get("context")
    if not isinstance(context, dict) or context.get("schema") != "native-context/v1":
        return False
    requested, acquired = context.get("requested"), context.get("acquired")
    provenance = context.get("provenance")
    if not isinstance(requested, dict) or not isinstance(acquired, dict):
        return False
    if not isinstance(provenance, dict) or provenance.get("complete") is not True:
        return False
    if provenance.get("missing") != []:
        return False
    database_oid = acquired.get("database_oid")
    principal = acquired.get("current_user")
    login = acquired.get("session_user")
    host = acquired.get("host")
    port = acquired.get("port")
    server_started = acquired.get("server_started")
    server_version = acquired.get("server_version")
    database = acquired.get("database")
    if isinstance(port, str) and port.isdecimal():
        port = int(port)
    return (
        isinstance(database_oid, int)
        and not isinstance(database_oid, bool)
        and database_oid > 0
        and isinstance(principal, str)
        and bool(principal.strip())
        and isinstance(login, str)
        and bool(login.strip())
        and isinstance(host, str)
        and bool(host.strip())
        and isinstance(port, int)
        and not isinstance(port, bool)
        and 1 <= port <= 65535
        and isinstance(server_started, str)
        and bool(server_started.strip())
        and isinstance(server_version, str)
        and bool(server_version.strip())
        and isinstance(database, str)
        and bool(database.strip())
    )


def _group_cleanup_errors(process: dict[str, Any]) -> list[str]:
    """Shared owned-group settlement requirements for Python and Rust process artifacts."""
    cleanup = process.get("owned_group_cleanup", {})
    errors = []
    if process.get("cleanup_error"):
        errors.append("owned process group cleanup failed")
    if cleanup.get("descendants_after_leader_exit"):
        errors.append("owned descendants survived the process leader exit")
    if cleanup.get("group_present_after_cleanup"):
        errors.append("owned process group still present after bounded cleanup")
    return errors


def _group_unsettled(process: dict[str, Any]) -> bool:
    cleanup = process.get("owned_group_cleanup") or {}
    return bool(process.get("cleanup_error") or cleanup.get("group_present_after_cleanup"))


def _manifest_evidence_selection(manifest: dict[str, Any]) -> str:
    mode = manifest.get("evidence_selection", "ordinary")
    if mode not in {"ordinary", "providers"}:
        raise ValueError("invalid evidence selection")
    providers = manifest.get("provider_evidence", [])
    if not isinstance(providers, list) or not all(isinstance(node, str) for node in providers):
        raise ValueError("invalid provider-evidence identities")
    selected = set(manifest["selected"])
    if len(providers) != len(set(providers)) or not set(providers) <= selected:
        raise ValueError("provider-evidence identities are outside selected manifest")
    if mode == "providers" and set(providers) != selected:
        raise ValueError("provider selection includes identities without provider evidence")
    if mode == "ordinary" and providers:
        raise ValueError("ordinary selection includes provider evidence")
    return mode


def _node_aliases(manifests: list[dict[str, Any]]) -> dict[str, str]:
    """Validate exact collected identities, including historical partial alias maps."""
    aliases: dict[str, str] = {}
    for manifest in manifests:
        mapping = manifest.get("nodeid_aliases", {})
        selected = manifest["selected"]
        if not isinstance(selected, (list, tuple)) or not all(isinstance(n, str) for n in selected):
            raise ValueError("invalid selected-node manifest")
        if len(selected) != len(set(selected)):
            raise ValueError("duplicate selected node identity")
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and k and v for k, v in mapping.items()
        ):
            raise ValueError("invalid node identity map")
        if set(mapping) - set(selected):
            raise ValueError("node identity map includes unselected identities")
        inverse: dict[str, str] = {}
        for raw in selected:
            logical = mapping.get(raw, raw)
            if logical in inverse and inverse[logical] != raw:
                raise ValueError(f"colliding collected node identity: {logical}")
            inverse[logical] = raw
            if raw in aliases and aliases[raw] != logical:
                raise ValueError(f"conflicting worker node identity for {raw}")
            aliases[raw] = logical
        if not set(manifest.get("native_required", [])).issubset(selected):
            raise ValueError("native-required nodes are outside selected manifest")
        _manifest_evidence_selection(manifest)
        if manifest.get("native_host", "shared") not in {"shared", "private"}:
            raise ValueError("invalid native host mode in collection manifest")
    return aliases


def _required_manifests(paths: list[Path]) -> list[dict[str, Any]]:
    manifests = []
    for path in paths:
        if not path.is_dir() and path.suffix != ".jsonl":
            manifests.append(read_json(path))
            continue
        found = []
        streams = sorted(path.glob("events-*.jsonl")) if path.is_dir() else [path]
        for stream in streams:
            events, errors = read_stream(stream)
            if errors:
                raise ValueError("; ".join(errors))
            found.extend(event for event in events if event.get("event") == "collection_finish")
        if not found:
            raise ValueError(f"no collection manifest: {path}")
        if len({tuple(sorted(item["selected"])) for item in found}) > 1:
            raise ValueError(f"workers disagree on selected identities: {path}")
        manifests.extend(found)
    return manifests


def classify_receipt(directory: Path) -> dict[str, Any]:
    reports, errors = read_stream(directory / "reportlog.jsonl")
    companion: list[dict[str, Any]] = []
    streams = sorted(directory.glob("events-*.jsonl"))
    if not streams:
        errors.append("missing companion stream")
    for path in streams:
        events, problems = read_stream(path)
        companion.extend(events)
        errors.extend(problems)
    selection_refusals = [
        event["message"]
        for event in companion
        if event.get("event") == "selection_refusal" and isinstance(event.get("message"), str)
    ]
    errors.extend(selection_refusals)
    # loadgroup appends scheduler-only suffixes. Retain raw reportlog unchanged while
    # comparing the original pytest identities with earlier required-node manifests.
    identity_valid = True
    invocation = (
        read_json(directory / "invocation.json")
        if (directory / "invocation.json").exists()
        else None
    )
    evidence_selection = (invocation or {}).get("evidence_selection", "ordinary")
    collection_manifests: list[dict[str, Any]] = []
    try:
        collection_manifests = [e for e in companion if e.get("event") == "collection_finish"]
        if not collection_manifests:
            raise ValueError("missing selected-node manifest")
        aliases = _node_aliases(collection_manifests)
        hosts = {manifest.get("native_host", "shared") for manifest in collection_manifests}
        hosts.add((invocation or {}).get("native_host", "shared"))
        if len(hosts) != 1:
            raise ValueError("invocation or workers disagree on native host mode")
        modes = {_manifest_evidence_selection(manifest) for manifest in collection_manifests}
        if invocation and "evidence_selection" in invocation:
            modes.add(invocation["evidence_selection"])
        if len(modes) != 1:
            raise ValueError("invocation or workers disagree on evidence selection")
        evidence_selection = modes.pop()
        if len({tuple(sorted(e["selected"])) for e in collection_manifests}) > 1:
            raise ValueError("workers disagree on selected scheduled identities")
    except (ValueError, TypeError, KeyError) as error:
        errors.append(f"invalid collection identity: {error}")
        identity_valid = False
        aliases = {}
    for event in [*companion, *reports]:
        if "nodeid" in event:
            event["nodeid"] = aliases.get(event["nodeid"], event["nodeid"])
        for key in ("selected", "native_required", "provider_evidence", "nodes"):
            if key in event:
                event[key] = [aliases.get(node, node) for node in event[key]]
    group_observations: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    group_metadata_complete = bool(collection_manifests)
    for manifest in collection_manifests:
        groups = manifest.get("affinity_groups")
        if not isinstance(groups, dict):
            group_metadata_complete = False
            continue
        for raw, values in groups.items():
            if (
                not isinstance(raw, str)
                or not isinstance(values, list)
                or not all(isinstance(value, str) for value in values)
            ):
                group_metadata_complete = False
                continue
            group_observations[aliases.get(raw, raw)].add(tuple(sorted(set(values))))
    observed_workers: dict[str, set[str]] = defaultdict(set)
    for event in companion:
        if (
            event.get("event") == "phase_start"
            and isinstance(event.get("nodeid"), str)
            and isinstance(event.get("worker"), str)
        ):
            observed_workers[event["nodeid"]].add(event["worker"])
    selected: set[str] = set()
    deselected: set[str] = set()
    starts: set[str] = set()
    finishes: set[str] = set()
    active: dict[str, dict[str, Any]] = {}
    manifests = 0
    worker_loss = []
    native_required: set[str] = set()
    native_metadata_manifests = 0
    for event in companion:
        kind = event.get("event")
        identity = f"{event.get('worker')}:{event.get('pid')}"
        if kind == "collection_finish":
            manifests += 1
            selected.update(event["selected"])
            if "native_required" in event:
                native_metadata_manifests += 1
                native_required.update(event["native_required"])
        elif kind == "deselected":
            deselected.update(event["nodes"])
        elif kind == "logstart":
            starts.add(event["nodeid"])
        elif kind == "logfinish":
            finishes.add(event["nodeid"])
            active.pop(identity, None)
        elif kind == "phase_start":
            active[identity] = event
        elif kind == "worker_down" and event.get("error"):
            worker_loss.append(event)
    by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    collection_errors = []
    session_finishes = []
    for report in reports:
        kind = report.get("$report_type")
        if kind == "TestReport":
            by_node[report["nodeid"]].append(report)
        elif kind == "CollectReport" and report.get("outcome") == "failed":
            collection_errors.append(report)
        elif kind == "SessionFinish":
            session_finishes.append(report)
    nodes = {
        node: _node_status(
            by_node[node],
            node in starts,
            node in finishes,
            provider_required=evidence_selection == "providers",
        )
        for node in sorted(selected | set(by_node) | starts)
    }
    native_events = [e for e in companion if e.get("event") == "native_context"]
    if not manifests or native_metadata_manifests != manifests:
        # Older receipts did not record fixture applicability. Keep their original result and
        # make the missing provenance explicit; never infer a historical native obligation.
        native_provenance = {
            "status": "unavailable",
            "required": None,
            "unresolved": [],
            "reason": "collection manifest lacks native applicability metadata",
        }
    elif not native_required:
        native_provenance = {
            "status": "not_required",
            "required": [],
            "unresolved": [],
            "reason": None,
        }
    else:
        complete_nodes = {
            event["nodeid"] for event in native_events if _complete_native_context(event)
        }
        claimed = {
            node for node in native_required if nodes.get(node, {}).get("status") == "passed"
        }
        unresolved = sorted(claimed - complete_nodes)
        native_provenance = {
            "status": ("incomplete" if unresolved else "complete" if claimed else "no_claim"),
            "required": sorted(native_required),
            "claimed": sorted(claimed),
            "unresolved": unresolved,
            "not_claimed": sorted(native_required - claimed),
            "reason": "required native test has no complete item-bound acquisition context"
            if unresolved
            else None,
        }
    process_path = directory / "pytest.process.json"
    process = read_json(process_path) if process_path.exists() else {}
    if not process:
        errors.append("missing process result")
    if len(session_finishes) != 1:
        errors.append(f"expected one SessionFinish, found {len(session_finishes)}")
    if not manifests:
        errors.append("missing selected-node manifest")
    if not any(r.get("$report_type") == "SessionStart" for r in reports):
        errors.append("missing SessionStart")
    if session_finishes and process.get("returncode") != session_finishes[-1]["exitstatus"]:
        errors.append("session exitstatus disagrees with process returncode")
    if process.get("interruption") or process.get("launch_error"):
        errors.append("process interrupted or failed to launch")
    runner_path = directory / "runner.process.json"
    runner = read_json(runner_path) if runner_path.exists() else {}
    if runner.get("interruption"):
        errors.append("supervising runner interrupted")
    errors.extend(_group_cleanup_errors(process))
    cohort_path = directory / "private-cohort.process.json"
    cohort = read_json(cohort_path) if cohort_path.exists() else {}
    if cohort:
        errors.extend(_group_cleanup_errors(cohort))
        if cohort.get("interruption") or cohort.get("launch_error"):
            errors.append("private host interrupted or failed to launch")
        if cohort.get("returncode") not in (None, 0) and cohort.get("returncode") != process.get(
            "returncode"
        ):
            errors.append("private host cohort exited unsuccessfully")
    statuses = [value["status"] for value in nodes.values()]
    empty_selection = (
        not nodes
        and not errors
        and not worker_loss
        and not collection_errors
        and process.get("returncode") in (0, 5)
    )
    process_failed = (
        process.get("returncode") not in (None, 0) or cohort.get("returncode") not in (None, 0)
    ) and not empty_selection
    if collection_errors or "failed" in statuses:
        status = "failed"
    elif errors or worker_loss:
        status = "incomplete"
    elif "blocked" in statuses:
        status = "blocked"
    elif empty_selection:
        status = "not_run"  # A complete empty pytest selection establishes no coverage.
    elif process_failed:
        status = "failed"
    elif not nodes or any(s in {"not_run", "incomplete"} for s in statuses):
        status = "not_run" if not starts else "incomplete"
    else:
        status = "passed" if "passed" in statuses else "not_run"
    if status == "passed" and native_provenance["status"] == "incomplete":
        status = "incomplete"
    return {
        "directory": str(directory),
        "status": status,
        "nodes": nodes,
        "selected": sorted(selected),
        "evidence_selection": evidence_selection,
        "scheduling": {
            "group_metadata_complete": group_metadata_complete
            and all(len(group_observations[node]) == 1 for node in selected),
            "items": [
                {
                    "nodeid": node,
                    "affinity_groups": list(next(iter(group_observations[node])))
                    if group_metadata_complete and len(group_observations[node]) == 1
                    else None,
                    "observed_workers": sorted(observed_workers[node]),
                    "scheduled_workers": None,
                    "native_required": node in native_required
                    if native_metadata_manifests
                    else None,
                }
                for node in sorted(selected)
            ],
        },
        "deselected": sorted(deselected),
        "collection_errors": collection_errors,
        "stream_errors": errors,
        "selection_refusals": selection_refusals,
        "active_phases": list(active.values()),
        "worker_loss": worker_loss,
        "process": process,
        "native_host_process": cohort,
        "runner": runner,
        "process_failed": process_failed,
        "session_finishes": session_finishes,
        "reporting_complete": not errors and not worker_loss,
        "identity_valid": identity_valid,
        "empty_selection": empty_selection,
        "native_contexts": native_events,
        "sql_batches": [event for event in companion if event.get("event") == "sql_batch"],
        "deployments": [
            {
                **event["context"]["native_test_deployment"],
                "worker": event.get("worker"),
                "pid": event.get("pid"),
            }
            for event in native_events
            if event.get("scope") == "session"
            and isinstance(event.get("context"), dict)
            and isinstance(event.get("context", {}).get("native_test_deployment"), dict)
        ],
        "native_provenance": native_provenance,
        "session_contexts": [e for e in companion if e.get("event") == "session_start"],
        "worker_facts": _worker_facts(companion),
        "invocation": invocation,
    }


def _worker_facts(events: list[dict[str, Any]]) -> dict[str, Any]:
    executing = sorted({str(e.get("worker")) for e in events if e.get("event") == "phase_start"})
    # Phase intervals come from durable process journals, not controller dispatch times.
    intervals: list[tuple[float, int, str]] = []
    finished = {(e.get("worker"), e.get("nodeid")) for e in events if e.get("event") == "logfinish"}
    for event in events:
        if (
            str(event.get("worker")) in executing
            and "time" in event
            and (event.get("worker"), event.get("nodeid")) in finished
            and (
                event.get("event") == "logfinish"
                or (event.get("event") == "phase_start" and event.get("phase") == "setup")
            )
        ):
            intervals.append(
                (
                    event["time"],
                    1 if event["event"] == "phase_start" else -1,
                    str(event.get("worker")),
                )
            )
    active: set[str] = set()
    peak = 0
    for _, direction, worker in sorted(intervals):
        if direction == 1:
            active.add(worker)
        else:
            active.discard(worker)
        peak = max(peak, len(active))
    return {
        "actual": next(
            (e["count"] for e in events if e.get("event") == "workers_created"),
            0
            if any(
                e.get("event") == "session_start" and e.get("xdist_numprocesses") == 0
                for e in events
            )
            else None,
        ),
        "created": [e for e in events if e.get("event") == "workers_created"],
        "ready": sorted({e["ready_worker"] for e in events if e.get("event") == "worker_ready"}),
        "executing": executing,
        "executing_processes": [
            dict(worker=worker, pid=pid)
            for worker, pid in sorted(
                {
                    (str(e.get("worker")), e.get("pid"))
                    for e in events
                    if e.get("event") == "phase_start"
                }
            )
        ],
        "observed_peak_overlap": peak,
    }


def classify_rust(directory: Path) -> dict[str, Any]:
    if (directory / "rust-state.json").exists():
        return read_json(directory / "rust-state.json")
    if not (directory / "nextest.process.json").exists():
        return {
            "status": "incomplete",
            "applicability": "unknown",
            "functional_coverage": False,
            "reason": "requested Rust route has no nextest process result",
        }
    process = read_json(directory / "nextest.process.json")
    result: dict[str, Any] = {
        "process": process,
        "status": "incomplete",
        "applicability": "unknown",
        "functional_coverage": False,
    }
    listing = directory / "nextest-list.stdout"
    junit = directory / "nextest.junit.xml"
    try:
        count = read_json(listing)["test-count"]
        result["listed_test_count"] = count
        result["applicability"] = "empty-selection" if count == 0 else "selected"
        if process.get("returncode") not in (0, None):
            result["status"] = "failed"
        elif process.get("returncode") is None or process.get("interruption"):
            result["status"] = "incomplete"
        elif count == 0:
            result["status"] = "not_run"
            result["reason"] = "zero Rust tests establish no functional coverage"
        elif junit.exists():
            with _open_receipt(junit) as stream:
                root = ET.parse(stream).getroot()
            cases = list(root.iter("testcase"))
            result["reported_test_count"] = len(cases)
            failures = any(
                case.find("failure") is not None or case.find("error") is not None for case in cases
            )
            skips = any(case.find("skipped") is not None for case in cases)
            if failures or process.get("returncode") not in (0, None):
                result["status"] = "failed"
            elif skips:
                result["status"] = "blocked"
            elif len(cases) == count and not process.get("interruption"):
                result["status"] = "passed"
                result["functional_coverage"] = True
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        result["reason"] = str(error)
    cleanup_errors = _group_cleanup_errors(process)
    if cleanup_errors:
        result["cleanup_errors"] = cleanup_errors
        result["functional_coverage"] = False
        if result["status"] != "failed":
            result["status"] = "incomplete"
    return result


def classify(
    directories: list[Path],
    required_from: list[Path] | None = None,
    *,
    required_lanes: dict[str, list[Path]] | None = None,
) -> dict[str, Any]:
    receipts = [classify_receipt(path) for path in directories]
    required: set[str] = set()
    native_required: set[str] = set()
    required_evidence: dict[str, str] = {}
    required_hosts: dict[str, str] = {}
    manifests = _required_manifests(required_from or [])
    missing_lanes = []
    lane_selections = {}
    for lane, candidates in (required_lanes or {}).items():
        expected_mode = "ordinary"
        expected_host = "shared"
        if candidates:
            initial = candidates[0]
            if initial.is_dir() and (initial / "invocation.json").is_file():
                original_invocation = read_json(initial / "invocation.json")
                expected_mode = original_invocation.get("evidence_selection", "ordinary")
                expected_host = original_invocation.get("native_host", "shared")
            else:
                with suppress(OSError, ValueError, KeyError, TypeError, IndexError):
                    initial_manifest = _required_manifests([initial])[0]
                    expected_mode = _manifest_evidence_selection(initial_manifest)
                    expected_host = initial_manifest.get("native_host", "shared")
        for candidate in candidates:
            try:
                selected = _required_manifests([candidate])
                for manifest in selected:
                    _node_aliases([manifest])
                    if _manifest_evidence_selection(manifest) != expected_mode:
                        raise ValueError("replacement lane has a different evidence selection")
                    if manifest.get("native_host", "shared") != expected_host:
                        raise ValueError("replacement lane has a different native host mode")
            except ValueError, KeyError, TypeError:
                continue
            manifests.extend(selected)
            lane_selections[lane] = str(candidate)
            break
        else:
            missing_lanes.append(lane)
    for manifest in manifests:
        aliases = _node_aliases([manifest])
        required.update(aliases[node] for node in manifest["selected"])
        mode = _manifest_evidence_selection(manifest)
        for node in manifest["selected"]:
            logical = aliases[node]
            if logical in required_evidence and required_evidence[logical] != mode:
                raise ValueError("required identity has conflicting evidence selections")
            required_evidence[logical] = mode
            host = manifest.get("native_host", "shared")
            if logical in required_hosts and required_hosts[logical] != host:
                raise ValueError("required identity has conflicting native host modes")
            required_hosts[logical] = host
        native_required.update(aliases[node] for node in manifest.get("native_required", []))
    union = {
        node: [
            _union_node_status(receipt, node, native_required)
            if receipt["evidence_selection"] == required_evidence[node]
            and (receipt.get("invocation") or {}).get("native_host", "shared")
            == required_hosts[node]
            else "incomplete"
            for receipt in receipts
            if node in receipt["nodes"]
        ]
        for node in sorted(required)
    }
    missing = [node for node, states in union.items() if "passed" not in states]
    rust = [
        classify_rust(path)
        for path, receipt in zip(directories, receipts, strict=True)
        if (path / "nextest.process.json").exists()
        or (path / "rust-state.json").exists()
        or (receipt["invocation"] or {}).get("python_only") is False
    ]
    states = [receipt["status"] for receipt in receipts] + [
        r["status"]
        for r in rust
        if not (r["status"] == "not_run" and r["applicability"] == "empty-selection")
    ]
    if "failed" in states:
        status = "failed"
    elif "incomplete" in states:
        status = "incomplete"
    elif "blocked" in states:
        status = "blocked"
    elif missing or "not_run" in states:
        status = "not_run"
    else:
        status = "passed"
    contexts = [
        {
            "directory": receipt["directory"],
            "invocation": receipt["invocation"],
            "evidence_selection": receipt["evidence_selection"],
            "native_contexts": receipt["native_contexts"],
            "native_provenance": receipt["native_provenance"],
            "session_contexts": receipt["session_contexts"],
        }
        for receipt in receipts
    ]
    # Surface identities for SP-10's applicability judgment; changes do not invalidate by hash.
    sources = {
        json.dumps((context["invocation"] or {}).get("source"), sort_keys=True)
        for context in contexts
    }
    unsettled_receipts = [
        receipt["directory"]
        for directory, receipt in zip(directories, receipts, strict=True)
        if _group_unsettled(receipt["process"])
        or _group_unsettled(receipt.get("native_host_process", {}))
        or any(
            _group_unsettled(read_json(path))
            for name in ("rustc", "nextest-version", "nextest-list", "nextest")
            if (path := directory / f"{name}.process.json").is_file()
        )
    ]
    return {
        "status": status,
        "contexts": contexts,
        "source_contexts_differ": len(sources) > 1,
        "custody_unsettled": bool(unsettled_receipts),
        "unsettled_receipts": unsettled_receipts,
        "receipts": receipts,
        "rust": rust,
        "required": sorted(required),
        "required_unresolved": missing,
        "missing_lanes": missing_lanes,
        "lane_selections": lane_selections,
        "coverage": union,
        "required_node_coverage": {
            "status": "not_declared"
            if not required_from and not required_lanes
            else "covered"
            if required and not missing and not missing_lanes
            else "unresolved",
            "required": sorted(required),
            "unresolved": missing,
            "applicability_note": (
                "Observed node coverage only, not complete qualification. The owning plan "
                "judges source/context applicability and remaining obligations."
            ),
        },
    }


def _coverage_context(contexts: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Compare recorded facts without treating unknown as a different value."""
    observations: dict[str, list[Any]] = {
        "source": [],
        "python": [],
        "workers": [],
        "evidence_selection": [],
        "native_host": [],
        "native_host_context": [],
    }
    observations.update({name: [] for name in _INVOCATION_PACKAGES})
    for context in contexts:
        invocation = context["invocation"] or {}
        versions = invocation.get("versions") or {}
        observations["native_host"].append(invocation.get("native_host", "shared"))
        if invocation.get("native_host", "shared") == "private":
            observations["native_host_context"].append(invocation.get("native_host_context"))
        observations["source"].append(invocation.get("source"))
        observations["python"].append(invocation.get("python"))
        observations["workers"].append(invocation.get("workers"))
        observations["evidence_selection"].append(
            context.get("evidence_selection", invocation.get("evidence_selection", "ordinary"))
        )
        for name in _INVOCATION_PACKAGES:
            observations[name].append(versions.get(name))
        provenance = context["native_provenance"]["status"]
        if provenance != "not_required":
            bindings = native_bindings(context["native_contexts"])
            observations.setdefault("native bindings", []).append(
                bindings if provenance == "complete" and bindings else None
            )
    differences, unknowns = [], []
    for name, values in observations.items():
        if name == "native_host_context" and not values:
            continue
        if len({json.dumps(value, sort_keys=True) for value in values if value is not None}) > 1:
            differences.append(name)
        if not values or None in values:
            unknowns.append(name)
    return differences, unknowns


def _coverage_projection(result: dict[str, Any], limit: int | None) -> dict[str, Any]:
    coverage = result["required_node_coverage"]
    required, unresolved = len(coverage["required"]), coverage["unresolved"]
    unresolved_set = set(unresolved)
    unsettled = set(result["unsettled_receipts"])
    differences, unknowns = _coverage_context(result["contexts"])
    report = {
        "status": result["status"],
        "node_coverage": {
            "status": coverage["status"],
            "required": required,
            "covered": required - len(unresolved),
            "unresolved": len(unresolved),
            "applicability_note": coverage["applicability_note"],
        },
        "source_contexts_differ": "source" in differences,
        "context_differences": [name for name in differences if name != "source"],
        "context_unknowns": unknowns,
        "missing_lanes": result["missing_lanes"],
        "selected_lanes": sorted(result["lane_selections"]),
        "receipt_states": {
            receipt["directory"]: {
                "custody_unsettled": receipt["directory"] in unsettled,
                "retryable": (
                    receipt["directory"] not in unsettled
                    and not unresolved_set.isdisjoint(receipt["selected"])
                    and _receipt_retryable(receipt)
                ),
            }
            for receipt in result["receipts"]
        },
        "native_observations": dict(
            Counter(entry["native_provenance"]["status"] for entry in result["contexts"])
        ),
    }
    if limit is not None:
        report["items"] = [
            {
                "nodeid": node,
                "observations": sorted(set(result["coverage"][node])),
            }
            for node in unresolved[:limit]
        ]
    return report


_FAILURE_PHASES = ("collection", "setup", "call", "teardown", "unknown")


def _scheduling_projection(
    result: dict[str, Any], limit: int, after: int, group: str | None
) -> dict[str, Any]:
    from sql_batch_receipts import sql_batches

    (receipt,) = result["receipts"]
    scheduling = receipt["scheduling"]
    items = [
        item
        for item in scheduling["items"]
        if group is None or group in (item["affinity_groups"] or [])
    ]
    return {
        "status": result["status"],
        "reporting_complete": receipt["reporting_complete"],
        "group_metadata_complete": scheduling["group_metadata_complete"],
        "workers": (receipt["invocation"] or {}).get("workers"),
        "evidence_selection": receipt["evidence_selection"],
        "native_required_count": len(receipt["native_provenance"]["required"])
        if receipt["native_provenance"]["required"] is not None
        else None,
        "available": len(items),
        "items": items[after : after + limit],
        "deployments": receipt["deployments"][:limit],
        "deployments_available": len(receipt["deployments"]),
        "deployments_omitted": max(0, len(receipt["deployments"]) - limit),
        **sql_batches(receipt, limit, after, group),
    }


def _startup_failure(receipt: dict[str, Any]) -> dict[str, Any] | None:
    failure_path = Path(receipt["directory"]) / "private-host-failure.json"
    if failure_path.is_file():
        failure = read_json(failure_path)
        message = f"{failure.get('type', 'Error')}: {failure.get('message', 'private host failed')}"
        return {
            "kind": "native_host_bootstrap",
            "source": "private-host-failure.json",
            "availability": "available" if len(message) <= 32768 else "omitted",
            "diagnostic": message if len(message) <= 32768 else None,
            **(
                {"reason": "private host diagnostic exceeds transport limit"}
                if len(message) > 32768
                else {}
            ),
        }
    if "missing SessionStart" not in receipt["stream_errors"] or not receipt["process_failed"]:
        return None
    if receipt.get("native_host_process"):
        path = Path(receipt["directory"]) / "private-cohort.stderr"
        result = {
            "kind": "native_host_bootstrap",
            "source": "private-cohort.stderr",
            "availability": "unavailable",
            "diagnostic": None,
        }
        if not path.is_file():
            return result
        if path.stat().st_size > 65536:
            return {
                **result,
                "availability": "omitted",
                "reason": "private bootstrap stderr exceeds capture byte limit",
            }
        diagnostic = path.read_text(errors="replace").strip()
        if len(diagnostic) > 32768:
            return {
                **result,
                "availability": "omitted",
                "reason": "complete private bootstrap diagnostic exceeds transport limit",
            }
        return {
            **result,
            "availability": "available" if diagnostic else "unavailable",
            "diagnostic": diagnostic or None,
        }
    result: dict[str, Any] = {
        "kind": "pytest_child_startup",
        "source": "pytest.stderr",
        "availability": "unavailable",
        "diagnostic": None,
    }
    path = Path(receipt["directory"]) / "pytest.stderr"
    if not path.is_file():
        return result
    if path.stat().st_size > 65536:
        return {
            **result,
            "availability": "omitted",
            "reason": "startup stderr exceeds capture byte limit",
        }
    # Keep terminal exception messages, excluding source listings and rendered frames.
    messages = []
    for line in path.read_text(errors="replace").splitlines():
        message = re.sub(r"^E\s+", "", line.lstrip())
        if re.match(r"^[\w.]*(?:Error|Exception|Exit|Interrupt):", message):
            messages.append(message)
    diagnostic = "\n".join(messages)
    if not diagnostic:
        return result
    if len(diagnostic) > 32768:
        return {
            **result,
            "availability": "omitted",
            "reason": "complete startup exception exceeds transport limit",
        }
    return {**result, "availability": "available", "diagnostic": diagnostic}


def _failure_diagnostic(report: dict[str, Any]) -> dict[str, Any]:
    representation = report.get("longrepr")
    if isinstance(representation, dict):
        crash = representation.get("reprcrash")
        message = crash.get("message") if isinstance(crash, dict) else None
    elif isinstance(representation, str):
        # FixtureLookupError and some collection errors are rendered strings with
        # a location footer. Prefer pytest's error lines over that footer, while
        # continuing to omit source listings and captured streams.
        lines = representation.splitlines()
        errors = [
            line[1:].strip()
            for raw in lines
            if (line := raw.lstrip()).startswith("E")
            and len(line) > 1
            and line[1].isspace()
            and line[1:].strip()
        ]
        message = (
            "\n".join(errors)
            if errors
            else next((line for line in reversed(lines) if line.strip()), None)
        )
    else:
        message = None
    if not isinstance(message, str) or not message:
        return {}
    try:
        message.encode("utf-8")
    except UnicodeEncodeError:
        return {"diagnostic_truncated": True}
    if len(message) > 32768:
        # The CLI redacts before clipping. Never pass a pre-clipped credential there.
        return {"diagnostic_truncated": True}
    return {"diagnostic": message}


_NATIVE_LOCATION_LIMIT = 64
_NATIVE_CHAIN_LIMIT = 16
_NATIVE_VISIT_LIMIT = 256
_NATIVE_STRING_LIMIT = 32768
_NATIVE_TRANSPORT_LIMIT = 65536


def _native_traceback(report: dict[str, Any]) -> dict[str, Any]:
    """Select pytest's recorded locations, never rendered source/locals or inferred edges."""
    selected: dict[str, Any] = dict(
        version=1,
        format="pytest_report_longrepr",
        scope="structured_file_locations_and_chain_descriptions",
        availability="unavailable",
        locations=[],
        chains=[],
        omissions=[],
        omissions_omitted=0,
        location_limit=_NATIVE_LOCATION_LIMIT,
        traversal_limit=_NATIVE_VISIT_LIMIT,
        string_char_limit=_NATIVE_STRING_LIMIT,
        transport_bytes_limit=_NATIVE_TRANSPORT_LIMIT,
    )
    visits = 0

    def omit(path: str, reason: str) -> None:
        if len(selected["omissions"]) < 16:
            selected["omissions"].append(dict(native_path=path, reason=reason))
        else:
            selected["omissions_omitted"] += 1

    def visit(path: str) -> bool:
        nonlocal visits
        visits += 1
        if visits > _NATIVE_VISIT_LIMIT:
            omit(path, "native traversal limit")
            return False
        return True

    def string(value: Any, path: str, *, optional: bool = False) -> str | None:
        if value is None and optional:
            return None
        if not isinstance(value, str):
            omit(path, "native string unavailable")
            return None
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            omit(path, "complete native string has unsupported Unicode encoding")
            return None
        if len(value) > _NATIVE_STRING_LIMIT:
            # A cut credential is unsafe to redact. Omit the complete raw field instead.
            omit(path, "complete native string exceeds transport character limit")
            return None
        return value

    def append(kind: str, value: dict[str, Any], path: str) -> None:
        def fits() -> bool:
            candidate = {**selected, kind: [*selected[kind], value]}
            # Match the supervisor's actual json.dumps default ASCII escaping.
            return len(json.dumps(candidate).encode()) <= _NATIVE_TRANSPORT_LIMIT - 8192

        if not fits():
            for field in ("message", "description", "path"):
                if value.get(field) is not None:
                    value[field] = None
                    omit(
                        path + ("[2]" if field == "description" else "." + field),
                        "complete native field exceeds transport byte limit",
                    )
                    if fits():
                        break
        if fits():
            selected[kind].append(value)
        else:
            omit(path, "complete native record exceeds transport byte limit")

    def location(value: Any, path: str, role: str) -> None:
        if not visit(path):
            return
        if len(selected["locations"]) >= _NATIVE_LOCATION_LIMIT:
            omit(path, "native location limit")
            return
        if not isinstance(value, dict):
            omit(path, "structured native location unavailable")
            return
        lineno = value.get("lineno")
        if type(lineno) is not int or lineno < 1:
            lineno = None
            omit(path + ".lineno", "native line number unavailable")
        append(
            "locations",
            dict(
                native_path=path,
                role=role,
                path=string(value.get("path"), path + ".path"),
                lineno=lineno,
                message=string(value.get("message"), path + ".message"),
            ),
            path,
        )

    def traceback(value: Any, path: str) -> None:
        if not visit(path):
            return
        if not isinstance(value, dict) or not isinstance(value.get("reprentries"), list):
            omit(path, "structured pytest traceback entries unavailable or unsupported")
            return
        entries = value["reprentries"]
        for index, entry in enumerate(entries[:_NATIVE_LOCATION_LIMIT]):
            located = f"{path}.reprentries[{index}]"
            if not visit(located):
                break
            if not isinstance(entry, dict) or entry.get("type") != "ReprEntry":
                omit(located, "native-only or unknown entry; rendered lines are not parsed")
                continue
            data = entry.get("data")
            if not isinstance(data, dict):
                omit(located, "native entry data unavailable")
                continue
            location(data.get("reprfileloc"), located + ".data.reprfileloc", "reprfileloc")
        if len(entries) > _NATIVE_LOCATION_LIMIT:
            omit(path + ".reprentries", "native entry traversal limit")

    representation = report.get("longrepr")
    if not isinstance(representation, dict):
        omit(
            "$.longrepr",
            "structured native representation unavailable; rendered text is not parsed",
        )
        return selected
    location(representation.get("reprcrash"), "$.longrepr.reprcrash", "reprcrash")
    traceback(representation.get("reprtraceback"), "$.longrepr.reprtraceback")
    chain = representation.get("chain")
    if chain is not None:
        if not isinstance(chain, list):
            omit("$.longrepr.chain", "native chain format unsupported")
        else:
            for index, entry in enumerate(chain[:_NATIVE_CHAIN_LIMIT]):
                located = f"$.longrepr.chain[{index}]"
                if not visit(located):
                    break
                if not isinstance(entry, (list, tuple)) or len(entry) != 3:
                    omit(located, "native chain entry format unsupported")
                    continue
                append(
                    "chains",
                    dict(
                        native_path=located,
                        description=string(entry[2], located + "[2]", optional=True),
                    ),
                    located,
                )
                traceback(entry[0], located + "[0]")
                location(entry[1], located + "[1]", "reprcrash")
            if len(chain) > _NATIVE_CHAIN_LIMIT:
                omit("$.longrepr.chain", "native chain traversal limit")
    if selected["locations"]:
        selected["availability"] = "partial" if selected["omissions"] else "available"
    return selected


def _failure_events(receipt: dict[str, Any]) -> Generator[tuple[dict[str, Any], dict[str, Any]]]:
    for report in sorted(receipt["collection_errors"], key=lambda report: report.get("nodeid", "")):
        yield (
            {
                "nodeid": report.get("nodeid", ""),
                "phase": "collection",
                "outcome": "failed",
                "reason": "collection_failure",
                **_failure_diagnostic(report),
            },
            report,
        )
    if not receipt["identity_valid"]:
        return
    for nodeid, node in receipt["nodes"].items():
        for report in sorted(
            (
                report
                for report in node["reports"]
                if report.get("outcome") == "failed"
                or (report.get("outcome") == "skipped" and _failed_prerequisite(report))
            ),
            key=lambda report: (
                _FAILURE_PHASES.index(report["when"])
                if report.get("when") in _FAILURE_PHASES
                else len(_FAILURE_PHASES) - 1
            ),
        ):
            phase = report.get("when")
            blocked = _failed_prerequisite(report)
            prerequisites = _prerequisites(_properties([report])) if blocked else []
            detail = _failure_diagnostic(report)
            if blocked and detail.get("diagnostic") is None:
                detail["diagnostic"] = "; ".join(
                    f"{entry['name']}: {entry['reason']}" for entry in prerequisites
                )
            yield (
                {
                    "nodeid": nodeid,
                    "phase": phase if phase in _FAILURE_PHASES else "unknown",
                    "outcome": "blocked" if blocked else "failed",
                    "reason": "prerequisite" if blocked else "pytest_failure",
                    **({"prerequisites": prerequisites} if blocked else {}),
                    **detail,
                },
                report,
            )


def _failure_projection(
    result: dict[str, Any],
    limit: int,
    phase: str | None,
    after: int = 0,
    *,
    native_traceback: bool = False,
    native_after: int = 0,
    native_limit: int | None = None,
) -> dict[str, Any]:
    (receipt,) = result["receipts"]
    items = []
    available = 0
    for event, native_report in _failure_events(receipt):
        if phase is not None and event["phase"] != phase:
            continue
        available += 1
        if available > after and len(items) < limit:
            if native_traceback:
                event["native_traceback"] = _native_traceback(native_report)
            items.append(event)
    health = [
        *receipt["stream_errors"],
        *[
            f"worker {event.get('lost_worker', 'unknown')}: {event['error']}"
            for event in receipt["worker_loss"]
        ],
    ]
    provenance = receipt["native_provenance"]
    unresolved = sorted(provenance["unresolved"])
    size = limit if native_limit is None else native_limit
    native_page = unresolved[native_after : native_after + size]
    native = None
    if unresolved or provenance.get("reason"):
        end = native_after + len(native_page)
        native = {
            "reason": provenance.get("reason"),
            "limit": size,
            "after": native_after,
            "next_after": end if end < len(unresolved) else None,
            "available": len(unresolved),
            "selected": len(native_page),
            "omitted": len(unresolved) - len(native_page),
            "unresolved": native_page,
        }
    return {
        "status": result["status"],
        "items": items,
        "available": available,
        "reporting_errors": [
            message
            if len(message) <= 32768
            else "Reporting error exceeds diagnostic capture limit."
            for message in health[:20]
        ],
        "reporting_errors_omitted": max(0, len(health) - 20),
        "rust": [
            {
                key: entry[key]
                for key in (
                    "status",
                    "applicability",
                    "functional_coverage",
                    "listed_test_count",
                    "reported_test_count",
                    "reason",
                )
                if key in entry
            }
            for entry in result["rust"]
        ],
        "reporting_complete": receipt["reporting_complete"] and receipt["identity_valid"],
        "custody_unsettled": result["custody_unsettled"],
        "retryable": _retryable(result),
        "native_observation": receipt["native_provenance"]["status"],
        "native_provenance": native,
        "startup": _startup_failure(receipt),
    }


def _union_node_status(receipt: dict[str, Any], node: str, native_required: set[str]) -> str:
    """Return the status eligible for the current manifest's required union.

    Historical node outcomes remain available in ``receipt["nodes"]``. A current native
    requirement additionally needs a complete item-bound acquisition event in this receipt.
    """
    if not receipt["identity_valid"] or node not in receipt["selected"]:
        return "incomplete"
    if (receipt["invocation"] or {}).get("collection_only"):
        return "not_run"
    status = receipt["nodes"][node]["status"]
    if node not in native_required or status != "passed":
        return status
    if any(
        event.get("nodeid") == node and _complete_native_context(event)
        for event in receipt["native_contexts"]
    ):
        return "passed"
    return "incomplete"


def _positive_timeout(value: str) -> float:
    import math

    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return timeout


def _positive_workers(value: str) -> int:
    try:
        workers = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("workers must be a positive integer") from error
    if workers <= 0:
        raise argparse.ArgumentTypeError("workers must be a positive integer")
    return workers


def _canonical_node_id(node: object) -> bool:
    return (
        isinstance(node, str)
        and not node.startswith(("-", "@"))
        and not any(char in node for char in "\n\r\0")
        and "::" in node
    )


def _retryable(result: dict[str, Any]) -> bool:
    if result["custody_unsettled"] or len(result["receipts"]) != 1:
        return False
    return _receipt_retryable(result["receipts"][0])


def _receipt_retryable(receipt: dict[str, Any]) -> bool:
    selected = receipt["selected"]
    if (receipt["invocation"] or {}).get("collection_only"):
        return False
    if not selected or not receipt["identity_valid"] or receipt["collection_errors"]:
        return False
    return all(map(_canonical_node_id, selected)) and (
        bool(receipt["native_provenance"]["unresolved"])
        or any(
            receipt["nodes"][node]["status"] in {"failed", "blocked", "incomplete", "not_run"}
            for node in selected
        )
    )


def write_unresolved(
    result: dict[str, Any],
    destination: Path,
    *,
    required_from: list[Path],
    lane: str,
    managed: bool = False,
) -> dict[str, Any]:
    """Publish full canonical IDs only after fresh, body-free collection in the selected lane.

    The explicit current required manifest remains the operator's applicability declaration.
    Collection checks identity, never source/evidence compatibility or test outcomes.
    """
    if not required_from or not result["required"] or not result["receipts"]:
        raise ValueError("export needs receipts and an explicit nonempty current required manifest")
    nodes = result["required_unresolved"]
    if not nodes:
        raise ValueError("empty unresolved selection; no argument file written")
    if destination.exists():
        raise ValueError(f"refusing to overwrite {destination}")
    for node in result["required"]:
        if not _canonical_node_id(node):
            raise ValueError(f"not a full canonical test node ID: {node!r}")
    # Validate the whole declared selection, so stale covered IDs cannot conceal stale history.
    scratch = (
        destination.parent if managed else ROOT / "build" / "test-receipts" / "selection-validation"
    )
    scratch.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="collection-", dir=scratch))
    selection = directory / "required.txt"
    selection.write_text("\n".join(result["required"]) + "\n")
    modes = {receipt.get("evidence_selection", "ordinary") for receipt in result["receipts"]}
    if len(modes) != 1:
        raise ValueError("retry requires one original evidence selection")
    evidence_selection = modes.pop()
    hosts = {
        (receipt.get("invocation") or {}).get("native_host", "shared")
        for receipt in result["receipts"]
    }
    if len(hosts) != 1:
        raise ValueError("retry requires one original native host mode")
    native_host = hosts.pop()
    write_json(
        directory / "invocation.json",
        {
            **invocation_context(native_host),
            "evidence_selection": evidence_selection,
            "collection_only": True,
        },
    )
    with supervision(directory):
        run_python(
            directory,
            [
                "-n",
                "0",
                "--collect-only",
                "-m",
                "shared_cluster_fault" if lane == "fault" else "not shared_cluster_fault",
                "@" + str(selection),
            ],
            cwd=Path.cwd(),
            timeout=120,
            managed=managed,
            evidence_selection=evidence_selection,
            native_host=native_host,
        )
    collected = classify_receipt(directory)
    if (
        collected["process"].get("returncode") != 0
        or collected["stream_errors"]
        or collected["collection_errors"]
        or collected["worker_loss"]
        or set(collected["selected"]) != set(result["required"])
    ):
        if managed:
            # The caller owns this settled collection receipt. Retain it through
            # the ordinary lane's existing diagnostic views without executing a
            # broadened or stale functional selection.
            write_json(
                directory / "classification.json",
                classify([directory]),
            )
            return {
                "path": None,
                "nodes": [],
                "lane": lane,
                "validation_receipt": str(directory),
                "evidence_selection": evidence_selection,
                "native_host": native_host,
                "validation": "failed",
            }
        raise ValueError(
            "current collection is stale, ambiguous, failed or outside the selected lane; "
            f"receipt: {directory}"
        )
    # Exclusive creation also handles a file appearing between validation and publication.
    with destination.open("x") as handle:
        handle.write("\n".join(nodes) + "\n")
    return {
        "path": str(destination),
        "nodes": nodes,
        "lane": lane,
        "validation_receipt": str(directory),
        "evidence_selection": evidence_selection,
        "native_host": native_host,
        "validation": "fresh collection only; no test bodies executed",
    }


def _forwardable_selector(value: str) -> bool:
    if not value or value.startswith(("-", "@")) or any(c in value for c in ("\0", "\n", "\r")):
        return False
    path = (ROOT / value.split("::", 1)[0]).resolve()
    if any(path.is_relative_to(ROOT / root) for root in ("tests", "python/corpus-structure/tests")):
        return True
    # Explicit evidence probes are admitted by file only; they do not enter
    # default test discovery or permit an entire historical evidence sweep.
    return (
        path.is_relative_to(ROOT / "docs/design_review/evidence")
        and path.suffix == ".py"
        and path.is_file()
    )


def validate_pytest_args(args: list[str]) -> bool:
    """Allow managed pytest selectors and display controls without replacing owner policy."""
    has_selector = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-k":
            index += 1
            if index == len(args) or not args[index].strip() or args[index].startswith(("-", "@")):
                raise ValueError("-k requires a keyword expression")
            has_selector = True
        elif arg not in {"-q", "-qq", "-v", "-vv", "--quiet", "--verbose"}:
            if not _forwardable_selector(arg):
                raise ValueError(f"unsupported managed pytest argument: {arg!r}")
            has_selector = True
        index += 1
    return has_selector


def _managed_pytest_args(
    args: list[str],
    *,
    lane: str,
    directory: Path,
    selection_file: Path | None,
    workers: int | None = None,
    collection_only: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    if workers is not None and (type(workers) is not int or workers <= 0):
        raise ValueError("workers must be a positive integer")
    if lane == "fault" and workers is not None:
        raise ValueError("--workers applies only to the ordinary lane")
    has_selector = validate_pytest_args(args)
    if lane == "fault" and has_selector:
        raise ValueError("the exclusive fault lane owns its selection")
    if selection_file is not None:
        if (
            args
            or selection_file.parent.resolve() != directory.parent
            or selection_file.is_symlink()
            or not selection_file.is_file()
        ):
            raise ValueError("retry requires its own selection file beside the lane workspace")
        nodes = selection_file.read_text().splitlines()
        if not nodes or any("::" not in node or not _forwardable_selector(node) for node in nodes):
            raise ValueError("retry selection must contain canonical test node IDs")
        args = nodes
        has_selector = True
    if collection_only:
        if lane != "ordinary" or workers is not None:
            raise ValueError(
                "collection-only requires the ordinary lane and owns its serial worker policy"
            )
        return ["-n", "0", "--collect-only", "-m", "not shared_cluster_fault", *args], {
            "requested": 0
        }
    if lane == "fault":
        selectors = [] if has_selector else ["tests/scripts/test_native_auth.py"]
        return ["-n", "0", "-m", "shared_cluster_fault", *selectors, *args], {"requested": 0}
    request: dict[str, Any] = {"requested": workers if workers is not None else "auto"}
    capacity = []
    if workers is None:
        selectors = [arg for arg in args if _forwardable_selector(arg)]
        if "-k" not in args and selectors and all("::" in arg for arg in selectors):
            count = len(set(selectors))
            if count == 1:
                request["requested"] = 0
            else:
                request["maxprocesses"] = count
                capacity = ["--maxprocesses", str(count)]
    return [
        "-n",
        str(request["requested"]),
        *capacity,
        "--dist=loadgroup",
        "-m",
        "not shared_cluster_fault",
        *args,
    ], request


def _after_separator(args: list[str]) -> list[str]:
    return args[1:] if args[:1] == ["--"] else args


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument("--python-only", action="store_true")
    run.add_argument("--collection-only", action="store_true")
    run.add_argument("--managed-lane", choices=("ordinary", "fault"))
    run.add_argument("--evidence-selection", choices=("ordinary", "providers"), default="ordinary")
    run.add_argument(
        "--native-host",
        choices=("shared", "private"),
        default=os.environ.get("CORPUS_CI_NATIVE_HOST", "shared"),
    )
    run.add_argument("--workers", type=_positive_workers)
    run.add_argument("--selection-file", type=Path)
    run.add_argument("--test-timeout", type=_positive_timeout, default=TEST_TIMEOUT)
    run.add_argument("--command-timeout", type=_positive_timeout, default=SESSION_TIMEOUT)
    run.add_argument("pytest_args", nargs=argparse.REMAINDER)
    inspect = sub.add_parser("classify")
    inspect.add_argument("--receipt-dir", action="append", type=Path, required=True)
    inspect.add_argument("--required-from", action="append", type=Path, default=[])
    inspect.add_argument("--write-unresolved", type=Path)
    inspect.add_argument("--selection-lane", choices=("ordinary", "fault"), default="ordinary")
    inspect.add_argument("--managed-selection", action="store_true")
    projection = inspect.add_mutually_exclusive_group()
    projection.add_argument("--summary", action="store_true")
    projection.add_argument(
        "--projection", choices=("coverage", "unresolved", "failures", "scheduling")
    )
    inspect.add_argument("--limit", type=int, choices=range(101), default=20, metavar="N")
    inspect.add_argument("--phase", choices=_FAILURE_PHASES)
    inspect.add_argument("--after", type=int, default=0)
    inspect.add_argument("--native-after", type=int, default=0)
    inspect.add_argument("--native-limit", type=int, choices=range(101))
    inspect.add_argument("--native-traceback", action="store_true")
    inspect.add_argument("--group")
    inspect.add_argument(
        "--required-lane", action="append", choices=("ordinary", "fault"), default=[]
    )
    inspect.add_argument("--required-lane-from", action="append", nargs=2, default=[])
    validate = sub.add_parser("validate-pytest")
    validate.add_argument("--report-selection", action="store_true")
    validate.add_argument("pytest_args", nargs=argparse.REMAINDER)
    context = sub.add_parser("context")
    context.add_argument("--native-host", choices=("shared", "private"), default="shared")
    args = parser.parse_args(argv)
    collection_outcome = None
    if args.action == "context":
        print(json.dumps(invocation_context(args.native_host)))
        return 0
    if args.action == "validate-pytest":
        try:
            selected = validate_pytest_args(_after_separator(args.pytest_args))
        except ValueError as error:
            parser.error(str(error))
        if args.report_selection:
            print(json.dumps(selected))
        return 0
    if args.action == "classify":
        if args.projection is not None and args.write_unresolved is not None:
            parser.error("inspection projections cannot write a retry selection")
        if args.projection in {"failures", "scheduling"} and len(args.receipt_dir) != 1:
            parser.error("projection requires exactly one receipt directory")
        if args.native_traceback and args.projection != "failures":
            parser.error("native traceback requires a failure projection")
        if args.phase is not None and args.projection != "failures":
            parser.error("phase requires a failure projection")
        if args.after < 0 or (args.after and args.projection not in {"failures", "scheduling"}):
            parser.error("after requires a paginated projection and a nonnegative offset")
        if args.native_after < 0 or (
            (args.native_after or args.native_limit is not None) and args.projection != "failures"
        ):
            parser.error(
                "native pagination requires the failures projection and a nonnegative offset"
            )
        if args.group is not None and args.projection != "scheduling":
            parser.error("group requires a scheduling projection")
        try:
            lanes = {name: [] for name in args.required_lane}
            for name, path in args.required_lane_from:
                lanes[name].append(Path(path))
            result = classify(args.receipt_dir, args.required_from, required_lanes=lanes)
            if args.write_unresolved is not None:
                result["unresolved_selection"] = write_unresolved(
                    result,
                    args.write_unresolved,
                    required_from=args.required_from,
                    lane=args.selection_lane,
                    managed=args.managed_selection,
                )
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
    else:
        directory = args.out_dir.resolve()
        pytest_args = _after_separator(args.pytest_args)
        worker_request: dict[str, Any] = {"requested": None}
        try:
            if args.native_host == "private" and args.managed_lane != "ordinary":
                raise ValueError(
                    "private native host requires the managed ordinary lane; fault/shared-host claims are incompatible"
                )
            if args.collection_only:
                if args.managed_lane != "ordinary":
                    raise ValueError("collection-only requires the managed ordinary lane")
                args.python_only = True
            if args.evidence_selection == "providers":
                if args.managed_lane == "fault":
                    raise ValueError(
                        "provider evidence is incompatible with the exclusive fault lane"
                    )
                args.python_only = True
            if args.managed_lane:
                if (
                    not args.out_dir.is_absolute()
                    or directory.name != args.managed_lane
                    or not directory.parent.is_dir()
                    or args.out_dir.is_symlink()
                ):
                    raise ValueError(
                        "managed receipt directory must be a lane in its result workspace"
                    )
                pytest_args, worker_request = _managed_pytest_args(
                    pytest_args,
                    lane=args.managed_lane,
                    directory=directory,
                    selection_file=args.selection_file,
                    workers=args.workers,
                    collection_only=args.collection_only,
                )
                args.python_only |= args.managed_lane == "fault"
            elif args.selection_file is not None:
                raise ValueError("retry selection files require a managed lane")
            elif args.workers is not None:
                raise ValueError("--workers requires the managed ordinary lane")
        except (OSError, ValueError) as error:
            parser.error(str(error))
        directory.mkdir(parents=not args.managed_lane, exist_ok=False, mode=0o700)
        with supervision(directory) as control:
            write_json(
                directory / "invocation.json",
                {
                    "argv": sys.argv if argv is None else argv,
                    "cwd": str(Path.cwd()),
                    **invocation_context(args.native_host),
                    "hypothesis_profile": "ci",
                    "session_timeout": args.command_timeout,
                    "test_timeout": args.test_timeout,
                    "python_only": args.python_only,
                    "managed_lane": args.managed_lane,
                    "evidence_selection": args.evidence_selection,
                    "collection_only": args.collection_only,
                    "workers": {
                        **worker_request,
                        "actual": None,
                    },
                },
            )
            process = run_python(
                directory,
                pytest_args,
                timeout=args.command_timeout,
                test_timeout=args.test_timeout,
                managed=bool(args.managed_lane),
                evidence_selection=args.evidence_selection,
                native_host=args.native_host,
                python_only=args.python_only,
            )
            if args.native_host == "shared" and not args.python_only and not _cancelled(process):
                run_rust(directory, timeout=args.command_timeout)
            elif args.native_host == "shared" and not args.python_only:
                write_json(
                    directory / "rust-state.json",
                    {
                        "status": "not_run",
                        "applicability": "unknown",
                        "functional_coverage": False,
                        "reason": "cancelled after Python child drained",
                    },
                )
            control.persist(directory)
            result = classify([directory])
            if args.collection_only:
                collected = result["receipts"][0]
                collection_outcome = (
                    "passed"
                    if collected["reporting_complete"]
                    and collected["identity_valid"]
                    and collected["process"].get("returncode") == 0
                    and collected["selected"]
                    else "not_run"
                    if collected["empty_selection"]
                    else "failed"
                )
                result["collection_outcome"] = collection_outcome
            invocation = result["receipts"][0]["invocation"]
            invocation["workers"]["actual"] = result["receipts"][0]["worker_facts"]["actual"]
            write_json(directory / "invocation.json", invocation)
            write_json(directory / "classification.json", result)
    if args.action == "run" and args.managed_lane:
        receipt = result["receipts"][0]
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "custody_unsettled": result["custody_unsettled"],
                    "empty": not receipt["selected"] and receipt["reporting_complete"],
                    "retryable": _retryable(result),
                    "workers": receipt["invocation"]["workers"],
                    "evidence_selection": receipt["evidence_selection"],
                    "selection_refusals": receipt["selection_refusals"],
                    **({"collection_outcome": collection_outcome} if collection_outcome else {}),
                    "counts": {"selected": len(receipt["selected"])}
                    | dict(Counter(node["status"] for node in receipt["nodes"].values())),
                }
            )
        )
    elif args.action == "classify" and args.projection is not None:
        if args.projection == "scheduling":
            report = _scheduling_projection(result, args.limit, args.after, args.group)
        elif args.projection == "failures":
            report = _failure_projection(
                result,
                args.limit,
                args.phase,
                args.after,
                native_traceback=args.native_traceback,
                native_after=args.native_after,
                native_limit=args.native_limit,
            )
        else:
            report = _coverage_projection(
                result, args.limit if args.projection == "unresolved" else None
            )
        print(json.dumps(report))
    elif args.action == "classify" and args.summary:
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "status",
                        "required_unresolved",
                        "required_node_coverage",
                        "source_contexts_differ",
                        "missing_lanes",
                        "lane_selections",
                    )
                }
                | {
                    **(
                        {"unresolved_selection": result["unresolved_selection"]}
                        if "unresolved_selection" in result
                        else {}
                    ),
                    "custody_unsettled": result["custody_unsettled"],
                    "retryable": _retryable(result),
                    "contexts": [
                        {
                            "directory": entry["directory"],
                            "invocation": entry["invocation"],
                            "native": entry["native_provenance"]["status"],
                            "native_required": len(entry["native_provenance"]["required"] or ()),
                            "native_unresolved": len(
                                entry["native_provenance"]["unresolved"] or ()
                            ),
                            "native_context_count": len(entry["native_contexts"]),
                            "native_bindings": native_bindings(entry["native_contexts"]),
                        }
                        for entry in result["contexts"]
                    ],
                }
            )
        )
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" or collection_outcome == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
