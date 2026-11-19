"""Exact tagged values shared by data identities and selected result projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .identity import canonical_bytes
from .value_codec import value_meaning


def decode_semantic_value(value: Any) -> Any:
    """Decode the owned tagged value format, refusing noncanonical alternatives."""
    result = _decode_semantic_value(value)
    # Re-encoding the complete value checks every nested tag, ordering and spelling.
    # Repeating this round-trip at each subtree serializes the same descendants again.
    if canonical_bytes(semantic_value(result)) != canonical_bytes(value):
        raise ValueError("noncanonical semantic value")
    return result


def _decode_semantic_value(value: Any) -> Any:
    from datetime import date, datetime
    from decimal import Decimal

    if not isinstance(value, list) or not value or not isinstance(value[0], str):
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
                not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str)
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
    """Extend the shared exact primitive codec with declared collection/state forms."""
    if isinstance(value, CollectionValue):
        if value.kind not in {"ordered-bag", "bag", "set"}:
            raise ValueError(f"unsupported collection kind {value.kind!r}")
        members = [semantic_value(member) for member in value.members]
        if value.kind != "ordered-bag":
            by_bytes = sorted(
                ((canonical_bytes(member), member) for member in members), key=lambda item: item[0]
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
            return ["present", semantic_value(value.value)]
        if value.state not in {"known-absent", "unavailable", "unknown"}:
            raise ValueError(f"unsupported optional state {value.state!r}")
        if value.value is not None:
            raise ValueError(f"{value.state} cannot carry a present value")
        return [value.state]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("semantic mapping keys must be strings")
        return ["mapping", [[key, semantic_value(item)] for key, item in sorted(value.items())]]
    if isinstance(value, (list, tuple)):
        return ["sequence", [semantic_value(item) for item in value]]
    return value_meaning(value)
