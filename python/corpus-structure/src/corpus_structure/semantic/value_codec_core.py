"""Pure exact primitive value algorithms over one explicit model-derived limit."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

DECIMAL_LIMIT_MESSAGE = "decimal exceeds canonical fixed-point digit limit"


def decimal_text(value: Decimal, *, decimal_fixed_point_digits: int) -> str:
    """Canonical finite decimal meaning, independent of scale or exponent spelling."""
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    if not value:
        return "0"
    sign, digits, exponent = value.as_tuple()
    assert isinstance(exponent, int)
    end = len(digits)
    while digits[end - 1] == 0:
        end -= 1
    point = len(digits) + exponent
    if max(point, 1) + max(end - point, 0) > decimal_fixed_point_digits:
        raise ValueError(DECIMAL_LIMIT_MESSAGE)
    trimmed = Decimal((sign, digits[:end], point - end))
    return format(trimmed, "f")


def value_meaning(value: Any, *, decimal_fixed_point_digits: int) -> Any:
    if value is None:
        return ["null"]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("naive datetime has no semantic instant")
        return ["datetime", value.astimezone(UTC).isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, int):
        return ["integer", str(value)]
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite decimal")
        return [
            "decimal",
            decimal_text(value, decimal_fixed_point_digits=decimal_fixed_point_digits),
        ]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return ["float", value.hex()]
    if isinstance(value, (list, tuple)):
        return [
            "sequence",
            [
                value_meaning(x, decimal_fixed_point_digits=decimal_fixed_point_digits)
                for x in value
            ],
        ]
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return [
            "mapping",
            [
                [k, value_meaning(v, decimal_fixed_point_digits=decimal_fixed_point_digits)]
                for k, v in sorted(value.items())
            ],
        ]
    raise TypeError(f"unsupported semantic value {type(value).__name__}")
