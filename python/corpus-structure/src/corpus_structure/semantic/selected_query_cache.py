"""Bounded immutable derived rows; every caller separately reacquires native authority."""

from __future__ import annotations

from collections.abc import Generator, Iterable
from concurrent.futures import Future, TimeoutError
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from itertools import chain
from struct import pack
from threading import RLock
from typing import Any

from cachetools import LRUCache

from corpus_structure.caches import register

from .data_operation_json import json_bytes
from .refusal_types import InvalidContinuation
from .served_row_codec import JsonDerivedRows, UnstorableValue, decode_value, encode_value

ENTRY_BYTES = 8 * 1024 * 1024
ENTRY_ROWS = 4096


@dataclass(frozen=True, slots=True)
class ServedKey:
    query: str
    selection: bytes
    implementation: str
    authorization: tuple[str, ...] | None
    basis: bytes

    @property
    def content(self) -> bytes:
        return json_bytes(
            [
                self.query,
                self.selection.hex(),
                self.implementation,
                self.authorization,
                self.basis.hex(),
            ]
        )

    @property
    def byte_size(self):
        return len(self.content)


def served_key(
    connection,
    query,
    *,
    implementation,
    selection,
    basis,
):
    """Scope derivation to the principal and database of the already authorized connection."""
    authorization = _authorization_scope(connection)
    from .serving_code import reuse_implementation_key

    return ServedKey(
        query,
        json_bytes(selection),
        reuse_implementation_key(implementation),
        authorization,
        json_bytes(basis),
    )


def _authorization_scope(connection):
    from sqlalchemy import Connection, func, select

    from .storage_target import acquired_database_identity

    authorization = None
    if isinstance(connection, Connection):
        target = acquired_database_identity(connection)
        principal = connection.execute(select(func.session_user(), func.current_user())).one()
        authorization = (
            target.system_identifier,
            target.database,
            str(target.database_oid),
            principal[0],
            principal[1],
        )
    return authorization


class SizedLRU(LRUCache):
    """Charge immutable retained bytes and constrain the number of entries together."""

    def __init__(self, maxsize, max_entries):
        super().__init__(maxsize=maxsize, getsizeof=lambda item: item[0] + item[1].byte_size)
        self.max_entries = max_entries
        self.evictions = 0

    def popitem(self):
        item = super().popitem()
        self.evictions += 1
        return item

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        while len(self) > self.max_entries:
            self.popitem()


@dataclass
class _Load:
    key: ServedKey
    result: Any = None


_LOADING: ContextVar[tuple[_Load, ...]] = ContextVar("served_cache_load", default=())


class SelectedQueryCache:
    def __init__(self, max_bytes=None, *, max_entries=None):
        self._lock = RLock()
        self._rows = None
        self._limits = (max_bytes, max_entries)
        self._pending: dict[ServedKey, Future] = {}
        self.hits = self.misses = self.coalesced = self.admission_skips = 0

    def _storage(self):
        from corpus_structure.caches import configured

        settings = configured()
        byte_limit = self._limits[0] if self._limits[0] is not None else settings.served_bytes
        entry_limit = self._limits[1] if self._limits[1] is not None else settings.served_entries
        if self._rows is None or (self._rows.maxsize, self._rows.max_entries) != (
            byte_limit,
            entry_limit,
        ):
            self._rows = SizedLRU(byte_limit, entry_limit)
        return self._rows

    @staticmethod
    def _eligible(key: ServedKey) -> bool:
        from .serving_code import reusable_serving_code

        return reusable_serving_code(key.implementation) and key.authorization is not None

    def get(self, key: ServedKey):
        if not self._eligible(key):
            return None
        with self._lock:
            value = self._storage().get(key)
            if value is None:
                self.misses += 1
            else:
                self.hits += 1
                from .serving_code import record_serving_reuse

                record_serving_reuse("reused")
            return None if value is None else value[1]

    def put(self, key: ServedKey, entry):
        from .serving_code import record_serving_reuse

        record_serving_reuse("derived")
        if not self._eligible(key):
            return False
        for load in reversed(_LOADING.get()):
            if load.key == key:
                load.result = entry
                break
        with self._lock:
            weight = key.byte_size
            rows = self._storage()
            if weight + entry.byte_size > rows.maxsize:
                self.admission_skips += 1
                return False
            rows[key] = (weight, entry)
            return True

    @contextmanager
    def loading(self, key: ServedKey) -> Generator[Any]:
        """Share complete immutable values and failures, keeping streaming remainders local."""
        from corpus_structure.caches import configured

        if not self._eligible(key):
            yield None
            return
        with self._lock:
            entry = self.get(key)
            if entry is not None:
                future, owner = None, False
            elif key in self._pending:
                future, owner = self._pending[key], False
                self.coalesced += 1
            else:
                future, owner = Future(), True
                self._pending[key] = future
        if entry is not None:
            yield entry
            return
        assert future is not None
        if not owner:
            if any(load.key == key for load in _LOADING.get()):
                raise RuntimeError("a served derivation cannot wait on its own key")
            try:
                entry = future.result(timeout=configured().wait_seconds)
            except TimeoutError:
                entry = future.result() if future.done() else None
            yield entry
            return
        load = _Load(key)
        token = _LOADING.set((*_LOADING.get(), load))
        try:
            yield None
        except BaseException as error:
            future.set_exception(error)
            raise
        else:
            future.set_result(load.result)
        finally:
            _LOADING.reset(token)
            with self._lock:
                self._pending.pop(key, None)

    def clear(self):
        with self._lock:
            if self._rows is not None:
                self._rows.clear()
            self.hits = self.misses = self.coalesced = self.admission_skips = 0
            if self._rows is not None:
                self._rows.evictions = 0

    def snapshot(self):
        from corpus_structure.caches import CacheMetrics

        with self._lock:
            rows = self._storage()
            return CacheMetrics(
                budget="bytes",
                entries=len(rows),
                size=rows.currsize,
                maxsize=rows.maxsize,
                hits=self.hits,
                misses=self.misses,
                coalesced=self.coalesced,
                admission_skips=self.admission_skips,
                evictions=rows.evictions,
            )


