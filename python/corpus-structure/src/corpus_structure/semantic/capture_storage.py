"""Owned detached capture storage and batch-independent logical content encoding."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal
from hashlib import file_digest, sha256
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .identity import canonical_bytes


def _scalar(value: pa.Scalar):
    if not value.is_valid:
        return None
    kind = value.type
    if (
        pa.types.is_timestamp(kind)
        or pa.types.is_date(kind)
        or pa.types.is_time(kind)
        or pa.types.is_duration(kind)
    ):
        return [str(kind), value.value]
    data = value.as_py()
    if isinstance(data, Decimal):
        parts = data.as_tuple()
        return ["decimal", parts.sign, list(parts.digits), parts.exponent]
    if isinstance(data, float):
        return ["float", data.hex()]
    if isinstance(data, bytes):
        return ["binary", base64.b64encode(data).decode("ascii")]
    return data


class LogicalRows:
    """Length-framed typed rows; neither chunk boundaries nor file codecs enter identity."""

    def __init__(self, schema: pa.Schema, keys: tuple[str, ...] = ()):
        self._hash = sha256()
        self._keys = keys
        self._previous = None
        self.rows = 0
        self._update(
            [
                "canonical-rows-1",
                base64.b64encode(schema.remove_metadata().serialize().to_pybytes()).decode("ascii"),
            ]
        )

    def _update(self, value):
        data = canonical_bytes(value)
        self._hash.update(len(data).to_bytes(8, "big"))
        self._hash.update(data)

    def write(self, batch: pa.RecordBatch) -> None:
        for index in range(batch.num_rows):
            if self._keys:
                key = tuple(
                    batch.column(batch.schema.get_field_index(name))[index].as_py()
                    for name in self._keys
                )
                if self._previous is not None and key <= self._previous:
                    raise ValueError("capture rows are not in unique primary-key order")
                self._previous = key
            self._update([_scalar(column[index]) for column in batch.columns])
        self.rows += batch.num_rows

    @property
    def digest(self) -> str:
        return self._hash.hexdigest()


@dataclass(frozen=True)
class FileRelation:
    path: Path
    schema: pa.Schema
    num_rows: int
    sha256: str
    logical_digest: str

    def iter_batches(self, batch_size=65536):
        yield from pq.ParquetFile(self.path).iter_batches(batch_size=batch_size)

    def verify(self) -> None:
        with self.path.open("rb") as source:
            digest = file_digest(source, "sha256").hexdigest()
        if digest != self.sha256:
            raise ValueError("captured file integrity differs")
        metadata = pq.ParquetFile(self.path)
        if metadata.metadata.num_rows != self.num_rows or not metadata.schema_arrow.equals(
            self.schema, check_metadata=True
        ):
            raise ValueError("captured file integrity/schema differs")
