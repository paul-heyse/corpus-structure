"""Dispatch the checkout's owned recipes with literal argv."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

import typer


class RecipeError(ValueError):
    """A checkout or recipe prerequisite is unavailable."""


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
    )
