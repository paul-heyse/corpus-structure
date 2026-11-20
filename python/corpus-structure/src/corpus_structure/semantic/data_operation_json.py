"""Exact JSON numbers at DDO context boundaries, independent of typed values.

RapidJSON's NM_DECIMAL parses fractional literals as Decimal and emits Decimal
as JSON numbers: https://python-rapidjson.readthedocs.io/en/latest/loads.html
and https://python-rapidjson.readthedocs.io/en/latest/dumps.html .
"""

from decimal import Decimal
from typing import Any

import rapidjson

# Operator JSON includes exact fractional scope values; semantic tagged values
# and native admission retain their own interpretation/authorization contracts.
type DdoJsonValue = (
    bool | int | float | Decimal | str | list[DdoJsonValue] | dict[str, DdoJsonValue] | None
)


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
        if isinstance(value, dict):
            return {
                name: presentation(item, scope=scope or name == "analyzed_scope")
                for name, item in value.items()
            }
        if isinstance(value, list):
            return [presentation(item, scope=scope) for item in value]
        return float(value) if isinstance(value, Decimal) and not scope else value

    return presentation(json_loads(content))
