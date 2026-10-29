"""Canonical JSON, digests, keys and the decimal helpers (D1 §10.1, §6.2; foundations §6 F2a)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import unicodedata
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from corpus_structure.core.canonical import (
    CANONICAL_DECIMAL,
    CanonicalJsonError,
    canonical_decimal,
    canonical_json,
    decimal_of_float,
    digest,
    is_canonical_decimal,
    make_key,
)

# Text biased towards characters with distinct NFC and NFD forms.
TEXT = st.text(alphabet=st.sampled_from("abcAé́ÅÅÅ ç̧z\U0001f600") | st.characters(
    codec="utf-8"), max_size=8)  # fmt: skip
JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | TEXT,
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(TEXT, inner, max_size=4),
    max_leaves=20,
)


def nfd(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFD", value)
    if isinstance(value, list):
        return [nfd(v) for v in value]
    if isinstance(value, dict):
        return {nfd(k): nfd(v) for k, v in value.items()}
    return value


def nfc_collides(value: Any) -> bool:
    if isinstance(value, list):
        return any(nfc_collides(v) for v in value)
    if isinstance(value, dict):
        keys = [unicodedata.normalize("NFC", k) for k in value]
        return len(set(keys)) < len(keys) or any(nfc_collides(v) for v in value.values())
    return False


def shuffled(value: Any, data: st.DataObject) -> Any:
    if isinstance(value, list):
        return [shuffled(v, data) for v in value]
    if isinstance(value, dict):
        items = data.draw(st.permutations(list(value.items())))
        return {k: shuffled(v, data) for k, v in items}
    return value


@given(JSON, st.data())
def test_permuted_object_keys_give_equal_output(value: Any, data: st.DataObject) -> None:
    assume(not nfc_collides(value))
    assert canonical_json(shuffled(value, data)) == canonical_json(value)


@given(JSON)
def test_nfd_input_gives_equal_keys(value: Any) -> None:
    assume(not nfc_collides(value))
    assert make_key("t", nfd(value)) == make_key("t", value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, b"null"),
        (True, b"true"),
        (-12, b"-12"),
        (10**20, b"100000000000000000000"),
        ("", b'""'),
        ('a"b\\c\n\u0001', b'"a\\"b\\\\c\\n\\u0001"'),
        ("e\u0301\U0001f600", b'"\xc3\xa9\xf0\x9f\x98\x80"'),  # NFC, raw UTF-8, never \u escapes
        ([], b"[]"),
        ({}, b"{}"),
        ([1, [2, {}]], b"[1,[2,{}]]"),
        ({"b": 1, "a": [True, None], "B": "x"}, b'{"B":"x","a":[true,null],"b":1}'),
        ({"z": {"y": 1, "x": 2}}, b'{"z":{"x":2,"y":1}}'),
        ({"\u00e9": 1, "f": 2, "e": 3}, b'{"e":3,"f":2,"\xc3\xa9":1}'),
        ((1, "a"), b'[1,"a"]'),  # a tuple is an array
    ],
)
def test_canonical_bytes(value: Any, expected: bytes) -> None:
    assert canonical_json(value) == expected


@given(JSON)
def test_output_parses_back_to_the_nfc_value(value: Any) -> None:
    assume(not nfc_collides(value))
    out = canonical_json(value)
    assert json.loads(out) == nfc(value)
    text = out.decode("utf-8")
    assert unicodedata.is_normalized("NFC", text)


def nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [nfc(v) for v in value]
    if isinstance(value, dict):
        return {nfc(k): nfc(v) for k, v in value.items()}
    return value


def test_known_bytes_and_key() -> None:
    value = {"b": [1, True, None], "a": "é"}
    expected = '{"a":"é","b":[1,true,null]}'.encode()
    assert canonical_json(value) == expected
    assert digest(value) == hashlib.sha256(expected).hexdigest()
    assert make_key("doc", value) == "doc:" + hashlib.sha256(expected).hexdigest()[:32]
    assert re.fullmatch(r"doc:[0-9a-f]{32}", make_key("doc", value))


def test_keys_sort_by_code_point_not_utf16() -> None:
    # U+FFFF < U+10000 by code point; UTF-16 (RFC 8785) would put the surrogate pair first.
    out = canonical_json({"\U00010000": 1, "￿": 2}).decode("utf-8")
    assert out == '{"￿":2,"\U00010000":1}'


@pytest.mark.parametrize(
    ("value", "path", "reason"),
    [
        (1.0, "$", "float"),
        ({"a": [0, 0.5]}, "$.a[1]", "float"),
        (Decimal("1.5"), "$", "Decimal"),
        ({"d": dt.date(2026, 1, 1)}, "$.d", "date"),
        (b"x", "$", "bytes"),
        ({1, 2}, "$", "set"),
        ({1: "x"}, "$", "not a string"),
        ("a\ud800", "$", "surrogate"),
        ({"x": {"\ud800": 1}}, "$.x", "surrogate"),
        ({"é": 1, "é": 2}, "$", "after NFC"),
        (float("nan"), "$", "float"),
    ],
)
def test_refusals_name_the_path(value: Any, path: str, reason: str) -> None:
    with pytest.raises(CanonicalJsonError) as caught:
        canonical_json(value)
    assert caught.value.path.startswith(path)
    assert reason in caught.value.reason


def test_make_key_prefix_is_checked() -> None:
    with pytest.raises(ValueError):
        make_key("Doc", {})
    with pytest.raises(ValueError):
        make_key("doc:", {})


@pytest.mark.parametrize(
    ("literal", "canonical"),
    [
        ("1e-3", "0.001"),
        ("300.0", "300"),
        ("300.", "300"),
        ("+5", "5"),
        (".5", "0.5"),
        ("007.50", "7.5"),
        ("-0", "0"),
        ("-0.000", "0"),
        ("-0.010", "-0.01"),
        ("1E+2", "100"),
        ("2.50", "2.5"),
        ("0", "0"),
        ("-12.034e1", "-120.34"),
    ],
)
def test_canonical_decimal_cases(literal: str, canonical: str) -> None:
    assert canonical_decimal(literal) == canonical
    assert is_canonical_decimal(canonical)


@pytest.mark.parametrize("bad", ["", "NaN", "Infinity", "1_000", "1e", "--1", " 1", "0x10", "."])
def test_canonical_decimal_refuses_non_literals(bad: str) -> None:
    with pytest.raises(ValueError):
        canonical_decimal(bad)


@pytest.mark.parametrize("text", ["2.50", "1.", "+1", "00", "-0", ".5", "1e3", "01"])
def test_pattern_refuses_non_canonical(text: str) -> None:
    assert not is_canonical_decimal(text)


DECIMAL_LITERAL = st.from_regex(
    r"[+-]?([0-9]{1,6}\.?[0-9]{0,6}|\.[0-9]{1,6})([eE][+-]?[0-9]{1,2})?", fullmatch=True
)


@given(DECIMAL_LITERAL)
def test_canonical_decimal_keeps_the_value(literal: str) -> None:
    out = canonical_decimal(literal)
    assert re.fullmatch(CANONICAL_DECIMAL, out)
    assert Decimal(out) == Decimal(literal)
    assert canonical_decimal(out) == out


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_decimal_of_float_round_trips(value: float) -> None:
    out = decimal_of_float(value)
    assert is_canonical_decimal(out)
    assert float(out) == value


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_decimal_of_float_refuses_non_finite(bad: float) -> None:
    with pytest.raises(ValueError):
        decimal_of_float(bad)


def test_decimal_of_float_examples() -> None:
    assert decimal_of_float(0.1) == "0.1"
    assert decimal_of_float(1e-05) == "0.00001"
    assert decimal_of_float(-0.0) == "0"
    assert decimal_of_float(300.0) == "300"
    with pytest.raises(TypeError):
        decimal_of_float(3)
