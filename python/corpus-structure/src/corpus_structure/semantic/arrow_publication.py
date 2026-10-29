"""Frozen Arrow input to SP-03, encoded directly into publisher-owned staging.

Arrow schemas derive from the fixed metadata transport. Decimal128 is an optional exact
projection; lexical decimal and temporal text never cross a lossy native conversion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import astuple, dataclass, field, fields
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType

import psycopg
import pyarrow as pa
from pgpq import ArrowToPostgresBinaryEncoder
from pgpq.encoders import StringEncoderBuilder
from pgpq.schema import Jsonb
from psycopg import sql
from sqlalchemy import Connection, Engine, text

from .identity import canonical_bytes
from .publication import STAGE_TYPES, PublicationBatch, PublicationReceipt, _publish


class ArrowPublicationError(ValueError):
    """Arrow input cannot faithfully represent the protected transport."""


class StaleAnalysisError(ValueError):
    """Recompute analysis from a new snapshot before attempting publication again."""


def stage_schema(name: str, *, decimals: Mapping[str, pa.DataType] | None = None) -> pa.Schema:
    """Compile exact field order and PostgreSQL wire types from SP-03 metadata.

    All staging columns are nullable (native admission validates required values).
    Decimal precision/scale may be chosen for the batch, within pgpq's Decimal128 profile.
    """
    row_type, types = STAGE_TYPES[name]
    result = []
    for column, pg_type in zip(fields(row_type), types, strict=True):
        if pg_type == "numeric":
            arrow_type = (decimals or {}).get(column.name, pa.decimal128(38, 0))
            if not pa.types.is_decimal128(arrow_type):
                raise ArrowPublicationError("numeric transport requires exact Decimal128")
        else:
            try:
                arrow_type = {
                    "text": pa.string(),
                    "bigint": pa.int64(),
                    "boolean": pa.bool_(),
                    "jsonb": pa.string(),
                }[pg_type]
            except KeyError as exc:
                raise ArrowPublicationError(f"unsupported staging type {pg_type}") from exc
        result.append(pa.field(column.name, arrow_type, nullable=True))
    return pa.schema(result)


def _encoder(name: str, schema: pa.Schema) -> ArrowToPostgresBinaryEncoder:
    encoders = {
        f.name: StringEncoderBuilder.new_with_output(f, Jsonb())
        if pg_type == "jsonb"
        else ArrowToPostgresBinaryEncoder.infer_encoder(f)
        for f, pg_type in zip(schema, STAGE_TYPES[name][1], strict=True)
    }
    encoder = ArrowToPostgresBinaryEncoder.new_with_encoders(schema, encoders)
    aliases = {"bool": "boolean", "int8": "bigint"}
    actual = tuple(
        (
            c.name,
            aliases.get(str(c.data_type.ddl()).lower(), str(c.data_type.ddl()).lower()),
            c.nullable,
        )
        for c in encoder.schema().columns
    )
    expected = tuple(
        (f.name, typ, True) for f, typ in zip(schema, STAGE_TYPES[name][1], strict=True)
    )
    if actual != expected:
        raise ArrowPublicationError(f"pgpq wire schema differs from protected {name}: {actual}")
    return encoder


@dataclass(frozen=True, init=False)
class ArrowPublicationBatch:
    release_id: str
    realization_id: str
    batch_id: str
    relations: Mapping[str, pa.Table]
    expected_data_revision: int | None = None
    _content: bytes = field(init=False, repr=False)

    def __init__(
        self,
        release_id: str,
        realization_id: str,
        batch_id: str,
        relations: Mapping[str, pa.Table | tuple[pa.RecordBatch, ...]],
        expected_data_revision: int | None = None,
    ) -> None:
        object.__setattr__(self, "release_id", release_id)
        object.__setattr__(self, "realization_id", realization_id)
        object.__setattr__(self, "batch_id", batch_id)
        object.__setattr__(self, "expected_data_revision", expected_data_revision)
        if any(
            type(v) is not str or not v
            for v in (self.release_id, self.realization_id, self.batch_id)
        ):
            raise ArrowPublicationError(
                "publication requires release, realization and batch identity"
            )
        if self.expected_data_revision is not None and (
            type(self.expected_data_revision) is not int or self.expected_data_revision < 0
        ):
            raise ArrowPublicationError("expected revision must be a nonnegative integer")
        unknown = relations.keys() - STAGE_TYPES.keys()
        if unknown:
            raise ArrowPublicationError(f"unknown staging relations: {sorted(unknown)}")
        frozen = {}
        body = {}
        for name in STAGE_TYPES:
            source = relations.get(name)
            if source is None:
                value = pa.Table.from_batches([], schema=stage_schema(name))
            elif isinstance(source, pa.Table):
                value = source
            elif isinstance(source, tuple) and source:
                value = pa.Table.from_batches(source)
            else:
                raise ArrowPublicationError(f"{name} requires a Table or nonempty tuple of batches")
            decimals = {f.name: f.type for f in value.schema if pa.types.is_decimal(f.type)}
            expected = stage_schema(name, decimals=decimals)
            if not value.schema.equals(expected, check_metadata=False):
                raise ArrowPublicationError(f"{name} schema must be {expected}")
            # IPC owns immutable buffers even when input wraps mutable NumPy memory.
            sink = pa.BufferOutputStream()
            with pa.ipc.new_stream(sink, expected) as writer:
                writer.write_table(value)
            value = pa.ipc.open_stream(pa.BufferReader(sink.getvalue().to_pybytes())).read_all()
            _encoder(name, expected)
            rows = []
            for row in value.to_pylist():
                if name == "typed_value":
                    if row["opaque_payload"] is not None:
                        raise ArrowPublicationError(
                            "opaque payload has no admitted semantic lowering"
                        )
                    for column in ("integer_value", "numeric_value"):
                        numeric = row[column]
                        if numeric is not None:
                            lexical = (
                                row["text_value"]
                                if column == "integer_value"
                                else row["decimal_lexical"]
                            )
                            if lexical is None or Decimal(lexical) != numeric:
                                raise ArrowPublicationError(
                                    "numeric projection contradicts exact lexical value"
                                )
                            if column == "integer_value" and numeric != numeric.to_integral_value():
                                raise ArrowPublicationError("integer projection is not integral")
                            row[column] = format(
                                numeric.copy_abs() if numeric.is_zero() else numeric, "f"
                            )
                rows.append(list(row.values()))
            body[name] = sorted(rows, key=canonical_bytes)
            frozen[name] = value
        object.__setattr__(self, "relations", MappingProxyType(frozen))
        object.__setattr__(
            self, "_content", canonical_bytes([self.release_id, self.realization_id, body])
        )

    @property
    def content(self) -> bytes:
        return self._content

    @classmethod
    def from_rows(
        cls, batch: PublicationBatch, *, expected_data_revision: int | None = None
    ) -> ArrowPublicationBatch:
        """Adapt legitimate row producers at freeze, retaining exact optional projections.

        Decimal128 overflow clears only the optional numeric projection, never lexical text.
        This adapter is not used by analytical kernels, which supply their result batches.
        """
        relations = {}
        for name, (row_type, _) in STAGE_TYPES.items():
            names = [f.name for f in fields(row_type)]
            rows = [dict(zip(names, astuple(r), strict=True)) for r in getattr(batch, name)]
            decimals = {}
            if name == "typed_value":
                for column in ("integer_value", "numeric_value"):
                    candidates = [Decimal(r[column]) for r in rows if r[column] is not None]
                    scales = []
                    for value in candidates:
                        exponent = value.as_tuple().exponent
                        if not isinstance(exponent, int):
                            raise ArrowPublicationError("non-finite numeric projection")
                        scale = max(-exponent, 0)
                        if max(len(value.as_tuple().digits) + exponent, 0) + scale <= 38:
                            scales.append(scale)
                    scale = max(scales, default=0)
                    # Individually out-of-profile values do not force exact smaller
                    # values to lose their projection. Shared-scale overflow is NULL.
                    decimal_type = pa.decimal128(38, scale)
                    decimals[column] = decimal_type
                    for row in rows:
                        if row[column] is not None:
                            try:
                                pa.scalar(row[column], type=decimal_type)
                            except pa.ArrowInvalid, OverflowError:
                                if column == "integer_value" and row["text_value"] is None:
                                    row["text_value"] = str(row[column])
                                row[column] = None
            relations[name] = pa.Table.from_pylist(
                rows, schema=stage_schema(name, decimals=decimals)
            )
        return cls(
            batch.release_id,
            batch.realization_id,
            batch.batch_id,
            relations,
            expected_data_revision,
        )


def stage_arrow(connection: Connection, batch: ArrowPublicationBatch) -> None:
    connection.execute(text("SELECT data.begin_stage()"))
    driver = connection.connection.driver_connection
    if not isinstance(driver, psycopg.Connection):
        raise TypeError("publication requires the existing psycopg-backed SQLAlchemy engine")
    with driver.cursor() as cursor:
        for name, relation in batch.relations.items():
            encoder = _encoder(name, relation.schema)
            statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT BINARY)").format(
                sql.Identifier("pg_temp", "sp_" + name),
                sql.SQL(",").join(map(sql.Identifier, relation.column_names)),
            )
            with cursor.copy(statement) as copy:
                copy.write(encoder.write_header())
                for chunk in relation.to_batches():
                    copy.write(encoder.write_batch(chunk))
                copy.write(encoder.finish())


def publish_arrow_on_connection(
    connection: Connection, batch: ArrowPublicationBatch
) -> PublicationReceipt:
    """Stage and publish without committing the SQLAlchemy-owned transaction."""
    stage_arrow(connection, batch)
    function = "data.publish_batch(:r,:z,:b,:c)"
    params: dict[str, str | bytes | int] = {
        "r": batch.release_id,
        "z": batch.realization_id,
        "b": batch.batch_id,
        "c": batch.content,
    }
    if batch.expected_data_revision is not None:
        function = "data.publish_analysis_batch(:r,:z,:b,:c,:expected)"
        params["expected"] = batch.expected_data_revision
    try:
        revision = connection.execute(text("SELECT " + function), params).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, "orig", exc), "sqlstate", None) == "P0004":
            raise StaleAnalysisError(
                "analysis source revision changed; recompute outside publication"
            ) from exc
        raise
    return PublicationReceipt(batch.batch_id, revision, sha256(batch.content).hexdigest())


def publish_arrow(
    engine: Engine, batch: ArrowPublicationBatch, *, attempts: int = 3
) -> PublicationReceipt:
    return _publish(engine, batch, publish_arrow_on_connection, attempts=attempts)
