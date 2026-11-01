"""Private PDF record representations compiled from the trusted model.

These are foundation schemas, not a publication or staging API. Field order, types
and nullability come from the shared physical projection, including inherited
record declarations. JSON uses a declared UTF-8 wire representation in Arrow.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

import pyarrow as pa
from pydantic import ConfigDict, Field, JsonValue, TypeAdapter, create_model
from sqlalchemy import BigInteger, Boolean, Integer, MetaData, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB

from .metadata import PHYSICAL_MODEL_ID, metadata


def record_tables(model: MetaData | None = None):
    """Select the fixed private families from an explicitly supplied projection."""
    model = metadata if model is None else model
    return {
        name: table
        for name, table in model.tables.items()
        if table.name.startswith("pdf_record_") or table.name.startswith("pdf_artifact_")
    }


def _types(column):
    if isinstance(column.type, Text):
        return str, pa.string(), "text"
    if isinstance(column.type, BigInteger):
        return int, pa.int64(), "bigint"
    if isinstance(column.type, Integer):
        return int, pa.int32(), "integer"
    if isinstance(column.type, Boolean):
        return bool, pa.bool_(), "boolean"
    if isinstance(column.type, BYTEA):
        return bytes, pa.binary(), "bytea"
    if isinstance(column.type, JSONB):
        return JsonValue, pa.string(), "jsonb:utf8"
    raise ValueError(f"unsupported PDF record field {column}: {column.type}")


def record_arrow_schema(name: str, *, model: MetaData | None = None) -> pa.Schema:
    table = record_tables(model)[name]
    return pa.schema(
        [
            pa.field(
                column.name,
                _types(column)[1],
                nullable=column.nullable,
                metadata={
                    "postgresql": _types(column)[2],
                    "constraints": json.dumps(column.info, sort_keys=True),
                },
            )
            for column in table.columns
        ],
        metadata={"relation": name, "physical_model_id": PHYSICAL_MODEL_ID},
    )


def record_boundary_adapter(name: str, *, model: MetaData | None = None) -> TypeAdapter[Any]:
    table = record_tables(model)[name]
    fields: dict[str, Any] = {}
    literal_factory: Any = Literal
    for column in table.columns:
        kind: Any = _types(column)[0]
        if column.info.get("enum"):
            kind = literal_factory[column.info["enum"]]
        kind = Annotated[
            kind,
            Field(
                ge=column.info.get("minimum"),
                le=column.info.get("maximum"),
                pattern=column.info.get("pattern"),
            ),
        ]
        fields[column.name] = (kind | None, None) if column.nullable else (kind, ...)
    boundary = create_model(
        "PdfRecord_" + table.name,
        __config__=ConfigDict(strict=True, extra="forbid"),
        **fields,
    )
    return TypeAdapter(boundary)
