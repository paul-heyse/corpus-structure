"""Scoped structlog/stdlib ingress, safe fan-out, and the bounded child transfer channel."""

from __future__ import annotations

import logging
import os
import stat
import threading
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import structlog
from structlog.contextvars import bind_contextvars, merge_contextvars, reset_contextvars
from structlog.typing import EventDict, Processor

from corpus_structure.cli.exception_observations import ExceptionTrace, transform_exception
from corpus_structure.cli.observations import (
    RECORD_BYTES,
    SPOOL_BYTES,
    Bindings,
    Observation,
    ObservationWriter,
    normalize,
)

SPOOL_ENV = "CORPUS_OBSERVATION_SPOOL"
INVOCATION_ENV = "CORPUS_OBSERVATION_INVOCATION"
RUN_ENV = "CORPUS_OBSERVATION_RUN"
PROVIDER_ENV = "CORPUS_AGENT_INVOCATION_ID"


@dataclass(frozen=True)
class Destination:
    writer: ObservationWriter | None
    stream: TextIO | None


_DESTINATION: ContextVar[Destination | None] = ContextVar("observation_destination", default=None)
_ROUTE_LOCK = threading.RLock()


@dataclass
class RoutePolicy:
    count: int
    level: int
    effective_level: int
    propagate: bool
    handlers: tuple[logging.Handler, ...]


_ROUTES: dict[str, RoutePolicy] = {}


def _ordinary_route(record: logging.LogRecord) -> None:
    """Concurrent non-observational callers keep their prior stdlib routing policy."""
    with _ROUTE_LOCK:
        candidates = [
            name for name in _ROUTES if record.name == name or record.name.startswith(name + ".")
        ]
        if not candidates:
            return
        name = max(candidates, key=len)
        policy = _ROUTES[name]
        origin = logging.getLogger(record.name)
        if (
            origin.name == name or origin.level == logging.NOTSET
        ) and record.levelno < policy.effective_level:
            return
        current = logging.getLogger(name)
        handled = 0
        while current is not None:
            prior = _ROUTES.get(current.name)
            handlers = prior.handlers if prior is not None else tuple(current.handlers)
            for handler in handlers:
                handled += 1
                if record.levelno >= handler.level:
                    handler.handle(record)
            if not (prior.propagate if prior is not None else current.propagate):
                break
            current = current.parent
        if (
            not handled
            and logging.lastResort is not None
            and record.levelno >= logging.lastResort.level
        ):
            logging.lastResort.handle(record)


def _safe_processor(logger: Any, method: str, event: EventDict) -> EventDict:
    # ProcessorFormatter needs these metadata references until its own removal processor.
    meta = {key: event[key] for key in ("_record", "_from_structlog") if key in event}
    exception = event.get("exception")
    typed_exception = exception if isinstance(exception, ExceptionTrace) else None
    owned, omissions = normalize(
        {
            key: value
            for key, value in event.items()
            if key not in meta and not (key == "exception" and typed_exception is not None)
        }
    )
    if typed_exception is not None and isinstance(owned, dict):
        owned["exception"] = typed_exception.model_dump(mode="json")
    assert isinstance(owned, dict)
    if omissions:
        owned["normalization_omissions"] = list(omissions)
    return {**owned, **meta}


_EXCEPTION_PROCESSOR = structlog.processors.ExceptionRenderer(transform_exception)
_COMMON: list[Processor] = [
    merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    _EXCEPTION_PROCESSOR,
    _safe_processor,
]


