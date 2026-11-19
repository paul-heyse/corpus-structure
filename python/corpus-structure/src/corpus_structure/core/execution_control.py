"""Cooperative stop at the owning execution boundary."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Event


class ExecutionStopped(KeyboardInterrupt):
    """An authenticated managed owner asked this execution to drain."""


@dataclass
class ExecutionStopRequest:
    requested: Event = field(default_factory=Event)
    draining: Event = field(default_factory=Event)


_request: ContextVar[ExecutionStopRequest | None] = ContextVar(
    "execution_stop_request", default=None
)


@contextmanager
def execution_stop_scope(request: ExecutionStopRequest) -> Generator[None]:
    token = _request.set(request)
    try:
        yield
    finally:
        _request.reset(token)


def check_execution_active() -> None:
    request = _request.get()
    if request is not None and request.requested.is_set():
        request.draining.set()
        raise ExecutionStopped()
