"""Exact bounded continuation encoding without selected-read acquisition."""

import base64

from pydantic import BaseModel

from .data_operation_json import finite_json_loads, json_bytes, native_json_loads


def encode_cursor(value):
    wire = json_bytes(value)
    if type(wire) is not bytes:
        raise TypeError("selected cursor must be encoded as native bytes")
    encoded = base64.urlsafe_b64encode(wire).decode()
    if len(encoded) > 32768:
        raise ValueError("selected cursor exceeds the supported encoded bound")
    return encoded


def decode_resource_handle[Request: BaseModel](value: str, request: type[Request]) -> Request:
    """Decode a bounded selected resource handle through its actual request model."""
    if len(value) > 32768:
        raise ValueError("selected resource handle exceeds the supported encoded bound")
    try:
        parsed = native_json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected resource handle") from error
    return request.model_validate(parsed)


def decode_demand_cursor(value):
    """Decode the finite continuation envelope, excluding captured context documents.

    A selected demand cursor retains only native paging coordinates. The complete
    contextual selection and trust snapshot belong to the acquired cut, not to
    this public cursor's embedded request.
    """
    from .data_operation_wire import validate_native_wire

    try:
        parsed = finite_json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
        if not isinstance(parsed, dict) or set(parsed) != {
            "version",
            "implementation",
            "selection",
            "request",
            "cut",
            "ordinal",
        }:
            raise ValueError("invalid demand cursor envelope")
        if (
            parsed["version"] != "demand-query-v2"
            or any(type(parsed[key]) is not str for key in ("implementation", "selection", "cut"))
            or type(parsed["ordinal"]) is not int
            or parsed["ordinal"] < 0
        ):
            raise ValueError("invalid demand cursor coordinates")
        request = parsed["request"]
        if (
            not isinstance(request, dict)
            or {"selection", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"}
            & request.keys()
        ):
            raise ValueError("demand cursor cannot carry captured context or acquisition policy")
        parsed["request"] = validate_native_wire("read_demand_result", "input", request)
        return parsed
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected-result cursor") from error


def decode_rich_cursor(value: str) -> dict:
    from .refusal_types import InvalidContinuation

    try:
        parsed = native_json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise InvalidContinuation(
            "invalid rich query cursor", reason="invalid_continuation"
        ) from error
    if not isinstance(parsed, dict):
        raise InvalidContinuation("invalid rich query cursor", reason="invalid_continuation")
    return parsed
