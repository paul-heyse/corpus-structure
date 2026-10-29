"""Pydantic's native JSON-extra schema without narrowing BaseModel's nullable storage slot."""

from typing import Any

from pydantic import GetCoreSchemaHandler, JsonValue
from pydantic_core import CoreSchema


def json_extras_schema(source: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
    """Retain generated model validators and install the same native extras value schema."""
    schema = handler(source)
    node = schema
    while node["type"] in {"function-before", "function-after", "function-wrap"}:
        node = node["schema"]
    if node["type"] != "model":
        raise TypeError("JSON extras require a model schema")
    fields = node["schema"]
    while fields["type"] in {"function-before", "function-after", "function-wrap"}:
        fields = fields["schema"]
    if fields["type"] != "model-fields":
        raise TypeError("JSON extras require model fields")
    fields["extras_schema"] = handler.generate_schema(JsonValue)
    return schema
