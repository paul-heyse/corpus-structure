"""Bounded immutable derived rows; every caller separately reacquires native authority."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import chain
from pickle import dumps, loads
from struct import pack, unpack_from
from threading import RLock

from cachetools import LRUCache

from .data_operation_json import json_bytes
from .refusals import InvalidContinuation

CACHE_BYTES = 32 * 1024 * 1024
ENTRY_BYTES = 8 * 1024 * 1024
ENTRY_ROWS = 4096
CACHE_ENTRIES = 128
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
            raise InvalidContinuation("cursor is outside its immutable derived row population", reason="invalid_continuation")
        for ordinal in range(start, len(self)):
            begin, end = unpack_from("!QQ", self.offsets, ordinal * 8)
            yield loads(self.content[begin:end])


class SelectedQueryCache:
    def __init__(self, max_bytes=CACHE_BYTES, *, max_entries=CACHE_ENTRIES):
        self._lock = RLock()
        self._rows = LRUCache(maxsize=max_bytes, getsizeof=lambda value: len(value[0]) + value[1].byte_size)
        self.max_entries = max_entries

    def get(self, key: bytes):
        with self._lock:
            value = self._rows.get(key)
            return None if value is None else value[1]

    def put(self, key: bytes, entry):
        with self._lock:
            if len(key) + entry.byte_size > self._rows.maxsize:
                return False
            if key not in self._rows:
                while len(self._rows) >= self.max_entries:
                    self._rows.popitem()
            self._rows[key] = (key, entry)
            return True

    def clear(self):
        with self._lock:
            self._rows.clear()


SELECTED_QUERY_CACHE = SelectedQueryCache()


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
                raise InvalidContinuation("cursor is outside its immutable derived row population", reason="invalid_continuation") from None
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
        return _OwnedRows(chain((loads(body) for body in encoded), extra, iterator),
                          getattr(iterator, "close", None))

    if len(header) + 8 > max_bytes:
        return None, remainder()
    for value in iterator:
        body = dumps(value, protocol=5)
        if len(encoded) >= max_rows or len(header) + offsets[-1] + len(body) + 8 * (len(offsets) + 1) > max_bytes:
            return None, remainder((value,))
        encoded.append(body)
        offsets.append(offsets[-1] + len(body))
    close = getattr(iterator, "close", None)
    if close is not None:
        close()
    header = dumps(snapshot(), protocol=5)
    entry = DerivedRows(header, b"".join(encoded), b"".join(pack("!Q", offset) for offset in offsets))
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
    fields = {"items": lambda value: (value,)} if row_fields is None else row_fields
    dynamic_names = {"cursor", "continuation", "next_cursor", "page_complete", "knowledge", "unknowns", *fields}
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
        next_widths = {name: widths[name] + sum(len(json_bytes(value)) for value in additions[name]) for name in fields}
        next_counts = {name: counts[name] + len(additions[name]) for name in fields}
        values.append(row)
        candidate = report(offset + len(values), values, True)
        dynamic = {key: value for key, value in candidate.items() if key in dynamic_names}
        dynamic.update({name: [] for name in fields})
        row_width = sum(next_widths[name] + _SEPARATOR * max(0, next_counts[name] - 1) for name in fields)
        width = static_width + len(json_bytes(dynamic)) - 2 + (_SEPARATOR if static and dynamic else 0) + row_width
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
