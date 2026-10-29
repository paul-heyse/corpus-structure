"""Independent exact-value examples; source lexical text is a separate observation."""

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


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), float("nan"), float("inf")])
def test_nonfinite_meaning_refuses(value):
    with pytest.raises(ValueError, match="non-finite"):
        value_meaning(value)
