"""Independent lossless process row retention after fresh acquisition."""

from decimal import Decimal

import pytest

from corpus_structure.semantic.selected_query_cache import (
    bounded_rows,
)
from corpus_structure.semantic.served_row_codec import (
    UnstorableValue,
    decode_value,
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
def test_unsupported_values_have_no_encoding(value):
    with pytest.raises(UnstorableValue):
        encode_value(value)


def test_unencodable_value_preserves_the_fresh_row_stream():
    value = {"text": "\ud800"}
    entry, remaining = bounded_rows([{"text": "prefix"}, value, {"text": "tail"}], {})
    assert entry is None and remaining is not None
    assert list(remaining) == [{"text": "prefix"}, value, {"text": "tail"}]


def test_row_offsets_and_complete_metadata_roundtrip():
    entry, remaining = bounded_rows([1, Decimal("1.00"), -0.0], {"unknowns": ["one"]})
    assert entry is not None and remaining is None
    assert entry.record() == {"unknowns": ["one"]}
    rows = list(entry.rows(1))
    assert rows[0].as_tuple() == Decimal("1.00").as_tuple()
    assert rows[1].hex() == (-0.0).hex()


def test_retained_entry_seeks_without_decoding_prior_rows_again(monkeypatch):
    from corpus_structure.semantic import served_row_codec as codec

    retained, remaining = bounded_rows(list(range(100)), {})
    assert retained is not None and remaining is None
    decoded = []
    actual = codec.decode_value

    def observe(content):
        decoded.append(content)
        return actual(content)

    monkeypatch.setattr(codec, "decode_value", observe)
    assert list(retained.rows(98)) == [98, 99]
    assert decoded == [encode_value(98), encode_value(99)]


def test_unsupported_value_returns_stream_without_invoking_object_protocols():
    calls = []

    class Unsupported:
        def __reduce__(self):
            calls.append("pickle")
            raise AssertionError("selected rows must never invoke object serialization")

    unsupported = Unsupported()
    cached, remaining = bounded_rows(iter([Decimal("1.00"), unsupported, 3]), {})
    assert cached is None and remaining is not None
    values = list(remaining)
    assert values[0].as_tuple() == Decimal("1.00").as_tuple()
    assert values[1] is unsupported and values[2] == 3
    assert calls == []


def test_unsupported_metadata_leaves_the_row_stream_untouched():
    seen = []

    def rows():
        seen.append(True)
        yield {"n": 1}

    cached, remaining = bounded_rows(rows(), {"unsupported": object()})
    assert cached is None and remaining is not None and seen == []
    assert list(remaining) == [{"n": 1}]
    assert seen == [True]
