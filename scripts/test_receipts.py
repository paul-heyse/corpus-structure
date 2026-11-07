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
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Generator
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_stream(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return events, [f"missing stream: {path.name}"]
    for index, line in enumerate(path.read_text().splitlines(keepends=True), 1):
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError("event must be an object")
            events.append(data)
        except ValueError as error:
            errors.append(f"{path.name}:{index}: {error}")
        if not line.endswith("\n"):
            errors.append(f"{path.name}:{index}: truncated line")
    return events, errors


def run_process(
    argv: list[str],
    directory: Path,
    prefix: str,
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout: float = SESSION_TIMEOUT,
) -> dict[str, Any]:
    """Bound the owned process group; never signal application/database processes by name."""
    with supervision(directory) as control:
        return _run_process(argv, directory, prefix, control, cwd=cwd, env=env, timeout=timeout)


def _run_process(
    argv: list[str],
    directory: Path,
    prefix: str,
    control: RunControl,
    *,
    cwd: Path,
    env: dict[str, str] | None,
    timeout: float,
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
                result["owned_group_cleanup"] = _stop_group(child)
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


def invocation_context() -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    for package in (
        "pytest",
        "pytest-xdist",
        "pytest-reportlog",
        "hypothesis",
        "psycopg",
        "SQLAlchemy",
    ):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {"source": source_identity(), "python": sys.version, "versions": versions}


def run_python(
    directory: Path,
    args: list[str],
    *,
    timeout: float = SESSION_TIMEOUT,
    test_timeout: float = TEST_TIMEOUT,
    cwd: Path = ROOT,
    managed: bool = False,
) -> dict[str, Any]:
    env = dict(os.environ)
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
    return {key: value for report in reports for key, value in report.get("user_properties", [])}


def _node_status(reports: list[dict[str, Any]], started: bool, finished: bool) -> dict[str, Any]:
    properties = _properties(reports)
    failed = [report for report in reports if report.get("outcome") == "failed"]
    skipped = [report for report in reports if report.get("outcome") == "skipped"]
    successful_phases = {
        report.get("when") for report in reports if report.get("outcome") == "passed"
    }
    reason: object = None
    if failed:
        # A prerequisite annotates the failed setup itself, not an unrelated teardown failure.
        unexpected = [
            r
            for r in failed
            if r.get("when") != "setup" or "qualification_prerequisite" not in _properties([r])
        ]
        status = "failed" if unexpected else "blocked"
        reason = properties.get("qualification_reason")
    elif (started or reports) and not finished:
        status = "incomplete"
    elif skipped:
        status = "inapplicable" if properties.get("qualification_optional") else "blocked"
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
    return aliases


def _required_manifests(paths: list[Path]) -> list[dict[str, Any]]:
    manifests = []
    for path in paths:
        if path.suffix == ".jsonl":
            events, errors = read_stream(path)
            if errors:
                raise ValueError("; ".join(errors))
            found = [event for event in events if event.get("event") == "collection_finish"]
            if not found:
                raise ValueError(f"no collection manifest: {path}")
            manifests.extend(found)
        else:
            manifests.append(read_json(path))
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
    # loadgroup appends scheduler-only suffixes. Retain raw reportlog unchanged while
    # comparing the original pytest identities with earlier required-node manifests.
    identity_valid = True
    try:
        manifests = [e for e in companion if e.get("event") == "collection_finish"]
        if not manifests:
            raise ValueError("missing selected-node manifest")
        aliases = _node_aliases(manifests)
        if len({tuple(sorted(e["selected"])) for e in manifests}) > 1:
            raise ValueError("workers disagree on selected scheduled identities")
    except (ValueError, TypeError, KeyError) as error:
        errors.append(f"invalid collection identity: {error}")
        identity_valid = False
        aliases = {}
    for event in [*companion, *reports]:
        if "nodeid" in event:
            event["nodeid"] = aliases.get(event["nodeid"], event["nodeid"])
        for key in ("selected", "native_required", "nodes"):
            if key in event:
                event[key] = [aliases.get(node, node) for node in event[key]]
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
        node: _node_status(by_node[node], node in starts, node in finishes)
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
    statuses = [value["status"] for value in nodes.values()]
    empty_selection = (
        not nodes
        and not errors
        and not worker_loss
        and not collection_errors
        and process.get("returncode") in (0, 5)
    )
    process_failed = process.get("returncode") not in (None, 0) and not empty_selection
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
        "deselected": sorted(deselected),
        "collection_errors": collection_errors,
        "stream_errors": errors,
        "active_phases": list(active.values()),
        "worker_loss": worker_loss,
        "process": process,
        "runner": runner,
        "process_failed": process_failed,
        "session_finishes": session_finishes,
        "reporting_complete": not errors and not worker_loss,
        "identity_valid": identity_valid,
        "empty_selection": empty_selection,
        "native_contexts": native_events,
        "native_provenance": native_provenance,
        "session_contexts": [e for e in companion if e.get("event") == "session_start"],
        "worker_facts": _worker_facts(companion),
        "invocation": read_json(directory / "invocation.json")
        if (directory / "invocation.json").exists()
        else None,
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
        count = json.loads(listing.read_text())["test-count"]
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
            root = ET.parse(junit).getroot()
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


def classify(directories: list[Path], required_from: list[Path] | None = None) -> dict[str, Any]:
    receipts = [classify_receipt(path) for path in directories]
    required: set[str] = set()
    native_required: set[str] = set()
    manifests = _required_manifests(required_from or [])
    for manifest in manifests:
        aliases = _node_aliases([manifest])
        required.update(aliases[node] for node in manifest["selected"])
        native_required.update(aliases[node] for node in manifest.get("native_required", []))
    union = {
        node: [
            _union_node_status(receipt, node, native_required)
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
    return {
        "status": status,
        "contexts": contexts,
        "source_contexts_differ": len(sources) > 1,
        "custody_unsettled": any(
            _group_unsettled(item.get("process", {})) for item in [*receipts, *rust]
        ),
        "receipts": receipts,
        "rust": rust,
        "required": sorted(required),
        "required_unresolved": missing,
        "coverage": union,
        "required_node_coverage": {
            "status": "not_declared"
            if not required_from
            else "covered"
            if required and not missing
            else "unresolved",
            "required": sorted(required),
            "unresolved": missing,
            "applicability_note": (
                "Observed node coverage only, not complete qualification. The owning plan "
                "judges source/context applicability and remaining obligations."
            ),
        },
    }


def _union_node_status(receipt: dict[str, Any], node: str, native_required: set[str]) -> str:
    """Return the status eligible for the current manifest's required union.

    Historical node outcomes remain available in ``receipt["nodes"]``. A current native
    requirement additionally needs a complete item-bound acquisition event in this receipt.
    """
    if not receipt["identity_valid"] or node not in receipt["selected"]:
        return "incomplete"
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
        if (
            not isinstance(node, str)
            or not node
            or node.startswith(("-", "@"))
            or "\n" in node
            or "\r" in node
            or "\0" in node
            or "::" not in node
        ):
            raise ValueError(f"not a full canonical test node ID: {node!r}")
    # Validate the whole declared selection, so stale covered IDs cannot conceal stale history.
    scratch = (
        destination.parent if managed else ROOT / "build" / "test-receipts" / "selection-validation"
    )
    scratch.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="collection-", dir=scratch))
    selection = directory / "required.txt"
    selection.write_text("\n".join(result["required"]) + "\n")
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
        )
    collected = classify_receipt(directory)
    if (
        collected["process"].get("returncode") != 0
        or collected["stream_errors"]
        or collected["collection_errors"]
        or collected["worker_loss"]
        or set(collected["selected"]) != set(result["required"])
    ):
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
        "validation": "fresh collection only; no test bodies executed",
    }


