"""Model-owned release archive relations and exact directional binary COPY.

Only JSONB columns use JSON text. Native bytea content stays binary throughout the
stream; immutable archive bytes and the reader format are unchanged.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pyarrow as pa
from sqlalchemy import BigInteger, Boolean, Integer, Table, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.sql.ddl import sort_tables

from .arrow_transfer import ArrowTransferError, ArrowWriteProfile
from .metadata import PHYSICAL_MODEL_ID, metadata


def archive_tables() -> tuple[Table, ...]:
    selected = sorted(
        (t for t in metadata.tables.values() if t.info.get("archive_role") is not None),
        key=lambda t: t.fullname,
    )
    roles = [t.info["archive_role"] for t in selected]
    if (
        any(t.schema != "sem" or not t.primary_key.columns for t in selected)
        or any(roles.count(role) != 1 for role in ("header", "input", "artifact"))
        or any(role not in {"header", "input", "artifact", "projection"} for role in roles)
    ):
        raise ValueError("invalid trusted release archive relation declaration")
    return tuple(sort_tables(selected))


def scratch_name(relation: Table) -> str:
    return "cs_archive_" + relation.name


def archive_write_profile(relation: Table, release_id: str) -> ArrowWriteProfile:
    fields = []
    wires = []
    for column in relation.columns:
        kind = column.type
        if isinstance(kind, Text):
            arrow, wire = pa.string(), "text"
        elif isinstance(kind, BigInteger):
            arrow, wire = pa.int64(), "bigint"
        elif isinstance(kind, Integer):
            arrow, wire = pa.int32(), "integer"
        elif isinstance(kind, Boolean):
            arrow, wire = pa.bool_(), "boolean"
        elif isinstance(kind, BYTEA):
            arrow, wire = pa.binary(), "bytea"
        elif isinstance(kind, JSONB):
            arrow, wire = pa.string(), "jsonb"
        else:
            raise ArrowTransferError(f"unsupported archive column {column}: {kind}")
        fields.append(pa.field(column.name, arrow, nullable=column.nullable))
        wires.append(wire)
    return ArrowWriteProfile.prepare(
        release_id=release_id,
        physical_id=PHYSICAL_MODEL_ID,
        operation="archive:" + relation.fullname,
        schema=pa.schema(fields),
        wire_types=wires,
    )


def archive_batch(
    relation: Table, profile: ArrowWriteProfile, rows: Sequence[Mapping[str, Any]]
) -> pa.RecordBatch:
    columns: list[list[Any]] = [[] for _ in relation.columns]
    names = set(relation.columns.keys())
    for row in rows:
        if set(row) != names:
            raise ArrowTransferError(f"archive row columns differ: {relation.fullname}")
        for column, values in zip(relation.columns, columns, strict=True):
            value = row[column.name]
            if isinstance(column.type, JSONB):
                value = (
                    None
                    if value is None
                    else json.dumps(
                        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    )
                )
            elif isinstance(column.type, BYTEA) and isinstance(value, memoryview):
                value = bytes(value)
            values.append(value)
    return pa.RecordBatch.from_arrays(
        [
            pa.array(values, type=field.type)
            for values, field in zip(columns, profile.schema, strict=True)
        ],
        schema=profile.schema,
    )
