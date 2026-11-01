"""Connection ownership ends at the source read, before computation consumes it."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.orchestrate.source_reader import ScopedSourceReader


def test_reader_returns_owned_values_and_releases_between_reads_and_on_failure():
    live = []
    owner: Any = SimpleNamespace(conn="closed setup", prepared="release")

    @contextmanager
    def connect():
        token = object()
        live.append(token)
        try:
            yield token
        finally:
            live.remove(token)

    engine: Any = SimpleNamespace(connect=connect)

    def original(document_id):
        assert owner.conn in live
        return b"owned source"

    def bad(document_id):
        raise ValueError("read failed")

    owner.original = original
    reader = ScopedSourceReader(engine, owner)
    assert reader.prepared == "release"
    assert reader.original(1) == b"owned source"
    assert not live  # Native/inference work starts here, without a borrowed connection.
    assert owner.conn == "closed setup"
    owner.original = bad
    with pytest.raises(ValueError, match="read failed"):
        reader.original(1)
    assert not live
    assert owner.conn == "closed setup"
    with reader.connection() as connection:
        assert connection in live
    assert not live


def test_parallel_read_calls_never_cross_owner_connections():
    import time

    live = []
    seen = []
    owner: Any = SimpleNamespace(conn=None, prepared="release")

    @contextmanager
    def connect():
        assert not live
        token = object()
        live.append(token)
        try:
            yield token
        finally:
            live.remove(token)

    def original(number):
        token = owner.conn
        time.sleep(0.001)
        assert token is owner.conn
        seen.append(number)
        return bytes([number])

    owner.original = original
    engine: Any = SimpleNamespace(connect=connect)
    reader = ScopedSourceReader(engine, owner)
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(reader.original, range(8)))
    assert values == [bytes([number]) for number in range(8)]
    assert sorted(seen) == list(range(8))
    assert not live
    assert owner.conn is None
