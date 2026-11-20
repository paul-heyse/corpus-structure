"""Lossless inert representation shared by process and disk derived-row retention."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from struct import unpack_from

from .data_operation_json import json_bytes, json_loads


class UnstorableValue(ValueError):
    """The value is outside the row codec's finite supported vocabulary."""


def _encode(value, depth=0):
    if depth > 128:
        raise UnstorableValue("served value nesting exceeds the codec bound")
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", value]
    if type(value) is str:
        return ["str", value]
    if type(value) is Decimal and value.is_finite():
        # Decimal text retains scale, positive exponent and integral signed zero.
        # A JSON number parser normalizes the last case to the integer zero.
        return ["decimal", str(value)]
    if type(value) is float and isfinite(value):
        return ["float", value.hex()]
    if type(value) is list:
        return ["list", [_encode(item, depth + 1) for item in value]]
    if type(value) is tuple:
        return ["tuple", [_encode(item, depth + 1) for item in value]]
    if type(value) is dict and all(type(key) is str for key in value):
        return ["map", [[key, _encode(value[key], depth + 1)] for key in sorted(value)]]
    raise UnstorableValue("served value is outside the row codec vocabulary")


def _decode(value, depth=0):
    if depth > 128 or type(value) is not list or not value:
        raise ValueError("invalid served value")
    tag = value[0]
    if tag == "null" and len(value) == 1:
        return None
    if len(value) != 2:
        raise ValueError("invalid served value fields")
    content = value[1]
    if tag == "bool" and type(content) is bool:
        return content
    if tag == "str" and type(content) is str:
        return content
    if tag == "int" and type(content) is int:
        return content
    if tag == "decimal" and type(content) is str:
        try:
            result = Decimal(content)
        except InvalidOperation as error:
            raise ValueError("invalid served decimal") from error
        if result.is_finite() and str(result) == content:
            return result
    if tag == "float" and type(content) is str:
        result = float.fromhex(content)
        if isfinite(result) and result.hex() == content:
            return result
    if tag == "list" and type(content) is list:
        return [_decode(item, depth + 1) for item in content]
    if tag == "tuple" and type(content) is list:
        return tuple(_decode(item, depth + 1) for item in content)
    if tag == "map" and type(content) is list:
        result = {}
        for item in content:
            if type(item) is not list or len(item) != 2 or type(item[0]) is not str:
                raise ValueError("invalid served mapping")
            if item[0] in result:
                raise ValueError("duplicate served mapping key")
            result[item[0]] = _decode(item[1], depth + 1)
        return result
    raise ValueError("invalid served value kind")


def encode_value(value) -> bytes:
    try:
        return json_bytes(_encode(value))
    except UnstorableValue:
        raise
    except (ValueError, OverflowError, RecursionError) as error:
        raise UnstorableValue("served value cannot be encoded for retention") from error


def decode_value(content: bytes):
    value = _decode(json_loads(content))
    if encode_value(value) != content:
        raise ValueError("served value encoding is not canonical")
    return value


@dataclass(frozen=True, slots=True)
class JsonDerivedRows:
    """Immutable encoded rows with direct ordinal access in either retention tier."""

    metadata: bytes
    content: bytes
    offsets: bytes

    @property
    def byte_size(self):
        return len(self.metadata) + len(self.content) + len(self.offsets)

    def __len__(self):
        return len(self.offsets) // 8 - 1

    def record(self):
        return decode_value(self.metadata)

    def rows(self, start=0):
        from .refusal_types import InvalidContinuation

        if type(start) is not int or not 0 <= start <= len(self):
            raise InvalidContinuation(
                "cursor is outside its immutable derived row population",
                reason="invalid_continuation",
            )
        for ordinal in range(start, len(self)):
            begin, end = unpack_from("!QQ", self.offsets, ordinal * 8)
            yield decode_value(self.content[begin : end - 1])
