"""Pure tagged-value encoding and canonical decoding over explicit codec inputs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .data_operation_values import CollectionValue, OptionalValue
from .value_codec_core import value_meaning


def tagged_bytes(value) -> bytes:
    """Canonical JSON for the owned tag language, whose numbers are text payloads."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def decode_semantic_value(value: Any, *, decimal_fixed_point_digits: int) -> Any:
    """Decode the owned tagged value format, refusing noncanonical alternatives."""
    result = _decode_semantic_value(value)
    if tagged_bytes(
        semantic_value(result, decimal_fixed_point_digits=decimal_fixed_point_digits)
    ) != tagged_bytes(value):
        raise ValueError("noncanonical semantic value")
    return result


def _decode_semantic_value(value: Any) -> Any:
    from datetime import date, datetime
    from decimal import Decimal

    if not isinstance(value, list) or not value or (not isinstance(value[0], str)):
        raise ValueError("semantic value requires a tagged array")
    tag = value[0]
    if tag == "null" and len(value) == 1:
        result = None
    elif tag in {"known-absent", "unknown", "unavailable"} and len(value) == 1:
        result = OptionalValue(tag)
    elif len(value) == 2:
        payload = value[1]
        is_text = tag == "string" and isinstance(payload, str)
        is_boolean = tag == "boolean" and type(payload) is bool
        if is_text or is_boolean:
            result = payload
        elif tag == "integer" and isinstance(payload, str):
            result = int(payload)
        elif tag == "decimal" and isinstance(payload, str):
            result = Decimal(payload)
        elif tag == "float" and isinstance(payload, str):
            result = float.fromhex(payload)
        elif tag == "date" and isinstance(payload, str):
            result = date.fromisoformat(payload)
        elif tag == "datetime" and isinstance(payload, str):
            result = datetime.fromisoformat(payload)
        elif tag == "present":
            result = OptionalValue("present", _decode_semantic_value(payload))
        elif tag == "sequence" and isinstance(payload, list):
            result = [_decode_semantic_value(member) for member in payload]
        elif tag in {"set", "bag", "ordered-bag"} and isinstance(payload, list):
            result = CollectionValue(
                tag, tuple(_decode_semantic_value(member) for member in payload)
            )
        elif tag == "mapping" and isinstance(payload, list):
            if any(
                not isinstance(pair, list) or len(pair) != 2 or (not isinstance(pair[0], str))
                for pair in payload
            ):
                raise ValueError("invalid semantic mapping")
            if len({pair[0] for pair in payload}) != len(payload):
                raise ValueError("duplicate semantic mapping key")
            result = {name: _decode_semantic_value(member) for name, member in payload}
        else:
            raise ValueError("unsupported semantic value tag or payload")
    else:
        raise ValueError("invalid semantic value arity")
    return result


def semantic_value(value: Any, *, decimal_fixed_point_digits: int) -> Any:
    """Extend the shared exact primitive codec with declared collection/state forms."""
    if isinstance(value, CollectionValue):
        if value.kind not in {"ordered-bag", "bag", "set"}:
            raise ValueError(f"unsupported collection kind {value.kind!r}")
        members = [
            semantic_value(member, decimal_fixed_point_digits=decimal_fixed_point_digits)
            for member in value.members
        ]
        if value.kind != "ordered-bag":
            by_bytes = sorted(
                ((tagged_bytes(member), member) for member in members), key=lambda item: item[0]
            )
            if value.kind == "set":
                members = []
                previous = None
                for encoded, member in by_bytes:
                    if encoded != previous:
                        members.append(member)
                    previous = encoded
            else:
                members = [member for _, member in by_bytes]
        return [value.kind, members]
    if isinstance(value, OptionalValue):
        if value.state == "present":
            return [
                "present",
                semantic_value(value.value, decimal_fixed_point_digits=decimal_fixed_point_digits),
            ]
        if value.state not in {"known-absent", "unavailable", "unknown"}:
            raise ValueError(f"unsupported optional state {value.state!r}")
        if value.value is not None:
            raise ValueError(f"{value.state} cannot carry a present value")
        return [value.state]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("semantic mapping keys must be strings")
        return [
            "mapping",
            [
                [key, semantic_value(item, decimal_fixed_point_digits=decimal_fixed_point_digits)]
                for key, item in sorted(value.items())
            ],
        ]
    if isinstance(value, (list, tuple)):
        return [
            "sequence",
            [
                semantic_value(item, decimal_fixed_point_digits=decimal_fixed_point_digits)
                for item in value
            ],
        ]
    return value_meaning(value, decimal_fixed_point_digits=decimal_fixed_point_digits)
