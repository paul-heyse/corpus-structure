"""Detached native-demand records from the generated structural wire model.

Draft7 admission remains with the native call. This decoder uses the generated
TypedDict to preserve Python field/union fidelity without silently dropping keys
or coercing the material consumed by selected projections.
"""

from functools import lru_cache

from pydantic import TypeAdapter

from ._data_operation_wire import WireDemandReadScope, WireReadDemandResultResult
from .data_operation_json import json_bytes, wire_json_loads


@lru_cache(maxsize=1)
def _demand_result_adapter() -> TypeAdapter[WireReadDemandResultResult]:
    return TypeAdapter(WireReadDemandResultResult)


@lru_cache(maxsize=1)
def _demand_scope_adapter() -> TypeAdapter[WireDemandReadScope]:
    return TypeAdapter(WireDemandReadScope)


def validate_wire_demand_scope(value: object) -> WireDemandReadScope:
    return _demand_scope_adapter().validate_python(value, strict=True, extra="forbid")


def _same_json_types(source, result) -> bool:
    """Validation must preserve exact scalar types as well as JSON spelling."""
    if type(source) is not type(result):
        return False
    if type(source) is dict:
        return source.keys() == result.keys() and all(
            _same_json_types(source[key], result[key]) for key in source
        )
    if type(source) is list:
        return len(source) == len(result) and all(
            _same_json_types(left, right) for left, right in zip(source, result, strict=True)
        )
    return True


def decode_wire_demand_result(content: bytes) -> WireReadDemandResultResult:
    """Decode exact bytes into an owned generated record, preserving all material.

    Omitted optional keys remain omitted. The canonical equality check makes
    validation a refusing identity projection, including exact numeric content.
    """
    if type(content) is not bytes:
        raise TypeError("native demand decoding requires exact immutable bytes")
    source = wire_json_loads(content)
    witness = json_bytes(source)
    result = _demand_result_adapter().validate_python(source, strict=True, extra="forbid")
    if not _same_json_types(source, result) or json_bytes(result) != witness:
        raise ValueError("typed demand decoding changed its material native record")
    return result