def logger(name: str = "corpus_structure.observations") -> Any:
    """Explicit standard wrapper configuration avoids changing unrelated structlog users."""
    return structlog.wrap_logger(
        logging.getLogger(name),
        processors=[
            structlog.stdlib.filter_by_level,
            *_COMMON,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def _dispatch(_logger: Any, _method: str, event: EventDict) -> str:
    destination = _DESTINATION.get()
    if destination is None:
        return ""
    owned = dict(event)
    message = owned.pop("event", "Observation")
    severity = str(owned.pop("level", "info")).upper()
    severity = {"WARN": "WARNING", "FATAL": "CRITICAL", "EXCEPTION": "ERROR"}.get(
        severity, severity
    )
    binding = {key: owned.pop(key) for key in Bindings.model_fields if key in owned}
    payload = {**owned, "message": message, "severity": severity, "bindings": binding}
    if destination.writer is not None:
        destination.writer.append(payload, normalized=True)
    if destination.stream is not None:
        # The terminal sees only a new safe message record. Original exc_info and raw extras
        # cannot be rediscovered by a second exception-aware handler.
        summary = f"{severity}: {message}"
        if "exception" in owned:
            summary += " [structured exception retained]"
        terminal = logging.StreamHandler(destination.stream)
        terminal.setFormatter(logging.Formatter("%(message)s"))
        terminal.handle(
            logging.LogRecord("corpus_structure.safe", logging.INFO, "", 0, summary, (), None)
        )
    return ""


class _Ingress(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=[
                    structlog.stdlib.ExtraAdder(
                        allow={"database_notice", "method", "run_id", "task_id", "attempt"}
                    ),
                    *_COMMON,
                ],
                processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, _dispatch],
                keep_exc_info=False,
                keep_stack_info=False,
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        if _DESTINATION.get() is None:
            _ordinary_route(record)
            return
        try:
            self.format(record)
        except Exception as error:
            destination = _DESTINATION.get()
            if destination is not None and destination.writer is not None:
                destination.writer.unavailable(type(error).__name__)


_INGRESS = _Ingress()


@contextmanager
def routes(*names: str) -> Generator[None]:
    """Reference-count owned routes across concurrent scopes and restore prior logger policy."""
    if _DESTINATION.get() is None:
        yield
        return
    selected = tuple(dict.fromkeys(names or ("corpus_structure",)))
    with _ROUTE_LOCK:
        for name in selected:
            route = logging.getLogger(name)
            if name in _ROUTES:
                _ROUTES[name].count += 1
            else:
                _ROUTES[name] = RoutePolicy(
                    1,
                    route.level,
                    route.getEffectiveLevel(),
                    route.propagate,
                    tuple(route.handlers),
                )
                route.handlers = []
                route.addHandler(_INGRESS)
                route.setLevel(logging.INFO)
                route.propagate = False
    try:
        yield
    finally:
        with _ROUTE_LOCK:
            for name in selected:
                policy = _ROUTES[name]
                if policy.count > 1:
                    policy.count -= 1
                else:
                    route = logging.getLogger(name)
                    route.removeHandler(_INGRESS)
                    route.handlers = list(policy.handlers)
                    route.setLevel(policy.level)
                    route.propagate = policy.propagate
                    del _ROUTES[name]


@contextmanager
def bound(**values: Any) -> Generator[None]:
    # Contextvars propagate through AnyIO's synchronous tool dispatch. Other thread handoffs
    # must explicitly capture copy_context at their execution owner.
    tokens = bind_contextvars(**values)
    try:
        yield
    finally:
        reset_contextvars(**tokens)


@contextmanager
def capture(
    writer: ObservationWriter | None, *, stream: TextIO | None = None, **values: Any
) -> Generator[None]:
    token = _DESTINATION.set(Destination(writer, stream))
    try:
        with routes("corpus_structure"), bound(**values):
            yield
    finally:
        _DESTINATION.reset(token)


def current_writer() -> ObservationWriter | None:
    destination = _DESTINATION.get()
    return destination.writer if destination is not None else None


def event(kind: str, message: str, *, severity: str = "info", **fields: Any) -> None:
    try:
        getattr(logger(), severity)(message, kind=kind, **fields)
    except Exception as error:
        writer = current_writer()
        if writer is not None:
            writer.unavailable(type(error).__name__)


@contextmanager
def child_capture(*, run_id: int | None = None) -> Generator[ObservationWriter | None]:
    path = os.environ.get(SPOOL_ENV)
    writer = None
    if path is not None:
        try:
            selected = Path(path)
            if not selected.is_absolute():
                raise OSError("child spool must be absolute")
            writer = ObservationWriter(selected, limit=SPOOL_BYTES)
        except OSError:
            # The transfer channel is optional; native provider receipts retain authority.
            writer = None
    with capture(
        writer,
        stream=None,
        invocation_id=os.environ.get(INVOCATION_ENV),
        provider_invocation=os.environ.get(PROVIDER_ENV),
        run_id=run_id,
    ):
        try:
            yield writer
        finally:
            if writer is not None:
                writer.close()


class ChildDrain:
    """Read one named child channel during the existing provider wait, never directory-scan."""

    def __init__(self, path: Path, writer: ObservationWriter | None):
        self.path, self.writer = path, writer
        self.offset = 0
        self.sequence = 0
        self.identity: tuple[int, int] | None = None
        self.stopped = False

    def drain(self, *, final: bool = False) -> None:
        if self.writer is None or self.stopped:
            return
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return
        except OSError:
            self._unavailable("child spool unavailable")
            return
        try:
            info = os.fstat(fd)
            identity = (info.st_dev, info.st_ino)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_size > SPOOL_BYTES
                or info.st_size < self.offset
                or (self.identity is not None and identity != self.identity)
            ):
                self._unavailable("child spool replaced, shortened, or beyond bound")
                return
            self.identity = identity
            # A drain is independently bounded. Final cleanup drains the complete bounded spool.
            budget = SPOOL_BYTES if final else 256 * 1024
            batch = os.pread(fd, min(budget, info.st_size - self.offset), self.offset)
            index = 0
            while index < len(batch):
                end = batch.find(b"\n", index)
                if end < 0:
                    if len(batch) - index >= RECORD_BYTES or (
                        final and self.offset + len(batch) - index == info.st_size
                    ):
                        self._unavailable("child spool has an incomplete final record")
                    return
                try:
                    line = batch[index : end + 1]
                    if len(line) > RECORD_BYTES:
                        raise ValueError("oversized child record")
                    row = Observation.model_validate_json(line)
                    if row.producer_sequence <= self.sequence:
                        raise ValueError("child producer sequence is not increasing")
                except ValueError:
                    self._unavailable("child spool has a corrupt complete record")
                    return
                self.writer.append({}, imported=row)
                self.sequence = row.producer_sequence
                consumed = end + 1 - index
                self.offset += consumed
                index = end + 1
        except OSError:
            self._unavailable("child spool descriptor read unavailable")
        finally:
            os.close(fd)

    def _unavailable(self, reason: str) -> None:
        self.stopped = True
        if self.writer is not None:
            self.writer.append(
                {"kind": "child_transfer_unavailable", "message": reason, "severity": "WARNING"}
            )
