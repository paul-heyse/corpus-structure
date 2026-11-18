"""Compare final JSON and incremental reportlog with synthetic pytest cases."""

import errno
import importlib.metadata
import json
import os
import pty
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CASES = """
import os
import time
from pathlib import Path

import pytest


@pytest.fixture
def setup_error():
    pytest.fail("setup sentinel")


@pytest.fixture
def teardown_error():
    yield
    pytest.fail("teardown sentinel")


def test_01_pass(json_metadata):
    json_metadata["item_sentinel"] = "present"
    print("stdout sentinel")


def test_02_setup(setup_error):
    pass


def test_03_call():
    assert False, "call sentinel"


def test_04_teardown(teardown_error):
    pass


def test_05_wait():
    Path("started").touch()
    time.sleep(30)


def test_06_crash():
    os._exit(23)
"""

CLI = """
import json
import sys

import typer
from rich.console import Console
from rich.progress import Progress


def main(json_output: bool = True):
    console = Console(stderr=True)
    with Progress(console=console, disable=not console.is_terminal,
                  redirect_stdout=False, redirect_stderr=False) as progress:
        item = progress.add_task("diagnosing", total=1)
        if console.is_terminal:
            progress.refresh()
        progress.update(item, advance=1)
    if json_output:
        print(json.dumps({"outcome": "failed"}))
    raise typer.Exit(1)


typer.run(main)
"""


def pytest_case(root, name, *args, stop=None):
    folder = root / name
    folder.mkdir()
    (folder / "test_cases.py").write_text(CASES)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--json-report",
        "--json-report-file=report.json",
        "--report-log=report.jsonl",
        "--metadata",
        "session_sentinel",
        "present",
        *args,
    ]
    with subprocess.Popen(
        command, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as child:
        if stop is not None:
            deadline = time.monotonic() + 12
            while not (folder / "started").exists():
                if time.monotonic() >= deadline or child.poll() is not None:
                    child.kill()
                    raise RuntimeError(f"{name}: did not reach the wait case")
                time.sleep(0.025)
            child.send_signal(stop)
        stdout, stderr = child.communicate(timeout=20)
        status = child.returncode
    report_file, log_file = folder / "report.json", folder / "report.jsonl"
    report = json.loads(report_file.read_bytes()) if report_file.exists() else None
    events = (
        [json.loads(line) for line in log_file.read_text().splitlines()]
        if log_file.exists()
        else []
    )
    if not events:
        raise RuntimeError((name, status, stdout.decode(), stderr.decode()))

    def outcome(event):
        return [event["nodeid"], event.get("when"), event["outcome"]]

    return {
        "exit": status,
        "final_json": report is not None,
        "session_metadata": report["environment"].get("session_sentinel")
        if report
        else None,
        "collection_items": sum(
            len(entry.get("result", ())) for entry in report.get("collectors", ())
        )
        if report
        else None,
        "tests": {
            item["nodeid"]: {
                "outcome": item["outcome"],
                "phases": {
                    phase: item[phase]["outcome"]
                    for phase in ("setup", "call", "teardown")
                    if phase in item
                },
                "item_metadata": item.get("metadata", {}).get("item_sentinel"),
                "captured_stdout": "stdout sentinel"
                in item.get("call", {}).get("stdout", ""),
            }
            for item in report.get("tests", ())
        }
        if report
        else {},
        "reportlog_phases": [
            outcome(event)
            for event in events
            if event.get("$report_type") == "TestReport"
        ],
        "reportlog_session_finished": any(
            event.get("$report_type") == "SessionFinish" for event in events
        ),
    }


def presentation(root):
    program = root / "cli.py"
    program.write_text(CLI)
    env = dict(os.environ, TERM="xterm-256color")
    command = [sys.executable, str(program)]
    pipe = subprocess.run(command, capture_output=True, env=env, check=False)
    reader, writer = pty.openpty()
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=writer, env=env
    ) as child:
        os.close(writer)
        chunks = []
        try:
            while chunk := os.read(reader, 4096):
                chunks.append(chunk)
        except OSError as error:
            if error.errno != errno.EIO:
                raise
        finally:
            os.close(reader)
        stdout, _ = child.communicate(timeout=10)
    return {
        "pipe": {
            "exit": pipe.returncode,
            "stdout": json.loads(pipe.stdout),
            "stderr_bytes": len(pipe.stderr),
        },
        "stderr_tty": {
            "exit": child.returncode,
            "stdout": json.loads(stdout),
            "stderr_has_progress": b"diagnosing" in b"".join(chunks),
        },
    }


def main():
    with tempfile.TemporaryDirectory(prefix="tdm-reporting-") as temp:
        root = Path(temp)
        standard = ("-k", "not wait and not crash")
        result = {
            "python": sys.version.split()[0],
            "versions": {
                package: importlib.metadata.version(package)
                for package in (
                    "pytest",
                    "pytest-xdist",
                    "pytest-reportlog",
                    "pytest-json-report",
                    "pytest-metadata",
                    "pluggy",
                    "typer",
                    "rich",
                )
            },
            "serial": pytest_case(root, "serial", *standard),
            "xdist": pytest_case(root, "xdist", "-n", "2", *standard),
            "interrupt": pytest_case(
                root, "interrupt", "-k", "01_pass or 05_wait", stop=signal.SIGINT
            ),
            "controller_kill": pytest_case(
                root, "controller-kill", "-k", "01_pass or 05_wait", stop=signal.SIGKILL
            ),
            "worker_loss": pytest_case(
                root,
                "worker-loss",
                "-n",
                "2",
                "--max-worker-restart=0",
                "-k",
                "01_pass or 06_crash",
            ),
            "presentation": presentation(root),
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
