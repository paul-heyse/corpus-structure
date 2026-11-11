"""Explicit characterization-session ownership of the existing CPU model workers."""

from __future__ import annotations

import json
from collections.abc import Callable, Generator, Mapping
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from .gliner import GlinerProfile
from .gliner_worker import GlinerWorker
from .pm2_worker import Pm2Worker, Pm2WorkerRefused
from .pm2_worker import open_pm2_worker as _open_pm2_worker
from .pm2_worker import preflight_pm2_runtime as _preflight_pm2_runtime

_PROVIDERS = ("hanlp", "maverick", "dipo", "d1")
_session: ContextVar[_Session | None] = ContextVar("characterization_resources", default=None)


def _active(check_active: Callable[[], None] | None) -> None:
    if check_active is not None:
        check_active()


class _Pm2Slot:
    def __init__(self) -> None:
        self.gate = Lock()
        self.stack = ExitStack()
        self.worker: Pm2Worker | None = None
        self.key: object = None
        self.callback: Callable[[], None] | None = None
        self.preflight: tuple[bytes, dict[str, Any]] | None = None

    def check_active(self) -> None:
        # This callback, captured by the child owner at startup, never captures a lease.
        if self.callback is None:
            raise Pm2WorkerRefused("characterization worker has no active borrower")
        self.callback()

    def close(self, *exception) -> None:
        stack, self.stack = self.stack, ExitStack()
        self.worker, self.key = None, None
        if exception:
            stack.__exit__(*exception)
        else:
            stack.close()


class _GlinerSlot:
    def __init__(self) -> None:
        self.gate = Lock()
        self.worker: GlinerWorker | None = None
        self.profile: GlinerProfile | None = None

    def close(self) -> None:
        worker, self.worker = self.worker, None
        self.profile = None
        if worker is not None:
            worker.close()


class _Session:
    def __init__(self, stack: ExitStack) -> None:
        self.closed = False
        # One fixed slot per selected provider; profile changes replace a slot.
        self.pm2 = {provider: _Pm2Slot() for provider in _PROVIDERS}
        self.gliner = _GlinerSlot()
        for slot in self.pm2.values():
            stack.callback(slot.close)
        stack.callback(self.gliner.close)


@contextmanager
def characterization_resource_session() -> Generator[None]:
    """Share CPU preparations until the outermost scope exits; nested scopes join it."""
    current = _session.get()
    if current is not None:
        if current.closed:
            raise Pm2WorkerRefused("characterization resource session is closed")
        yield
        return
    with ExitStack() as stack:
        current = _Session(stack)
        token = _session.set(current)
        try:
            yield
        finally:
            current.closed = True
            _session.reset(token)


