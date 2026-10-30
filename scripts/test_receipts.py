"""Run qualification with durable native artifacts, or classify existing receipts (stdlib only).

SP-10 owns required selections and applicability. This module records what actually ran; it
never interprets the number of skips as provider coverage or invents an assertion for a crash.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import signal
import subprocess
import sys
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


def run_python(
    directory: Path,
    args: list[str],
    *,
    timeout: float = SESSION_TIMEOUT,
    test_timeout: float = TEST_TIMEOUT,
    cwd: Path = ROOT,
) -> dict[str, Any]:
    env = dict(os.environ)
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
    junit = ROOT / "target/nextest/qualification/junit.xml"
    before = junit.stat().st_mtime_ns if junit.exists() else None
    env = {**os.environ, "INSTA_UPDATE": "no"}
    process = run_process(
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
        env=env,
        timeout=timeout,
    )
    if junit.exists() and junit.stat().st_mtime_ns != before:
        shutil.copyfile(junit, directory / "nextest.junit.xml")


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
    selected: set[str] = set()
    deselected: set[str] = set()
    starts: set[str] = set()
    finishes: set[str] = set()
    active: dict[str, dict[str, Any]] = {}
    manifests = 0
    worker_loss = []
    for event in companion:
        kind = event.get("event")
        identity = f"{event.get('worker')}:{event.get('pid')}"
        if kind == "collection_finish":
            manifests += 1
            selected.update(event["selected"])
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
    cleanup = process.get("owned_group_cleanup", {})
    runner_path = directory / "runner.process.json"
    runner = read_json(runner_path) if runner_path.exists() else {}
    if runner.get("interruption"):
        errors.append("supervising runner interrupted")
    if process.get("cleanup_error"):
        errors.append("owned process group cleanup failed")
    if cleanup.get("descendants_after_leader_exit"):
        errors.append("owned descendants survived the process leader exit")
    if cleanup.get("group_present_after_cleanup"):
        errors.append("owned process group still present after bounded cleanup")
    statuses = [value["status"] for value in nodes.values()]
    process_failed = process.get("returncode") not in (None, 0)
    if collection_errors or "failed" in statuses:
        status = "failed"
    elif errors or worker_loss:
        status = "incomplete"
    elif "blocked" in statuses:
        status = "blocked"
    elif process_failed:
        status = "failed"
    elif not nodes or any(s in {"not_run", "incomplete"} for s in statuses):
        status = "not_run" if not starts else "incomplete"
    else:
        status = "passed" if "passed" in statuses else "not_run"
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
        "native_contexts": [e for e in companion if e.get("event") == "native_context"],
        "session_contexts": [e for e in companion if e.get("event") == "session_start"],
        "invocation": read_json(directory / "invocation.json")
        if (directory / "invocation.json").exists()
        else None,
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
    return result


def classify(directories: list[Path], required_from: list[Path] | None = None) -> dict[str, Any]:
    receipts = [classify_receipt(path) for path in directories]
    required: set[str] = set()
    for path in required_from or []:
        if path.suffix == ".jsonl":
            events, errors = read_stream(path)
            if errors:
                raise ValueError("; ".join(errors))
            manifests = [event for event in events if event.get("event") == "collection_finish"]
            if not manifests:
                raise ValueError(f"no collection manifest: {path}")
            for event in manifests:
                required.update(event["selected"])
        else:
            required.update(read_json(path)["selected"])
    union = {
        node: [receipt["nodes"][node]["status"] for receipt in receipts if node in receipt["nodes"]]
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
        "receipts": receipts,
        "rust": rust,
        "required": sorted(required),
        "required_unresolved": missing,
        "coverage": union,
    }


def _positive_timeout(value: str) -> float:
    import math

    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return timeout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument("--python-only", action="store_true")
    run.add_argument("--test-timeout", type=_positive_timeout, default=TEST_TIMEOUT)
    run.add_argument("--command-timeout", type=_positive_timeout, default=SESSION_TIMEOUT)
    run.add_argument("pytest_args", nargs=argparse.REMAINDER)
    inspect = sub.add_parser("classify")
    inspect.add_argument("--receipt-dir", action="append", type=Path, required=True)
    inspect.add_argument("--required-from", action="append", type=Path, default=[])
    args = parser.parse_args(argv)
    if args.action == "classify":
        result = classify(args.receipt_dir, args.required_from)
    else:
        directory = args.out_dir.resolve()
        directory.mkdir(parents=True, exist_ok=False)
        with supervision(directory) as control:
            versions: dict[str, str | None] = {}
            for package in ("pytest", "pytest-reportlog", "hypothesis", "psycopg", "SQLAlchemy"):
                try:
                    versions[package] = importlib.metadata.version(package)
                except importlib.metadata.PackageNotFoundError:
                    versions[package] = None
            write_json(
                directory / "invocation.json",
                {
                    "argv": sys.argv if argv is None else argv,
                    "cwd": str(Path.cwd()),
                    "source": source_identity(),
                    "python": sys.version,
                    "versions": versions,
                    "hypothesis_profile": "ci",
                    "session_timeout": args.command_timeout,
                    "test_timeout": args.test_timeout,
                    "python_only": args.python_only,
                },
            )
            pytest_args = args.pytest_args
            if pytest_args[:1] == ["--"]:
                pytest_args = pytest_args[1:]
            process = run_python(
                directory, pytest_args, timeout=args.command_timeout, test_timeout=args.test_timeout
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
