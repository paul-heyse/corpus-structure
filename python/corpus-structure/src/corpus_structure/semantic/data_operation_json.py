"""Finite JSON interchange and the archived DDO context-number profile.

RapidJSON's NM_DECIMAL parses fractional literals as Decimal and emits Decimal
as JSON numbers: https://python-rapidjson.readthedocs.io/en/latest/loads.html
and https://python-rapidjson.readthedocs.io/en/latest/dumps.html .
"""

import json
import math
from decimal import Decimal
from typing import Any

import rapidjson

# Operator JSON includes exact fractional scope values; semantic tagged values
# and native admission retain their own interpretation/authorization contracts.
type DdoJsonValue = (
    bool | int | float | Decimal | str | list[DdoJsonValue] | dict[str, DdoJsonValue] | None
)


class JsonBoundaryError(ValueError):
    """A value cannot cross the supported finite JSON boundary."""


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JsonBoundaryError("JSON contains a repeated object key")
        result[key] = value
    return result


def _json_constant(value):
    raise JsonBoundaryError("JSON requires finite numbers")


def _json_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise JsonBoundaryError("JSON number exceeds the finite floating-point domain")
    return result


def finite_json_loads(content: str | bytes) -> Any:
    """Read ordinary PostgreSQL-compatible JSON without implicit key or number coercion."""
    try:
        return _own_finite_json(
            json.loads(
                content,
                object_pairs_hook=_json_object,
                parse_constant=_json_constant,
                parse_float=_json_float,
            )
        )
    except (ValueError, RecursionError) as error:
        raise JsonBoundaryError("invalid finite JSON document") from error


def finite_json_bytes(value: Any) -> bytes:
    """Encode owned finite JSON; identity and retained original bytes have separate owners."""
    try:
        return json.dumps(
            _own_finite_json(value),
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as error:
        raise JsonBoundaryError("unsupported finite JSON value") from error


def _own_finite_json(value):
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        if "\x00" in value:
            raise JsonBoundaryError("PostgreSQL JSON strings cannot contain zero characters")
        value.encode("utf-8")
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_own_finite_json(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_own_finite_json(key): _own_finite_json(item) for key, item in value.items()}
    raise JsonBoundaryError("finite JSON requires owned inert values")


def json_loads(content: str | bytes) -> Any:
    return rapidjson.loads(content, number_mode=rapidjson.NM_DECIMAL, allow_nan=False)


def json_bytes(value: Any) -> bytes:
    return rapidjson.dumps(
        value,
        number_mode=rapidjson.NM_DECIMAL,
        allow_nan=False,
        sort_keys=True,
        ensure_ascii=False,
        bytes_mode=rapidjson.BM_NONE,
    ).encode()


def scope_identity(value: Any) -> Any:
    """JSONB numeric equality, including equal integral/fractional spellings."""
    import json

    return json.loads(json_bytes(value), parse_int=Decimal, parse_float=Decimal)


def wire_json_loads(content: str | bytes) -> Any:
    """Keep scope JSON exact while retaining existing non-context float values."""

    def presentation(value, *, scope=False):
        if type(value) is dict:
            return {
                name: presentation(item, scope=scope or name == "analyzed_scope")
                for name, item in value.items()
            }
        if type(value) is list:
            return [presentation(item, scope=scope) for item in value]
        return float(value) if type(value) is Decimal and not scope else value

    return presentation(json_loads(content))


def own_json_value(value):
    """Copy only exact inert JSON/Decimal values; never call a user's protocol.

    This is ownership preparation, not schema validation. Native wire and public
    request validators retain their own domain constraints.
    """
    import math

    if value is None:
        return None
    if type(value) is bool:
        return value
    if type(value) is int:
        return value
    if type(value) is str:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("owned JSON requires finite numbers")
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("owned JSON requires finite numbers")
        return value
    if type(value) is list:
        return [own_json_value(item) for item in value]
    if type(value) is dict:
        result = {}
        for key in value:
            if type(key) is not str:
                raise TypeError("owned JSON requires exact string keys")
            result[key] = own_json_value(value[key])
        return result
    raise TypeError("owned JSON requires exact inert values")
