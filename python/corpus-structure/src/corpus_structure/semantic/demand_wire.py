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
from .data_operation_json import native_json_loads, own_json_value, own_wire_json_value

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


@lru_cache(maxsize=1)
def _cut_validator():
    from .data_operation_wire import prepare_wire_schema, wire_contextual_fields, wire_record_schema

    return prepare_wire_schema(
        wire_record_schema("cut_selection"), contextual_fields=wire_contextual_fields()
    )


def decode_wire_cut(content: bytes) -> dict:
    """Interpret the explicit cut fields while leaving its original identity bytes owned."""
    return _cut_validator()(native_json_loads(content))


def decode_wire_demand_request(content: bytes, *, demand_id: str | None = None) -> dict:
    from .data_operation_wire import validate_native_wire

    parsed = native_json_loads(content)
    if demand_id is not None:
        parsed = {"demand_id": demand_id, **parsed}
    return validate_native_wire("read_demand_result", "input", parsed)


def declared_frontier(value: object) -> bool:
    return isinstance(value, dict) and value.get("view") == "frontier"


def project_frontier_record(value: dict) -> dict:
    from .data_operation_wire import validate_native_wire

    return validate_native_wire("read_demand_result", "output", value)


def decode_wire_demand_result(content: bytes) -> WireReadDemandResultResult:
    """Decode exact bytes into an owned generated record, preserving all material.

    Omitted optional keys remain omitted. The recursive equality check makes
    validation a refusing identity projection, including exact numeric content.
    """
    if type(content) is not bytes:
        raise TypeError("native demand decoding requires exact immutable bytes")
    parsed = native_json_loads(content)
    source = (
        project_frontier_record(parsed)
        if declared_frontier(parsed)
        else own_wire_json_value(parsed)
    )
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