SELECTED_QUERY_CACHE = SelectedQueryCache()

register("served-results", SELECTED_QUERY_CACHE.snapshot, SELECTED_QUERY_CACHE.clear)


class _OwnedRows:
    """Request-local iterator custody, including closure before first iteration."""

    def __init__(self, rows, close, *, skip=0):
        self._rows, self._close, self._skip = iter(rows), close, skip

    def __iter__(self):
        return self

    def __next__(self):
        try:
            while self._skip:
                next(self._rows)
                self._skip -= 1
            return next(self._rows)
        except StopIteration:
            incomplete = self._skip
            self.close()
            if incomplete:
                raise InvalidContinuation(
                    "cursor is outside its immutable derived row population",
                    reason="invalid_continuation",
                ) from None
            raise

    def close(self):
        close, self._close = self._close, None
        self._rows = iter(())
        self._skip = 0
        if close is not None:
            close()


def bounded_rows(rows: Iterable, metadata, *, max_bytes=ENTRY_BYTES, max_rows=ENTRY_ROWS):
    """Finish a small finite query or return its bounded prefix plus open remainder.

    A large Cartesian result is never exhausted merely to populate the cache.
    The caller owns and closes the returned iterator on the ordinary miss path.
    """
    iterator = iter(rows)
    encoded = []
    offsets = [0]

    def remainder(extra=()):
        return _OwnedRows(
            chain((decode_value(body[:-1]) for body in encoded), extra, iterator),
            getattr(iterator, "close", None),
        )

    try:
        header = encode_value(metadata)
    except UnstorableValue:
        return None, remainder()
    if len(header) + 8 > max_bytes:
        return None, remainder()
    for value in iterator:
        try:
            body = encode_value(value) + b"\n"
        except UnstorableValue:
            return None, remainder((value,))
        if (
            len(encoded) >= max_rows
            or len(header) + offsets[-1] + len(body) + 8 * (len(offsets) + 1) > max_bytes
        ):
            return None, remainder((value,))
        encoded.append(body)
        offsets.append(offsets[-1] + len(body))
    close = getattr(iterator, "close", None)
    if close is not None:
        close()
    try:
        header = encode_value(metadata)
    except UnstorableValue:
        return None, remainder()
    entry = JsonDerivedRows(
        header, b"".join(encoded), b"".join(pack("!Q", offset) for offset in offsets)
    )
    if entry.byte_size > max_bytes:
        return None, remainder()
    return entry, None


def uncached_rows_from(rows, ordinal):
    """A cache miss rederives its bounded query; never accept a fabricated ordinal."""
    return _OwnedRows(rows, getattr(rows, "close", None), skip=ordinal)
