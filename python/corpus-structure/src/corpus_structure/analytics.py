"""Invocation-owned analytical resources and expression-only relation construction."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Lock, RLock, Thread
from typing import TYPE_CHECKING
from weakref import WeakSet

import duckdb
from duckdb import Expression

if TYPE_CHECKING:
    from corpus_structure.settings import AnalyticsSettings

_lock = RLock()
_settings: AnalyticsSettings | None = None


@dataclass(frozen=True)
class AnalyticalAllocation:
    """Physical allowance carried with the admitted request, outside semantic identity."""

    threads: int
    workspace_bytes: int
    spill_bytes: int
    scratch_root: Path | None = None
    memory_limit_bytes: int | None = None
    batch_size_hint_bytes: int = 1

    @classmethod
    def for_policy(cls, policy, settings: AnalyticsSettings) -> AnalyticalAllocation:
        memory_limit = None
        if settings.memory_limit.strip().lower() not in {"-1", "unlimited"}:
            from pydantic import ByteSize, TypeAdapter

            memory_limit = int(TypeAdapter(ByteSize).validate_python(settings.memory_limit))
        return cls(
            min(policy.cpu_native_threads, settings.threads),
            settings.job_workspace_bytes,
            settings.job_spill_bytes,
            memory_limit_bytes=memory_limit,
            batch_size_hint_bytes=settings.batch_size_hint_bytes,
        )

    def connection_config(self) -> dict[str, int | str]:
        # Leave a quarter of the analytical workspace for read-ahead, mapped
        # batches and native allocations outside DuckDB's buffer manager.
        buffer_bytes = self.workspace_bytes * 3 // 4
        if buffer_bytes < self.batch_size_hint_bytes:
            raise MemoryError("admitted analytical workspace cannot hold one input batch")
        if self.memory_limit_bytes is not None:
            buffer_bytes = min(buffer_bytes, self.memory_limit_bytes)
        return {
            "threads": self.threads,
            "async_threads": self.threads,
            "memory_limit": f"{buffer_bytes}B",
            "max_temp_directory_size": f"{self.spill_bytes}B",
        }


@dataclass
class _Job:
    allocation: AnalyticalAllocation
    check_active: Callable[[], None]
    settings: AnalyticsSettings | None
    connection_slot: Lock = field(default_factory=Lock)


_job: ContextVar[_Job | None] = ContextVar("analytical_job", default=None)


def current_allocation() -> AnalyticalAllocation | None:
    job = _job.get()
    return job.allocation if job is not None else None


@contextmanager
def analytical_job(
    allocation: AnalyticalAllocation,
    *,
    check_active: Callable[[], None],
    settings: AnalyticsSettings | None = None,
):
    """Bind the admitted allowance to one worker invocation and its connections."""
    current = _job.get()
    if current is not None:
        if current.allocation != allocation:
            raise ValueError("analytical allocation changed within an admitted job")
        yield
        return
    token = _job.set(_Job(allocation, check_active, settings))
    try:
        yield
    finally:
        _job.reset(token)


def configure(settings: AnalyticsSettings) -> None:
    global _settings
    with _lock:
        _settings = settings


def configured() -> AnalyticsSettings:
    job = _job.get()
    if job is not None and job.settings is not None:
        return job.settings
    with _lock:
        if _settings is not None:
            return _settings
        from corpus_structure.settings import Settings

        return Settings().analytics


def _expressions(values):
    if not all(isinstance(value, Expression) for value in values):
        raise TypeError("analytical relations require expression objects")
    return values


class Relation:
    """Finite relational operations with explicit bag and set semantics."""

    def __init__(self, native, owner):
        self._native = native
        self._owner = owner

    def _wrap(self, native):
        return Relation(native, self._owner)

    @property
    def columns(self):
        return self._native.columns

    @property
    def types(self):
        return self._native.types

    def select(self, *expressions):
        return self._wrap(self._native.select(*_expressions(expressions)))

    def filter(self, expression):
        _expressions((expression,))
        return self._wrap(self._native.filter(expression))

    def sort(self, *expressions):
        return self._wrap(self._native.sort(*_expressions(expressions)))

    def aggregate(self, expressions):
        return self._wrap(self._native.aggregate(list(_expressions(expressions))))

    def join(self, other, condition, *, how="inner"):
        _expressions((condition,))
        if not isinstance(other, Relation):
            raise TypeError("analytical joins require a declared relation")
        return self._wrap(self._native.join(other._native, condition, how=how))

    def set_alias(self, name):
        return self._wrap(self._native.set_alias(name))

    def distinct(self):
        return self._wrap(self._native.distinct())

    def _compatible(self, other):
        if not isinstance(other, Relation):
            raise TypeError("analytical set operations require a declared relation")
        if self.columns != other.columns or self.types != other.types:
            raise TypeError("analytical set operands differ in declared columns or types")

    def union_all(self, other):
        self._compatible(other)
        return self._wrap(self._native.union(other._native))

    def except_all(self, other):
        self._compatible(other)
        return self._wrap(self._native.except_(other._native))

    def intersect_all(self, other):
        self._compatible(other)
        return self._wrap(self._native.intersect(other._native))

    def union(self, other):
        return self.union_all(other).distinct()

    def except_(self, other):
        return self.distinct().except_all(other.distinct())

    def intersect(self, other):
        return self.distinct().intersect_all(other.distinct())

    def limit(self, count):
        return self._wrap(self._native.limit(count))

    def create(self, name):
        return self._native.create(name)

    def fetchall(self):
        return self._native.fetchall()

    def to_arrow_table(self):
        return self._native.to_arrow_table()

    def to_arrow_reader(self, *, batch_size):
        reader = self._native.to_arrow_reader(batch_size=batch_size)
        self._owner.readers.add(reader)
        return reader


class AnalyticalConnection:
    def __init__(self, native):
        self.native = native
        self.readers = WeakSet()

    def from_arrow(self, table):
        return Relation(self.native.from_arrow(table), self)

    def from_parquet(self, path):
        return Relation(self.native.from_parquet(path), self)

    def table(self, name):
        return Relation(self.native.table(name), self)


@contextmanager
def _active_connection(native, job):
    owner = AnalyticalConnection(native)
    done = Event()

    def interrupt_on_stop():
        while not done.wait(0.05):
            try:
                job.check_active()
            except Exception:
                native.interrupt()
                return

    watcher = None
    try:
        if job is not None:
            job.check_active()
            watcher = Thread(
                target=copy_context().run,
                args=(interrupt_on_stop,),
                name="analytical-cancellation",
                daemon=True,
            )
            watcher.start()
        try:
            yield owner
        except Exception:
            if job is not None:
                job.check_active()
            raise
        if job is not None:
            job.check_active()
    finally:
        done.set()
        if watcher is not None:
            watcher.join()
        try:
            for reader in tuple(owner.readers):
                reader.close()
        finally:
            native.close()


@contextmanager
def connection(settings: AnalyticsSettings | None = None):
    """Keep the configured connection and its private spill directory together."""
    job = _job.get()
    if job is None:
        selected = configured() if settings is None else settings
        root = selected.scratch_path.resolve()
        resources = {
            "threads": selected.threads,
            "async_threads": selected.threads,
            "memory_limit": selected.memory_limit,
        }
    else:
        resources = job.allocation.connection_config()
        root = job.allocation.scratch_root
        if root is None:
            selected = configured() if settings is None else settings
            root = selected.scratch_path.resolve()
        if not job.connection_slot.acquire(blocking=False):
            raise RuntimeError("analytical job already owns an open connection")
    try:
        try:
            root.mkdir(parents=True, exist_ok=True)
            scratch = TemporaryDirectory(prefix="invocation-", dir=root)
        except OSError as error:
            raise OSError(f"analytical scratch directory is unavailable: {root}") from error
        with scratch as directory:
            native = duckdb.connect(
                config={
                    "TimeZone": "UTC",
                    "default_collation": "binary",
                    "temp_directory": directory,
                    **resources,
                }
            )
            with _active_connection(native, job) as owner:
                yield owner
    finally:
        if job is not None:
            job.connection_slot.release()
