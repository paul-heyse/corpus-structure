"""Invocation-owned analytical resources and expression-only relation construction."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock

import duckdb
from duckdb import Expression

from corpus_structure.settings import AnalyticsSettings, Settings

_lock = RLock()
_settings: AnalyticsSettings | None = None


def configure(settings: AnalyticsSettings) -> None:
    global _settings
    with _lock:
        _settings = settings


def configured() -> AnalyticsSettings:
    with _lock:
        return _settings if _settings is not None else Settings().analytics


def _expressions(values):
    if not all(isinstance(value, Expression) for value in values):
        raise TypeError("analytical relations require expression objects")
    return values


class Relation:
    """Finite relational operations with explicit bag and set semantics."""

    def __init__(self, native):
        self._native = native

    @property
    def columns(self):
        return self._native.columns

    @property
    def types(self):
        return self._native.types

    def select(self, *expressions):
        return Relation(self._native.select(*_expressions(expressions)))

    def filter(self, expression):
        _expressions((expression,))
        return Relation(self._native.filter(expression))

    def sort(self, *expressions):
        return Relation(self._native.sort(*_expressions(expressions)))

    def aggregate(self, expressions):
        return Relation(self._native.aggregate(list(_expressions(expressions))))

    def join(self, other, condition, *, how="inner"):
        _expressions((condition,))
        if not isinstance(other, Relation):
            raise TypeError("analytical joins require a declared relation")
        return Relation(self._native.join(other._native, condition, how=how))

    def set_alias(self, name):
        return Relation(self._native.set_alias(name))

    def distinct(self):
        return Relation(self._native.distinct())

    def _compatible(self, other):
        if not isinstance(other, Relation):
            raise TypeError("analytical set operations require a declared relation")
        if self.columns != other.columns or self.types != other.types:
            raise TypeError("analytical set operands differ in declared columns or types")

    def union_all(self, other):
        self._compatible(other)
        return Relation(self._native.union(other._native))

    def except_all(self, other):
        self._compatible(other)
        return Relation(self._native.except_(other._native))

    def intersect_all(self, other):
        self._compatible(other)
        return Relation(self._native.intersect(other._native))

    def union(self, other):
        return self.union_all(other).distinct()

    def except_(self, other):
        return self.distinct().except_all(other.distinct())

    def intersect(self, other):
        return self.distinct().intersect_all(other.distinct())

    def limit(self, count):
        return Relation(self._native.limit(count))

    def create(self, name):
        return self._native.create(name)

    def fetchall(self):
        return self._native.fetchall()

    def to_arrow_table(self):
        return self._native.to_arrow_table()

    def to_arrow_reader(self, *, batch_size):
        return self._native.to_arrow_reader(batch_size=batch_size)


class AnalyticalConnection:
    def __init__(self, native):
        self.native = native

    def from_arrow(self, table):
        return Relation(self.native.from_arrow(table))

    def from_parquet(self, path):
        return Relation(self.native.from_parquet(path))

    def table(self, name):
        return Relation(self.native.table(name))


@contextmanager
def connection(settings: AnalyticsSettings | None = None):
    """Keep the configured connection and its private spill directory together."""
    selected = configured() if settings is None else settings
    root = selected.scratch_path.resolve()
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
                "threads": selected.threads,
                "async_threads": selected.threads,
                "memory_limit": selected.memory_limit,
                "temp_directory": str(Path(directory).resolve()),
            }
        )
        try:
            yield AnalyticalConnection(native)
        finally:
            native.close()
