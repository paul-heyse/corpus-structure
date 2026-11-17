"""Immutable LRU capacity, bounded construction, ordinal seeks and byte-exact pages."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.selected_query_cache import (
    SelectedQueryCache, bounded_rows, byte_bounded_page, uncached_rows_from,
)


def entry(value):
    result, remaining = bounded_rows([value], {"value": value})
    assert result is not None and remaining is None
    return result


def test_lru_charges_actual_encoded_buffers_and_defends_cached_values():
    first, second, third = (entry({"value": i}) for i in range(3))
    capacity = sum(len(buffer) for item in (first, second) for buffer in (item.metadata, item.content, item.offsets)) + len(b"firstsecond")
    cache = SelectedQueryCache(capacity)
    assert cache.put(b"first", first) and cache.put(b"second", second)
    assert cache.get(b"first") is first
    assert cache.put(b"third", third) and cache.get(b"second") is None
    value = next(cache.get(b"first").rows())
    value["value"] = "mutated"
    assert next(cache.get(b"first").rows()) == {"value": 0}
    metadata = cache.get(b"first").record()
    metadata.clear()
    assert cache.get(b"first").record() == {"value": {"value": 0}}
    oversized = entry({"body": "x" * (capacity + 1)})
    assert not cache.put(b"oversized", oversized)
    assert cache._rows.currsize <= capacity


def test_cache_rechecks_and_mutations_are_thread_safe():
    cache, barrier = SelectedQueryCache(1024, max_entries=3), Barrier(3)

    def use(identity):
        barrier.wait()
        for n in range(8):
            expected = {"identity": identity, "n": n}
            assert cache.put(str(identity).encode(), entry(expected))
            actual = cache.get(str(identity).encode())
            assert actual is not None and next(actual.rows()) == expected
        return identity

    with ThreadPoolExecutor(max_workers=3) as workers:
        assert set(workers.map(use, range(3))) == {0, 1, 2}
    assert len(cache._rows) == 3 and cache._rows.currsize <= 1024


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
    assert [next(remainder) for _ in range(2)] == [{"n": 0}, {"n": 1}]
    remainder.close()
    assert closed == [True] and seen == [0, 1, 2, 3]
    with pytest.raises(InvalidContinuation):
        list(uncached_rows_from(iter((1, 2)), 3))


def test_ordinal_cache_seek_does_not_visit_prior_rows():
    cached, _ = bounded_rows(({"n": n} for n in range(8)), {})
    assert list(cached.rows(6)) == [{"n": 6}, {"n": 7}]
    with pytest.raises(InvalidContinuation):
        list(cached.rows(9))


def test_byte_budget_matches_independent_full_response_sizes_at_digit_boundary():
    rows = [{"text": "α" * n, "ordinal": n} for n in range(8, 14)]

    def report(end, values, more):
        return dict(version="test", cut={"read_id": "actual"}, items=values,
                    cursor=str(end) if more else None, knowledge="observed" if values else "unknown")

    maximum = len(json_bytes(report(10, rows[:2], True)))
    result = byte_bounded_page(iter(rows), offset=8, limit=5, max_bytes=maximum, report=report)
    assert result == report(10, rows[:2], True)
    assert len(json_bytes(result)) <= maximum
    assert len(json_bytes(report(11, rows[:3], True))) > maximum


def test_multiple_output_arrays_keep_indivisible_member_and_all_citations():
    rows = [dict(members=[{"id": i}], citations=[{"member": i, "text": "x" * 20}], facets=[]) for i in range(4)]

    def report(end, values, more):
        return dict(version="dossier", members=[item for row in values for item in row["members"]],
                    citations=[item for row in values for item in row["citations"]],
                    facets=[], next_cursor=end if more else None)

    maximum = len(json_bytes(report(2, rows[:2], True)))
    result = byte_bounded_page(iter(rows), offset=0, limit=4, max_bytes=maximum, report=report,
                              row_fields={name: lambda row, name=name: row[name] for name in ("members", "citations", "facets")})
    assert result == report(2, rows[:2], True)


def test_cache_preserves_exact_decimal_scale_float_kind_and_nested_copies():
    value = {"amount": Decimal("12345678901234567890.123400"),
             "float": 0.125, "nested": [{"scaled": Decimal("0.00")}]}
    cached = entry(value)
    decoded = next(cached.rows())
    assert decoded["amount"].as_tuple() == value["amount"].as_tuple()
    assert type(decoded["float"]) is float and decoded["float"].hex() == value["float"].hex()
    assert decoded["nested"][0]["scaled"].as_tuple() == Decimal("0.00").as_tuple()
    assert json_bytes(decoded) == json_bytes(value)
    decoded["nested"][0]["scaled"] = "mutated"
    assert next(cached.rows())["nested"][0]["scaled"] == Decimal("0.00")
    assert json_bytes(cached.record()["value"]) == json_bytes(value)
