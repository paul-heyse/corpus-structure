"""Dispatch the checkout's owned recipes with literal argv."""

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer
from pydantic import TypeAdapter, ValidationError

from corpus_structure._diagnostic_capture import (
    EXCERPT_CHARS,
    MAX_RECIPE_STEPS,
    STEP_CHANNEL_BYTES,
    StepExcerpt,
    StepExit,
    valid_step_output,
)


class RecipeError(ValueError):
    """A checkout or recipe prerequisite is unavailable."""


class RecipeCancellation(RecipeError):
    """The owner observed a signal but could not establish settlement."""

    def __init__(self, signum: int):
        self.signum = signum
        super().__init__("recipe did not report settlement after cancellation")


@dataclass(frozen=True)
class RecipeStep:
    name: str
    outcome: Literal["passed", "failed", "not_run", "interrupted", "not_started", "unobserved"]
    exit_code: int | None = None
    reason: str | None = None


_STEP_FD = "CORPUS_CI_STEP_FD"
_STEP_BYTES = STEP_CHANNEL_BYTES
_STEP_EXIT = TypeAdapter(StepExit)


def checkout(ctx: typer.Context | None = None) -> Path:
    if ctx is not None and (resolved := ctx.meta.get("checkout")) is not None:
        return resolved
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "justfile").is_file() and (candidate / "scripts/setup-env").is_file():
            if ctx is not None:
                ctx.meta["checkout"] = candidate
            return candidate
    raise RecipeError("run from a prepared corpus-structure checkout")


def run_owned(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    """Give recipe supervisors time to settle their own child process groups."""
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        pass_fds=pass_fds,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    signum: int | None = None
    deadline: float | None = None

    def forward(number: int, _frame: object) -> None:
        nonlocal signum, deadline
        if signum is not None:
            return
        signum = number
        deadline = time.monotonic() + 45
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, number)

    previous = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, forward)
    try:
        # communicate(timeout) periodically returns control after signal delivery,
        # even when an intermediate process leaves one of the pipe writers open.
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if deadline is not None and time.monotonic() >= deadline:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGKILL)
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        proc.wait(timeout=5)
                    assert signum is not None
                    raise RecipeCancellation(signum) from None
        return subprocess.CompletedProcess(
            argv, proc.returncode if signum is None else 128 + signum, stdout, stderr
        )
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()


def run_recipe(
    name: str,
    *args: str,
    env: dict[str, str] | None = None,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    root = checkout()
    return run_owned(
        [
            "just",
            "--justfile",
            str(root / "justfile"),
            "--working-directory",
            str(root),
            name,
            *args,
        ],
        cwd=root,
        env=env,
        pass_fds=pass_fds,
    )


@dataclass(frozen=True)
class RecipeCapture:
    availability: Literal["available", "unavailable"]
    reason: str | None = None
    records: tuple[StepExit, ...] = ()
    missing_steps: tuple[str, ...] = ()


def run_recipe_steps(
    name: str,
    *args: str,
) -> tuple[
    subprocess.CompletedProcess[str], tuple[RecipeStep, ...], tuple[StepExcerpt, ...], RecipeCapture
]:
    """Drain the owned side channel independently of the recipe's ordinary streams."""
    read_fd, write_fd = os.pipe()
    body = bytearray()
    read_failure: list[str] = []

    def drain() -> None:
        try:
            with os.fdopen(read_fd, "rb") as stream:
                while chunk := stream.read1(8192):
                    remaining = max(0, _STEP_BYTES + 1 - len(body))
                    body.extend(chunk[:remaining])
        except OSError as error:
            read_failure.append(type(error).__name__)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        process = run_recipe(
            name,
            *args,
            env={
                **os.environ,
                _STEP_FD: str(write_fd),
                "CORPUS_CI_STEP_PYTHON": sys.executable,
            },
            pass_fds=(write_fd,),
        )
    finally:
        os.close(write_fd)
        reader.join(timeout=2)
    if reader.is_alive() or read_failure:
        return process, (), (), RecipeCapture("unavailable", "step channel reader did not settle")
    interrupted = process.returncode in (130, 143, -signal.SIGINT, -signal.SIGTERM)
    steps, excerpts, captured = _recipe_steps(bytes(body), interrupted=interrupted)
    return process, steps, excerpts, captured


def _recipe_steps(
    body: bytes, *, interrupted: bool
) -> tuple[tuple[RecipeStep, ...], tuple[StepExcerpt, ...], RecipeCapture]:
    if len(body) > _STEP_BYTES:
        return (), (), RecipeCapture("unavailable", "step channel byte limit exceeded")
    if not body.endswith(b"\n"):
        return (), (), RecipeCapture("unavailable", "step channel is incomplete")
    header, *records = body.rstrip(b"\n").split(b"\n")
    if not header.startswith(b"plan ") or not header.isascii():
        return (), (), RecipeCapture("unavailable", "step channel is invalid")
    names = header.decode("ascii").split()[1:]
    if len(names) > MAX_RECIPE_STEPS or len(names) != len(set(names)):
        return (), (), RecipeCapture("unavailable", "step channel is invalid")
    if any(not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", name) for name in names):
        return (), (), RecipeCapture("unavailable", "step channel is invalid")
    events = iter(records)
    steps = []
    excerpts = []
    captured = []
    missing = []
    for name in names:
        start = next(events, None)
        if start is None:
            missing.append(name)
            steps.append(RecipeStep(name, "not_started" if interrupted else "unobserved"))
            continue
        if start != f"start {name}".encode():
            return (), (), RecipeCapture("unavailable", "step channel is invalid")
        end = next(events, None)
        if end is None:
            missing.append(name)
            steps.append(RecipeStep(name, "interrupted" if interrupted else "unobserved"))
            continue
        try:
            exit = _STEP_EXIT.validate_json(end, strict=True)
        except ValidationError:
            return (), (), RecipeCapture("unavailable", "step channel is invalid")
        if exit.name != name or not 0 <= exit.status <= 255:
            return (), (), RecipeCapture("unavailable", "step channel is invalid")
        if any(item.step != name or len(item.text) > EXCERPT_CHARS for item in exit.excerpts):
            return (), (), RecipeCapture("unavailable", "step channel is invalid")
        if (
            {item.stream for item in exit.outputs} != {"stdout", "stderr"}
            or len(exit.outputs) != 2
            or not all(valid_step_output(item) for item in exit.outputs)
        ):
            return (), (), RecipeCapture("unavailable", "step output accounting is invalid")
        captured.append(exit)
        if exit.interrupted:
            steps.append(RecipeStep(name, "interrupted"))
        elif exit.status:
            steps.append(RecipeStep(name, "failed", exit.status))
        elif exit.no_rules:
            steps.append(RecipeStep(name, "not_run", 0, "no rules yet"))
        else:
            steps.append(RecipeStep(name, "passed", 0))
        excerpts.extend(exit.excerpts)
    if next(events, None) is not None:
        return (), (), RecipeCapture("unavailable", "step channel has unexpected records")
    return (
        tuple(steps),
        tuple(excerpts),
        RecipeCapture("available", records=tuple(captured), missing_steps=tuple(missing)),
    )
