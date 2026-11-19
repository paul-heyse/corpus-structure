"""Exact tagged values shared by data identities and selected result projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


def decode_semantic_value(value: Any) -> Any:
    """Acquire the current model's limit and use the shared pure tagged codec."""
    from .data_operation_value_codec import decode_semantic_value as encode
    from .value_codec import decimal_digit_limit

    return encode(value, decimal_fixed_point_digits=decimal_digit_limit())


@dataclass(frozen=True)
class CollectionValue:
    """An explicitly declared collection; an ordinary list remains a sequence."""

    kind: Literal["ordered-bag", "bag", "set"]
    members: tuple[Any, ...]


@dataclass(frozen=True)
class OptionalValue:
    """Present null/empty, known absence and incomplete states have different tags."""

    state: Literal["present", "known-absent", "unavailable", "unknown"]
    value: Any = None


def semantic_value(value: Any) -> Any:
    """Acquire the current model's limit and use the shared pure tagged codec."""
    from .data_operation_value_codec import semantic_value as encode
    from .value_codec import decimal_digit_limit

    return encode(value, decimal_fixed_point_digits=decimal_digit_limit())
