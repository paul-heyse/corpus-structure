"""Bounded terminal-safe capture for an individual owned check process."""

from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from typing import Literal

_OUTCOME_FD = "CORPUS_CI_STEP_OUTCOME_FD"
_READ_BYTES = 8192
EXCERPT_CHARS = 1200
STEP_STREAM_BYTES = 128 * 1024
MAX_RECIPE_STEPS = 24
# Each safe UTF-8 payload can double when JSON escapes quotes/newlines. Reserve
# fixed metadata and the two existing bounded excerpts for every declared step.
STEP_CHANNEL_BYTES = MAX_RECIPE_STEPS * (4 * STEP_STREAM_BYTES + 16384) + 4096


@dataclass(frozen=True)
class StepExcerpt:
    step: str
    stream: Literal["stdout", "stderr"]
    text: str
    truncated: bool
    basis: Literal["retained_safe_output"] | None = None


@dataclass(frozen=True)
class StepOutput:
    stream: Literal["stdout", "stderr"]
    text: str
    source_coordinate: Literal["native_bytes", "decoded_process_utf8_bytes"]
    observed_source_bytes: int
    examined_source_bytes: int
    unexamined_source_bytes: int
    derived_safe_bytes: int
    retained_safe_bytes: int
    omitted_safe_bytes: int
    truncated: bool
    retained_safe_bytes_limit: int = STEP_STREAM_BYTES


@dataclass(frozen=True)
class StepExit:
    name: str
    status: int
    interrupted: bool
    no_rules: bool
    excerpts: tuple[StepExcerpt, ...]
    outputs: tuple[StepOutput, ...] = ()


_TERMINAL = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_CREDENTIAL = re.compile(
    r"(://[^:/@\s]+:)[^@/\s]+(?=@)|"
    r"(?i:(password|token|api[_-]?key)\s*=\s*)(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|[^\s&]+)"
)


def _credential_secrets() -> Iterator[str]:
    for key, secret in os.environ.items():
        if secret and (
            key == "PGPASSWORD"
            or (
                key.startswith("CORPUS_")
                and any(part in key for part in ("PASSWORD", "TOKEN", "API_KEY"))
            )
        ):
            yield secret


def safe_text(value: str) -> str:
    """Remove terminal controls and redact credentials from complete diagnostic text."""
    value = _CONTROL.sub("", _TERMINAL.sub("", value))
    for secret in _credential_secrets():
        value = value.replace(secret, "**********")
    return _CREDENTIAL.sub(lambda match: (match[1] or f"{match[2]}=") + "**********", value)


def bounded_safe_output(
    stream: Literal["stdout", "stderr"],
    safe: str,
    *,
    source_coordinate: Literal["native_bytes", "decoded_process_utf8_bytes"],
    observed_source_bytes: int,
    examined_source_bytes: int,
) -> StepOutput:
    """Bound an already-safe complete selection; this function does not sanitize again."""
    encoded = safe.encode("utf-8", errors="replace")
    text = encoded[:STEP_STREAM_BYTES].decode("utf-8", errors="ignore")
    retained = len(text.encode("utf-8"))
    unexamined = observed_source_bytes - examined_source_bytes
    return StepOutput(
        stream,
        text,
        source_coordinate,
        observed_source_bytes,
        examined_source_bytes,
        unexamined,
        len(encoded),
        retained,
        len(encoded) - retained,
        bool(unexamined or len(encoded) > retained),
    )


_INCOMPLETE_QUOTED = re.compile(
    r"(?i:(?:password|token|api[_-]?key)\s*=\s*)"
    r"(?:'(?:\\[\s\S]|[^'\\])*(?:\\)?|\"(?:\\[\s\S]|[^\"\\])*(?:\\)?)\Z"
)
_INCOMPLETE_OSC = re.compile(r"\x1b\][^\x07\x1b]*\Z")


def _unfinished_secret_suffix(text: str, secret: str) -> bool:
    """Find a cut known-secret prefix with a linear prefix scan, including multiline values."""
    failure = [0] * len(secret)
    matched = 0
    for index in range(1, len(secret)):
        while matched and secret[index] != secret[matched]:
            matched = failure[matched - 1]
        if secret[index] == secret[matched]:
            matched += 1
        failure[index] = matched
    matched = 0
    for character in text:
        while matched and character != secret[matched]:
            matched = failure[matched - 1]
        if character == secret[matched]:
            matched += 1
        if matched == len(secret):
            # safe_text replaces complete, nonoverlapping occurrences itself.
            matched = 0
    return matched > 0


