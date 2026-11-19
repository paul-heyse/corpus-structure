"""Exact value meaning and observable representation shared by semantic consumers.

Decimal representation records the Decimal object's text, not the original authored token.
Float hex retains signed zero. Native decimal_canonical/value_meaning mirror this contract.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from corpus_structure.model.compiled import CompiledModel

VALUE_CODEC_SOURCE = "value-codec.yaml"


def decimal_digit_limit(model: CompiledModel | None = None) -> int:
    from corpus_structure.model.compiled import annotation_values, running_model

    capture = running_model() if model is None else model

    def build():
        value = annotation_values(capture.view(VALUE_CODEC_SOURCE).schema).get(
            "cs:decimal_fixed_point_digits"
        )
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2_147_483_647:
            raise ValueError("value codec requires a positive decimal digit limit")
        return int.__int__(value)

    return capture.projection((VALUE_CODEC_SOURCE, "decimal-digit-limit"), build)


def decimal_text(value: Decimal) -> str:
    from .value_codec_core import decimal_text as encode

    return encode(value, decimal_fixed_point_digits=decimal_digit_limit())


def value_meaning(value: Any) -> Any:
    from .value_codec_core import value_meaning as encode

    return encode(value, decimal_fixed_point_digits=decimal_digit_limit())


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
