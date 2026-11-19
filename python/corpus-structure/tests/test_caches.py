"""Bounded holders coordinate preparation and report only their own process."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from weakref import ref

from corpus_structure.caches import clear, configure, configured, declare, snapshot


def test_same_key_prepares_once():
    entered, proceed = Event(), Event()
    calls = []

    @declare("test-compiled-coalescing", "model_entries")
    def load(key):
        calls.append(key)
        entered.set()
        assert proceed.wait(timeout=5)
        return object()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(load, "model")
        assert entered.wait(timeout=5)
        second = pool.submit(load, "model")
        proceed.set()
        assert first.result(timeout=5) is second.result(timeout=5)
    assert calls == ["model"]


def test_weighted_namespaces_share_a_bound_and_oversized_values_return():
    config = configured()
    configure(config.model_copy(update={"release_bytes": 4}))
    try:

        @declare("test-archive-weight", "release_bytes", weight=len)
        def archive(value: bytes) -> bytes:
            return value

        @declare("test-prepare-weight", "release_bytes", weight=len)
        def prepare(value: bytes) -> bytes:
            return value

        assert archive(b"abc") == b"abc"
        assert prepare(b"de") == b"de"
        assert prepare(b"oversized") == b"oversized"
        report = snapshot(owner="test")
        rows = {row.name: row for row in report.caches}
        assert rows["test-archive-weight"].entries == 0
        assert rows["test-prepare-weight"].entries == 1
        assert rows["test-prepare-weight"].size == 2
    finally:
        configure(config)


def test_cleared_budget_releases_its_values_without_another_use():
    class Resource:
        pass

    @declare("test-release-retention", "release_bytes")
    def retained():
        return Resource()

    item = retained()
    observed = ref(item)
    del item
    assert observed() is not None
    clear("release_bytes")
    assert observed() is None
