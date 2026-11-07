"""Bounded Rich/Typer presentation and stream controls, with synthetic input."""

import errno
import io
import json
import os
import pty
import select
import signal
import subprocess
import sys
from importlib.metadata import version
from textwrap import dedent

from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import safe_text

CHILD = dedent("""
    import json
    import sys
    import time
    from typing import Annotated

    import typer
    from rich.console import Console
    from rich.live import Live

    app = typer.Typer()

    @app.command()
    def main(source: Annotated[typer.FileText, typer.Argument()], wait: bool = False):
        row = json.load(source)
        console = Console(stderr=True)
        if console.is_terminal:
            with Live(
                "validating", console=console, auto_refresh=False,
                redirect_stdout=False, redirect_stderr=False,
            ) as live:
                if wait:
                    print("live-entered", file=sys.stderr, flush=True)
                    time.sleep(30)
                live.update("settled", refresh=True)
                typer.echo(json.dumps({"selected": row["selected"]}))
        else:
            console.print("validating")
            typer.echo(json.dumps({"selected": row["selected"]}))

    app()
""")
INPUT = b'{"selected":5119}'
EXPECTED = b'{"selected": 5119}\n'
ARGV = [sys.executable, "-c", CHILD, "-"]
ENV = {**os.environ, "TERM": "xterm-256color", "NO_COLOR": "1"}


def render(renderable, width):
    stream = io.StringIO()
    Console(file=stream, width=width, force_terminal=False, color_system=None).print(renderable)
    return stream.getvalue()


def terminal_run(*, interrupt=False):
    master, slave = pty.openpty()
    try:
        try:
            child = subprocess.Popen(
                [*ARGV, "--wait"] if interrupt else ARGV,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=slave,
                env=ENV,
            )
        finally:
            os.close(slave)
        with child:
            try:
                if interrupt:
                    assert child.stdin is not None
                    child.stdin.write(INPUT)
                    child.stdin.close()
                    first = bytearray()
                    while b"live-entered" not in first:
                        assert select.select([master], [], [], 5)[0]
                        chunk = os.read(master, 4096)
                        assert chunk
                        first.extend(chunk)
                    assert b"\x1b[?25l" in first
                    child.send_signal(signal.SIGINT)
                    child.wait(timeout=5)
                    assert child.stdout is not None
                    stdout = child.stdout.read()
                else:
                    stdout, _ = child.communicate(INPUT, timeout=5)
                stderr = bytearray()
                while True:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        break
                    if not chunk:
                        break
                    stderr.extend(chunk)
                return child.returncode, stdout, bytes(stderr)
            finally:
                if child.poll() is None:
                    child.kill()
    finally:
        os.close(master)


def main():
    nodes = [f"tests/unit/test_coverage.py::test_case[{index}]" for index in range(5119)]
    table = Table("Decision", "Value")
    table.add_row("Required", "5119")
    table.add_row("Unresolved", "1")
    table.add_row("Node", Text(nodes[-1]))
    payload = {"status": "failed", "unresolved": nodes[-1:], "required": nodes}
    lines = {
        width: {
            "table": len(render(table, width).splitlines()),
            "pretty": len(render(Pretty(payload), width).splitlines()),
        }
        for width in (44, 100)
    }
    literal = Text(safe_text("見 [bold] x \x1b[31mred\x1b[0m password=s3cret"))
    assert render(literal, 100) == "見 [bold] x red password=**********\n"
    pipe = subprocess.run(ARGV, input=INPUT, capture_output=True, env=ENV, timeout=5, check=True)
    assert pipe.stdout == EXPECTED
    assert pipe.stderr == b"validating\n"
    status, stdout, stderr = terminal_run()
    assert status == 0 and stdout == EXPECTED
    assert b"\x1b[?25l" in stderr and b"\x1b[?25h" in stderr
    status, stdout, stderr = terminal_run(interrupt=True)
    assert status == 130 and stdout == b""
    assert b"\x1b[?25h" in stderr
    print(json.dumps({
        "python": sys.version.split()[0],
        "rich": version("rich"),
        "typer": version("typer"),
        "synthetic_nodes": len(nodes),
        "rendered_lines": lines,
        "literal_unicode_markup_and_redaction": "passed",
        "typed_stdin_clean_json_with_pipe_and_stderr_pty": "passed",
        "no_color_still_permits_cursor_controls": True,
        "sigint_cursor_restored": True,
        "synthetic_typer_sigint_exit": status,
    }, indent=2))


if __name__ == "__main__":
    main()
