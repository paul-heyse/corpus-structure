"""Owned detached capture storage and batch-independent logical content encoding."""

from __future__ import annotations

import base64
from hashlib import sha256
from itertools import repeat

import pyarrow as pa

from .identity import canonical_bytes


def _column_values(column: pa.Array):
    """Normalize one typed column without constructing an Arrow scalar per cell."""
    kind = column.type
    if pa.types.is_dictionary(kind):
        return _column_values(column.dictionary_decode())
    if (
        pa.types.is_timestamp(kind)
        or pa.types.is_date(kind)
        or pa.types.is_time(kind)
        or pa.types.is_duration(kind)
    ):
        integer = pa.int32() if kind.bit_width == 32 else pa.int64()
        return [None if value is None else [str(kind), value] for value in column.view(integer).to_pylist()]
    values = column.to_pylist()
    if pa.types.is_decimal(kind):
        return [
            None if value is None else ["decimal", value.as_tuple().sign, list(value.as_tuple().digits), value.as_tuple().exponent]
            for value in values
        ]
    if pa.types.is_floating(kind):
        return [None if value is None else ["float", value.hex()] for value in values]
    if pa.types.is_binary(kind) or pa.types.is_large_binary(kind) or pa.types.is_fixed_size_binary(kind):
        return [None if value is None else ["binary", base64.b64encode(value).decode("ascii")] for value in values]
    return values


class LogicalRows:
    """Length-framed typed rows; neither chunk boundaries nor file codecs enter identity."""

    def __init__(self, schema: pa.Schema, keys: tuple[str, ...] = ()):
        self._hash = sha256()
        self._key_indices = tuple(schema.get_field_index(name) for name in keys)
        if any(index < 0 for index in self._key_indices):
            raise ValueError("capture primary-key column is absent")
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
        columns = tuple(_column_values(column) for column in batch.columns)
        keys = tuple(batch.column(index).to_pylist() for index in self._key_indices)
        rows = zip(*columns, strict=True) if columns else repeat((), batch.num_rows)
        for index, row in enumerate(rows):
            if keys:
                key = tuple(column[index] for column in keys)
                if self._previous is not None and key <= self._previous:
                    raise ValueError("capture rows are not in unique primary-key order")
                self._previous = key
            self._update(list(row))
        self.rows += batch.num_rows

    @property
    def digest(self) -> str:
        return self._hash.hexdigest()
