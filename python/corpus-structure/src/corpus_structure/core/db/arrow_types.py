"""SQL-to-Arrow types for native source exports, independent of model compilation."""

from __future__ import annotations

import pyarrow as pa
from sqlalchemy import BigInteger, Boolean, Double, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, REAL, REGCONFIG, TIMESTAMP
from sqlalchemy.types import TypeEngine

from corpus_structure.schema.model import ModelError


def sql_arrow_type(typ: TypeEngine) -> pa.DataType:
    """Preserve the physical scalar/array types selected by native source export."""
    if isinstance(typ, ARRAY):
        return pa.list_(pa.field("item", sql_arrow_type(typ.item_type), nullable=False))
    by_class: list[tuple[type, pa.DataType]] = [
        (BigInteger, pa.int64()),
        (SmallInteger, pa.int16()),
        (Integer, pa.int32()),
        (REAL, pa.float32()),
        (Double, pa.float64()),
        (Boolean, pa.bool_()),
        (TIMESTAMP, pa.timestamp("us", tz="UTC")),
        (JSONB, pa.json_(pa.string())),
        (BYTEA, pa.binary()),
        (REGCONFIG, pa.string()),
        (Text, pa.string()),
    ]
    for cls, arrow in by_class:
        if isinstance(typ, cls):
            return arrow
    raise ModelError([f"no Arrow type for SQL type {typ!r}"])