def _forwardable_selector(value: str) -> bool:
    if not value or value.startswith(("-", "@")) or any(c in value for c in ("\0", "\n", "\r")):
        return False
    path = (ROOT / value.split("::", 1)[0]).resolve()
    return any(
        path.is_relative_to(ROOT / root) for root in ("tests", "python/corpus-structure/tests")
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
        elif arg not in {"-q", "-qq", "-v", "-vv", "--quiet", "--verbose"}:
            if not _forwardable_selector(arg):
                raise ValueError(f"unsupported managed pytest argument: {arg!r}")
            has_selector = True
        index += 1
    return has_selector


def _managed_pytest_args(
    args: list[str], *, lane: str, directory: Path, selection_file: Path | None
) -> list[str]:
    has_selector = validate_pytest_args(args)
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
    if lane == "fault":
        selectors = [] if has_selector else ["tests/scripts/test_native_auth.py"]
        return ["-n", "0", "-m", "shared_cluster_fault", *selectors, *args]
    return ["-n", "auto", "--dist=loadgroup", "-m", "not shared_cluster_fault", *args]


def _after_separator(args: list[str]) -> list[str]:
    return args[1:] if args[:1] == ["--"] else args


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument("--python-only", action="store_true")
    run.add_argument("--managed-lane", choices=("ordinary", "fault"))
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
    validate = sub.add_parser("validate-pytest")
    validate.add_argument("--report-selection", action="store_true")
    validate.add_argument("pytest_args", nargs=argparse.REMAINDER)
    sub.add_parser("context")
    args = parser.parse_args(argv)
    if args.action == "context":
        print(json.dumps(invocation_context()))
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
        try:
            result = classify(args.receipt_dir, args.required_from)
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
        try:
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
                pytest_args = _managed_pytest_args(
                    pytest_args,
                    lane=args.managed_lane,
                    directory=directory,
                    selection_file=args.selection_file,
                )
                args.python_only |= args.managed_lane == "fault"
            elif args.selection_file is not None:
                raise ValueError("retry selection files require a managed lane")
        except (OSError, ValueError) as error:
            parser.error(str(error))
        directory.mkdir(parents=not args.managed_lane, exist_ok=False, mode=0o700)
        with supervision(directory) as control:
            write_json(
                directory / "invocation.json",
                {
                    "argv": sys.argv if argv is None else argv,
                    "cwd": str(Path.cwd()),
                    **invocation_context(),
                    "hypothesis_profile": "ci",
                    "session_timeout": args.command_timeout,
                    "test_timeout": args.test_timeout,
                    "python_only": args.python_only,
                    "managed_lane": args.managed_lane,
                },
            )
            process = run_python(
                directory,
                pytest_args,
                timeout=args.command_timeout,
                test_timeout=args.test_timeout,
                managed=bool(args.managed_lane),
            )
            if not args.python_only and not _cancelled(process):
                run_rust(directory, timeout=args.command_timeout)
            elif not args.python_only:
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
            write_json(directory / "classification.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
