"""The boundary between persisted producer values and authorized physical COPY rows."""

from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.compute as pc

if TYPE_CHECKING:
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef


_PHYSICAL_COLUMNS = frozenset(("product_id", "revision_id", "release_id"))


@dataclass(frozen=True, slots=True)
class PdfReplayBinding:
    build_id: str
    release_id: str

    def value(self, name: str) -> str:
        return self.release_id if name == "release_id" else self.build_id


def replay_schema(copy_schema: pa.Schema) -> pa.Schema:
    metadata = dict(copy_schema.metadata or {})
    metadata.pop(b"physical_model_id", None)
    metadata[b"replay_profile"] = b"pdf-replay-v2"
    return pa.schema(
        [field for field in copy_schema if field.name not in _PHYSICAL_COLUMNS],
        metadata=metadata,
    )


def read_replay_batches(
    replay: PdfReplayRef,
    copy_schema: pa.Schema,
    *,
    check_active: Callable[[], None],
    legacy_binding: PdfReplayBinding | None = None,
    legacy_schema: pa.Schema | None = None,
) -> Generator[pa.RecordBatch]:
    """Verify one bounded IPC packet and keep its exact buffers through consumption."""
    check_active()
    schema = replay_schema(copy_schema)
    with pa.BufferReader(replay.read_bytes()) as source:
        reader = pa.ipc.open_file(source, options=pa.ipc.IpcReadOptions(use_threads=False))
        legacy = not reader.schema.equals(schema, check_metadata=True)
        original = copy_schema if legacy_schema is None else legacy_schema
        if legacy and (
            legacy_binding is None
            or not reader.schema.equals(original, check_metadata=True)
            or not replay_schema(original).equals(schema, check_metadata=True)
        ):
            raise ValueError("PDF replay differs from its captured transport schema")
        rows = 0
        for ordinal in range(reader.num_record_batches):
            check_active()
            batch = reader.get_batch(ordinal)
            batch.validate(full=True)
            rows += batch.num_rows
            if legacy_binding is not None and legacy:
                for name in _PHYSICAL_COLUMNS.intersection(copy_schema.names):
                    column = batch.column(name)
                    if len(column) and (
                        column.null_count
                        or not pc.call_function(
                            "all",
                            [
                                pc.call_function(
                                    "equal", [column, pa.scalar(legacy_binding.value(name))]
                                )
                            ],
                        ).as_py()
                    ):
                        raise ValueError("original PDF replay has a foreign physical carrier")
                batch = pa.RecordBatch.from_arrays(
                    [batch.column(name) for name in schema.names], schema=schema
                )
            yield batch
        if rows != replay.rows:
            raise ValueError("PDF replay row count differs from its receipt")


def bind_copy_batch(
    batch: pa.RecordBatch, copy_schema: pa.Schema, binding: PdfReplayBinding
) -> pa.RecordBatch:
    """Supply current physical ownership after the build's native stage guard."""
    if batch.schema.equals(copy_schema, check_metadata=True):
        # Independent native stage callers can still supply already bound rows.
        return batch
    if not batch.schema.equals(replay_schema(copy_schema), check_metadata=True):
        raise ValueError("PDF replay differs from the authorized COPY schema")
    return pa.RecordBatch.from_arrays(
        [
            pa.repeat(pa.scalar(binding.value(field.name), type=field.type), batch.num_rows)
            if field.name in _PHYSICAL_COLUMNS
            else batch.column(field.name)
            for field in copy_schema
        ],
        schema=copy_schema,
    )
