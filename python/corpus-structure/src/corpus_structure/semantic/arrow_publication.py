"""Frozen Arrow input to SP-03, encoded directly into publisher-owned staging.

Arrow schemas derive from the fixed metadata transport. Decimal128 is an optional exact
projection; lexical decimal and temporal text never cross a lossy native conversion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType

import pyarrow as pa
from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation

from .arrow_transfer import ArrowTransferError, ArrowWriteProfile, copy_arrow_stream
from .identity import canonical_bytes
from .metadata import PHYSICAL_MODEL_ID
from .publication import (
    STAGE_TYPES,
    PublicationBatch,
    PublicationReceipt,
    _publish,
    publication_row_values,
)
from .query import SnapshotBinding


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


def publication_write_profile(
    name: str, schema: pa.Schema, *, release_id: str
) -> ArrowWriteProfile:
    decimals = {f.name: f.type for f in schema if pa.types.is_decimal(f.type)}
    expected = stage_schema(name, decimals=decimals)
    if not schema.equals(expected, check_metadata=True):
        raise ArrowPublicationError(f"{name} schema must be {expected}")
    return ArrowWriteProfile.prepare(
        release_id=release_id,
        physical_id=PHYSICAL_MODEL_ID,
        operation="publication:" + name,
        schema=expected,
        wire_types=STAGE_TYPES[name][1],
    )


@dataclass(frozen=True, init=False)
class AppendPublication:
    release_id: str
    realization_id: str
    batch_id: str
    relations: Mapping[str, pa.Table]
    _content: bytes = field(init=False, repr=False)
    _write_profiles: Mapping[str, ArrowWriteProfile] = field(init=False, repr=False)

    def __init__(
        self,
        release_id: str,
        realization_id: str,
        batch_id: str,
        relations: Mapping[str, pa.Table | tuple[pa.RecordBatch, ...]],
    ) -> None:
        object.__setattr__(self, "release_id", release_id)
        object.__setattr__(self, "realization_id", realization_id)
        object.__setattr__(self, "batch_id", batch_id)
        if any(
            type(v) is not str or not v
            for v in (self.release_id, self.realization_id, self.batch_id)
        ):
            raise ArrowPublicationError(
                "publication requires release, realization and batch identity"
            )
        unknown = relations.keys() - STAGE_TYPES.keys()
        if unknown:
            raise ArrowPublicationError(f"unknown staging relations: {sorted(unknown)}")
        frozen = {}
        profiles = {}
        body = {}
        for name in STAGE_TYPES:
            source = relations.get(name)
            if source is None:
                value = pa.Table.from_batches([], schema=stage_schema(name))
            elif isinstance(source, pa.Table):
                value = source
            elif isinstance(source, tuple) and source:
                if any(
                    not part.schema.equals(source[0].schema, check_metadata=True) for part in source
                ):
                    raise ArrowPublicationError(f"{name} batch schema/metadata differs")
                value = pa.Table.from_batches(source)
            else:
                raise ArrowPublicationError(f"{name} requires a Table or nonempty tuple of batches")
            decimals = {f.name: f.type for f in value.schema if pa.types.is_decimal(f.type)}
            expected = stage_schema(name, decimals=decimals)
            if not value.schema.equals(expected, check_metadata=True):
                raise ArrowPublicationError(f"{name} schema must be {expected}")
            # IPC owns immutable buffers even when input wraps mutable NumPy memory.
            sink = pa.BufferOutputStream()
            with pa.ipc.new_stream(sink, expected) as writer:
                writer.write_table(value)
            value = pa.ipc.open_stream(pa.BufferReader(sink.getvalue().to_pybytes())).read_all()
            profiles[name] = publication_write_profile(name, expected, release_id=release_id)
            profiles[name].new_encoder()
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
                for column, pg_type in zip(
                    fields(STAGE_TYPES[name][0]), STAGE_TYPES[name][1], strict=True
                ):
                    if pg_type == "numeric" and isinstance(row[column.name], Decimal):
                        row[column.name] = format(row[column.name], "f")
                    elif pg_type == "jsonb" and row[column.name] is not None:
                        import json

                        row[column.name] = json.loads(row[column.name])
                rows.append(list(row.values()))
            body[name] = sorted(rows, key=canonical_bytes)
            frozen[name] = value
        object.__setattr__(self, "relations", MappingProxyType(frozen))
        object.__setattr__(self, "_write_profiles", MappingProxyType(profiles))
        object.__setattr__(
            self, "_content", canonical_bytes([self.release_id, self.realization_id, body])
        )

    @property
    def content(self) -> bytes:
        return self._content

    @classmethod
    def from_rows(cls, batch: PublicationBatch) -> AppendPublication:
        """Adapt legitimate row producers at freeze, retaining exact optional projections.

        Decimal128 overflow clears only the optional numeric projection, never lexical text.
        This adapter is not used by analytical kernels, which supply their result batches.
        """
        batch.validate_preparation()
        relations = {}
        for name, (row_type, _) in STAGE_TYPES.items():
            names = [f.name for f in fields(row_type)]
            rows = [
                dict(zip(names, publication_row_values(r), strict=True))
                for r in getattr(batch, name)
            ]
            for row in rows:
                for column, typ in zip(names, STAGE_TYPES[name][1], strict=True):
                    if typ == "jsonb" and row[column] is not None:
                        row[column] = canonical_bytes(row[column]).decode()
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
            if name != "typed_value":
                for column, pg_type in zip(names, STAGE_TYPES[name][1], strict=True):
                    if pg_type != "numeric":
                        continue
                    candidates = [Decimal(row[column]) for row in rows if row[column] is not None]
                    scale = max(
                        (max(-int(value.as_tuple().exponent), 0) for value in candidates), default=0
                    )
                    if scale > 38:
                        raise ArrowPublicationError(
                            "required numeric value exceeds Decimal128 profile"
                        )
                    decimals[column] = pa.decimal128(38, scale)
                    try:
                        for value in candidates:
                            pa.scalar(value, type=decimals[column])
                    except (pa.ArrowInvalid, OverflowError) as exc:
                        raise ArrowPublicationError(
                            "required numeric value exceeds Decimal128 profile"
                        ) from exc
            relations[name] = pa.Table.from_pylist(
                rows, schema=stage_schema(name, decimals=decimals)
            )
        return cls(
            batch.release_id,
            batch.realization_id,
            batch.batch_id,
            relations,
        )


@dataclass(frozen=True, init=False)
class SnapshotDerivedPublication:
    transport: AppendPublication
    source: SnapshotBinding
    operation_id: str
    projection_id: str
    contract_id: str
    cut_id: int | None
    profile_digest: str | None

    def __init__(
        self,
        release_id: str,
        realization_id: str,
        batch_id: str,
        relations: Mapping[str, pa.Table | tuple[pa.RecordBatch, ...]],
        *,
        source: SnapshotBinding,
        operation_id: str,
        projection_id: str,
        contract_id: str | None = None,
        cut_id: int | None = None,
        profile_digest: str | None = None,
    ) -> None:
        self._bind(
            AppendPublication(release_id, realization_id, batch_id, relations),
            source=source,
            operation_id=operation_id,
            projection_id=projection_id,
            contract_id=contract_id,
            cut_id=cut_id,
            profile_digest=profile_digest,
        )

    def _bind(
        self,
        transport: AppendPublication,
        *,
        source: SnapshotBinding,
        operation_id: str,
        projection_id: str,
        contract_id: str | None,
        cut_id: int | None,
        profile_digest: str | None,
    ) -> None:
        if type(transport) is not AppendPublication:
            raise ArrowPublicationError("derived composition requires an owned AppendPublication")
        release_id, realization_id = transport.release_id, transport.realization_id
        if type(source.data_revision) is not int or source.data_revision < 0:
            raise ArrowPublicationError("derived source revision must be a nonnegative integer")
        if any(
            type(v) is not str or not v
            for v in (
                operation_id,
                projection_id,
                source.capture_id,
                source.release_id,
                source.realization_id,
            )
        ):
            raise ArrowPublicationError(
                "derived publication requires operation, projection and snapshot identity"
            )
        object.__setattr__(self, "transport", transport)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "operation_id", operation_id)
        object.__setattr__(self, "projection_id", projection_id)
        resolved = contract_id or ("accepted" if projection_id == "accepted" else "candidate")
        if (operation_id, resolved) not in {
            ("evaluate", "candidate"),
            ("publish_inference", "accepted"),
        }:
            raise ArrowPublicationError("unsupported semantic derived operation/projection")
        if source.release_id != release_id:
            raise ArrowPublicationError("derived operation cannot cross releases")
        if resolved == "candidate":
            if (
                type(cut_id) is not int
                or cut_id < 1
                or not profile_digest
                or not projection_id.startswith("projection:")
                or source.realization_id == realization_id
            ):
                raise ArrowPublicationError(
                    "candidate publication requires bound cut/profile/projection "
                    "and distinct target"
                )
        elif (
            cut_id is not None
            or profile_digest is not None
            or source.realization_id != realization_id
            or projection_id != "accepted"
        ):
            raise ArrowPublicationError(
                "accepted inference requires exact same-realization projection"
            )
        object.__setattr__(self, "contract_id", resolved)
        object.__setattr__(self, "cut_id", cut_id)
        object.__setattr__(self, "profile_digest", profile_digest)

    @classmethod
    def from_transport(
        cls,
        transport: AppendPublication,
        *,
        source: SnapshotBinding,
        operation_id: str,
        projection_id: str,
        contract_id: str | None = None,
        cut_id: int | None = None,
        profile_digest: str | None = None,
    ) -> SnapshotDerivedPublication:
        """Compose actual owned buffers/content; never re-freeze or recanonicalize them."""
        result = object.__new__(cls)
        result._bind(
            transport,
            source=source,
            operation_id=operation_id,
            projection_id=projection_id,
            contract_id=contract_id,
            cut_id=cut_id,
            profile_digest=profile_digest,
        )
        return result

    @property
    def release_id(self) -> str:
        return self.transport.release_id

    @property
    def realization_id(self) -> str:
        return self.transport.realization_id

    @property
    def batch_id(self) -> str:
        return self.transport.batch_id

    @property
    def relations(self) -> Mapping[str, pa.Table]:
        return self.transport.relations

    @property
    def content(self) -> bytes:
        return self.transport.content

    @classmethod
    def from_rows(
        cls,
        batch: PublicationBatch,
        *,
        source: SnapshotBinding,
        operation_id: str,
        projection_id: str,
        contract_id: str | None = None,
        cut_id: int | None = None,
        profile_digest: str | None = None,
    ) -> SnapshotDerivedPublication:
        append = AppendPublication.from_rows(batch)
        return cls.from_transport(
            append,
            source=source,
            operation_id=operation_id,
            projection_id=projection_id,
            contract_id=contract_id,
            cut_id=cut_id,
            profile_digest=profile_digest,
        )


# Existing name denotes append transport only; omission can no longer select derived intent.
ArrowPublicationBatch = AppendPublication


def stage_arrow(
    connection: Connection,
    batch: AppendPublication | SnapshotDerivedPublication,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> None:
    from ._operation_calls import begin_stage

    begin_stage(connection)
    owned = batch.transport if isinstance(batch, SnapshotDerivedPublication) else batch
    for name, relation in batch.relations.items():
        try:
            copy_arrow_stream(
                connection,
                owned._write_profiles[name],
                target=("pg_temp", "sp_" + name),
                batches=relation.to_batches(),
                cancellation=cancellation,
            )
        except ArrowTransferError as exc:
            raise ArrowPublicationError(str(exc)) from exc


def publish_arrow_on_connection(
    connection: Connection,
    batch: AppendPublication | SnapshotDerivedPublication,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> PublicationReceipt:
    """Stage and publish without committing the SQLAlchemy-owned transaction."""
    from .contracts import require_database_operation

    require_database_operation(connection, batch.release_id, "publish_arrow")
    if isinstance(batch, SnapshotDerivedPublication):
        require_database_operation(connection, batch.source.release_id, batch.operation_id)
    if cancellation is None:
        stage_arrow(connection, batch)
    else:
        stage_arrow(connection, batch, cancellation=cancellation)
    from ._operation_calls import publish_batch, publish_derived_batch
    from ._operation_ids import CutId, RealizationId, ReleaseId

    try:
        if isinstance(batch, SnapshotDerivedPublication):
            revision = publish_derived_batch(
                connection,
                release_id=ReleaseId(batch.release_id),
                realization_id=RealizationId(batch.realization_id),
                batch_id=batch.batch_id,
                content=batch.content,
                source_release_id=ReleaseId(batch.source.release_id),
                source_realization_id=RealizationId(batch.source.realization_id),
                source_revision=batch.source.data_revision,
                source_capture_id=batch.source.capture_id,
                operation=batch.operation_id,
                projection=batch.projection_id,
                contract_id=batch.contract_id,
                cut_id=CutId(batch.cut_id) if batch.cut_id is not None else None,
                profile_digest=batch.profile_digest,
            )
        else:
            revision = publish_batch(
                connection,
                release_id=ReleaseId(batch.release_id),
                realization_id=RealizationId(batch.realization_id),
                batch_id=batch.batch_id,
                content=batch.content,
            )
    except Exception as exc:
        if getattr(getattr(exc, "orig", exc), "sqlstate", None) == "P0004":
            raise StaleAnalysisError(
                "analysis source revision changed; recompute outside publication"
            ) from exc
        raise
    return PublicationReceipt(batch.batch_id, revision, sha256(batch.content).hexdigest())


def publish_arrow(
    engine: Engine,
    batch: AppendPublication | SnapshotDerivedPublication,
    *,
    attempts: int = 3,
    cancellation: BorrowerCancellation | None = None,
) -> PublicationReceipt:
    if cancellation is None:
        return _publish(engine, batch, publish_arrow_on_connection, attempts=attempts)

    def publish(connection: Connection, candidate):
        return publish_arrow_on_connection(connection, candidate, cancellation=cancellation)

    return _publish(engine, batch, publish, attempts=attempts, cancellation=cancellation)
