"""Detached native-demand records from the generated structural wire model.

Draft7 admission remains with the native call. This decoder uses the generated
TypedDict to preserve Python field/union fidelity without silently dropping keys
or coercing the material consumed by selected projections.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from math import isfinite
from typing import TYPE_CHECKING, cast

from pydantic import TypeAdapter

from . import _data_operation_wire
from ._data_operation_wire import WireDemandReadScope, WireReadDemandResultResult
from .data_operation_json import own_json_value, wire_json_loads

if TYPE_CHECKING:
    from .demand_wire_schema import CapturedWireValidator


@lru_cache(maxsize=1)
def _demand_result_adapter() -> TypeAdapter[WireReadDemandResultResult]:
    return TypeAdapter(WireReadDemandResultResult)


@lru_cache(maxsize=1)
def captured_demand_wire_validator() -> CapturedWireValidator | None:
    """Acquire the executable validation schema and keep it with its native validator."""
    from .demand_wire_schema import UnsupportedWireSchema, capture_wire_validator

    try:
        return capture_wire_validator(_demand_result_adapter(), _data_operation_wire)
    except UnsupportedWireSchema:
        # The generated adapter still serves fresh reads for an unmodeled schema.
        return None


@lru_cache(maxsize=1)
def _demand_scope_adapter() -> TypeAdapter[WireDemandReadScope]:
    return TypeAdapter(WireDemandReadScope)


def validate_wire_demand_scope(value: object) -> WireDemandReadScope:
    return _demand_scope_adapter().validate_python(value, strict=True, extra="forbid")


def _same_json_material(source, result) -> bool:
    """Compare an inert native tree without rebuilding its full wire encoding."""
    if type(source) is not type(result):
        return False
    if type(source) is dict:
        return source.keys() == result.keys() and all(
            _same_json_material(source[key], result[key]) for key in source
        )
    if type(source) is list:
        return len(source) == len(result) and all(
            _same_json_material(left, right) for left, right in zip(source, result, strict=True)
        )
    if type(source) is float:
        return isfinite(source) and source.hex() == result.hex()
    if type(source) is Decimal:
        return source.is_finite() and source.as_tuple() == result.as_tuple()
    return (source is None or type(source) in {str, int, bool}) and source == result


def decode_wire_demand_result(content: bytes) -> WireReadDemandResultResult:
    """Decode exact bytes into an owned generated record, preserving all material.

    Omitted optional keys remain omitted. The recursive equality check makes
    validation a refusing identity projection, including exact numeric content.
    """
    if type(content) is not bytes:
        raise TypeError("native demand decoding requires exact immutable bytes")
    source = wire_json_loads(content)
    candidate = own_json_value(source)
    validator = captured_demand_wire_validator()
    result = (
        _demand_result_adapter().validate_python(candidate, strict=True, extra="forbid")
        if validator is None
        else cast(WireReadDemandResultResult, validator.validate_python(candidate))
    )
    if not _same_json_material(source, result):
        raise ValueError("typed demand decoding changed its material native record")
    return result