def characterization_pm2_preflight(
    *,
    python: Path,
    script: Path,
    project: Path,
    provider: str,
    assets: Path,
    frozen_runtime: Mapping[str, Any] | None = None,
    frozen_artifacts: Mapping[str, Any] | None = None,
    device: Literal["cpu", "cuda"] = "cpu",
    check_active: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Memoize one exact preflight selection per CPU provider, never child startup checks."""
    _active(check_active)
    current = _session.get()
    arguments = dict(
        python=python, script=script, project=project, provider=provider, assets=assets
    )
    if current is None or device != "cpu":
        result = _preflight_pm2_runtime(**arguments)
    else:
        if current.closed or provider not in current.pm2:
            raise Pm2WorkerRefused("unsupported or closed characterization provider session")
        slot = current.pm2[provider]
        key = json.dumps(
            dict(
                paths=[str(path.absolute()) for path in (python, script, project, assets)],
                runtime=frozen_runtime,
                artifacts=frozen_artifacts,
            ),
            sort_keys=True,
            allow_nan=False,
        ).encode()
        if not slot.gate.acquire(blocking=False):
            raise Pm2WorkerRefused("characterization provider already has an active borrower")
        try:
            if slot.preflight is None or slot.preflight[0] != key:
                result = _preflight_pm2_runtime(**arguments)
                slot.preflight = (key, deepcopy(result))
            else:
                result = deepcopy(slot.preflight[1])
        finally:
            slot.gate.release()
    _active(check_active)
    return result


@contextmanager
def borrowed_pm2_worker(
    *,
    provider: str,
    python: Path,
    script: Path,
    profile: Path,
    device: Literal["cpu", "cuda"],
    nemotron_endpoint: str | None = None,
    check_active: Callable[[], None] | None = None,
    frozen_runtime: Mapping[str, Any] | None = None,
    frozen_artifacts: Mapping[str, Any] | None = None,
    startup_timeout_seconds: float = 300.0,
    inference_timeout_seconds: float = 120.0,
    max_request_bytes: int = 8_388_608,
    max_reply_bytes: int = 8_388_608,
) -> Generator[Pm2Worker]:
    """Borrow a compatible CPU resident, or retain ordinary worker/device custody."""
    _active(check_active)
    arguments: dict[str, Any] = dict(
        python=python,
        script=script,
        profile=profile,
        device=device,
        nemotron_endpoint=nemotron_endpoint,
        startup_timeout_seconds=startup_timeout_seconds,
        inference_timeout_seconds=inference_timeout_seconds,
        max_request_bytes=max_request_bytes,
        max_reply_bytes=max_reply_bytes,
    )
    current = _session.get()
    if current is None or device != "cpu":
        with _open_pm2_worker(**arguments, check_active=check_active) as worker:
            yield worker
        return
    if current.closed or provider not in current.pm2:
        raise Pm2WorkerRefused("unsupported or closed characterization provider session")
    slot = current.pm2[provider]
    if not slot.gate.acquire(blocking=False):
        raise Pm2WorkerRefused("characterization provider already has an active borrower")
    slot.callback = check_active if check_active is not None else lambda: None
    try:
        content = profile.read_bytes()
        selected = json.loads(content)
        if (
            not isinstance(selected, dict)
            or selected.get("provider") != provider
            or selected.get("device") != device
        ):
            raise Pm2WorkerRefused(
                "characterization worker profile differs from selected provider/device"
            )
        selection = json.dumps(
            dict(runtime=frozen_runtime, artifacts=frozen_artifacts),
            sort_keys=True,
            allow_nan=False,
        ).encode()
        key = (
            str(python.absolute()),
            str(script.absolute()),
            content,
            selection,
            nemotron_endpoint,
            startup_timeout_seconds,
            inference_timeout_seconds,
            max_request_bytes,
            max_reply_bytes,
        )
        if slot.worker is None or slot.worker.closed or slot.key != key:
            slot.close()
            slot.worker = slot.stack.enter_context(
                _open_pm2_worker(**arguments, check_active=slot.check_active)
            )
            slot.key = key
        slot.check_active()
        yield slot.worker
        slot.check_active()
    except BaseException as error:
        slot.close(type(error), error, error.__traceback__)
        raise
    finally:
        slot.callback = None
        slot.gate.release()


@contextmanager
def borrowed_gliner_worker(
    profile: GlinerProfile,
    *,
    check_active: Callable[[], None] | None = None,
) -> Generator[GlinerWorker]:
    """Borrow the one exact GLiNER CPU profile; inference keeps its explicit callback."""
    _active(check_active)
    current = _session.get()
    if current is None:
        worker = GlinerWorker(profile)
        try:
            yield worker
        finally:
            worker.close()
        return
    if current.closed:
        raise Pm2WorkerRefused("characterization resource session is closed")
    slot = current.gliner
    if not slot.gate.acquire(blocking=False):
        raise Pm2WorkerRefused("characterization GLiNER already has an active borrower")
    try:
        if slot.worker is None or slot.worker.closed or slot.profile != profile:
            slot.close()
            slot.worker, slot.profile = GlinerWorker(profile), profile
        yield slot.worker
        _active(check_active)
    except BaseException:
        slot.close()
        raise
    finally:
        slot.gate.release()
