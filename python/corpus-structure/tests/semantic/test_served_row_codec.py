"""Independent lossless values and optional disk retention after fresh acquisition."""

from decimal import Decimal
from struct import pack

import pytest

from corpus_structure.semantic.selected_query_cache import (
    SelectedQueryCache,
    ServedKey,
    bounded_rows,
    disk_row_cache,
)
from corpus_structure.semantic.served_row_codec import (
    UnstorableValue,
    decode_rows,
    decode_value,
    encode_rows,
    encode_value,
)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        3,
        Decimal("3"),
        Decimal("3.00"),
        Decimal("-0.00"),
        Decimal("-0"),
        Decimal("0E+3"),
        Decimal("1E+2"),
        3.0,
        -0.0,
        {"float": "0x0.0p+0", "nested": [Decimal("12.300"), -0.0]},
        ["map", [["typed", "float"]]],
        ("class", {"nested": (1, Decimal("2.00"))}),
    ],
)
def test_value_kinds_scale_and_float_bits_survive(value):
    actual = decode_value(encode_value(value))
    assert type(actual) is type(value)
    assert actual == value
    if isinstance(value, Decimal):
        assert actual.as_tuple() == value.as_tuple()
    if isinstance(value, float):
        assert actual.hex() == value.hex()
    if isinstance(value, dict):
        assert actual["nested"][0].as_tuple() == Decimal("12.300").as_tuple()
        assert actual["nested"][1].hex() == (-0.0).hex()


@pytest.mark.parametrize("value", [b"bytes", {1: "key"}, float("inf")])
def test_unsupported_values_have_no_disk_encoding(value):
    with pytest.raises(UnstorableValue):
        encode_value(value)


def test_row_offsets_and_complete_metadata_roundtrip():
    entry, remaining = bounded_rows([1, Decimal("1.00"), -0.0], {"unknowns": ["one"]})
    assert entry is not None and remaining is None
    files = encode_rows(entry)
    restored = decode_rows(files)
    assert restored.record() == {"unknowns": ["one"]}
    rows = list(restored.rows(1))
    assert rows[0].as_tuple() == Decimal("1.00").as_tuple()
    assert rows[1].hex() == (-0.0).hex()
    with pytest.raises(ValueError, match="offset"):
        decode_rows(dict(files, **{"offsets.bin": pack("!QQ", 0, 999999)}))


class MemoryStore:
    def __init__(self):
        self.files = {}
        self.reads = self.writes = 0

    def get(self, tier, version, key):
        self.reads += 1
        return self.files.get((tier, version, key))

    def put(self, tier, version, key, files):
        self.writes += 1
        self.files[tier, version, key] = files
        return True


def test_distinct_process_cache_owners_share_inert_rows_with_explicit_opt_in():
    store = MemoryStore()
    key = ServedKey("native", b"selection", "implementation", ("reader",), "cut", b"cut")
    original, _ = bounded_rows([Decimal("7.00")], {})
    with disk_row_cache(store):
        first = SelectedQueryCache()
        with first.loading(key) as entry:
            assert entry is None
            first.put(key, original)
        second = SelectedQueryCache()
        with second.loading(key) as entry:
            assert entry is not None
            assert next(entry.rows()).as_tuple() == Decimal("7.00").as_tuple()
    assert store.writes == 1 and store.reads == 2
    with SelectedQueryCache().loading(key) as entry:
        assert entry is None
    assert store.reads == 2


def test_incomplete_identity_and_prepared_graph_do_not_consult_disk():
    from corpus_structure.semantic.code_identity import CodeIdentity, CodeUnknown
    from corpus_structure.semantic.serving_code import ServingImplementation, serving_code

    store = MemoryStore()
    key = ServedKey("native", b"selection", "implementation", ("reader",), "cut", b"cut")
    incomplete = CodeIdentity(("test",), (), (), (CodeUnknown("test", 1, "unknown"),), b"{}")
    with (
        disk_row_cache(store),
        serving_code(ServingImplementation("i", incomplete)),
        SelectedQueryCache().loading(key) as entry,
    ):
        assert entry is None
    graph = ServedKey("rich-index", b"selection", "implementation", ("reader",), "cut", b"cut")
    with disk_row_cache(store), SelectedQueryCache().loading(graph) as entry:
        assert entry is None
    assert store.reads == store.writes == 0


def test_a_fresh_process_opens_verified_typed_rows(tmp_path):
    import subprocess
    import sys

    from corpus_structure.cache_store import CacheStore

    store = CacheStore(tmp_path / "cache", program_store_bytes=0, page_store_bytes=1048576)
    key = ServedKey("native", b"selection", "implementation", ("reader",), "cut", b"cut")
    original, _ = bounded_rows([Decimal("7.00"), -0.0], {"unknowns": ["bounded"]})
    with disk_row_cache(store), SelectedQueryCache().loading(key) as entry:
        assert entry is None
        SelectedQueryCache().put(key, original)
    code = """
import sys
from decimal import Decimal
from pathlib import Path
from corpus_structure.cache_store import CacheStore
from corpus_structure.semantic.selected_query_cache import SelectedQueryCache, ServedKey, disk_row_cache
store = CacheStore(Path(sys.argv[1]), program_store_bytes=0, page_store_bytes=1048576)
key = ServedKey("native", b"selection", "implementation", ("reader",), "cut", b"cut")
with disk_row_cache(store), SelectedQueryCache().loading(key) as entry:
    assert entry is not None
    values = list(entry.rows())
    assert values[0].as_tuple() == Decimal("7.00").as_tuple()
    assert values[1].hex() == (-0.0).hex()
    assert entry.record() == {"unknowns": ["bounded"]}
print("verified fresh-process disk hit")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(store.root)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "verified fresh-process disk hit"


def test_verified_disk_entry_seeks_without_decoding_prior_rows_again(monkeypatch):
    from corpus_structure.semantic import served_row_codec as codec

    original, _ = bounded_rows(list(range(100)), {})
    restored = decode_rows(encode_rows(original))
    decoded = []
    actual = codec.decode_value

    def observe(content):
        decoded.append(content)
        return actual(content)

    monkeypatch.setattr(codec, "decode_value", observe)
    assert list(restored.rows(98)) == [98, 99]
    assert decoded == [encode_value(98), encode_value(99)]