def _complete_prefix(prefix: bytes) -> bytes:
    prefix = prefix[: prefix.rfind(b"\n") + 1]
    text = prefix.decode("utf-8", errors="replace")
    cut = len(text)
    spans = [
        (match.start(), match.end())
        for pattern in (_CREDENTIAL, _TERMINAL)
        for match in pattern.finditer(text)
    ]
    for pattern in (_INCOMPLETE_QUOTED, _INCOMPLETE_OSC):
        incomplete = pattern.search(text)
        if incomplete is not None:
            cut = min(cut, incomplete.start())
    for secret in _credential_secrets():
        if "\n" not in secret:
            continue
        if _unfinished_secret_suffix(text, secret):
            # Mapping a cut environment secret back to another token could itself expose
            # a fragment. Omit this bounded selection rather than retain any such fragment.
            return b""
        position = text.find(secret)
        while position >= 0:
            spans.append((position, position + len(secret)))
            position = text.find(secret, position + len(secret))
    # A cut inside a complete enclosing credential/control token moves to its start.
    # Descending starts preserve this property for nested/overlapping protected spans.
    cut = text.rfind("\n", 0, cut) + 1 if cut < len(text) else cut
    for start, end in sorted(spans, reverse=True):
        if start < cut < end:
            cut = text.rfind("\n", 0, start) + 1
    # Newlines map exactly across UTF-8 replacement decoding. Count the retained byte
    # boundary without guessing byte positions from replacement characters.
    position = 0
    for _ in range(text[:cut].count("\n")):
        position = prefix.index(b"\n", position) + 1
    return prefix[:position]


def safe_prefix_output(
    stream: Literal["stdout", "stderr"],
    prefix: bytes,
    observed: int,
) -> StepOutput:
    """Sanitize complete retained tokens, never a credential/control token cut by collection."""
    if observed > len(prefix):
        prefix = _complete_prefix(prefix)
    safe = safe_text(prefix.decode("utf-8", errors="replace"))
    return bounded_safe_output(
        stream,
        safe,
        source_coordinate="native_bytes",
        observed_source_bytes=observed,
        examined_source_bytes=len(prefix),
    )


def valid_step_output(output: StepOutput) -> bool:
    """Check the declared selected-source and derived-text accounting at a read boundary."""
    return (
        output.retained_safe_bytes_limit == STEP_STREAM_BYTES
        and 0 <= output.examined_source_bytes <= output.observed_source_bytes
        and output.unexamined_source_bytes
        == output.observed_source_bytes - output.examined_source_bytes
        and output.retained_safe_bytes == len(output.text.encode("utf-8")) <= STEP_STREAM_BYTES
        and output.derived_safe_bytes >= output.retained_safe_bytes
        and output.omitted_safe_bytes == output.derived_safe_bytes - output.retained_safe_bytes
        and output.truncated == bool(output.unexamined_source_bytes or output.omitted_safe_bytes)
    )


def _capture_step(name: str, report_fd: int) -> int:
    """Run one owned check; safe selections feed retained output and compact excerpts."""
    prefixes = {"stdout": bytearray(), "stderr": bytearray()}
    observed = {"stdout": 0, "stderr": 0}
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
                    chunk = os.read(key.fd, _READ_BYTES)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    observed[key.data] += len(chunk)
                    prefixes[key.data].extend(
                        chunk[: max(0, STEP_STREAM_BYTES - len(prefixes[key.data]))]
                    )
        os.set_blocking(read_fd, False)
        try:
            no_rules = os.read(read_fd, 128) == b"no_rules\n"
        except BlockingIOError:
            no_rules = False
    finally:
        os.close(read_fd)

    status = child.returncode
    status = 128 + (signum or -status) if signum or status < 0 else status
    outputs = tuple(
        safe_prefix_output(stream, bytes(prefixes[stream]), observed[stream])
        for stream in ("stdout", "stderr")
    )
    excerpts = []
    if status:
        for output in outputs:
            content = output.text.strip()
            truncated = output.truncated or len(content) > EXCERPT_CHARS
            if content or truncated:
                excerpts.append(
                    StepExcerpt(
                        name,
                        output.stream,
                        content[-EXCERPT_CHARS:],
                        truncated,
                        basis="retained_safe_output",
                    )
                )
    observation = StepExit(name, status, signum is not None, no_rules, tuple(excerpts), outputs)
    try:
        with os.fdopen(report_fd, "wb", closefd=False) as report:
            report.write(json.dumps(asdict(observation), ensure_ascii=False).encode() + b"\n")
    except OSError:
        # Losing an optional report channel cannot replace the native step's status.
        pass
    return status


if __name__ == "__main__":
    raise SystemExit(_capture_step(sys.argv[1], int(sys.argv[2])))
