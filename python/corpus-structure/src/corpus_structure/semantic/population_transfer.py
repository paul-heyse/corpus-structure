"""Directional upload shape for privately prepared population item intake.

The caller owns intake authentication and transaction lifetime. Native admission
supplies the attempt and derives addresses and rule projections from canonical items.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyarrow as pa
from sqlalchemy import Integer, MetaData, Text
from sqlalchemy.dialects.postgresql import dialect

from .arrow_transfer import ArrowWriteProfile
from .arrow_types import sql_arrow_type
from .data_operation_partitions import PartitionCommitment
from .metadata import get_metadata

if TYPE_CHECKING:
    from ._data_operation_wire import WireProductPopulationManifest

_ITEM_RELATION = "ops.data_retained_population_item"
POPULATION_UPLOAD_SCRATCH = "ddo_population_upload"
POPULATION_UPLOAD_FIELDS = (
    "output_role",
    "output_position",
    "collection",
    "partition_key",
    "item_ordinal",
    "canonical_text",
)


@dataclass(frozen=True, slots=True)
class PopulationUploadPartition:
    commitment: PartitionCommitment
    group_digests: dict[str, str]
    items: pa.Table

    def __post_init__(self):
        if self.items.column_names != ["item_ordinal", "canonical_text"]:
            raise ValueError("population upload differs from the canonical item relation")
        if self.items.num_rows != self.commitment.item_count:
            raise ValueError("population upload count differs from its commitment")

    def manifest(self) -> WireProductPopulationManifest:
        partition = self.commitment
        return {
            "collection": partition.collection,
            "partition_key": partition.key,
            "ordinal": partition.ordinal,
            "placement": {"start": partition.start, "end": partition.end},
            "partition_digest": partition.digest,
            "item_count": partition.item_count,
            "group_digests": self.group_digests,
        }


def population_upload_batches(
    profile: ArrowWriteProfile,
    outputs: Iterable[tuple[str, int, PopulationUploadPartition]],
) -> Iterator[pa.RecordBatch]:
    """Add output and partition coordinates without expanding typed items into rows."""
    fields = list(profile.schema)
    item_schema = pa.schema(fields[4:])
    for role, position, partition in outputs:
        coordinates = (role, position, partition.commitment.collection, partition.commitment.key)
        items = partition.items.cast(item_schema)
        for batch in items.to_batches(max_chunksize=4096):
            columns = [
                pa.repeat(pa.scalar(value, type=field.type), batch.num_rows)
                for field, value in zip(fields[:4], coordinates, strict=True)
            ]
            yield pa.RecordBatch.from_arrays([*columns, *batch.columns], schema=profile.schema)


def write_population_upload(profile: ArrowWriteProfile, batches, *, max_bytes: int) -> bytes:
    """Encode the admitted upload once for durable draft custody."""
    with pa.BufferOutputStream() as sink:
        with pa.ipc.new_stream(sink, profile.schema) as writer:
            for batch in batches:
                profile.validate_batch(batch)
                writer.write_batch(batch)
                if sink.tell() > max_bytes:
                    raise ValueError("population upload exceeds the draft byte limit")
        if sink.tell() > max_bytes:
            raise ValueError("population upload exceeds the draft byte limit")
        return sink.getvalue().to_pybytes()


def population_item_write_profile(
    *, release_id: str, model: MetaData | None = None
) -> ArrowWriteProfile:
    """Prepare only submitted item values against their compiled physical columns.

    The native preparation call binds the upload to its actual context. This profile
    accepts no claim, intent, product identity or caller-provided projection evidence.
    Each transfer creates its own pgpq encoder through the shared write profile.
    """
    selected = get_metadata() if model is None else model
    relation = selected.tables[_ITEM_RELATION]
    fields = []
    wire_types = []
    for name in POPULATION_UPLOAD_FIELDS:
        column = relation.c[name]
        if not isinstance(column.type, (Text, Integer)):
            raise ValueError(f"unsupported population upload field {column}: {column.type}")
        wire = column.type.compile(dialect=dialect()).lower()
        fields.append(pa.field(column.name, sql_arrow_type(column.type), nullable=column.nullable))
        wire_types.append(wire)
    schema = pa.schema(
        fields,
        metadata={
            "source_relation": _ITEM_RELATION,
            "physical_model_id": selected.info["physical_model_id"],
            "release_id": release_id,
        },
    )
    return ArrowWriteProfile.prepare(
        release_id=release_id,
        physical_id=selected.info["physical_model_id"],
        operation="private-population-items",
        schema=schema,
        wire_types=wire_types,
    )
