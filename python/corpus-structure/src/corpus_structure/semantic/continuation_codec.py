"""Exact bounded continuation encoding without selected-read acquisition."""

import base64

from .data_operation_json import json_bytes, json_loads, wire_json_loads


def encode_cursor(value):
    wire = json_bytes(value)
    if type(wire) is not bytes:
        raise TypeError("selected cursor must be encoded as native bytes")
    encoded = base64.urlsafe_b64encode(wire).decode()
    if len(encoded) > 32768:
        raise ValueError("selected cursor exceeds the supported encoded bound")
    return encoded


def decode_cursor(value):
    try:
        return wire_json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected-result cursor") from error


def decode_rich_cursor(value: str) -> dict:
    from .refusals import InvalidContinuation

    try:
        parsed = json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise InvalidContinuation(
            "invalid rich query cursor", reason="invalid_continuation"
        ) from error
    if not isinstance(parsed, dict):
        raise InvalidContinuation("invalid rich query cursor", reason="invalid_continuation")
    return parsed
