"""Batch-independent content, detached files and borrowed backing lifetimes."""

from decimal import Decimal

import pyarrow as pa

from corpus_structure.semantic.capture_storage import (
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


def test_column_conversion_matches_independent_mixed_type_rows_and_key_boundaries():
    import base64
    from hashlib import sha256

    import pytest

    from corpus_structure.semantic.identity import canonical_bytes

    table = pa.table(
        {
            "id": ["a", "b"],
            "binary": pa.array([b"\x00\xff", None]),
            "float": pa.array([-0.0, 1e-20]),
            "decimal": pa.array([Decimal("-1.2300"), None], type=pa.decimal256(40, 4)),
            "timestamp": pa.array([1680000000000000001, None], type=pa.timestamp("ns", tz="UTC")),
            "day": pa.array([1, None], type=pa.date32()),
            "dictionary": pa.array(["é", "x"]).dictionary_encode(),
        }
    )
    header = ["canonical-rows-1", base64.b64encode(table.schema.serialize().to_pybytes()).decode()]
    expected = [
        [
            "a",
            ["binary", "AP8="],
            ["float", "-0x0.0p+0"],
            ["decimal", 1, [1, 2, 3, 0, 0], -4],
            ["timestamp[ns, tz=UTC]", 1680000000000000001],
            ["date32[day]", 1],
            "é",
        ],
        ["b", None, ["float", 1e-20.hex()], None, None, None, "x"],
    ]
    digest = sha256()
    for row in [header, *expected]:
        payload = canonical_bytes(row)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    for chunksize in (1, 2):
        logical = LogicalRows(table.schema, ("id",))
        for batch in table.to_batches(max_chunksize=chunksize):
            logical.write(batch)
        assert logical.digest == digest.hexdigest() and logical.rows == 2
        with pytest.raises(ValueError, match="unique primary-key order"):
            logical.write(table.to_batches()[0])


def test_column_preparation_bounds_wide_batches_and_keeps_oversized_rows(monkeypatch):
    from corpus_structure.semantic import capture_storage

    sizes = []
    original = capture_storage._column_values

    def prepare(column):
        sizes.append(column.nbytes)
        return original(column)

    monkeypatch.setattr(capture_storage, "_column_values", prepare)
    table = pa.table({"text": ["x" * (1024**2)] * 10})
    actual = LogicalRows(table.schema)
    actual.write(table.to_batches()[0])
    assert actual.rows == 10 and max(sizes) <= 4 * 1024**2
    expected = LogicalRows(table.schema)
    for batch in table.to_batches(max_chunksize=1):
        expected.write(batch)
    assert actual.digest == expected.digest
    large = pa.record_batch({"text": ["y" * (5 * 1024**2)]})
    oversized = LogicalRows(large.schema)
    oversized.write(large)
    assert oversized.rows == 1
