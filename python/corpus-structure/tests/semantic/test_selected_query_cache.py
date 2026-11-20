"""Immutable LRU capacity, bounded construction, ordinal seeks and byte-exact pages."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from corpus_structure.semantic.continuation_codec import encode_cursor
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.page_envelope import PageEnvelope
from corpus_structure.semantic.refusal_types import InvalidContinuation
from corpus_structure.semantic.selected_pages import byte_bounded_page
from corpus_structure.semantic.selected_query_cache import (
    SelectedQueryCache,
    ServedKey,
    bounded_rows,
    uncached_rows_from,
)


@pytest.fixture(autouse=True)
def cache_contract_context(monkeypatch):
    """These controls exercise retention after the serving owner establishes custody."""
    monkeypatch.setattr(
        "corpus_structure.semantic.serving_code.reusable_serving_code",
        lambda implementation=None: True,
    )


def cut_key(cut: bytes) -> ServedKey:
    return ServedKey("test", b"selection", "implementation", ("reader",), "cut", cut)


def entry(value):
    result, remaining = bounded_rows([value], {"value": value})
    assert result is not None and remaining is None
    return result


@pytest.mark.xdist_group("selected-cache-isolation-control")
def test_cache_isolation_can_warm_global_cache_within_a_case():
    from corpus_structure.semantic.selected_query_cache import SELECTED_QUERY_CACHE

    assert SELECTED_QUERY_CACHE.put(cut_key(b"isolation-control"), entry({"payload": "owned"}))
    assert SELECTED_QUERY_CACHE.get(cut_key(b"isolation-control")) is not None


@pytest.mark.xdist_group("selected-cache-isolation-control")
def test_cache_isolation_clears_previous_cases_without_support_import():
    from corpus_structure.semantic.selected_query_cache import SELECTED_QUERY_CACHE

    assert SELECTED_QUERY_CACHE.get(cut_key(b"isolation-control")) is None


def test_lru_charges_actual_encoded_buffers_and_defends_cached_values():
    first, second, third = (entry({"value": i}) for i in range(3))
    capacity = (
        sum(
            len(buffer)
            for item in (first, second)
            for buffer in (item.metadata, item.content, item.offsets)
        )
        + cut_key(b"first").byte_size
        + cut_key(b"second").byte_size
        + 2
    )
    cache = SelectedQueryCache(capacity)
    assert cache.put(cut_key(b"first"), first) and cache.put(cut_key(b"second"), second)
    assert cache.get(cut_key(b"first")) is first
    assert cache.put(cut_key(b"third"), third) and cache.get(cut_key(b"second")) is None
    retained = cache.get(cut_key(b"first"))
    assert retained is not None
    value = next(retained.rows())
    value["value"] = "mutated"
    assert next(retained.rows()) == {"value": 0}
    metadata = retained.record()
    metadata.clear()
    assert retained.record() == {"value": {"value": 0}}
    oversized = entry({"body": "x" * (capacity + 1)})
    assert not cache.put(cut_key(b"oversized"), oversized)
    observed = cache.snapshot()
    assert observed.size is not None and observed.size <= capacity


def test_cache_rechecks_and_mutations_are_thread_safe():
    cache, barrier = SelectedQueryCache(1024, max_entries=3), Barrier(3)

    def use(identity):
        barrier.wait()
        for n in range(8):
            expected = {"identity": identity, "n": n}
            assert cache.put(cut_key(str(identity).encode()), entry(expected))
            actual = cache.get(cut_key(str(identity).encode()))
            assert actual is not None and next(actual.rows()) == expected
        return identity

    with ThreadPoolExecutor(max_workers=3) as workers:
        assert set(workers.map(use, range(3))) == {0, 1, 2}
    observed = cache.snapshot()
    assert observed.entries == 3
    assert observed.size is not None and observed.size <= 1024


def test_bounded_builder_never_exhausts_large_query_and_closes_unused_remainder():
    seen, closed = [], []

    def rows():
        try:
            for n in range(1000000):
                seen.append(n)
                yield {"n": n}
        finally:
            closed.append(True)

    cached, remainder = bounded_rows(rows(), {}, max_rows=3)
    assert cached is None and seen == [0, 1, 2, 3]
    assert remainder is not None
    assert [next(remainder) for _ in range(2)] == [{"n": 0}, {"n": 1}]
    remainder.close()
    assert closed == [True] and seen == [0, 1, 2, 3]
    with pytest.raises(InvalidContinuation):
        list(uncached_rows_from(iter((1, 2)), 3))


def test_ordinal_cache_seek_does_not_visit_prior_rows():
    cached, _ = bounded_rows(({"n": n} for n in range(8)), {})
    assert cached is not None
    assert list(cached.rows(6)) == [{"n": 6}, {"n": 7}]
    with pytest.raises(InvalidContinuation):
        list(cached.rows(9))


def test_byte_budget_matches_independent_full_response_sizes_at_digit_boundary():
    rows = [{"text": "\N{GREEK SMALL LETTER ALPHA}" * n, "ordinal": n} for n in range(8, 14)]

    def report(end, values, more):
        return dict(
            version="test",
            cut={"read_id": "actual"},
            items=values,
            cursor=encode_cursor(dict(ordinal=end)) if more else None,
            knowledge="observed" if values else "unknown",
        )

    maximum = len(json_bytes(report(10, rows[:2], True)))
    result = byte_bounded_page(
        iter(rows),
        offset=8,
        limit=5,
        max_bytes=maximum,
        presentation=PageEnvelope(
            header=dict(version="test", cut={"read_id": "actual"}),
            cursor_basis={},
            cursor_field="cursor",
            include_knowledge=True,
        ),
    )
    assert result == report(10, rows[:2], True)
    assert len(json_bytes(result)) <= maximum
    assert len(json_bytes(report(11, rows[:3], True))) > maximum


def test_multiple_output_arrays_keep_indivisible_member_and_all_citations():
    rows = [
        dict(members=[{"id": i}], citations=[{"member": i, "text": "x" * 20}], facets=[])
        for i in range(4)
    ]

    def report(end, values, more):
        return dict(
            version="dossier",
            members=[item for row in values for item in row["members"]],
            citations=[item for row in values for item in row["citations"]],
            facets=[],
            next_cursor=encode_cursor(dict(offset=end)) if more else None,
        )

    maximum = len(json_bytes(report(2, rows[:2], True)))
    result = byte_bounded_page(
        iter(rows),
        offset=0,
        limit=4,
        max_bytes=maximum,
        presentation=PageEnvelope(
            header=dict(version="dossier"),
            cursor_basis={},
            cursor_field="next_cursor",
            position_field="offset",
            arrays=tuple((name, name, None, None) for name in ("members", "citations", "facets")),
        ),
    )
    assert result == report(2, rows[:2], True)


def test_cache_preserves_exact_decimal_scale_float_kind_and_nested_copies():
    value = {
        "amount": Decimal("12345678901234567890.123400"),
        "float": 0.125,
        "nested": [{"scaled": Decimal("0.00")}],
    }
    cached = entry(value)
    decoded = next(cached.rows())
    assert decoded["amount"].as_tuple() == value["amount"].as_tuple()
    assert type(decoded["float"]) is float and decoded["float"].hex() == value["float"].hex()
    assert decoded["nested"][0]["scaled"].as_tuple() == Decimal("0.00").as_tuple()
    assert json_bytes(decoded) == json_bytes(value)
    decoded["nested"][0]["scaled"] = "mutated"
    assert next(cached.rows())["nested"][0]["scaled"] == Decimal("0.00")
    assert json_bytes(cached.record()["value"]) == json_bytes(value)


@pytest.mark.parametrize("failure_type", [ValueError, TimeoutError])
def test_single_flight_shares_owner_failure_and_retries_next_request(failure_type):
    from threading import Event
    from time import monotonic, sleep

    cache, entered, release = SelectedQueryCache(1024), Event(), Event()
    failure = failure_type("controlled derivation failure")
    calls = []

    def use():
        with cache.loading(cut_key(b"cold")) as retained:
            assert retained is None
            calls.append(True)
            entered.set()
            assert release.wait(5)
            raise failure

    with ThreadPoolExecutor(max_workers=4) as pool:
        owner = pool.submit(use)
        assert entered.wait(5)
        waiters = [pool.submit(use) for _ in range(3)]
        deadline = monotonic() + 5
        while cache.coalesced < 3 and monotonic() < deadline:
            sleep(0.005)
        assert cache.coalesced == 3
        release.set()
        for future in (owner, *waiters):
            with pytest.raises(failure_type) as observed:
                future.result()
            assert observed.value is failure
    assert calls == [True]
    with cache.loading(cut_key(b"cold")) as retained:
        assert retained is None
        cache.put(cut_key(b"cold"), entry("recovered"))
    recovered = cache.get(cut_key(b"cold"))
    assert recovered is not None and list(recovered.rows()) == ["recovered"]


def test_served_keys_keep_authorization_and_cut_scopes_distinct():
    cache = SelectedQueryCache(4096)
    value = entry("authorized")
    reader = ServedKey(
        "query", b"selection", "implementation", ("database", "reader"), "cut", b"one"
    )
    evaluator = ServedKey(
        "query", b"selection", "implementation", ("database", "evaluator"), "cut", b"one"
    )
    other_cut = ServedKey(
        "query", b"selection", "implementation", ("database", "reader"), "cut", b"two"
    )
    unavailable = ServedKey("query", b"selection", "implementation", None, "cut", b"one")
    assert cache.put(reader, value)
    assert cache.get(reader) is value
    assert cache.get(evaluator) is None
    assert cache.get(other_cut) is None
    assert not cache.put(unavailable, value)


def test_oversize_completed_result_is_shared_without_retention():
    from threading import Event
    from time import monotonic, sleep

    cache, entered, release = SelectedQueryCache(1), Event(), Event()
    value = entry("larger than one byte")
    calls = []

    def use():
        with cache.loading(cut_key(b"large")) as retained:
            if retained is None:
                calls.append(True)
                entered.set()
                assert release.wait(5)
                retained = value
                assert not cache.put(cut_key(b"large"), retained)
            return retained

    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(use)
        assert entered.wait(5)
        waiter = pool.submit(use)
        deadline = monotonic() + 5
        while cache.coalesced < 1 and monotonic() < deadline:
            sleep(0.005)
        assert cache.coalesced == 1
        release.set()
        assert owner.result() is value and waiter.result() is value
    assert calls == [True] and cache.get(cut_key(b"large")) is None


def test_waiter_timeout_derives_privately_and_leaves_owner_running(monkeypatch):
    from threading import Event

    from corpus_structure import caches

    settings = caches.configured().model_copy(update={"wait_seconds": 0.01})
    monkeypatch.setattr(caches, "configured", lambda: settings)
    cache, entered, release = SelectedQueryCache(1024), Event(), Event()
    value = entry("same answer")

    def owner():
        with cache.loading(cut_key(b"slow")) as retained:
            assert retained is None
            entered.set()
            assert release.wait(5)
            cache.put(cut_key(b"slow"), value)
        return value

    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(owner)
        assert entered.wait(5)
        with cache.loading(cut_key(b"slow")) as retained:
            assert retained is None and not running.done()
            cache.put(cut_key(b"slow"), value)
        assert not running.done()
        release.set()
        assert running.result() is value
    assert cache.get(cut_key(b"slow")) is value


def test_success_completed_at_wait_timeout_is_delivered(monkeypatch):
    from concurrent.futures import Future

    cache = SelectedQueryCache(1024)
    value = entry("completed at the deadline")
    future = Future()
    result = future.result
    calls = []

    def elapsed_then_complete(timeout=None):
        calls.append(timeout)
        if len(calls) == 1:
            future.set_result(value)
            raise TimeoutError("wait elapsed immediately before completion")
        return result(timeout)

    monkeypatch.setattr(future, "result", elapsed_then_complete)
    cache._pending[cut_key(b"race")] = future
    with cache.loading(cut_key(b"race")) as observed:
        assert observed is value
    assert len(calls) == 2


def test_completed_stream_snapshots_its_final_inert_metadata():
    metadata = {"unknowns": []}

    def rows():
        yield {"n": 1}
        metadata["unknowns"].append("observed while exhausting the query")

    cached, remaining = bounded_rows(rows(), metadata)
    assert cached is not None and remaining is None
    metadata["unknowns"].clear()
    assert cached.record() == {"unknowns": ["observed while exhausting the query"]}
    assert list(cached.rows()) == [{"n": 1}]
