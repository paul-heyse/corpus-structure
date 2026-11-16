"""Batch-independent content, detached files and borrowed backing lifetimes."""

from decimal import Decimal

import pyarrow as pa
import pytest

from corpus_structure.semantic.capture_storage import (
    CaptureOwner,
    FileRelation,
    LogicalRows,
    store_relation,
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


def test_spooled_empty_schema_file_integrity_and_lease(tmp_path):
    owner = CaptureOwner(tmp_path)
    schema = pa.schema([pa.field("id", pa.string())], metadata={b"identity": b"bound"})
    relation, _descriptor = store_relation(owner, "empty", schema, [], ("id",), [0], 100)
    assert isinstance(relation, FileRelation)
    relation.verify()
    assert relation.num_rows == 0 and relation.schema.equals(schema, check_metadata=True)
    owner.acquire()
    owner.close()
    assert relation.path.exists()
    with pytest.raises(RuntimeError, match="closed"):
        owner.acquire()
    owner.release()
    assert not relation.path.exists()


def test_resident_limit_refuses_and_corrupt_file_refuses(tmp_path):
    table = pa.table({"id": ["a", "b"]})
    with pytest.raises(ValueError, match="spooled"):
        store_relation(None, "rows", table.schema, table.to_batches(), ("id",), [0], 1)
    owner = CaptureOwner(tmp_path)
    relation, _ = store_relation(owner, "rows", table.schema, table.to_batches(), ("id",), [0], 1)
    assert isinstance(relation, FileRelation)
    relation.path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        relation.verify()
    owner.close()


def test_writer_cleanup_preserves_cancellation(monkeypatch, tmp_path):
    from corpus_structure.semantic import capture_storage

    class BrokenWriter:
        def __init__(self, *args, **kwargs):
            pass

        def write_batch(self, batch):
            raise KeyboardInterrupt("write cancelled")

        def close(self):
            raise ValueError("cleanup failed")

    monkeypatch.setattr(capture_storage.pq, "ParquetWriter", BrokenWriter)
    owner = CaptureOwner(tmp_path)
    rows = pa.table({"id": ["a"]})
    try:
        with pytest.raises(KeyboardInterrupt, match="write cancelled") as failure:
            store_relation(owner, "rows", rows.schema, rows.to_batches(), ("id",), [0], 1)
        assert any("cleanup failed" in note for note in failure.value.__notes__)
    finally:
        owner.close()
