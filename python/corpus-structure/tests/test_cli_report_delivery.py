"""Process-level controls for report output, including interpreter shutdown."""

import os
import subprocess
import sys

import pytest


def _closed_pipe(
    *args: str,
    code: str = "from corpus_structure.cli.app import main; main()",
    close_stderr=False,
    full_stderr=False,
):
    reader, writer = os.pipe()
    os.close(reader)
    stderr = subprocess.PIPE
    if close_stderr:
        error_reader, stderr = os.pipe()
        os.close(error_reader)
    elif full_stderr:
        stderr = os.open("/dev/full", os.O_WRONLY)
    try:
        return subprocess.run(
            [sys.executable, "-c", code, *args],
            stdout=writer,
            stderr=stderr,
            check=False,
            timeout=15,
        )
    finally:
        os.close(writer)
        if close_stderr or full_stderr:
            os.close(stderr)


@pytest.mark.parametrize("args", [(), ("--json",)])
def test_existing_report_honors_closed_stdout(tmp_path, monkeypatch, args):
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path))
    process = _closed_pipe("results", "list", *args)
    assert process.returncode == 74
    assert process.stderr == b"ci: stdout closed before report delivery completed\n"


def test_reporting_a_refusal_preserves_failure_exit(tmp_path, monkeypatch):
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path))
    process = _closed_pipe("results", "show", "0" * 32, "--json")
    assert process.returncode == 1
    assert process.stderr == b"ci: stdout closed before report delivery completed\n"


@pytest.mark.parametrize(("size", "status"), [(1, 74), (65536, 74), (1, 130)])
def test_stream_delivery_handles_write_and_flush(size, status):
    process = _closed_pipe(
        code=f"""import typer
from corpus_structure.cli.output import write_report_bytes

def report():
    write_report_bytes(b"x" * {size}, exit_code={130 if status == 130 else 0})

typer.run(report)
"""
    )
    assert process.returncode == status
    assert process.stderr == b"ci: stdout closed before report delivery completed\n"


@pytest.mark.parametrize(("size", "operation_exit"), [(1, 0), (65536, 0), (1, 143)])
def test_stream_delivery_survives_stderr_io_error(size, operation_exit):
    process = _closed_pipe(
        code=f"""import typer
from corpus_structure.cli.output import write_report_bytes

def report():
    write_report_bytes(b"x" * {size}, exit_code={operation_exit})

typer.run(report)
""",
        full_stderr=True,
    )
    assert process.returncode == (operation_exit or 74)


def test_installed_reference_honors_closed_stdout():
    process = _closed_pipe("docs", "commands", "schema", "inspect", "--stdout")
    assert process.returncode == 74
    assert process.stderr == b"ci: stdout closed before report delivery completed\n"


def test_headless_json_keeps_terminal_stage_diagnostics_separate(tmp_path, monkeypatch):
    import errno
    import json
    import pty

    from corpus_structure.cli.managed import ResultStore

    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path))
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.setenv("NO_COLOR", "1")
    reader, terminal = pty.openpty()
    try:
        with ResultStore(tmp_path).operation("test", scope={"lane": "ordinary"}) as result:
            result.stage("ordinary", lane_counts={"ordinary": {"selected": 3, "passed": 1}})
            process = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from corpus_structure.cli.app import main; main()",
                    "results",
                    "watch",
                    result.id,
                    "--seconds",
                    "0.01",
                    "--json",
                ],
                stdout=subprocess.PIPE,
                stderr=terminal,
                check=False,
                timeout=15,
            )
            assert process.returncode == 0
            assert json.loads(process.stdout)["custody"] == "unsettled"
    finally:
        os.close(terminal)
    with os.fdopen(reader, "rb", buffering=0) as stream:
        chunks = []
        try:
            while chunk := stream.read(4096):
                chunks.append(chunk)
        except OSError as error:
            if error.errno != errno.EIO:
                raise
    diagnostic = b"".join(chunks)
    assert b"selected=3, passed=1" in diagnostic
    assert b"\x1b[" not in diagnostic


@pytest.mark.parametrize(
    ("args", "status"),
    [
        (("results", "list"), 74),
        (("results", "list", "--json"), 74),
        (("results", "show", "0" * 32, "--json"), 1),
    ],
)
def test_both_closed_pipes_preserve_exit(tmp_path, monkeypatch, args, status):
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path))
    assert _closed_pipe(*args, close_stderr=True).returncode == status
