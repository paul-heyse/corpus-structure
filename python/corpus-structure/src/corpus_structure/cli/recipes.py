"""Dispatch the checkout's owned recipes with literal argv."""

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer


class RecipeError(ValueError):
    """A checkout or recipe prerequisite is unavailable."""


@dataclass(frozen=True)
class RecipeStep:
    name: str
    outcome: Literal["passed", "failed", "interrupted", "not_started", "unobserved"]
    exit_code: int | None = None


_STEP_FD = "CORPUS_CI_STEP_FD"
_STEP_BYTES = 4096  # The _bundle plan and its two records per step fit in this pipe budget.


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
        if proc.poll() is None:
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
                    proc.wait(timeout=5)
                    raise RecipeError(
                        "recipe did not report settlement after cancellation"
                    ) from None
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


def run_recipe_steps(
    name: str,
) -> tuple[subprocess.CompletedProcess[str], tuple[RecipeStep, ...]]:
    """Collect only owned bundle records, independently of foreign stdout and stderr."""
    read_fd, write_fd = os.pipe()
    try:
        try:
            os.set_blocking(write_fd, False)
            process = run_recipe(
                name, env={**os.environ, _STEP_FD: str(write_fd)}, pass_fds=(write_fd,)
            )
        finally:
            os.close(write_fd)
        try:
            os.set_blocking(read_fd, False)
            body = os.read(read_fd, _STEP_BYTES + 1)
        except BlockingIOError:
            body = b""
    finally:
        os.close(read_fd)
    interrupted = process.returncode in (130, 143, -signal.SIGINT, -signal.SIGTERM)
    return process, _recipe_steps(body, interrupted=interrupted)


def _recipe_steps(body: bytes, *, interrupted: bool) -> tuple[RecipeStep, ...]:
    if not body.endswith(b"\n") or len(body) > _STEP_BYTES or not body.isascii():
        return ()
    header, *records = [line.split() for line in body.decode("ascii").splitlines()]
    if not header or header[0] != "plan" or not header[1:]:
        return ()
    names = header[1:]
    if len(names) > 24 or len(names) != len(set(names)):
        return ()
    if any(not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", name) for name in names):
        return ()
    events = iter(records)
    steps = []
    for name in names:
        start = next(events, None)
        if start is None:
            steps.append(RecipeStep(name, "not_started" if interrupted else "unobserved"))
            continue
        if start != ["start", name]:
            return ()
        match next(events, None):
            case ["exit", exit_name, code] if exit_name == name and code.isdecimal():
                if len(code) > 3:
                    return ()
                status = int(code)
                if status > 255:
                    return ()
                steps.append(RecipeStep(name, "failed" if status else "passed", status))
            case None:
                steps.append(RecipeStep(name, "interrupted" if interrupted else "unobserved"))
            case _:
                return ()
    return tuple(steps) if next(events, None) is None else ()
