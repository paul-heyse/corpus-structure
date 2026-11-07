"""Bounded terminal-safe capture for an individual owned check process."""

from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Literal

_OUTCOME_FD = "CORPUS_CI_STEP_OUTCOME_FD"
_TAIL_BYTES = 8192
EXCERPT_CHARS = 1200


@dataclass(frozen=True)
class StepExcerpt:
    step: str
    stream: Literal["stdout", "stderr"]
    text: str
    truncated: bool


@dataclass(frozen=True)
class StepExit:
    name: str
    status: int
    interrupted: bool
    no_rules: bool
    excerpts: tuple[StepExcerpt, ...]


_TERMINAL = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_CREDENTIAL = re.compile(
    r"(://[^:/@\s]+:)[^@/\s]+(?=@)|"
    r"(?i:(password|token|api[_-]?key)\s*=\s*)(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|[^\s&]+)"
)


def safe_text(value: str) -> str:
    """Remove terminal controls and redact credentials from complete diagnostic text."""
    value = _CONTROL.sub("", _TERMINAL.sub("", value))
    for key, secret in os.environ.items():
        if secret and (
            key == "PGPASSWORD"
            or (
                key.startswith("CORPUS_")
                and any(part in key for part in ("PASSWORD", "TOKEN", "API_KEY"))
            )
        ):
            value = value.replace(secret, "**********")
    return _CREDENTIAL.sub(lambda match: (match[1] or f"{match[2]}=") + "**********", value)


def _capture_step(name: str, report_fd: int) -> int:
    """Run one owned check in the bundle's group, keeping bounded stream tails."""
    tails: dict[Literal["stdout", "stderr"], bytearray] = {
        "stdout": bytearray(),
        "stderr": bytearray(),
    }
    clipped = set()
    signum = None

    def interrupt(number: int, _frame: object) -> None:
        nonlocal signum
        signum = number

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupt)

    read_fd, write_fd = os.pipe()
    try:
        try:
            child = subprocess.Popen(
                ["just", name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, _OUTCOME_FD: str(write_fd)},
                pass_fds=(write_fd,),
            )
        finally:
            os.close(write_fd)
        with child, selectors.DefaultSelector() as selector:
            for stream, pipe in (("stdout", child.stdout), ("stderr", child.stderr)):
                assert pipe is not None
                selector.register(pipe, selectors.EVENT_READ, stream)
            while selector.get_map():
                for key, _ in selector.select():
                    chunk = os.read(key.fd, _TAIL_BYTES)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    tail = tails[key.data]
                    tail.extend(chunk)
                    if len(tail) > _TAIL_BYTES:
                        del tail[:-_TAIL_BYTES]
                        clipped.add(key.data)
        os.set_blocking(read_fd, False)
        try:
            no_rules = os.read(read_fd, 128) == b"no_rules\n"
        except BlockingIOError:
            no_rules = False
    finally:
        os.close(read_fd)

    status = child.returncode
    status = 128 + (signum or -status) if signum or status < 0 else status
    excerpts = []
    if status:
        for stream, tail in tails.items():
            # Discard the clipped first line so a partial credential cannot bypass redaction.
            if stream in clipped:
                _, _, tail = tail.partition(b"\n")
            content = safe_text(tail.decode("utf-8", errors="replace")).strip()
            truncated = stream in clipped or len(content) > EXCERPT_CHARS
            if content or truncated:
                excerpts.append(StepExcerpt(name, stream, content[-EXCERPT_CHARS:], truncated))
    observation = StepExit(name, status, signum is not None, no_rules, tuple(excerpts))
    with os.fdopen(report_fd, "wb", closefd=False) as report:
        report.write(json.dumps(asdict(observation), ensure_ascii=False).encode() + b"\n")
    return status


if __name__ == "__main__":
    raise SystemExit(_capture_step(sys.argv[1], int(sys.argv[2])))
