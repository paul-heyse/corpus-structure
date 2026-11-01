"""Independent binary expectations for exact directional profile encoding."""

import struct
from dataclasses import replace
from decimal import Decimal

import pyarrow as pa
import pytest

from corpus_structure.semantic.arrow_transfer import ArrowTransferError, ArrowWriteProfile
from corpus_structure.semantic.pdf_record_model import record_write_profile


def profile(schema, types):
    return ArrowWriteProfile.prepare(
        release_id="r", physical_id="p", operation="test", schema=schema, wire_types=types
    )


def encoded_rows(prepared, batches):
    encoder = prepared.new_encoder()
    body = encoder.write_header()
    for batch in batches:
        prepared.validate_batch(batch)
        body += encoder.write_batch(batch)
    body += encoder.finish()
    assert body[:19] == b"PGCOPY\n\xff\r\n\0" + b"\0" * 8
    offset = 19
    rows = []
    while True:
        count = struct.unpack_from("!h", body, offset)[0]
        offset += 2
        if count == -1:
            break
        row = []
        for _ in range(count):
            size = struct.unpack_from("!i", body, offset)[0]
            offset += 4
            row.append(None if size == -1 else body[offset : offset + size])
            offset += max(size, 0)
        rows.append(row)
    assert offset == len(body)
    return rows


@pytest.mark.parametrize("kind", [pa.string(), pa.large_string(), pa.string_view()])
def test_json_null_and_sql_null_are_distinct_and_large_values_remain_exact(kind):
    schema = pa.schema([pa.field("value", kind)])
    prepared = profile(schema, ["jsonb"])
    large = '"' + "x" * (2 * 1024 * 1024) + '"'
    batch = pa.RecordBatch.from_arrays([pa.array([None, "null", large], type=kind)], schema=schema)
    assert encoded_rows(prepared, [batch]) == [[None], [b"\x01null"], [b"\x01" + large.encode()]]
    # No mutable encoder state survives successful or empty streams.
    assert encoded_rows(prepared, []) == []
    assert encoded_rows(prepared, [batch.slice(0, 0), batch.slice(0, 1)]) == [[None]]


def test_decimal128_extremes_have_independent_postgresql_numeric_digits():
    schema = pa.schema([pa.field("value", pa.decimal128(38, 4))])
    batch = pa.RecordBatch.from_pylist(
        [
            {"value": Decimal("-9999999999999999999999999999999999.9999")},
            {"value": Decimal("0.0001")},
        ],
        schema=schema,
    )
    rows = encoded_rows(profile(schema, ["numeric"]), [batch])
    assert rows == [
        [struct.pack("!hhhh", 10, 8, 0x4000, 4) + struct.pack("!10h", 99, *([9999] * 9))],
        [struct.pack("!hhhhh", 1, -1, 0, 4, 1)],
    ]


def test_exact_order_metadata_and_wire_profile_are_independent_checks():
    schema = pa.schema(
        [
            pa.field("left", pa.string(), metadata={"meaning": "identity"}),
            pa.field("right", pa.string()),
        ],
        metadata={"profile": "one"},
    )
    prepared = profile(schema, ["text", "text"])
    batch = pa.RecordBatch.from_pylist([{"left": "a", "right": "b"}], schema=schema)
    prepared.validate_batch(batch)
    for wrong in (
        batch.select([1, 0]),
        batch.replace_schema_metadata({"profile": "two"}),
        batch.replace_schema_metadata(None),
        pa.RecordBatch.from_arrays(
            batch.columns,
            schema=schema.set(0, schema.field(0).with_metadata({"meaning": "other"})),
        ),
    ):
        with pytest.raises(ArrowTransferError, match="wire schema"):
            prepared.validate_batch(wrong)
    with pytest.raises(ArrowTransferError, match="pgpq wire schema"):
        profile(pa.schema([pa.field("v", pa.int64())]), ["text"]).new_encoder()
    assert prepared.identity != replace(prepared, release_id="other").identity
    assert prepared.identity != replace(prepared, physical_id="other").identity
    changed = replace(prepared, schema=schema.with_metadata({"profile": "two"}))
    assert prepared.identity != changed.identity


def test_private_profile_preserves_model_metadata_nullability_and_fresh_encoders():
    prepared = record_write_profile("ops.pdf_stage_native", release_id="r")
    assert prepared.schema.metadata[b"relation"] == b"ops.pdf_stage_native"
    assert prepared.schema.field("record_id").nullable is False
    assert prepared.schema.field("native_address_stream_id").nullable is True
    # pgpq's native state machine would reject a second header on the same encoder.
    for _ in range(2):
        encoder = prepared.new_encoder()
        encoder.write_header()
        encoder.finish()


def test_publication_freeze_refuses_later_batch_metadata_before_table_normalization():
    from corpus_structure.semantic.arrow_publication import (
        AppendPublication,
        ArrowPublicationError,
        stage_schema,
    )

    schema = stage_schema("entity")
    first = pa.RecordBatch.from_pylist([{"entity_id": "one"}], schema=schema)
    second = first.replace_schema_metadata({"meaning": "different"})
    with pytest.raises(ArrowPublicationError, match="batch schema/metadata"):
        AppendPublication("r", "z", "b", {"entity": (first, second)})


def test_unselected_nanosecond_truncation_cannot_enter_inferred_write_profile():
    with pytest.raises(ArrowTransferError, match="explicit exact write normalization"):
        profile(pa.schema([pa.field("time", pa.timestamp("ns"))]), ["timestamp"])
