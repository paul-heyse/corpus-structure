"""Batch-independent content, detached files and borrowed backing lifetimes."""

from decimal import Decimal

import pyarrow as pa
import pytest

from corpus_structure.semantic.capture_storage import (
    FileRelation,
    LogicalRows,
)


def test_logical_digest_preserves_float_sign_decimal_and_nanosecond_without_batch_identity():
    table = pa.table(
        {
            "id": ["a", "b"],
            "f": [0.0, -0.0],
            "d": pa.array([Decimal("1.00"), Decimal("2.00")], type=pa.decimal128(10, 2)),
            "t": pa.array([1, 2], type=pa.timestamp("ns", tz="UTC")),
        }
    )
    whole = LogicalRows(table.schema, ("id",))
    split = LogicalRows(table.schema, ("id",))
    for batch in table.to_batches():
        whole.write(batch)
    for batch in table.to_batches(max_chunksize=1):
        split.write(batch)
    assert whole.digest == split.digest
    changed = table.set_column(1, "f", pa.array([0.0, 0.0]))
    other = LogicalRows(changed.schema, ("id",))
    for batch in changed.to_batches():
        other.write(batch)
    assert whole.digest != other.digest


def test_detached_empty_file_keeps_exact_schema_and_refuses_corrupt_bytes(tmp_path):
    from hashlib import file_digest

    import pyarrow.parquet as pq

    schema = pa.schema([pa.field("id", pa.string())], metadata={b"identity": b"bound"})
    path = tmp_path / "empty.parquet"
    pq.write_table(pa.Table.from_batches([], schema=schema), path, store_schema=True)
    with path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    logical = LogicalRows(schema)
    relation = FileRelation(path, schema, 0, digest, logical.digest)
    relation.verify()
    assert relation.num_rows == 0 and relation.schema.equals(schema, check_metadata=True)
    assert list(relation.iter_batches()) == []
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        relation.verify()
