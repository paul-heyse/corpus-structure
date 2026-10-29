"""Exact value meaning and observable representation shared by semantic consumers.

Decimal representation records the Decimal object's text, not the original authored token.
Float hex retains signed zero. Native decimal_canonical/value_meaning mirror this contract.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any


def decimal_text(value: Decimal) -> str:
    """Canonical finite decimal meaning, independent of scale or exponent spelling."""
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    text = format(value, "f") if value else "0"
    return text.rstrip("0").rstrip(".") if "." in text else text


def value_meaning(value: Any) -> Any:
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
        return ["decimal", decimal_text(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float")
        return ["float", value.hex()]
    if isinstance(value, (list, tuple)):
        return ["sequence", [value_meaning(x) for x in value]]
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return ["mapping", [[k, value_meaning(v)] for k, v in sorted(value.items())]]
    raise TypeError(f"unsupported semantic value {type(value).__name__}")


def observed_representation(value: Any) -> Any:
    """Preserve available report distinctions separately from canonical meaning."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite decimal")
        return ["decimal-report", str(value)]
    if isinstance(value, datetime):
        return ["datetime-report", value.isoformat()]
    if isinstance(value, date):
        return ["date-report", value.isoformat()]
    if isinstance(value, dict):
        return [
            "mapping",
            [[key, observed_representation(item)] for key, item in sorted(value.items())],
        ]
    if isinstance(value, (tuple, list)):
        return ["sequence", [observed_representation(item) for item in value]]
    return value_meaning(value)
