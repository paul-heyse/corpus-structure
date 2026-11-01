"""Private PDF record representations compiled from the trusted model.

These are foundation schemas, not a publication or staging API. Field order, types
and nullability come from the shared physical projection, including inherited
record declarations. JSON uses a declared UTF-8 wire representation in Arrow.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Annotated, Any, Literal

import pyarrow as pa
from pydantic import ConfigDict, Field, JsonValue, TypeAdapter, create_model
from sqlalchemy import BigInteger, Boolean, Integer, MetaData, Numeric, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB

from .arrow_transfer import ArrowWriteProfile
from .metadata import PHYSICAL_MODEL_ID, metadata


def _record_tables(model: MetaData | None, *, derived: bool | None):
    selected = metadata if model is None else model
    return {
        name: table
        for name, table in selected.tables.items()
        if (table.name.startswith("pdf_record_") or table.name.startswith("pdf_artifact_"))
        and (
            derived is None
            or (table.info.get("pdf_record_boundary_role") == "derived_core") == derived
        )
    }


def record_tables(model: MetaData | None = None):
    """Select every private record relation for native custody and privilege management."""
    return _record_tables(model, derived=None)


def record_upload_tables(model: MetaData | None = None):
    """Select upload/wire records; derived query projections use SQLAlchemy Core."""
    return _record_tables(model, derived=False)


def derived_record_tables(model: MetaData | None = None):
    """Select model-declared projections without inventing a bounded Arrow numeric type."""
    return _record_tables(model, derived=True)


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
    table = (metadata if model is None else model).tables[name]
    if table.info.get("pdf_record_boundary_role") == "derived_core":
        raise ValueError(f"derived PDF record projection {name} uses the SQLAlchemy Core boundary")
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
    table = (metadata if model is None else model).tables[name]
    fields: dict[str, Any] = {}
    literal_factory: Any = Literal
    for column in table.columns:
        kind: Any = Decimal if isinstance(column.type, Numeric) else _types(column)[0]
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


def record_write_profile(
    name: str, *, release_id: str, model: MetaData | None = None
) -> ArrowWriteProfile:
    """Derive private write fields and wire types from the same physical projection."""
    selected = metadata if model is None else model
    return ArrowWriteProfile.prepare(
        release_id=release_id,
        physical_id=PHYSICAL_MODEL_ID,
        operation="private-pdf:" + name,
        schema=record_arrow_schema(name, model=selected),
        wire_types=tuple(_types(c)[2].removesuffix(":utf8") for c in selected.tables[name].columns),
    )
