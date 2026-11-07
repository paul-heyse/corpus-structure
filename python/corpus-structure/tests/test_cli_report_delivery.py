"""Process-level controls for report output, including interpreter shutdown."""

import os
import subprocess
import sys

import pytest


def _closed_pipe(*args: str, code: str = "from corpus_structure.cli.app import main; main()"):
    reader, writer = os.pipe()
    os.close(reader)
    try:
        return subprocess.run(
            [sys.executable, "-c", code, *args],
            stdout=writer,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
    finally:
        os.close(writer)


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
