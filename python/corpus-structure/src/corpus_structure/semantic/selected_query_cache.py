"""Bounded immutable derived rows; every caller separately reacquires native authority."""

from __future__ import annotations

from collections.abc import Generator, Iterable
from concurrent.futures import Future, TimeoutError
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from itertools import chain
from pickle import dumps, loads
from struct import pack, unpack_from
from threading import RLock
from typing import Any, Literal

from cachetools import LRUCache

from corpus_structure.caches import register

from .data_operation_json import json_bytes
from .refusals import InvalidContinuation

ENTRY_BYTES = 8 * 1024 * 1024
ENTRY_ROWS = 4096
_SEPARATOR = len(json_bytes([0, 0])) - 2 * len(json_bytes(0)) - 2


@dataclass(frozen=True, slots=True)
class DerivedRows:
    """Only encoded derived values and offsets; no live cut, reader or generator.

    Buffers are created and consumed only inside this process. Pickle preserves
    exact Decimal scale and float kinds; the public JSON wire codec deliberately
    normalizes these and cannot serve as a lossless cache representation.
    """

    metadata: bytes
    content: bytes
    offsets: bytes

    @property
    def byte_size(self):
        return len(self.metadata) + len(self.content) + len(self.offsets)

    def __len__(self):
        return len(self.offsets) // 8 - 1

    def record(self):
        return loads(self.metadata)

    def rows(self, start=0):
        if type(start) is not int or not 0 <= start <= len(self):
            raise InvalidContinuation(
                "cursor is outside its immutable derived row population",
                reason="invalid_continuation",
            )
        for ordinal in range(start, len(self)):
            begin, end = unpack_from("!QQ", self.offsets, ordinal * 8)
            yield loads(self.content[begin:end])


@dataclass(frozen=True, slots=True)
class ServedKey:
    query: str
    selection: bytes
    implementation: str
    authorization: tuple[str, ...] | None
    basis_kind: Literal["cut", "content"]
    basis: bytes

    @property
    def content(self) -> bytes:
        return json_bytes(
            [
                self.query,
                self.selection.hex(),
                self.implementation,
                self.authorization,
                self.basis_kind,
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
    basis_kind: Literal["cut", "content"] = "cut",
):
    """Scope derivation to the principal and database of the already authorized connection."""
    authorization = _authorization_scope(connection)
    return ServedKey(
        query,
        json_bytes(selection),
        str(implementation),
        authorization,
        basis_kind,
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
_DISK_STORE: ContextVar[Any] = ContextVar("served_disk_store", default=None)


@contextmanager
def disk_row_cache(store=None):
    """Opt a command invocation into inert derived-row storage after native acquisition."""
    if store is None:
        from corpus_structure.cache_store import configured_store

        store = configured_store()
    token = _DISK_STORE.set(store)
    try:
        yield
    finally:
        _DISK_STORE.reset(token)


def _disk_rows(key: ServedKey):
    from .served_row_codec import VERSION, decode_rows

    store = _DISK_STORE.get()
    if store is None or key.query == "rich-index":
        return None
    try:
        files = store.get("pages", VERSION, key.content)
        return None if files is None else decode_rows(files)
    except OSError, ValueError, TypeError, OverflowError, RecursionError:
        return None


def _retain_disk_rows(key: ServedKey, entry):
    from .served_row_codec import VERSION, encode_rows

    store = _DISK_STORE.get()
    if store is None or not isinstance(entry, DerivedRows):
        return
    try:
        files = encode_rows(entry)
        store.put("pages", VERSION, key.content, files)
    except OSError, ValueError, TypeError, OverflowError, RecursionError:
        return


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

        return reusable_serving_code() and key.authorization is not None

    def get(self, key: ServedKey):
        if not self._eligible(key):
            return None
        with self._lock:
            value = self._storage().get(key)
            if value is None:
                self.misses += 1
            else:
                self.hits += 1
            return None if value is None else value[1]

    def put(self, key: ServedKey, entry):
        if not self._eligible(key):
            return False
        _retain_disk_rows(key, entry)
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
            entry = _disk_rows(key)
            if entry is not None:
                # A decoded hit is already authenticated by the caller's fresh
                # native acquisition. Retain only this inert value in T4.
                load.result = entry
                with self._lock:
                    rows = self._storage()
                    if key.byte_size + entry.byte_size <= rows.maxsize:
                        rows[key] = (key.byte_size, entry)
            yield entry
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
    snapshot = metadata if callable(metadata) else lambda: metadata
    header = dumps(snapshot(), protocol=5)

    def remainder(extra=()):
        return _OwnedRows(
            chain((loads(body) for body in encoded), extra, iterator),
            getattr(iterator, "close", None),
        )

    if len(header) + 8 > max_bytes:
        return None, remainder()
    for value in iterator:
        body = dumps(value, protocol=5)
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
    header = dumps(snapshot(), protocol=5)
    entry = DerivedRows(
        header, b"".join(encoded), b"".join(pack("!Q", offset) for offset in offsets)
    )
    if entry.byte_size > max_bytes:
        return None, remainder()
    return entry, None


def uncached_rows_from(rows, ordinal):
    """A cache miss rederives its bounded query; never accept a fabricated ordinal."""
    return _OwnedRows(rows, getattr(rows, "close", None), skip=ordinal)


def byte_bounded_page(rows, *, offset, limit, max_bytes, report, row_fields=None):
    """Account for the envelope once and each appended row once, then check exactly.

    report(end, values, more) supplies fresh cut/provenance and the ordinal cursor.
    Multiple output arrays can share one indivisible pagination unit (dossiers).
    """
    from .serving_code import serving_report

    original_report = report

    def report(end, values, more):
        return serving_report(original_report(end, values, more))

    fields = {"items": lambda value: (value,)} if row_fields is None else row_fields
    dynamic_names = {
        "cursor",
        "continuation",
        "next_cursor",
        "page_complete",
        "knowledge",
        "unknowns",
        *fields,
    }
    initial = report(offset, [], True)
    static = {key: value for key, value in initial.items() if key not in dynamic_names}
    static_width = len(json_bytes(static))
    values, widths, counts = [], dict.fromkeys(fields, 0), dict.fromkeys(fields, 0)
    more = False
    for row in rows:
        if len(values) == limit:
            more = True
            break
        additions = {name: tuple(extract(row)) for name, extract in fields.items()}
        next_widths = {
            name: widths[name] + sum(len(json_bytes(value)) for value in additions[name])
            for name in fields
        }
        next_counts = {name: counts[name] + len(additions[name]) for name in fields}
        values.append(row)
        candidate = report(offset + len(values), values, True)
        dynamic = {key: value for key, value in candidate.items() if key in dynamic_names}
        dynamic.update({name: [] for name in fields})
        row_width = sum(
            next_widths[name] + _SEPARATOR * max(0, next_counts[name] - 1) for name in fields
        )
        width = (
            static_width
            + len(json_bytes(dynamic))
            - 2
            + (_SEPARATOR if static and dynamic else 0)
            + row_width
        )
        if width > max_bytes:
            values.pop()
            if not values:
                raise ValueError("one complete selected answer and its envelope exceed max_bytes")
            more = True
            break
        widths, counts = next_widths, next_counts
    result = report(offset + len(values), values, more)
    while len(json_bytes(result)) > max_bytes:
        if not values:
            raise ValueError("complete selected answer envelope exceeds max_bytes")
        values.pop()
        if not values:
            raise ValueError("one complete selected answer and its envelope exceed max_bytes")
        result = report(offset + len(values), values, True)
    return result
