"""Primitive names shared by binding evaluation and native compilation."""

from datetime import date, datetime
from decimal import Decimal

BINDING_VALUE_TYPES = {
    "string": str,
    "uri": str,
    "uriorcurie": str,
    "integer": int,
    "boolean": bool,
    "float": float,
    "double": float,
    "decimal": Decimal,
    "date": date,
    "datetime": datetime,
    "bytes": bytes,
}
BINDING_PRIMITIVE_ALIASES = {
    "str": "string",
    "int": "integer",
    "bool": "boolean",
    "Decimal": "decimal",
}
BINDING_PRIMITIVES = (*BINDING_VALUE_TYPES, "json")
