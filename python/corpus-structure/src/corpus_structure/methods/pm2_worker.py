"""Locked native-runtime inspection and shared protocol/process helpers."""
from __future__ import annotations
import json
import math
import os
import shutil
import subprocess
from hashlib import file_digest
from pathlib import Path
from typing import Any

class Pm2WorkerRefused(ValueError):
    """A native request was not admitted."""

class Pm2WorkerError(RuntimeError):
    """An admitted native host or protocol failed."""

def preflight_pm2_runtime(
    *, python: Path, script: Path, project: Path, provider: str, assets: Path
) -> dict[str, Any]:
    """Verify the selected installed lock and authenticated assets before task reuse."""
    uv = shutil.which("uv")
    if uv is None:
        raise Pm2WorkerRefused("uv is unavailable for the PM2 locked environment check")
    lock = project / "uv.lock"
    environment = {
        "PATH": os.defpath,
        "UV_PROJECT_ENVIRONMENT": str(python.absolute().parent.parent),
    }
    # The root d1 environment can also hold optional workspace groups. They are
    # all captured by the worker inventory, even when not needed for this check.
    inexact = ["--inexact"] if project.resolve() == Path(__file__).resolve().parents[5] else []
    try:
        with lock.open("rb") as stream:
            lock_digest = file_digest(stream, "sha256").hexdigest()
        checked = subprocess.run(
            [
                uv,
                "sync",
                "--locked",
                "--check",
                "--offline",
                "--no-python-downloads",
                "--project",
                str(project.absolute()),
                "--python",
                str(python.absolute()),
                *inexact,
            ],
            env=environment,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if checked.returncode:
            raise Pm2WorkerRefused(
                f"{provider} worker environment does not match its lock; check the selected "
                "project and interpreter with uv sync --locked --check --offline"
                + (" --inexact" if inexact else "")
            )
        probe = subprocess.run(
            [
                str(python.absolute()),
                "-I",
                "-u",
                str(script.absolute()),
                "--preflight",
                provider,
                str(assets.absolute()),
            ],
            env={"PATH": os.defpath},
            capture_output=True,
            timeout=90,
            check=True,
        )
        reply = json.loads(probe.stdout, object_pairs_hook=_json_object, parse_float=_finite_float)
        if not isinstance(reply, dict):
            raise Pm2WorkerRefused("PM2 runtime preflight requires an object reply")
        if reply.get("kind") == "error":
            raise Pm2WorkerRefused(
                f"{provider} profile preflight failed: {reply['message'][:1800]}"
            )
        payload = reply.get("payload")
        if reply.get("kind") != "ready" or not isinstance(payload, dict):
            raise Pm2WorkerRefused("PM2 runtime preflight did not return a profile")
        if payload["runtime_identity"]["lock_sha256"] != lock_digest:
            raise Pm2WorkerRefused("PM2 lock changed during profile preflight")
    except Pm2WorkerRefused:
        raise
    except (OSError, subprocess.SubprocessError, TypeError, ValueError, KeyError) as error:
        raise Pm2WorkerRefused(
            f"{provider} profile preflight failed: {type(error).__name__}"
        ) from error
    return payload


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON value")
    return number


def _live_group(group: int) -> bool:
    # Linux reports zombies as group members too. They have no device resources
    # and adopted descendants may remain zombies until their new parent reaps them.
    with os.scandir("/proc") as entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                stat = Path(entry.path, "stat").read_bytes().rpartition(b")")[2].split()
            except FileNotFoundError, ProcessLookupError, PermissionError:
                continue
            if int(stat[2]) == group and stat[0] not in {b"Z", b"X", b"x"}:
                return True
    return False
