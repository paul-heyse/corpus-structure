"""PostgreSQL transport for exact DDO scope values."""

from typing import Any

from sqlalchemy import JSON, Text, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from .data_operation_json import json_bytes, json_loads


def json_context_value(value: Any) -> Any:
    """An explicit JSON null uses SQLAlchemy's native sentinel, never SQL NULL."""
    return JSON.NULL if value is None else value


def json_context_equal(column, value: Any):
    return column == json_context_value(value)


class ContextJSONB(TypeDecorator):
    """Cast only scope-bearing DDO columns through text, bypassing driver floats."""

    impl = Text
    cache_ok = True

    def bind_expression(self, bindparam):
        return cast(bindparam, JSONB)

    def column_expression(self, column):
        return cast(column, self)

    def process_bind_param(self, value, dialect):
        if value is JSON.NULL:
            return "null"
        return None if value is None else json_bytes(value).decode()

    def process_result_value(self, value, dialect):
        return None if value is None else json_loads(value)
