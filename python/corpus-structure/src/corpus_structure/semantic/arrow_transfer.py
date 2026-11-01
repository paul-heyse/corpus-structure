"""Prepared directional Arrow write profiles and transaction-borrowing binary COPY.

Profiles contain no connection or encoder state. Every stream builds its own encoder;
preparation/adoption, rollback, publication and replay remain the calling operation's job.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

import psycopg
import pyarrow as pa
from pgpq import ArrowToPostgresBinaryEncoder
from pgpq.encoders import (
    LargeStringEncoderBuilder,
    StringEncoderBuilder,
    StringViewEncoderBuilder,
)
from pgpq.schema import Jsonb
from psycopg import sql
from sqlalchemy import Connection

from corpus_structure.core.db.lifetime import BorrowerCancellation


class ArrowTransferError(ValueError):
    """Input or encoder schema differs from the selected directional profile."""


_ALIASES = {"bool": "boolean", "int8": "bigint", "int4": "integer"}


def _wire_type(value: str) -> str:
    value = value.lower()
    return _ALIASES.get(value, value)


@dataclass(frozen=True)
class WriteField:
    field: pa.Field
    wire_type: str
    encoding: Literal["inferred", "jsonb:utf8"]


@dataclass(frozen=True)
class ArrowWriteProfile:
    release_id: str
    physical_id: str
    compiler_id: str
    operation: str
    schema: pa.Schema
    fields: tuple[WriteField, ...]

    @classmethod
    def prepare(
        cls,
        *,
        release_id: str,
        physical_id: str,
        operation: str,
        schema: pa.Schema,
        wire_types: Sequence[str],
    ) -> ArrowWriteProfile:
        if len(set(schema.names)) != len(schema):
            raise ArrowTransferError("COPY profiles require unique field names")
        specs = []
        for field, wire in zip(schema, wire_types, strict=True):
            wire = _wire_type(wire)
            if pa.types.is_timestamp(field.type) and field.type.unit == "ns":
                raise ArrowTransferError(
                    "nanosecond timestamps require an explicit exact write normalization"
                )
            if wire == "jsonb" and not (
                pa.types.is_string(field.type)
                or pa.types.is_large_string(field.type)
                or pa.types.is_string_view(field.type)
            ):
                raise ArrowTransferError("JSONB wire requires a declared UTF-8 Arrow field")
            if wire == "numeric" and not pa.types.is_decimal128(field.type):
                raise ArrowTransferError("NUMERIC write requires exact Decimal128")
            specs.append(WriteField(field, wire, "jsonb:utf8" if wire == "jsonb" else "inferred"))
        return cls(release_id, physical_id, "arrow-write-1", operation, schema, tuple(specs))

    @property
    def identity(self) -> str:
        digest = sha256(self.schema.serialize().to_pybytes())
        for value in (
            self.release_id,
            self.physical_id,
            self.compiler_id,
            self.operation,
            *(f"{f.field.name}:{f.wire_type}:{f.encoding}" for f in self.fields),
        ):
            encoded = value.encode()
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
        return "arrow-write:" + digest.hexdigest()

    def new_encoder(self) -> ArrowToPostgresBinaryEncoder:
        builders: dict[str, Any] = {}
        for spec in self.fields:
            field = spec.field
            if spec.encoding == "jsonb:utf8":
                factory = (
                    StringEncoderBuilder
                    if pa.types.is_string(field.type)
                    else LargeStringEncoderBuilder
                    if pa.types.is_large_string(field.type)
                    else StringViewEncoderBuilder
                )
                builders[field.name] = factory.new_with_output(field, Jsonb())
            else:
                builders[field.name] = ArrowToPostgresBinaryEncoder.infer_encoder(field)
        encoder = ArrowToPostgresBinaryEncoder.new_with_encoders(self.schema, builders)
        actual = tuple(
            (column.name, _wire_type(str(column.data_type.ddl())), column.nullable)
            for column in encoder.schema().columns
        )
        expected = tuple((f.field.name, f.wire_type, f.field.nullable) for f in self.fields)
        if actual != expected:
            raise ArrowTransferError(
                f"pgpq wire schema differs for {self.operation}: {actual}; expected {expected}"
            )
        return encoder

    def validate_batch(self, batch: pa.RecordBatch) -> None:
        if not batch.schema.equals(self.schema, check_metadata=True):
            raise ArrowTransferError(f"Arrow wire schema differs for {self.operation}")


def copy_arrow_stream(
    connection: Connection,
    profile: ArrowWriteProfile,
    *,
    target: tuple[str, str],
    batches: Iterable[pa.RecordBatch],
    before_encode: Callable[[pa.RecordBatch], None] | None = None,
    cancellation: BorrowerCancellation | None = None,
) -> int:
    """Write one authenticated scratch stream in the caller's current Core transaction.

    The caller prepares and authenticates ``target`` before this call. Errors escape the
    COPY context; failed native encoder state is discarded without attempting a footer.
    """
    if cancellation is not None:
        cancellation.check_active()
    driver = connection.connection.driver_connection
    if not isinstance(driver, psycopg.Connection):
        raise TypeError("Arrow COPY requires the existing Psycopg-backed Core connection")
    encoder = profile.new_encoder()
    statement = sql.SQL("COPY {} ({}) FROM STDIN (FORMAT BINARY)").format(
        sql.Identifier(*target), sql.SQL(",").join(map(sql.Identifier, profile.schema.names))
    )
    count = 0
    with driver.cursor() as cursor, cursor.copy(statement) as copy:
        copy.write(encoder.write_header())
        for batch in batches:
            if cancellation is not None:
                cancellation.check_active()
            profile.validate_batch(batch)
            if before_encode is not None:
                before_encode(batch)
            copy.write(encoder.write_batch(batch))
            count += batch.num_rows
        if cancellation is not None:
            cancellation.check_active()
        copy.write(encoder.finish())
    return count
