"""Independent exact-value examples; source lexical text is a separate observation."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from corpus_structure.semantic.identity import canonical_bytes, fact_key
from corpus_structure.semantic.value_codec import observed_representation, value_meaning


@pytest.mark.parametrize(
    "value,expected",
    [
        (Decimal("1.2300"), ["decimal", "1.23"]),
        (Decimal("1e3"), ["decimal", "1000"]),
        (Decimal("-0.000"), ["decimal", "0"]),
        (-0.0, ["float", "-0x0.0p+0"]),
        (True, ["boolean", True]),
        ("é", ["string", "é"]),
        ({"roles": [None, None]}, ["mapping", [["roles", ["sequence", [["null"], ["null"]]]]]]),
    ],
)
def test_independent_meaning_vectors(value, expected):
    assert value_meaning(value) == expected


def test_observed_decimal_scale_is_not_fact_meaning():
    a, b = Decimal("1.2300"), Decimal("1.23")
    assert observed_representation(a) == ["decimal-report", "1.2300"]
    assert observed_representation(a) != observed_representation(b)
    assert canonical_bytes(a) == b'{"decimal":"1.23"}'
    assert fact_key("r", "z", "s", "p", a, {}) == fact_key("r", "z", "s", "p", b, {})
    assert fact_key("r", "z", "s", "p", -0.0, {}) != fact_key("r", "z", "s", "p", 0.0, {})


def test_equivalent_instants_share_meaning_without_erasing_observed_offsets():
    local = datetime(2026, 10, 29, 12, tzinfo=timezone(timedelta(hours=2)))
    utc = datetime(2026, 10, 29, 10, tzinfo=UTC)
    assert value_meaning(local) == value_meaning(utc) == ["datetime", "2026-10-29T10:00:00+00:00"]
    assert fact_key("r", "z", "s", "p", local, {}) == fact_key("r", "z", "s", "p", utc, {})
    assert observed_representation(local) == ["datetime-report", "2026-10-29T12:00:00+02:00"]
    assert observed_representation(utc) == ["datetime-report", "2026-10-29T10:00:00+00:00"]
    with pytest.raises(ValueError, match="naive datetime"):
        value_meaning(datetime(2026, 10, 29, 12))


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), float("nan"), float("inf")])
def test_nonfinite_meaning_refuses(value):
    with pytest.raises(ValueError, match="non-finite"):
        value_meaning(value)


def test_decimal_width_checks_canonical_form_before_expansion():
    wide = "9" * 10000
    assert value_meaning(Decimal(wide)) == ["decimal", wide]
    assert value_meaning(Decimal("1e16383")) == ["decimal", "1" + "0" * 16383]
    assert value_meaning(Decimal("1e-16383")) == ["decimal", "0." + "0" * 16382 + "1"]
    assert value_meaning(Decimal("-0.000e200000")) == ["decimal", "0"]
    assert value_meaning(Decimal("12." + "0" * 20000)) == ["decimal", "12"]


@pytest.mark.parametrize(
    "value",
    ["1e16384", "1e-16384", "9" * 16385, "1e1000000000000000"],
    ids=["wide", "tiny", "expanded", "large-exponent"],
)
def test_decimal_outside_canonical_width_refuses(value):
    with pytest.raises(ValueError, match="canonical fixed-point digit limit"):
        value_meaning(Decimal(value))


def test_pure_tagged_decimal_codec_uses_only_its_explicit_model_limit(monkeypatch):
    from corpus_structure.semantic import value_codec
    from corpus_structure.semantic.data_operation_value_codec import (
        decode_semantic_value,
        semantic_value,
    )

    def unexpected_model_acquisition(*args, **kwargs):
        raise AssertionError("pure codec acquired the running model")

    monkeypatch.setattr(value_codec, "decimal_digit_limit", unexpected_model_acquisition)
    value = {"amount": Decimal("1e7"), "signed_zero": -0.0}
    expected = [
        "mapping",
        [["amount", ["decimal", "10000000"]], ["signed_zero", ["float", "-0x0.0p+0"]]],
    ]
    assert semantic_value(value, decimal_fixed_point_digits=8) == expected
    restored = decode_semantic_value(expected, decimal_fixed_point_digits=8)
    assert restored["amount"] == Decimal("10000000")
    assert restored["signed_zero"].hex() == "-0x0.0p+0"
    with pytest.raises(ValueError, match="canonical fixed-point digit limit"):
        semantic_value(value, decimal_fixed_point_digits=7)
    with pytest.raises(ValueError, match="canonical fixed-point digit limit"):
        decode_semantic_value(expected, decimal_fixed_point_digits=7)
